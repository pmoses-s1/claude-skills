# SentinelOne Skills Plugin

Claude skills for SentinelOne SecOps workflows. Six skills are included:

| Skill | What it does |
|-------|-------------|
| sentinelone-powerquery | Write, debug, and run PowerQuery threat hunts and STAR detection rules |
| sentinelone-mgmt-console-api | Query and act on the Management Console (threats, alerts, agents, IOCs, RemoteOps, UAM, Purple AI) |
| sentinelone-sdl-api | Read and write data via the Singularity Data Lake API (ingest, queries, parsers, dashboards) |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards — panels, tabs, parameters, and full dashboard JSON |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

---

## Setup

Set these environment variables once and all skills pick them up automatically.

### Management Console (required for most skills)

| Variable | Value | How to get it |
|----------|-------|---------------|
| `S1_CONSOLE_URL` | Your console URL, e.g. `https://usea1-acme.sentinelone.net` | Region-specific; look it up in [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `S1_CONSOLE_API_TOKEN` | Management Console API token | Settings → Users → Service Users → Create New Service User → copy the API token. See [Creating service users](https://community.sentinelone.com/s/article/000005291) |
| `S1_HEC_INGEST_URL` | HEC ingest host, used for both log ingest and OCSF alert/indicator ingest, e.g. `https://ingest.us1.sentinelone.net` | Region-specific; see [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |

### Singularity Data Lake (required for sentinelone-sdl-api, sentinelone-sdl-dashboard, and sentinelone-sdl-log-parser)

| Variable | Value | How to get it |
|----------|-------|---------------|
| `SDL_XDR_URL` | Your SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net` | Region-specific; see [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `SDL_LOG_WRITE_KEY` | Log Write key, only needed for `uploadLogs` | In Singularity Data Lake → menu next to username → API Keys → Log Access Keys → New Key (Log Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `SDL_CONFIG_WRITE_KEY` | Config Write key, only needed for `putFile` (parser/dashboard deploy) | In Singularity Data Lake → menu next to username → API Keys → Configuration Access Keys → New Key (Configuration Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |

`S1_CONSOLE_API_TOKEN` alone is enough for SDL query and config-read workflows. Console tokens support the SDL API from Management version Z SP5+; the same JWT covers both. (The legacy `SDL_CONSOLE_API_TOKEN` key is still recognised as a deprecated alias and emits a one-time deprecation warning.)

---

## How to set credentials

Drop a single JSON file into a folder Cowork has access to. The plugin's SessionStart hook discovers it and copies it to `$HOME/.claude/sentinelone/credentials.json` inside the sandbox at the start of every session, so every script and CLI in the plugin finds it with no preflight or env vars.

Recommended path:

```
$COWORK_WORKSPACE/.sentinelone/credentials.json
```

Or any folder Cowork has access to under `.sentinelone/credentials.json`. The hook auto-discovers the workspace by scanning `$HOME/mnt/` if `$COWORK_WORKSPACE` isn't set.

| Where | Path | When |
|---|---|---|
| Workspace (recommended for Cowork) | `$COWORK_WORKSPACE/.sentinelone/credentials.json` | Cowork sandbox copies it to `$HOME/.claude/sentinelone/` automatically on session start |
| Any mounted folder | `<any-Cowork-accessible-folder>/.sentinelone/credentials.json` | Auto-discovered via `~/mnt/*` scan; same auto-copy |
| Cowork session | `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` | Read as fallback when set |
| Legacy paths | `~/.claude/sentinelone/credentials.json`, `~/.config/sentinelone/credentials.json` | Older paths, still honoured |

The file format is the same in every location. A fully annotated example is included in this repo at [`credentials.example.json`](credentials.example.json):

```json
{
  "S1_CONSOLE_URL": "https://usea1-acme.sentinelone.net",
  "S1_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "S1_HEC_INGEST_URL": "https://ingest.us1.sentinelone.net",
  "SDL_XDR_URL": "https://xdr.us1.sentinelone.net",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
```

Only include the keys you need. `S1_CONSOLE_URL` + `S1_CONSOLE_API_TOKEN` covers most skills (including SDL query and config methods).
Add `SDL_*` keys only if you need `uploadLogs` (`SDL_LOG_WRITE_KEY`) or parser/dashboard deploy (`SDL_CONFIG_WRITE_KEY`).

### Create the file

**macOS / Linux** — paste into Terminal:
```bash
# Pick a folder Cowork has access to. Optionally export it as $COWORK_WORKSPACE.
export COWORK_WORKSPACE=~/Documents/Claude/Projects/MyProject
mkdir -p "$COWORK_WORKSPACE/.sentinelone"
cat > "$COWORK_WORKSPACE/.sentinelone/credentials.json" << 'EOF'
{
  "S1_CONSOLE_URL": "https://usea1-acme.sentinelone.net",
  "S1_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "S1_HEC_INGEST_URL": "https://ingest.us1.sentinelone.net",
  "SDL_XDR_URL": "https://xdr.us1.sentinelone.net",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
EOF
chmod 600 "$COWORK_WORKSPACE/.sentinelone/credentials.json"
```

**Windows** — paste into PowerShell:
```powershell
$workspace = "$env:USERPROFILE\Documents\Claude\Projects\MyProject"
$dir = "$workspace\.sentinelone"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
@'
{
  "S1_CONSOLE_URL": "https://usea1-acme.sentinelone.net",
  "S1_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "S1_HEC_INGEST_URL": "https://ingest.us1.sentinelone.net",
  "SDL_XDR_URL": "https://xdr.us1.sentinelone.net",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
'@ | Set-Content "$dir\credentials.json" -Encoding UTF8
```

Start a new Claude session after creating the file. The SessionStart hook copies it into the sandbox automatically.

---

## Skills

**sentinelone-powerquery** -- Write and run PowerQuery (PQ) queries for Deep Visibility, Event Search, threat hunting, STAR detection rules, and SDL dashboard panels.

**sentinelone-mgmt-console-api** -- Interact with the SentinelOne Management Console REST and GraphQL APIs (UAM, Purple AI). Covers threats, alerts, agents, sites, groups, exclusions, RemoteOps, Hyperautomation, and IOCs.

**sentinelone-sdl-api** -- Read and write data through the Singularity Data Lake API. Supports event ingestion, PowerQuery execution, and configuration file management (parsers, dashboards, lookups).

**sentinelone-sdl-dashboard** -- Design, author, and deploy Singularity Data Lake dashboards. Covers all panel types (line, bar, pie, table, number, honeycomb, markdown), multi-tab layouts, parameters, and full dashboard JSON authoring with community examples.

**sentinelone-sdl-log-parser** -- Author, edit, debug, and validate SDL log parsers. Handles CEF, syslog, JSON, key=value, multi-line, CSV, and custom formats. Validates end-to-end against a live SDL tenant.

**sentinelone-hyperautomation** -- Design and generate SentinelOne Hyperautomation workflow JSON. Covers all trigger types, action types, functions, conditions, loops, and variable handling. Optionally imports workflows to a live console via API. Created by marco.rottigni@sentinelone.com.
