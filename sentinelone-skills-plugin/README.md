# SentinelOne Skills Plugin

Claude skills for SentinelOne SecOps workflows. Five skills are included:

| Skill | What it does |
|-------|-------------|
| sentinelone-powerquery | Write, debug, and run PowerQuery threat hunts and STAR detection rules |
| sentinelone-mgmt-console-api | Query and act on the Management Console (threats, alerts, agents, IOCs, RemoteOps, UAM, Purple AI) |
| sentinelone-sdl-api | Read and write data via the Singularity Data Lake API (ingest, queries, parsers, dashboards) |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

---

## Setup

Set these environment variables once and all skills pick them up automatically.

### Management Console (required for most skills)

| Variable | Value |
|----------|-------|
| `S1_BASE_URL` | Your console URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_API_TOKEN` | API token from Settings > Users > Service Users > Generate API Token |

### Singularity Data Lake (required for sentinelone-sdl-api and sentinelone-sdl-log-parser)

| Variable | Value |
|----------|-------|
| `SDL_BASE_URL` | Your SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net` |
| `SDL_CONSOLE_API_TOKEN` | Console user API token (covers all methods except raw log upload) |
| `SDL_LOG_WRITE_KEY` | Log Write access key (only needed for uploadLogs) |
| `SDL_CONFIG_WRITE_KEY` | Config Write key (only needed for putFile / parser deployment) |

`SDL_CONSOLE_API_TOKEN` alone is enough for most SDL workflows.

---

## How to set credentials

Create a single JSON file with your credentials. The skills check this file at startup —
no environment variables or shell config needed.

| OS | Credentials file location |
|----|--------------------------|
| macOS / Linux | `~/.config/sentinelone/credentials.json` |
| Windows | `%USERPROFILE%\.config\sentinelone\credentials.json` |

The file format is the same on all platforms. A fully annotated example is included in this repo at [`credentials.example.json`](credentials.example.json):

```json
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
```

Only include the keys you need. `S1_BASE_URL` + `S1_API_TOKEN` covers most skills.
Add `SDL_*` keys only if you use the SDL API or log parser skills.

### Create the file

**macOS / Linux** — paste into Terminal:
```bash
mkdir -p ~/.config/sentinelone
cat > ~/.config/sentinelone/credentials.json << 'EOF'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
EOF
```

**Windows** — paste into PowerShell:
```powershell
$dir = "$env:USERPROFILE\.config\sentinelone"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
@'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
'@ | Set-Content "$dir\credentials.json" -Encoding UTF8
```

Restart Claude after creating the file.

---

## Skills

**sentinelone-powerquery** -- Write and run PowerQuery (PQ) queries for Deep Visibility, Event Search, threat hunting, STAR detection rules, and SDL dashboard panels.

**sentinelone-mgmt-console-api** -- Interact with the SentinelOne Management Console REST and GraphQL APIs (UAM, Purple AI). Covers threats, alerts, agents, sites, groups, exclusions, RemoteOps, Hyperautomation, and IOCs.

**sentinelone-sdl-api** -- Read and write data through the Singularity Data Lake API. Supports event ingestion, PowerQuery execution, and configuration file management (parsers, dashboards, lookups).

**sentinelone-sdl-log-parser** -- Author, edit, debug, and validate SDL log parsers. Handles CEF, syslog, JSON, key=value, multi-line, CSV, and custom formats. Validates end-to-end against a live SDL tenant.

**sentinelone-hyperautomation** -- Design and generate SentinelOne Hyperautomation workflow JSON. Covers all trigger types, action types, functions, conditions, loops, and variable handling. Optionally imports workflows to a live console via API. Created by marco.rottigni@sentinelone.com.
