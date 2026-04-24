# claude-skills

SentinelOne skills for Claude. Install the plugin to get everything — no individual skill setup needed.

## Quick start

1. Download the latest `.plugin` file from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/)
2. Double-click it to install into Claude
3. Create `~/.config/sentinelone/credentials.json` with your tenant credentials (see [Configuration](#configuration) below)

That's it. All five skills are active immediately.

## What's included

The plugin bundles every skill in this repo — installing the plugin is sufficient, there is no need to install skills individually.

| Skill | What it does |
|-------|-------------|
| sentinelone-mgmt-console-api | Query and act on the Management Console: threats, alerts, agents, sites, RemoteOps, Deep Visibility, Hyperautomation, Purple AI, UAM |
| sentinelone-powerquery | Write, debug, and run PowerQuery for threat hunting, STAR detection rules, and SDL dashboards |
| sentinelone-sdl-api | Ingest events, run queries, and manage configuration files (parsers, dashboards, lookups) via the Singularity Data Lake API |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format, with OCSF field mapping by default |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

## Installing

**Plugin (recommended)** — download from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/) and double-click. All five skills are installed in one step.

**Individual skills (for development only)** — drop a skill folder into `~/.claude/skills/`. Claude will pick it up on next session.

## Configuration

All skills read credentials from `~/.config/sentinelone/credentials.json`. Create this file once and every skill picks it up automatically — no editing files inside the plugin or skill folder needed.

**macOS / Linux:**

```bash
mkdir -p ~/.config/sentinelone
cat > ~/.config/sentinelone/credentials.json << 'EOF'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token..."
}
EOF
```

**Windows (PowerShell):**

```powershell
$dir = "$env:USERPROFILE\.config\sentinelone"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
@'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token..."
}
'@ | Set-Content "$dir\credentials.json" -Encoding UTF8
```

A fully annotated example with all optional keys is in [`credentials.example.json`](./credentials.example.json).

| Credential key | Required for |
|---|---|
| `S1_BASE_URL` | All management console skills |
| `S1_API_TOKEN` | `sentinelone-mgmt-console-api`, `sentinelone-powerquery` |
| `SDL_BASE_URL` | `sentinelone-sdl-api`, `sentinelone-sdl-log-parser` |
| `SDL_CONSOLE_API_TOKEN` | SDL query and config methods (not `uploadLogs`) |
| `SDL_LOG_WRITE_KEY` | `uploadLogs` only |
| `SDL_CONFIG_WRITE_KEY` | Deploying parsers/dashboards via `putFile` |

Environment variables override the credentials file if set.

## sentinelone-skills-plugin

The [`sentinelone-skills-plugin/`](./sentinelone-skills-plugin/) directory contains the distributable Claude plugin that bundles all five skills (including `sentinelone-hyperautomation` by Marco Rottigni). The built `.plugin` file lives in `sentinelone-skills-plugin/dist/`.

To rebuild after syncing skill changes:

```bash
cd sentinelone-skills-plugin
./sync.sh --build-only
```

To sync from this repo and rebuild:

```bash
cd sentinelone-skills-plugin
./sync.sh
```

## Windsurf

This repo includes Windsurf workflow files in `.windsurf/workflows/`. Each workflow is a thin pointer that directs Cascade to read the canonical `SKILL.md` and reference docs in the matching skill folder — no duplicated content.

- `sentinelone-api.md` — Management Console API (agents, threats, alerts, sites, Purple AI, UAM).
- `sentinelone-powerquery.md` — PowerQuery authoring, debugging, and detection rules.
- `sentinelone-sdl-api.md` — Singularity Data Lake API (ingest, query, config files).
- `sentinelone-sdl-log-parser.md` — SDL log parser authoring with OCSF mapping.
