import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { agents as fullAgentCatalog, maps as fullMapCatalog, type CatalogItem } from "./catalog";
import "./style.css";

type LogEntry = { time: string; text: string; kind: "normal" | "error" | "success" };
type PlayerSnapshot = { id?: string; name?: string; team?: string; agentId?: string; agentName?: string; rankTier?: number; accountLevel?: number; kills?: number | null; deaths?: number | null; assists?: number | null; score?: number | null };
type MapRule = { agentId: string; agentName: string; mapName: string };
type TrackSnapshot = { phase?: string; mapId?: string; mapName?: string; agentId?: string; agentName?: string; region?: string; players?: PlayerSnapshot[]; updatedAt?: number };
const app = document.querySelector<HTMLDivElement>("#app")!;
let running = false;
let entries: LogEntry[] = [];
const sage = fullAgentCatalog.find((agent) => agent.name === "Sage")!;
const agents: CatalogItem[] = fullAgentCatalog;
const maps: CatalogItem[] = fullMapCatalog;
let mapRules: Record<string, MapRule> = {};
try { mapRules = JSON.parse(localStorage.getItem("lockstep-map-rules") || "{}"); } catch { mapRules = {}; }

const regions = [
  ["eu", "Europa"], ["na", "Nordamerika"], ["ap", "Asien-Pazifik"],
  ["kr", "Korea"], ["br", "Brasilien"], ["latam", "Lateinamerika"],
];

const sortedAgents = [...agents].sort((a, b) => a.name.localeCompare(b.name, "de"));
const sortedMaps = [...maps].sort((a, b) => a.name.localeCompare(b.name, "de"));
const agentOptions = (selectedId: string) => sortedAgents
  .map((agent) => `<option value="${escapeHtml(agent.id)}" ${agent.id === selectedId ? "selected" : ""}>${escapeHtml(agent.name)}</option>`)
  .join("");
const mapOptions = sortedMaps
  .map((map) => `<option value="${escapeHtml(map.id)}">${escapeHtml(map.name)}</option>`)
  .join("");



app.innerHTML = `
  <div class="shell">
    <header class="topbar">
      <div class="brand" aria-label="Lockstep">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
        <span>lockstep</span>
      </div>
      <div class="top-meta"><button id="check-updates" class="text-button" type="button">Updates suchen</button><span class="divider"></span><span class="build-label">DESKTOP</span><span class="divider"></span><span>VALORANT</span></div>
    </header>

    <main>
      <section class="intro">
        <p class="eyebrow">PRE-MATCH CONTROL</p>
        <h1>Agent lock</h1>
        <p class="subtitle">Wähle deinen Agent und warte auf den nächsten Matchstart.</p>
      </section>

      <section class="control-panel" aria-labelledby="agent-heading">
        <div class="panel-heading">
          <div><p class="section-index">01 <span>/ SETUP</span></p><h2 id="agent-heading">Konfiguration</h2></div>
          <div class="connection"><span class="connection-light" id="connection-light"></span><span id="connection-label">Bereit</span></div>
        </div>
        <div class="fields">
          <label class="field agent-field">
            <span>Standardagent</span>
            <select id="agent-select">${agentOptions(sage.id)}</select>
          </label>
          <label class="field region-field">
            <span>Regio</span>
            <select id="region">${regions.map(([value, label]) => `<option value="${value}" ${value === "eu" ? "selected" : ""}>${label}</option>`).join("")}</select>
          </label>
        </div>
        <div class="map-rule-builder">
          <label class="field">
            <span>Map</span>
            <select id="rule-map"><option value="">Map wählen</option>${mapOptions}</select>
          </label>
          <label class="field">
            <span>Agent auf dieser Map</span>
            <select id="rule-agent">${agentOptions(sage.id)}</select>
          </label>
          <button id="save-rule" class="secondary-button" type="button">Map-Regel speichern</button>
        </div>
        <div id="map-rules" class="map-rules" aria-live="polite"></div>
        <div class="web-tools">
          <label class="field webhook-field"><span>Discord Webhook</span><input id="discord-webhook" type="url" autocomplete="off" spellcheck="false" placeholder="https://discord.com/api/webhooks/…"></label>
          <div class="lobby-link"><span>Live-Lobby im Browser</span><a href="http://127.0.0.1:47831/" target="_blank" rel="noreferrer">http://127.0.0.1:47831/</a><small>Nur auf diesem PC erreichbar, solange der Lock läuft.</small></div>
        </div>
        <div class="action-row">
          <div class="action-note"><span class="key-hint">${running ? "RUNNING" : "AUTO"}</span><span id="action-copy">${running ? "Suche nach einem Match" : "Sobald das Match startet, wird der Agent gewählt."}</span></div>
          <button id="toggle-agent" class="primary-button ${running ? "is-stop" : ""}" type="button">
            <span class="button-icon" aria-hidden="true">${running ? "■" : "▶"}</span><span>${running ? "Stoppen" : "Lock starten"}</span>
          </button>
        </div>
        <p class="compat-note">Die valclient-Dokumentation rät von automatischem Instalocking ab.</p>
      </section>

      <section class="live-panel" aria-labelledby="live-heading">
        <div class="live-heading">
          <div><p class="section-index">02 <span>/ MATCH TRACKER</span></p><h2 id="live-heading">Live tracking</h2></div>
          <div class="live-state"><i id="live-indicator"></i><span id="live-phase">Noch nicht verbunden</span></div>
        </div>
        <div class="live-data">
          <div class="live-item"><span>MAP</span><strong id="live-map">—</strong></div>
          <div class="live-item"><span>AGENT</span><strong id="live-agent">—</strong></div>
          <div class="live-item"><span>REGION</span><strong id="live-region">—</strong></div>
          <div class="live-item"><span>LETZTES UPDATE</span><strong id="live-updated">—</strong></div>
        </div>
      </section>

      <section class="scoreboard" aria-labelledby="scoreboard-heading">
        <div class="activity-heading">
          <div><p class="section-index">03 <span>/ MATCH ROSTER</span></p><h2 id="scoreboard-heading">Spielerwerte</h2></div>
          <span id="roster-updated" class="roster-updated">Warte auf Match</span>
        </div>
        <div class="scoreboard-frame" id="scoreboard-frame">
          <div class="empty-state"><span class="empty-mark">—</span><span>Spieler und Rang erscheinen, sobald das Match verfügbar ist.</span></div>
        </div>
        <p class="stats-note">K/D/A und Score werden nach dem Match im Spielbericht verfügbar.</p>
      </section>

      <section class="activity" aria-labelledby="activity-heading">
        <div class="activity-heading">
          <div><p class="section-index">04 <span>/ LIVE OUTPUT</span></p><h2 id="activity-heading">Aktivität</h2></div>
          <button id="clear-log" class="text-button" type="button">Leeren</button>
        </div>
        <div class="log-window" id="log-window" role="log" aria-live="polite" aria-relevant="additions">
          <div class="empty-state" id="empty-state"><span class="empty-mark">—</span><span>Hier erscheinen Statusmeldungen des Agents.</span></div>
        </div>
        <div class="log-footer"><span><i class="footer-dot"></i><span id="footer-state">Warte auf Start</span></span><span id="log-count">0 Meldungen</span></div>
      </section>
    </main>

    <footer class="footnote"><span>LOCKSTEP <span class="foot-separator">/</span> LOKALER PROZESS</span><span>Agent im Setup enthalten.</span></footer>
  </div>`;

const agentSelect = document.querySelector<HTMLSelectElement>("#agent-select")!;
const regionSelect = document.querySelector<HTMLSelectElement>("#region")!;
const ruleMapSelect = document.querySelector<HTMLSelectElement>("#rule-map")!;
const ruleAgentSelect = document.querySelector<HTMLSelectElement>("#rule-agent")!;
const button = document.querySelector<HTMLButtonElement>("#toggle-agent")!;
const webhookInput = document.querySelector<HTMLInputElement>("#discord-webhook")!;
const updateButton = document.querySelector<HTMLButtonElement>("#check-updates")!;

updateButton.addEventListener("click", async () => {
  updateButton.disabled = true;
  updateButton.textContent = "Suche …";
  try {
    const result = await checkForUpdate(true);
    if (result === "current") {
      updateButton.textContent = "App ist aktuell";
    } else if (result === "declined") {
      updateButton.textContent = "Update bereit";
      return;
    }
  } catch (error) {
    addLog(`Update fehlgeschlagen: ${String(error)}`);
    updateButton.textContent = "Update fehlgeschlagen";
  } finally {
    updateButton.disabled = false;
    window.setTimeout(() => { updateButton.textContent = "Updates suchen"; }, 5000);
  }
});

async function checkForUpdate(askBeforeInstall: boolean): Promise<"current" | "declined" | "installing"> {
  const update = await check();
  if (!update) return "current";
  if (askBeforeInstall && !window.confirm(`Lockstep ${update.version} ist verfügbar. Jetzt installieren?`)) return "declined";
  addLog(`Installiere Lockstep ${update.version} …`);
  await update.downloadAndInstall();
  await relaunch();
  return "installing";
}

function renderLog() {
  const windowEl = document.querySelector<HTMLDivElement>("#log-window")!;
  if (!entries.length) {
    windowEl.innerHTML = `<div class="empty-state" id="empty-state"><span class="empty-mark">—</span><span>Hier erscheinen Statusmeldungen des Agents.</span></div>`;
  } else {
    windowEl.innerHTML = entries.map((entry) => `<div class="log-entry ${entry.kind}"><time>${entry.time}</time><span>${escapeHtml(entry.text)}</span></div>`).join("");
  }
  windowEl.scrollTop = windowEl.scrollHeight;
  document.querySelector("#log-count")!.textContent = `${entries.length} ${entries.length === 1 ? "Meldung" : "Meldungen"}`;
}

function escapeHtml(text: string) {
  return text.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]!);
}

function fillSelect(select: HTMLSelectElement, items: CatalogItem[], placeholder: string) {
  const oldValue = select.value;
  const sorted = [...items].sort((a, b) => a.name.localeCompare(b.name, "de"));
  select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>` + sorted
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("");
  if (sorted.some((item) => item.id === oldValue)) select.value = oldValue;
  else if (sorted.length) select.value = sorted[0].id;
}

function renderMapRules() {
  const list = document.querySelector<HTMLDivElement>("#map-rules")!;
  const rules = Object.entries(mapRules);
  if (!rules.length) {
    list.innerHTML = `<span class="rule-empty">Keine Map-Regeln gespeichert</span>`;
    return;
  }
  list.innerHTML = rules.map(([mapId, rule]) => {
    const mapName = maps.find((map) => map.id === mapId)?.name || rule.mapName;
    return `<div class="rule-chip"><span><strong>${escapeHtml(mapName)}</strong><small>${escapeHtml(rule.agentName)}</small></span><button type="button" data-remove-rule="${escapeHtml(mapId)}" aria-label="Regel für ${escapeHtml(mapName)} entfernen">Entfernen</button></div>`;
  }).join("");
}

function saveRules() {
  localStorage.setItem("lockstep-map-rules", JSON.stringify(mapRules));
  renderMapRules();
}

function rankName(tier: number | undefined) {
  const value = Number(tier || 0);
  if (value === 27) return "Radiant";
  const divisions = ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal"];
  if (value >= 3 && value <= 26) return `${divisions[Math.floor((value - 3) / 3)]} ${((value - 3) % 3) + 1}`;
  return "Unranked";
}

function renderPlayers(players: PlayerSnapshot[]) {
  const frame = document.querySelector<HTMLDivElement>("#scoreboard-frame")!;
  if (!players.length) {
    frame.innerHTML = `<div class="empty-state"><span class="empty-mark">—</span><span>Spieler und Rang erscheinen, sobald das Match verfügbar ist.</span></div>`;
    return;
  }
  frame.innerHTML = `<table class="roster-table"><thead><tr><th>Spieler</th><th>Team</th><th>Agent</th><th>Rang</th><th>K</th><th>T</th><th>A</th><th>Score</th></tr></thead><tbody>${players.map((player, index) => `
    <tr>
      <td class="player-name">${escapeHtml(player.name || `Spieler ${index + 1}`)}${player.accountLevel ? `<small>Lv. ${player.accountLevel}</small>` : ""}</td>
      <td><span class="team-name ${String(player.team).toLowerCase()}">${escapeHtml(teamLabel(player.team))}</span></td>
      <td>${escapeHtml(player.agentName || "—")}</td>
      <td><span class="rank-label">${escapeHtml(rankName(player.rankTier))}</span></td>
      <td>${displayStat(player.kills)}</td><td>${displayStat(player.deaths)}</td><td>${displayStat(player.assists)}</td><td>${displayStat(player.score)}</td>
    </tr>`).join("")}</tbody></table>`;
}

function displayStat(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : String(value);
}

function teamLabel(team: string | undefined) {
  const value = String(team || "");
  if (value.toLowerCase() === "blue") return "Blau · Verteidiger";
  if (value.toLowerCase() === "red") return "Rot · Angreifer";
  return value || "—";
}

function addLog(text: string) {
  const kind = /Fehler|error|konnte nicht/i.test(text) ? "error" : /eingelockt|beendet\./i.test(text) ? "success" : "normal";
  entries.push({ time: new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" }), text, kind });
  entries = entries.slice(-300);
  renderLog();
  document.querySelector("#footer-state")!.textContent = text;
}

function setRunning(value: boolean) {
  running = value;
  button.classList.toggle("is-stop", value);
  button.innerHTML = `<span class="button-icon" aria-hidden="true">${value ? "■" : "▶"}</span><span>${value ? "Stoppen" : "Lock starten"}</span>`;
  document.querySelector("#connection-light")!.classList.toggle("is-live", value);
  document.querySelector("#connection-label")!.textContent = value ? "Agent aktiv" : "Bereit";
  document.querySelector("#action-copy")!.textContent = value ? "Suche nach einem Match" : "Sobald das Match startet, wird der Agent gewählt.";
  document.querySelector("#footer-state")!.textContent = value ? "Warte auf Match" : "Warte auf Start";
  if (!value) {
    document.querySelector("#live-phase")!.textContent = "Nicht aktiv";
    document.querySelector("#live-indicator")!.classList.remove("is-live");
  } else {
    document.querySelector("#live-phase")!.textContent = "Verbinde …";
  }
  for (const field of [agentSelect, regionSelect, ruleMapSelect, ruleAgentSelect, webhookInput, document.querySelector<HTMLButtonElement>("#save-rule")!]) field.disabled = value;
  document.querySelectorAll<HTMLButtonElement>("[data-remove-rule]").forEach((removeButton) => { removeButton.disabled = value; });
}

button.addEventListener("click", async () => {
  button.disabled = true;
  try {
    if (running) {
      await invoke("stop_agent");
      setRunning(false);
    } else {
      const agent = agents.find((item) => item.id === agentSelect.value) || sage;
      await invoke("start_agent", { agentId: agent.id, agentName: agent.name, region: regionSelect.value, mapRules: JSON.stringify(mapRules), discordWebhook: webhookInput.value.trim() || null });
      setRunning(true);
    }
  } catch (error) {
    addLog(String(error));
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#clear-log")!.addEventListener("click", () => { entries = []; renderLog(); });
document.querySelector("#save-rule")!.addEventListener("click", () => {
  const map = maps.find((item) => item.id === ruleMapSelect.value);
  const agent = agents.find((item) => item.id === ruleAgentSelect.value);
  if (!map || !agent) return;
  mapRules[map.id] = { agentId: agent.id, agentName: agent.name, mapName: map.name };
  saveRules();
  addLog(`${agent.name} für ${map.name} gespeichert.`);
});
document.querySelector("#map-rules")!.addEventListener("click", (event) => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-remove-rule]");
  if (!button) return;
  delete mapRules[button.dataset.removeRule || ""];
  saveRules();
});
renderMapRules();

const listenersReady = Promise.all([
  listen<string>("agent-log", (event) => addLog(event.payload)),
  listen<{ running: boolean }>("agent-status", (event) => setRunning(event.payload.running)),
  listen<TrackSnapshot>("agent-track", (event) => {
  const snapshot = event.payload;
  const phases: Record<string, string> = { PREGAME: "Agentenauswahl", INGAME: "Im Match", IN_GAME: "Im Match", MENUS: "Im Menü", UNKNOWN: "Status wird gesucht" };
  const phase = snapshot.phase?.toUpperCase() || "UNKNOWN";
  const live = phase !== "MENUS" && phase !== "UNKNOWN";
  document.querySelector("#live-phase")!.textContent = phases[phase] || phase;
  document.querySelector("#live-indicator")!.classList.toggle("is-live", live);
  const mapEl = document.querySelector<HTMLElement>("#live-map")!;
  mapEl.textContent = snapshot.mapName || (snapshot.mapId ? snapshot.mapId.slice(0, 8) : "Wartet auf Map");
  mapEl.title = snapshot.mapId || "";
  document.querySelector("#live-agent")!.textContent = snapshot.agentName || "Noch nicht gewählt";
  const regionName = regions.find(([value]) => value === snapshot.region)?.[1] || snapshot.region || "—";
  document.querySelector("#live-region")!.textContent = regionName;
  document.querySelector("#live-updated")!.textContent = snapshot.updatedAt
    ? new Date(snapshot.updatedAt * 1000).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";
  const players = snapshot.players || [];
  renderPlayers(players);
  document.querySelector("#roster-updated")!.textContent = players.length
    ? `${players.length} Spieler · aktualisiert ${snapshot.updatedAt ? new Date(snapshot.updatedAt * 1000).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "gerade eben"}`
    : "Warte auf Match";
  }),
]);
void listenersReady.catch((error) => addLog(`Listener konnten nicht gestartet werden: ${String(error)}`));
void listenersReady.then(async () => {
  try {
    await checkForUpdate(true);
  } catch (error) {
    addLog(`Automatische Updatesuche fehlgeschlagen: ${String(error)}`);
  }
});
