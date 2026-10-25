#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::{io::{BufRead, BufReader, Write}, path::PathBuf, process::{Child, ChildStdin, Command, Stdio}, sync::Mutex, thread, time::Duration};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use tauri::{AppHandle, Emitter, Manager, State};

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct ManagedAgent { child: Child, input: ChildStdin }
struct AgentProcess(Mutex<Option<ManagedAgent>>);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct AgentStatus { running: bool, service_running: bool }

fn agent_runtime(app: &AppHandle) -> Result<(PathBuf, bool), String> {
    if let Ok(resources) = app.path().resource_dir() {
        let bundled = resources.join("agent").join("lockstep-agent.exe");
        if bundled.exists() {
            return Ok((bundled, true));
        }
    }

    let development = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("main.py");
    if development.exists() {
        return Ok((development, false));
    }

    Err("Der Lockstep-Agent fehlt. Bitte installiere das vollständige Setup erneut.".into())
}

#[tauri::command]
fn start_agent(app: AppHandle, state: State<'_, AgentProcess>, agent_id: String, agent_name: String, region: String, map_rules: String, discord_webhook: Option<String>) -> Result<(), String> {
    let mut process = state.0.lock().map_err(|e| e.to_string())?;
    if process.is_some() { return Err("Der Agent läuft bereits.".into()); }

    let (runtime, bundled) = agent_runtime(&app)?;
    let candidates: Vec<(&str, Vec<&str>)> = if bundled {
        vec![(runtime.to_str().ok_or("Ungültiger Pfad zum Lockstep-Agent.")?, vec![])]
    } else if cfg!(windows) {
        vec![("py", vec!["-3"]), ("python", vec![])]
    } else {
        vec![("python3", vec![])]
    };

    let mut started = None;
    let mut last_spawn_error = None;
    for (program, prefix_args) in candidates {
        let mut command = Command::new(program);
        command.args(prefix_args);
        if !bundled {
            command.arg(&runtime);
        }
        if let Some(webhook) = discord_webhook.as_ref().filter(|url| !url.trim().is_empty()) {
            command.env("LOCKSTEP_DISCORD_WEBHOOK", webhook);
        }
        #[cfg(windows)]
        command.creation_flags(CREATE_NO_WINDOW);
        match command
            .arg("--agent-id").arg(&agent_id)
            .arg("--agent-name").arg(&agent_name)
            .arg("--region").arg(&region)
            .arg("--rules").arg(&map_rules)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
        {
            Ok(child) => {
                started = Some(child);
                break;
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => last_spawn_error = Some(error),
            Err(error) => return Err(format!("Lockstep-Agent konnte nicht gestartet werden: {error}")),
        }
    }
    let mut child = started.ok_or_else(|| {
        if bundled {
            format!("Lockstep-Agent konnte nicht gestartet werden: {}", last_spawn_error.map(|e| e.to_string()).unwrap_or_else(|| "Datei nicht gefunden".into()))
        } else {
            "Python 3 wurde nicht gefunden. Installiere Python 3 oder verwende das vollständige Lockstep-Setup.".into()
        }
    })?;

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    let input = child.stdin.take().ok_or("Eingabekanal zum Lockstep-Agent fehlt.")?;
    *process = Some(ManagedAgent { child, input });
    drop(process);

    if let Some(pipe) = stdout { read_output(app.clone(), pipe, false); }
    if let Some(pipe) = stderr { read_output(app.clone(), pipe, true); }

    let app_for_monitor = app.clone();
    thread::spawn(move || loop {
        thread::sleep(Duration::from_millis(400));
        let Some(state) = app_for_monitor.try_state::<AgentProcess>() else { break };
        let Ok(mut process) = state.0.lock() else { break };
        let Some(agent) = process.as_mut() else { break };
        match agent.child.try_wait() {
            Ok(Some(status)) => {
                *process = None;
                let message = if status.success() { "Agent beendet.".to_string() } else { format!("Agent beendet mit Status {status}.") };
                let _ = app_for_monitor.emit("agent-log", message);
                let _ = app_for_monitor.emit("agent-status", AgentStatus { running: false, service_running: false });
                break;
            }
            Err(error) => {
                *process = None;
                let _ = app_for_monitor.emit("agent-log", format!("Prozessfehler: {error}"));
                let _ = app_for_monitor.emit("agent-status", AgentStatus { running: false, service_running: false });
                break;
            }
            _ => {}
        }
    });
    let _ = app.emit("agent-status", AgentStatus { running: false, service_running: true });
    Ok(())
}

#[tauri::command]
fn set_auto_lock(app: AppHandle, state: State<'_, AgentProcess>, enabled: bool, agent_id: String, agent_name: String, map_rules: String, discord_webhook: Option<String>) -> Result<(), String> {
    let mut process = state.0.lock().map_err(|e| e.to_string())?;
    let agent = process.as_mut().ok_or("Der Tracking-Dienst ist noch nicht gestartet.")?;
    let command = serde_json::json!({
        "type": "auto_lock",
        "enabled": enabled,
        "agentId": agent_id,
        "agentName": agent_name,
        "mapRules": map_rules,
        "discordWebhook": discord_webhook.unwrap_or_default(),
    });
    writeln!(agent.input, "{command}").map_err(|error| format!("Auto-Lock konnte nicht aktualisiert werden: {error}"))?;
    agent.input.flush().map_err(|error| format!("Auto-Lock-Befehl konnte nicht gesendet werden: {error}"))?;
    let _ = app.emit("agent-status", AgentStatus { running: enabled, service_running: true });
    Ok(())
}

#[tauri::command]
fn update_agent_config(state: State<'_, AgentProcess>, agent_id: String, agent_name: String, map_rules: String, discord_webhook: Option<String>) -> Result<(), String> {
    let mut process = state.0.lock().map_err(|e| e.to_string())?;
    let agent = process.as_mut().ok_or("Der Tracking-Dienst läuft noch nicht.")?;
    let command = serde_json::json!({
        "type": "configure",
        "agentId": agent_id,
        "agentName": agent_name,
        "mapRules": map_rules,
        "discordWebhook": discord_webhook.unwrap_or_default(),
    });
    writeln!(agent.input, "{command}").map_err(|error| format!("Konfiguration konnte nicht aktualisiert werden: {error}"))?;
    agent.input.flush().map_err(|error| format!("Konfiguration konnte nicht gesendet werden: {error}"))?;
    Ok(())
}

fn terminate_agent(agent: &mut ManagedAgent) {
    if agent.child.try_wait().ok().flatten().is_none() {
        #[cfg(windows)]
        {
            let pid = agent.child.id().to_string();
            let mut taskkill = Command::new("taskkill");
            taskkill.args(["/PID", &pid, "/T", "/F"]);
            taskkill.creation_flags(CREATE_NO_WINDOW);
            let tree_stopped = taskkill.status().map(|status| status.success()).unwrap_or(false);
            if !tree_stopped && agent.child.try_wait().ok().flatten().is_none() {
                let _ = agent.child.kill();
            }
        }
        #[cfg(not(windows))]
        {
            let _ = agent.child.kill();
        }
    }
    let _ = agent.child.wait();
}

fn read_output(app: AppHandle, pipe: impl std::io::Read + Send + 'static, is_error: bool) {
    thread::spawn(move || {
        for line in BufReader::new(pipe).lines().flatten() {
            if let Some(snapshot) = line.strip_prefix("TRACK:") {
                if let Ok(payload) = serde_json::from_str::<serde_json::Value>(snapshot) {
                    let _ = app.emit("agent-track", payload);
                    continue;
                }
            }
            let text = if is_error { format!("Fehler: {line}") } else { line };
            let _ = app.emit("agent-log", text);
        }
    });
}

#[tauri::command]
fn stop_agent(app: AppHandle, state: State<'_, AgentProcess>) -> Result<(), String> {
    let mut process = state.0.lock().map_err(|e| e.to_string())?;
    let mut agent = process.take();
    drop(process);

    if let Some(agent) = agent.as_mut() {
        terminate_agent(agent);
    }
    let _ = app.emit("agent-log", "Tracking-Dienst beendet.");
    let _ = app.emit("agent-status", AgentStatus { running: false, service_running: false });
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(AgentProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![start_agent, set_auto_lock, update_agent_config, stop_agent])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<AgentProcess>() {
                    if let Ok(mut process) = state.0.lock() {
                        if let Some(agent) = process.as_mut() {
                            terminate_agent(agent);
                        }
                        process.take();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Fehler beim Starten von Lockstep");
}
