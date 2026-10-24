# Lockstep

Lockstep is a Tauri desktop control for the Python script in `main.py`. It starts the script, forwards its output to the activity log, and can stop it. The live panel polls session state every two seconds and shows the phase, map, selected agent, and region when the client reports them. The agent and map dropdowns use a bundled catalog, so they are available without a Riot login or internet connection. Per-map agent rules persist in the app.

When the lock process is running, a local lobby page is served at `http://127.0.0.1:47831/`. It shows the current map, agent-selection countdown, and teammate picks. The page is only reachable from the same PC. An optional Discord webhook can be entered in the desktop app; it receives one short message for each newly found lobby.

## Development

Install Node.js, Rust, Python, and NSIS. Then install the Python dependency and frontend packages:

```powershell
python -m pip install -r requirements.txt
npm.cmd install
npm.cmd run tauri dev
```

The Windows release packages `main.py` and its Python dependencies into a standalone agent executable, so end users do not need to install Python or `valclient`. The selected agent ID is passed directly to the existing `valclient` calls. Sage is the default agent. For local installer builds, install Python 3 and Inno Setup first; `scripts/build-installer.ps1` installs the Python build dependencies and packages the agent.

The roster shows each player's agent and rank as soon as the match API provides them. Riot's current-game endpoint does not include per-player live K/D/A or score; those columns fill from the match-details endpoint after the match ends.

Build a local Windows executable with `npm.cmd run tauri -- build --no-bundle`. It is written to `src-tauri/target/release/lockstep.exe` and expects the project `main.py` alongside the source tree.

The project uses Tauri's signed updater. Installed apps check for updates at startup and ask before downloading and restarting; the **Updates suchen** button runs the same check on demand. A local signing key was generated as `src-tauri/lockstep.key`; that private key is ignored by Git and must be kept safe. Its public key is embedded in `tauri.conf.json`. The release workflow sets the update URL from the actual GitHub repository and publishes `latest.json` with each release.

Run `./scripts/build-installer.ps1` in PowerShell to bundle the Python agent and create a local installer. For a production release, add the contents of `src-tauri/lockstep.key` to the repository's GitHub Actions secrets as `TAURI_SIGNING_PRIVATE_KEY`. Push a version tag such as `v0.2.1`; `.github/workflows/release.yml` builds the standalone agent, NSIS installer, and signed updater bundle, then publishes `latest.json`. The release installer is the one to distribute so installed apps can update themselves. Never commit or share `src-tauri/lockstep.key`.

The upstream `valclient.py` repository is archived. Its README specifically says not to use its select/lock methods for automatic instalocking.
