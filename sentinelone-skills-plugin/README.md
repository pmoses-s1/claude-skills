# SentinelOne Skills Plugin

Claude skills for SentinelOne SecOps workflows. Six skills are included:

| Skill | What it does |
|-------|-------------|
| sentinelone-powerquery | Write, debug, and run PowerQuery threat hunts and STAR detection rules |
| sentinelone-mgmt-console-api | Query and act on the Management Console (threats, alerts, agents, IOCs, RemoteOps, UAM, Purple AI) |
| sentinelone-sdl-api | Read and write data via the Singularity Data Lake API (ingest, queries, parsers, dashboards) |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards: panels, tabs, parameters, and full dashboard JSON |
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

### With sentinelone-mcp (recommended)

If you have `sentinelone-mcp` installed, credentials are set in `claude_desktop_config.json` as environment variables. No `credentials.json` file is needed:

```json
{
  "mcpServers": {
    "sentinelone-mcp": {
      "command": "node",
      "args": ["/path/to/claude-skills/sentinelone-mcp/index.js"],
      "env": {
        "S1_CONSOLE_URL":       "https://usea1-acme.sentinelone.net",
        "S1_CONSOLE_API_TOKEN": "eyJ...your-token...",
        "S1_HEC_INGEST_URL":    "https://ingest.us1.sentinelone.net",
        "SDL_XDR_URL":          "https://xdr.us1.sentinelone.net",
        "SDL_LOG_WRITE_KEY":    "0Z1Fy0...your-log-write-key...",
        "SDL_LOG_READ_KEY":     "0tzj...your-log-read-key...",
        "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key...",
        "SDL_CONFIG_READ_KEY":  "0MQTx...your-config-read-key..."
      }
    }
  }
}
```

### Without sentinelone-mcp (direct skill use)

Drop a `credentials.json` file directly into your Cowork project folder. The plugin's SessionStart hook auto-discovers it. A fully annotated example is at [`credentials.example.json`](credentials.example.json):

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

Only include the keys you need. `S1_CONSOLE_URL` + `S1_CONSOLE_API_TOKEN` covers most skills (including SDL query and config methods). Add `SDL_*` keys only if you need `uploadLogs` (`SDL_LOG_WRITE_KEY`) or parser/dashboard deploy (`SDL_CONFIG_WRITE_KEY`).

Resolution order (highest priority wins):
1. Environment variables set via `sentinelone-mcp` in `claude_desktop_config.json`
2. `<project folder>/credentials.json` (auto-discovered by the plugin's SessionStart hook)
3. `~/.config/sentinelone/credentials.json` (terminal fallback when there is no project folder)

---

## Skills

**sentinelone-powerquery**: Write and run PowerQuery (PQ) queries for Deep Visibility, Event Search, threat hunting, STAR detection rules, and SDL dashboard panels.

**sentinelone-mgmt-console-api**: Interact with the SentinelOne Management Console REST and GraphQL APIs (UAM, Purple AI). Covers threats, alerts, agents, sites, groups, exclusions, RemoteOps, Hyperautomation, and IOCs.

**sentinelone-sdl-api**: Read and write data through the Singularity Data Lake API. Supports event ingestion, PowerQuery execution, and configuration file management (parsers, dashboards, lookups).

**sentinelone-sdl-dashboard**: Design, author, and deploy Singularity Data Lake dashboards. Covers all panel types (line, bar, pie, table, number, honeycomb, markdown), multi-tab layouts, parameters, and full dashboard JSON authoring with community examples.

**sentinelone-sdl-log-parser**: Author, edit, debug, and validate SDL log parsers. Handles CEF, syslog, JSON, key=value, multi-line, CSV, and custom formats. Validates end-to-end against a live SDL tenant.

**sentinelone-hyperautomation**: Design and generate SentinelOne Hyperautomation workflow JSON. Covers all trigger types, action types, functions, conditions, loops, and variable handling. Optionally imports workflows to a live console via API. Created by marco.rottigni@sentinelone.com.
