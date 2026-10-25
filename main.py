
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import socket
import sys
import time
from threading import Event, Thread, Lock
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from valclient.client import Client
import requests


LOBBY_STATE: dict[str, Any] = {"phase": "MENUS", "mapName": "", "agentName": "", "timerSeconds": None, "players": []}
LOBBY_LOCK = Lock()
MAP_NAME_FALLBACKS = {
    "7eaecc1b-4337-bbf6-6ab9-04b8f06b3319": "Ascent",
    "ascent": "Ascent",
    "d960549e-485c-e861-8d71-aa9d1aed12a2": "Split",
    "bonsai": "Split",
    "b529448b-4d60-346e-e89e-00a4c527a405": "Fracture",
    "canyon": "Fracture",
    "2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba": "Bind",
    "duality": "Bind",
    "2fb9a4fd-47b8-4e7d-a969-74b4046ebd53": "Breeze",
    "foxtrot": "Breeze",
    "690b3ed2-4dff-945b-8223-6da834e30d24": "District",
    "hurm-alley": "District",
    "12452a9d-48c3-0b02-e7eb-0381c3520404": "Kasbah",
    "hurm-bowl": "Kasbah",
    "2c09d728-42d5-30d8-43dc-96a05cc7ee9d": "Drift",
    "hurm-helix": "Drift",
    "d6336a5a-428f-c591-98db-c8a291159134": "Glitch",
    "hurm-hightide": "Glitch",
    "de28aa9b-4cbe-1003-320e-6cb3ec309557": "Piazza",
    "hurm-yard": "Piazza",
    "224b0a95-48b9-f703-1bd8-67aca101a61f": "Abyss",
    "infinity": "Abyss",
    "2fe4ed3a-450a-948b-6d6b-e89a78e680a9": "Lotus",
    "jam": "Lotus",
    "92584fbe-486a-b1b2-9faa-39b0f486b498": "Sunset",
    "juliett": "Sunset",
    "fd267378-4d1d-484f-ff52-77821ed10dc2": "Pearl",
    "pitt": "Pearl",
    "756da597-416b-c0f2-f47b-afbdf28670bc": "Summit",
    "plummet": "Summit",
    "e2ad5c54-4114-a870-9641-8ea21279579a": "Icebox",
    "port": "Icebox",
    "ee613ee9-28b7-4beb-9666-08db13bb2244": "The Range",
    "5914d1e0-40c4-cfdd-6b88-eba06347686c": "The Range",
    "poveglia": "The Range",
    "the-range": "The Range",
    "1c18ab1f-420d-0d8b-71d0-77ad3c439115": "Corrode",
    "rook": "Corrode",
    "2bee0dc9-4ffe-519b-1cbd-7fbe763a6047": "Haven",
    "triad": "Haven",
}


class LobbyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/mobile-url":
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                try:
                    probe.connect(("192.0.2.1", 80))
                    address = probe.getsockname()[0]
                except OSError:
                    address = "127.0.0.1"
            body = json.dumps({"url": f"http://{address}:47831/"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
        elif self.path == "/api/state":
            with LOBBY_LOCK:
                body = json.dumps(LOBBY_STATE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        else:
            body = '''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lockstep Lobby</title><style>body{margin:0;background:#111210;color:#e8e9e5;font:15px system-ui}main{max-width:900px;margin:8vh auto;padding:28px}h1{font-size:32px}.meta{display:flex;gap:20px;color:#a4a79e}.card{margin-top:24px;border:1px solid #34362f;border-radius:12px;padding:18px;background:#181a17}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid #34362f}.dim{color:#92958c}</style><main><p class="dim">LOCKSTEP / LOKALE LOBBY</p><h1>Warte auf Lobby …</h1><div class="meta"><span id="map">Map —</span><span id="agent">Agent —</span><span id="timer">Timer —</span></div><section class="card"><table><thead><tr><th>Spieler</th><th>Agent</th><th>Team</th></tr></thead><tbody id="players"><tr><td class="dim" colspan="3">Warte auf Spielerdaten …</td></tr></tbody></table></section></main><script>let timerEnd=0;async function update(){try{const s=await(await fetch('/api/state')).json();document.querySelector('h1').textContent=s.phase==='PREGAME'?'Agentenauswahl':s.phase==='MENUS'?'Warte auf Lobby …':'Match läuft';document.querySelector('#map').textContent='Map '+(s.mapName||'—');document.querySelector('#agent').textContent='Agent '+(s.agentName||'—');timerEnd=s.timerSeconds==null?0:Date.now()+s.timerSeconds*1000;document.querySelector('#players').innerHTML=(s.players||[]).map(p=>'<tr><td>'+esc(p.name||'Spieler')+'</td><td>'+esc(p.agentName||'Wählt …')+'</td><td>'+esc(p.team||'—')+'</td></tr>').join('')||'<tr><td class="dim" colspan="3">Keine Spielerdaten</td></tr>'}catch{} }function esc(s){return String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}setInterval(()=>{document.querySelector('#timer').textContent='Timer '+(timerEnd?Math.max(0,Math.ceil((timerEnd-Date.now())/1000))+' s':'—')},250);update();setInterval(update,1000);</script></html>'''.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        pass


def start_lobby_server() -> None:
    try:
        server = ThreadingHTTPServer(("0.0.0.0", 47831), LobbyHandler)
        Thread(target=server.serve_forever, daemon=True).start()
    except OSError:
        pass


def update_lobby(state: dict[str, Any]) -> None:
    with LOBBY_LOCK:
        LOBBY_STATE.update(state)


def notify_discord(webhook: str, map_name: str, agent_name: str) -> None:
    if not webhook:
        return
    payload = json.dumps({"content": f"Match gefunden · Map: {map_name or 'Unbekannt'} · Agent: {agent_name}"}).encode("utf-8")
    request = Request(webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=5):
            pass
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        try:
            response = json.loads(details)
            reason = str(response.get("message") or details or error.reason)
            code = response.get("code")
        except (json.JSONDecodeError, AttributeError):
            reason = details or str(error.reason)
            code = None
        code_text = f" (Discord-Code {code})" if code is not None else ""
        print(f"Discord-Webhook abgelehnt (HTTP {error.code}){code_text}: {reason}", flush=True)
    except Exception as error:
        print(f"Discord-Webhook fehlgeschlagen: {type(error).__name__}: {error}", flush=True)


def content_names(client: Client) -> tuple[dict[str, str], dict[str, str]]:
    try:
        content = client.fetch_content()
    except Exception:
        return {}, {}
    agent_names = {
        canonical_id(item.get("ID")): item.get("Name", "")
        for item in content.get("Characters", [])
    }
    map_names = {
        canonical_id(item.get("ID")): item.get("Name", "")
        for item in content.get("Maps", [])
    }
    return agent_names, map_names


def canonical_id(value: Any) -> str:
    return str(value or "").strip().strip("{}").casefold()


def map_slug(value: Any) -> str:
    """Normalize Riot map IDs, URLs, and display names to the catalog slug."""
    text = str(value or "").strip().replace("\\", "/")
    # Some modes add a HURM subfolder, where the mode folder alone is not the map.
    match = re.search(r"(?:^|/)Maps/([^/]+)(?:/([^/]+))?", text, re.IGNORECASE)
    if match:
        folder = match.group(1)
        text = match.group(2) if folder.casefold() == "hurm" and match.group(2) else folder
    else:
        text = text.rstrip("/").rsplit("/", 1)[-1]
        text = re.sub(r"\.[^.]+$", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def resolve_map_name(map_id: Any, map_names: dict[str, str]) -> str:
    raw = str(map_id or "").strip()
    canonical = canonical_id(raw)
    if canonical in map_names:
        return map_names[canonical]
    if canonical in MAP_NAME_FALLBACKS:
        return MAP_NAME_FALLBACKS[canonical]
    slug = map_slug(raw)
    for content_id, name in map_names.items():
        if slug and (map_slug(content_id) == slug or map_slug(name) == slug):
            return name
    return MAP_NAME_FALLBACKS.get(slug, "")


def competitive_tier(mmr: dict[str, Any]) -> int:
    latest = mmr.get("LatestCompetitiveUpdate") or {}
    season_id = str(latest.get("SeasonID") or "")
    competitive = (mmr.get("QueueSkills") or {}).get("competitive") or {}
    seasons = competitive.get("SeasonalInfoBySeasonID") or {}
    current = seasons.get(season_id) if season_id else None
    if not current and seasons:
        current = max(seasons.values(), key=lambda item: item.get("NumberOfGames", 0))
    return int((current or {}).get("CompetitiveTier") or 0)


def resolve_player_profiles(client: Client, puuids: list[str]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not puuids:
        return profiles
    try:
        response = requests.put(
            f"{client.base_url}/name-service/v2/players",
            headers=client.headers,
            json=puuids,
            timeout=8,
        )
        response.raise_for_status()
        named_players = response.json()
        if isinstance(named_players, dict):
            named_players = named_players.get("Players") or named_players.get("players") or []
        for player in named_players if isinstance(named_players, list) else []:
            if not isinstance(player, dict):
                continue
            subject = canonical_id(player.get("Subject") or player.get("subject"))
            game_name = player.get("GameName") or player.get("gameName") or player.get("DisplayName") or ""
            tag_line = player.get("TagLine") or player.get("tagLine") or ""
            if subject and game_name:
                resolved_name = game_name if "#" in game_name or not tag_line else f"{game_name}#{tag_line}"
                profiles.setdefault(subject, {})["name"] = resolved_name
    except requests.HTTPError as error:
        response = error.response
        reason = response.text[:240] if response is not None else str(error)
        status = response.status_code if response is not None else "?"
        print(f"Riot-Namen konnten nicht geladen werden (HTTP {status}): {reason}", flush=True)
    except Exception as error:
        print(f"Riot-Namen konnten nicht geladen werden: {type(error).__name__}: {error}", flush=True)

    for puuid in puuids:
        try:
            tier = competitive_tier(client.fetch_mmr(puuid))
            if tier:
                profiles.setdefault(canonical_id(puuid), {})["rankTier"] = tier
        except Exception:
            pass
    return profiles


def read_game_metadata(fallback_region: str) -> tuple[str, str]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    log_path = os.path.join(local_app_data, "VALORANT", "Saved", "Logs", "ShooterGame.log")
    region = fallback_region
    region_found = False
    version = ""
    try:
        with open(log_path, "rb") as log_file:
            log_file.seek(max(0, os.path.getsize(log_path) - 4_000_000))
            lines = log_file.read().decode("utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            region_match = re.search(r"https?://glz-([a-z]+)-1\.[a-z0-9-]+\.a\.pvp\.net", line, re.IGNORECASE)
            if region_match and not region_found:
                region = region_match.group(1).lower()
                region_found = True
            if not version and "CI server version:" in line:
                raw_version = line.split("CI server version:", 1)[1].strip().split()[0].strip("'\";,)")
                parts = raw_version.split("-")
                if len(parts) == 4 and parts[2] != "shipping":
                    parts.insert(2, "shipping")
                version = "-".join(parts)
            if version and region_found:
                break
    except (OSError, IndexError):
        pass

    if not version:
        try:
            data = requests.get("https://valorant-api.com/v1/version", timeout=5).json()["data"]
            version = f"{data['branch']}-shipping-{data['buildVersion']}-{data['version'].split('.')[3]}"
        except Exception as error:
            raise RuntimeError(f"VALORANT-Version konnte nicht gelesen werden: {error}") from error
    return region, version


def normalize_players(data: dict[str, Any], agent_names: dict[str, str]) -> list[dict[str, Any]]:
    players: list[dict[str, Any]] = []
    teams = data.get("Teams")
    if isinstance(teams, list):
        for team in teams:
            if not isinstance(team, dict):
                continue
            team_id = team.get("TeamID", "")
            for player in team.get("Players", []):
                if isinstance(player, dict):
                    players.append(normalize_player(player, team_id, agent_names))
    game_players = data.get("Players") or data.get("players")
    if not players and isinstance(game_players, list):
        players = [normalize_player(player, player.get("TeamID", player.get("teamId", "")), agent_names)
                   for player in game_players if isinstance(player, dict)]
    if not players:
        for key in ("AllyTeam", "EnemyTeam"):
            team = data.get(key)
            if isinstance(team, dict):
                label = "Teammate" if key == "AllyTeam" else "Gegner"
                players.extend(normalize_player(player, label, agent_names)
                               for player in team.get("Players", []) if isinstance(player, dict))
    return players


def normalize_player(player: dict[str, Any], team: str, agent_names: dict[str, str]) -> dict[str, Any]:
    identity = player.get("PlayerIdentity") or player.get("playerIdentity") or {}
    stats = player.get("Stats") or player.get("stats") or {}
    agent_id = (player.get("CharacterID") or player.get("characterId") or
                player.get("AgentID") or player.get("agentId") or identity.get("CharacterID") or "")
    rank = player.get("CompetitiveTier") or player.get("competitiveTier")
    badge = player.get("SeasonalBadgeInfo") or player.get("seasonalBadgeInfo") or {}
    if not rank:
        rank = badge.get("Rank")
    name = (player.get("GameName") or player.get("gameName") or identity.get("GameName") or
            identity.get("gameName") or "")
    tag = player.get("TagLine") or player.get("tagLine") or identity.get("TagLine") or ""
    if name and tag:
        name = f"{name}#{tag}"
    return {
        "id": player.get("Subject") or player.get("subject") or "",
        "name": name,
        "team": team,
        "agentId": agent_id,
        "agentName": agent_names.get(canonical_id(agent_id), ""),
        "rankTier": rank or 0,
        "accountLevel": identity.get("AccountLevel") or identity.get("accountLevel") or 0,
        "kills": stats.get("Kills", stats.get("kills")),
        "deaths": stats.get("Deaths", stats.get("deaths")),
        "assists": stats.get("Assists", stats.get("assists")),
        "score": stats.get("Score", stats.get("score")),
    }


def lock_agent(agent_id: str, agent_name: str, region: str, map_rules: dict[str, dict[str, str]]) -> None:
    start_lobby_server()
    control = {"agent_id": agent_id, "agent_name": agent_name, "map_rules": map_rules, "discord_webhook": os.environ.get("LOCKSTEP_DISCORD_WEBHOOK", "")}
    control_lock = Lock()
    auto_lock_enabled = Event()

    def read_commands() -> None:
        for line in sys.stdin:
            try:
                command = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(command, dict) or command.get("type") not in ("auto_lock", "configure"):
                continue
            with control_lock:
                control["agent_id"] = str(command.get("agentId") or control["agent_id"])
                control["agent_name"] = str(command.get("agentName") or control["agent_name"])
                control["map_rules"] = json.loads(command.get("mapRules") or "{}")
                control["discord_webhook"] = str(command.get("discordWebhook") or "")
            if command.get("type") != "auto_lock":
                continue
            if command.get("enabled"):
                auto_lock_enabled.set()
                print("Auto-Lock aktiviert.", flush=True)
            else:
                auto_lock_enabled.clear()
                print("Auto-Lock pausiert. Tracking und Lobby laufen weiter.", flush=True)

    Thread(target=read_commands, daemon=True).start()
    print("Lokale Lobby gestartet. Warte auf Valorant-Client …", flush=True)
    client = None
    last_connect_error = ""
    while client is None:
        try:
            detected_region, client_version = read_game_metadata(region)
            if detected_region != region:
                print(f"Region aus Spiel-Log verwendet: {detected_region.upper()}", flush=True)
                region = detected_region
            client = Client(region=region)
            client._Client__get_current_version = lambda: client_version
            client.activate()
        except Exception as error:
            client = None
            message = f"Warte auf Valorant-Client: {error}"
            if message != last_connect_error:
                print(message, flush=True)
                last_connect_error = message
            time.sleep(3)
    agent_names: dict[str, str] = {
        canonical_id(agent_id): name for agent_id, name in {
            "41fb69c1-4189-7b37-f117-bcaf1e96f1bf": "Astra",
            "5f8d3a7f-467b-97f3-062c-13acf203c006": "Breach",
            "9f0d8ba9-4140-b941-57d3-a7ad57c6b417": "Brimstone",
            "22697a3d-45bf-8dd7-4fec-84a9e28c69d7": "Chamber",
            "1dbf2edd-4729-0984-3115-daa5eed44993": "Clove",
            "117ed9e3-49f3-6512-3ccf-0cada7e3823b": "Cypher",
            "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235": "Deadlock",
            "dade69b4-4f5a-8528-247b-219e5a1facd6": "Fade",
            "e370fa57-4757-3604-3648-499e1f642d3f": "Gekko",
            "95b78ed7-4637-86d9-7e41-71ba8c293152": "Harbor",
            "0e38b510-41a8-5780-5e8f-568b2a4f2d6c": "Iso",
            "add6443a-41bd-e414-f6ad-e58d267f4e95": "Jett",
            "601dbbe7-43ce-be57-2a40-4abd24953621": "KAY/O",
            "1e58de9c-4950-5125-93e9-a0aee9f98746": "Killjoy",
            "7c8a4701-4de6-9355-b254-e09bc2a34b72": "Miks",
            "bb2a4828-46eb-8cd1-e765-15848195d751": "Neon",
            "8e253930-4c05-31dd-1b6c-968525494517": "Omen",
            "eb93336a-449b-9c1b-0a54-a891f7921d69": "Phoenix",
            "f94c3b30-42be-e959-889c-5aa313dba261": "Raze",
            "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc": "Reyna",
            "569fdd95-4d10-43ab-ca70-79becc718b46": "Sage",
            "6f2a04ca-43e0-be17-7f36-b3908627744d": "Skye",
            "320b2a48-4d9b-a075-30f1-1f93a9b638fa": "Sova",
            "b444168c-4e35-8076-db47-ef9bf368f384": "Tejo",
            "92eeef5d-43b5-1d4a-8d03-b3927a09034b": "Veto",
            "707eab51-4836-f488-046a-cda6bf494859": "Viper",
            "efba5359-4016-a1e5-7626-b1ae76895940": "Vyse",
            "df1cb487-4902-002e-5c17-d28e83e78588": "Waylay",
            "7f94d92c-4234-0a36-9646-3a87eb8b5c89": "Yoru",
        }.items()
    }
    map_names: dict[str, str] = {}
    player_profiles: dict[str, dict[str, Any]] = {}
    requested_profile_ids: set[str] = set()
    profiles_lock = Lock()

    def load_content_names() -> None:
        loaded_agents, loaded_maps = content_names(client)
        agent_names.update(loaded_agents)
        map_names.update(loaded_maps)
        if loaded_agents or loaded_maps:
            print("Map- und Agentennamen geladen.", flush=True)

    def enrich_profiles(puuids: list[str]) -> None:
        loaded_profiles = resolve_player_profiles(client, puuids)
        with profiles_lock:
            player_profiles.update(loaded_profiles)

    def apply_profiles(roster: list[dict[str, Any]]) -> None:
        missing: list[str] = []
        with profiles_lock:
            for player in roster:
                puuid = str(player.get("id") or "")
                profile = player_profiles.get(canonical_id(puuid), {})
                if not player.get("name") and profile.get("name"):
                    player["name"] = profile["name"]
                if not player.get("rankTier") and profile.get("rankTier"):
                    player["rankTier"] = profile["rankTier"]
                key = canonical_id(puuid)
                if puuid and key not in requested_profile_ids and (not player.get("name") or not player.get("rankTier")):
                    requested_profile_ids.add(key)
                    missing.append(puuid)
        if missing:
            Thread(target=enrich_profiles, args=(missing,), daemon=True).start()

    Thread(target=load_content_names, daemon=True).start()
    print(f"Warte in {region.upper()} auf ein Match für {agent_name} …", flush=True)

    locked = False
    pregame_id = ""
    pregame_started_at = 0.0
    lock_delay_announced_id = ""
    match_id = ""
    previous_phase = ""
    tracked_map_id = ""
    tracked_map_name = ""
    active_agent_id = agent_id
    active_agent_name = agent_name
    players: list[dict[str, Any]] = []
    awaiting_postgame = False
    final_stats_attempts = 0
    last_final_attempt = 0.0
    last_error = ""
    last_error_at = 0.0
    notified_pregame_id = ""
    was_auto_lock_enabled = False
    while True:
        try:
            with control_lock:
                agent_id = control["agent_id"]
                agent_name = control["agent_name"]
                map_rules = control["map_rules"]
                discord_webhook = control["discord_webhook"]
            lock_enabled = auto_lock_enabled.is_set()
            if lock_enabled and not was_auto_lock_enabled and pregame_id:
                pregame_started_at = time.monotonic()
                lock_delay_announced_id = ""
            was_auto_lock_enabled = lock_enabled
            try:
                presence = client.fetch_presence() or {}
            except Exception as error:
                presence = {}
                message = f"Presence-Abfrage fehlgeschlagen: {error}"
                if message != last_error or time.monotonic() - last_error_at >= 10:
                    print(message, flush=True)
                    last_error, last_error_at = message, time.monotonic()
            phase = str(presence.get("sessionLoopState") or presence.get("loopState") or "UNKNOWN").upper()
            if phase == "UNKNOWN":
                try:
                    session = client.session_fetch() or {}
                    phase = str(session.get("loopState") or session.get("sessionLoopState") or "UNKNOWN").upper()
                except Exception as error:
                    message = f"Session-Status nicht lesbar: {error}"
                    if message != last_error or time.monotonic() - last_error_at >= 10:
                        print(message, flush=True)
                        last_error, last_error_at = message, time.monotonic()
            if phase != previous_phase:
                print(f"Spielstatus erkannt: {phase}", flush=True)
            match_data = {}

            if phase == "PREGAME":
                stale_pregame_response = False
                try:
                    match_data = client.pregame_fetch_match() or {}
                except Exception as error:
                    match_data = {}
                    stale_pregame_response = "not in a pre-game" in str(error).casefold()
                    if not stale_pregame_response:
                        message = f"Pregame-Abfrage fehlgeschlagen: {error}"
                        if message != last_error or time.monotonic() - last_error_at >= 10:
                            print(message, flush=True)
                            last_error, last_error_at = message, time.monotonic()
                    else:
                        try:
                            latest_presence = client.fetch_presence() or {}
                            latest_phase = str(latest_presence.get("sessionLoopState") or latest_presence.get("loopState") or "").upper()
                            if latest_phase in ("INGAME", "IN_GAME", "MENUS"):
                                phase = latest_phase
                        except Exception:
                            pass
                if not match_data.get("ID") and not stale_pregame_response:
                    message = "Pregame erkannt, aber die Match-ID fehlt noch."
                    if message != last_error or time.monotonic() - last_error_at >= 10:
                        print(message, flush=True)
                        last_error, last_error_at = message, time.monotonic()
                candidate_pregame_id = str(match_data.get("ID", ""))
                if candidate_pregame_id and candidate_pregame_id != pregame_id:
                    pregame_id = candidate_pregame_id
                    pregame_started_at = time.monotonic()
                    lock_delay_announced_id = ""
                    locked = False
                    awaiting_postgame = False
                    final_stats_attempts = 0
                    last_final_attempt = 0.0
                    match_id = ""
                    tracked_map_id = ""
                    tracked_map_name = ""
                players = normalize_players(match_data, agent_names)
                map_id = str(match_data.get("MapID") or match_data.get("mapId") or "")
                map_name = resolve_map_name(map_id, map_names)
                map_key = map_slug(map_name or map_id)
                rule = next(
                    (saved for key, saved in map_rules.items()
                     if canonical_id(key) == canonical_id(map_id)
                     or (map_key and map_slug(key) == map_key)
                     or (map_key and map_slug(saved.get("mapName", "")) == map_key)),
                    {},
                )
                active_agent_id = rule.get("agentId") or agent_id
                active_agent_name = rule.get("agentName") or agent_name
                if match_data.get("ID"):
                    current_pregame_id = str(match_data["ID"])
                    if notified_pregame_id != current_pregame_id:
                        notified_pregame_id = current_pregame_id
                        Thread(target=notify_discord, args=(discord_webhook, map_name, active_agent_name), daemon=True).start()
                if not locked and match_data.get("ID") and lock_enabled:
                    current_pregame_id = str(match_data["ID"])
                    delay_remaining = 5.0 - (time.monotonic() - pregame_started_at)
                    if delay_remaining > 0:
                        if lock_delay_announced_id != current_pregame_id:
                            print(f"Match gefunden. {active_agent_name} wird in 5 Sekunden gelockt.", flush=True)
                            lock_delay_announced_id = current_pregame_id
                    else:
                        print(f"Match gefunden. {active_agent_name} wird ausgewählt ...", flush=True)
                        try:
                            client.pregame_select_character(active_agent_id, match_data["ID"])
                            client.pregame_lock_character(active_agent_id, match_data["ID"])
                            locked = True
                            print(f"{active_agent_name} wurde eingelockt.", flush=True)
                        except Exception as error:
                            print(f"{active_agent_name} konnte nicht ausgewählt/gelockt werden: {error}", flush=True)
            elif phase in ("INGAME", "IN_GAME"):
                try:
                    live_ref = client.coregame_fetch_player() or {}
                    live_id = live_ref.get("MatchID") or live_ref.get("matchId")
                    if live_id:
                        if str(live_id) != match_id:
                            match_id = str(live_id)
                            final_stats_attempts = 0
                            last_final_attempt = 0.0
                            awaiting_postgame = False
                        match_data = client.coregame_fetch_match(live_id) or {}
                    else:
                        match_data = {}
                except Exception:
                    match_data = {}
                live_players = normalize_players(match_data, agent_names)
                if live_players:
                    previous_by_id = {player["id"]: player for player in players if player.get("id")}
                    for player in live_players:
                        old_player = previous_by_id.get(player["id"], {})
                        if not player.get("rankTier"):
                            player["rankTier"] = old_player.get("rankTier", 0)
                        if not player.get("agentName"):
                            player["agentName"] = old_player.get("agentName", "")
                        if player.get("kills") is None:
                            player["kills"] = old_player.get("kills")
                        if player.get("deaths") is None:
                            player["deaths"] = old_player.get("deaths")
                        if player.get("assists") is None:
                            player["assists"] = old_player.get("assists")
                    players = live_players

            if previous_phase in ("INGAME", "IN_GAME") and phase not in ("INGAME", "IN_GAME"):
                awaiting_postgame = True

            apply_profiles(players)

            if awaiting_postgame and phase in ("MENUS", "UNKNOWN") and match_id and final_stats_attempts < 12:
                now = time.monotonic()
                if now - last_final_attempt >= 10:
                    last_final_attempt = now
                    final_stats_attempts += 1
                    try:
                        details = client.fetch_match_details(match_id) or {}
                        final_players = normalize_players(details, agent_names)
                        if final_players and any(player.get("kills") is not None for player in final_players):
                            players = final_players
                            print("Spielerwerte aus dem Matchbericht geladen.", flush=True)
                            awaiting_postgame = False
                    except Exception:
                        pass
                if final_stats_attempts >= 12:
                    awaiting_postgame = False

            if phase in ("MENUS", "UNKNOWN") and previous_phase in ("PREGAME", "INGAME", "IN_GAME"):
                locked = False
                pregame_id = ""
            previous_phase = phase

            reported_map_id = match_data.get("MapID") or match_data.get("mapId") or ""
            if reported_map_id:
                reported_map_id = str(reported_map_id)
                if canonical_id(reported_map_id) != canonical_id(tracked_map_id):
                    tracked_map_id = reported_map_id
                    tracked_map_name = ""

            if phase == "MENUS":
                tracked_map_id = ""
                tracked_map_name = ""
            elif tracked_map_id:
                tracked_map_name = resolve_map_name(tracked_map_id, map_names) or tracked_map_name

            map_id = tracked_map_id
            map_name = tracked_map_name
            timer_ns = match_data.get("PhaseTimeRemainingNS")
            snapshot = {
                "phase": phase,
                "mapId": map_id,
                "mapName": map_name,
                "agentId": active_agent_id if locked else "",
                "agentName": active_agent_name if locked else "",
                "region": region,
                "players": players if phase in ("PREGAME", "INGAME", "IN_GAME") else [],
                "timerSeconds": max(0, int(timer_ns / 1_000_000_000)) if isinstance(timer_ns, (int, float)) else None,
                "updatedAt": int(time.time()),
            }
            update_lobby(snapshot)
            print("TRACK:" + json.dumps(snapshot), flush=True)
        except Exception as error:
            message = str(error)
            if message != last_error or time.monotonic() - last_error_at >= 10:
                print(f"Tracking: {message}", flush=True)
                last_error, last_error_at = message, time.monotonic()
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", default="569fdd95-4d10-43ab-ca70-79becc718b46")
    parser.add_argument("--agent-name", default="Sage")
    parser.add_argument("--region", choices=("eu", "na", "ap", "kr", "br", "latam"), default="eu")
    parser.add_argument("--rules", default="{}")
    parser.add_argument("--catalog", action="store_true")
    args = parser.parse_args()
    lock_agent(args.agent_id, args.agent_name, args.region, json.loads(args.rules))
