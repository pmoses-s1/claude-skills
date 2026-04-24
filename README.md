# claude-skills

SentinelOne skills for Claude. Install the plugin to get everything — no individual skill setup needed.

## Quick start

1. Download the latest `.plugin` file from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/)
2. In Cowork, go to **Settings → Capabilities → Plugin** and click **Upload**, then select the `.plugin` file
3. Create `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` with your tenant credentials (see [Configuration](#configuration) below)

That's it. All six skills are active immediately.

## What's included

The plugin bundles every skill in this repo — installing the plugin is sufficient, there is no need to install skills individually.

| Skill | What it does |
|-------|-------------|
| sentinelone-mgmt-console-api | Query and act on the Management Console: threats, alerts, agents, sites, RemoteOps, Deep Visibility, Hyperautomation, Purple AI, UAM |
| sentinelone-powerquery | Write, debug, and run PowerQuery for threat hunting, STAR detection rules, and SDL dashboards |
| sentinelone-sdl-api | Ingest events, run queries, and manage configuration files (parsers, dashboards, lookups) via the Singularity Data Lake API |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards — panels, tabs, parameters, and full dashboard JSON |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format, with OCSF field mapping by default |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

## Installing

**Plugin (recommended)** — download from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/), then in Cowork go to **Settings → Capabilities → Plugin → Upload** and select the file. All six skills are installed in one step.

**Individual skills (for development only)** — drop a skill folder into `~/.claude/skills/`. Claude will pick it up on next session.

## Configuration

All skills read credentials from a single JSON file. The recommended path that works everywhere — both inside Cowork and from your terminal — is:

```
~/.claude/sentinelone/credentials.json
```

> **Why this path?** `~/.claude/` is your home-level Claude config directory. It's always accessible from your terminal without needing to know `CLAUDE_CONFIG_DIR`, and Cowork picks it up automatically too.

Full credential resolution order (highest priority wins):
1. Environment variables (`S1_BASE_URL`, `S1_API_TOKEN`, `SDL_*`)
2. `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` — Cowork session config (set automatically)
3. `~/.claude/sentinelone/credentials.json` — **recommended persistent path**
4. `~/.config/sentinelone/credentials.json` — legacy terminal fallback

**macOS / Linux:**

```bash
mkdir -p ~/.claude/sentinelone
cat > ~/.claude/sentinelone/credentials.json << 'EOF'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
EOF
```

**Windows (PowerShell):**

```powershell
# In Cowork: use $CLAUDE_CONFIG_DIR/sentinelone/credentials.json (set automatically)
# In terminal, use:
$dir = "$env:USERPROFILE\.config\sentinelone"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
@'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
'@ | Set-Content "$dir\credentials.json" -Encoding UTF8
```

A fully annotated example with all optional keys is in [`credentials.example.json`](./credentials.example.json).

| Credential key | Required for |
|---|---|
| `S1_BASE_URL` | All management console skills |
| `S1_API_TOKEN` | `sentinelone-mgmt-console-api`, `sentinelone-powerquery` |
| `SDL_BASE_URL` | `sentinelone-sdl-api`, `sentinelone-sdl-dashboard`, `sentinelone-sdl-log-parser` |
| `SDL_CONSOLE_API_TOKEN` | SDL query and config methods (not `uploadLogs`) |
| `SDL_LOG_WRITE_KEY` | `uploadLogs` only |
| `SDL_CONFIG_WRITE_KEY` | Deploying parsers/dashboards via `putFile` |

Environment variables override the credentials file if set.

## sentinelone-skills-plugin

The [`sentinelone-skills-plugin/`](./sentinelone-skills-plugin/) directory contains the distributable Claude plugin that bundles all six skills (including `sentinelone-hyperautomation` by Marco Rottigni). The built `.plugin` file lives in `sentinelone-skills-plugin/dist/`.

To rebuild after syncing skill changes:

```bash
cd sentinelone-skills-plugin
bash scripts/build.sh
```

To rebuild from scratch (removes old dist files first):

```bash
cd sentinelone-skills-plugin
bash scripts/build.sh --clean
```

## Windsurf

This repo includes Windsurf workflow files in `.windsurf/workflows/`. Each workflow is a thin pointer that directs Cascade to read the canonical `SKILL.md` and reference docs in the matching skill folder — no duplicated content.

- `sentinelone-api.md` — Management Console API (agents, threats, alerts, sites, Purple AI, UAM).
- `sentinelone-powerquery.md` — PowerQuery authoring, debugging, and detection rules.
- `sentinelone-sdl-api.md` — Singularity Data Lake API (ingest, query, config files).
- `sentinelone-sdl-log-parser.md` — SDL log parser authoring with OCSF mapping.
