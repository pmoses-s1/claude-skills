# SentinelOne MCP Server

A Model Context Protocol (MCP) server that orchestrates all six SentinelOne skills and their APIs. Built in pure Node.js 18+ with zero external dependencies.

## What this exposes

**19 tools** covering every skill in the plugin:

| Group | Tool | Skill |
|-------|------|-------|
| PowerQuery | `powerquery_enumerate_sources` | sentinelone-powerquery |
| PowerQuery | `powerquery_run` | sentinelone-powerquery |
| PowerQuery | `powerquery_schema_discover` | sentinelone-powerquery |
| Mgmt Console | `s1_api_get` | sentinelone-mgmt-console-api |
| Mgmt Console | `s1_api_post` | sentinelone-mgmt-console-api |
| Mgmt Console | `purple_ai_query` | sentinelone-mgmt-console-api |
| Mgmt Console | `uam_list_alerts` | sentinelone-mgmt-console-api |
| Mgmt Console | `uam_get_alert` | sentinelone-mgmt-console-api |
| Mgmt Console | `uam_add_note` | sentinelone-mgmt-console-api |
| Mgmt Console | `uam_set_status` | sentinelone-mgmt-console-api |
| SDL API | `sdl_list_files` | sentinelone-sdl-api / sdl-dashboard / sdl-log-parser |
| SDL API | `sdl_get_file` | sentinelone-sdl-api / sdl-dashboard / sdl-log-parser |
| SDL API | `sdl_put_file` | sentinelone-sdl-api / sdl-dashboard / sdl-log-parser |
| SDL API | `sdl_delete_file` | sentinelone-sdl-api |
| SDL API | `sdl_upload_logs` | sentinelone-sdl-api / sdl-log-parser |
| Hyperautomation | `ha_list_workflows` | sentinelone-hyperautomation |
| Hyperautomation | `ha_get_workflow` | sentinelone-hyperautomation |
| Hyperautomation | `ha_import_workflow` | sentinelone-hyperautomation |
| Hyperautomation | `ha_export_workflow` | sentinelone-hyperautomation |

**2 resources:**
- `sentinelone://soc-context`: CLAUDE.md (full SOC analyst operating instructions)
- `sentinelone://credentials-status`: Which credentials are configured

**2 prompts:**
- `soc_analyst`: Embeds CLAUDE.md as a system prompt; call at session start
- `session_init`: Structured initialization: enumerate sources + triage alerts in parallel

## Prerequisites

- Node.js 18 or later
- No `npm install` needed: zero external dependencies

## Credentials

Credentials are passed as environment variables in `claude_desktop_config.json` (see Installation below). The server also auto-discovers a `credentials.json` file by searching from the working directory upward as a backwards-compatible fallback for direct-skill users.

`S1_CONSOLE_URL` and `S1_CONSOLE_API_TOKEN` are sufficient for most tools. Add the SDL keys only if you need `sdl_upload_logs` (requires `SDL_LOG_WRITE_KEY`) or `sdl_put_file` (requires `SDL_CONFIG_WRITE_KEY`).

| Variable | Description |
|----------|-------------|
| `S1_CONSOLE_URL` | Your console URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_CONSOLE_API_TOKEN` | Management Console API token (Settings → Users → Service Users) |
| `S1_HEC_INGEST_URL` | HEC ingest host, e.g. `https://ingest.us1.sentinelone.net` |
| `SDL_XDR_URL` | SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net` |
| `SDL_LOG_WRITE_KEY` | SDL Log Write key (required for `sdl_upload_logs` only) |
| `SDL_LOG_READ_KEY` | SDL Log Read key (required for SDL query operations) |
| `SDL_CONFIG_WRITE_KEY` | SDL Config Write key (required for `sdl_put_file`) |
| `SDL_CONFIG_READ_KEY` | SDL Config Read key (required for `sdl_list_files`, `sdl_get_file`) |

## Run the server

```bash
# From the published npm package (no clone, no install)
npx -y @pmoses-s1/sentinelone-mcp

# Or from a local clone (development)
node /path/to/claude-skills/sentinelone-mcp/index.js
```

## Installation

### Why you need this (or the allowlist alternative)

The Claude sandbox proxy blocks outbound HTTPS to `*.sentinelone.net` by default. There are two ways to fix this:

**Option A: Install sentinelone-mcp (recommended).** The MCP server runs as a local process on your machine outside the sandbox. All API calls go directly from your machine to SentinelOne, bypassing the sandbox proxy entirely. No allowlist changes needed.

**Option B: Add `*.sentinelone.net` to the Claude sandbox allowlist.** In Claude Desktop go to Settings → Claude Code → Network Access and add `*.sentinelone.net` to the allowed domains. This lets the skills' Python scripts reach the API directly from inside the sandbox. Use this if you prefer to keep everything running in the sandbox rather than install a local server.

Most users should use Option A: it requires no admin changes and keeps credentials out of the sandbox environment.

### Option A: Add to Claude Desktop

In `~/Library/Application Support/Claude/claude_desktop_config.json`, add the `sentinelone-mcp` entry to your `mcpServers` block. The server runs via `npx` directly from npm, so there is no clone, no install, and no absolute path to manage. Credentials go in the `env` section:

```json
{
  "mcpServers": {
    "sentinelone-mcp": {
      "command": "npx",
      "args": ["-y", "@pmoses-s1/sentinelone-mcp"],
      "env": {
        "S1_CONSOLE_URL":        "https://usea1-yourorg.sentinelone.net",
        "S1_CONSOLE_API_TOKEN":  "eyJ...your-api-token...",
        "S1_HEC_INGEST_URL":     "https://ingest.us1.sentinelone.net",
        "SDL_XDR_URL":           "https://xdr.us1.sentinelone.net",
        "SDL_LOG_WRITE_KEY":     "0Z1Fy0...",
        "SDL_LOG_READ_KEY":      "0tzj...",
        "SDL_CONFIG_WRITE_KEY":  "0mXas6PD...",
        "SDL_CONFIG_READ_KEY":   "0MQTx..."
      }
    }
  }
}
```

`npx -y` answers "yes" to the install prompt on first launch, fetches the package, and caches it. Subsequent launches start instantly from the cache. Restart Claude Desktop after saving.

`S1_CONSOLE_URL` and `S1_CONSOLE_API_TOKEN` are the minimum required for most tools. Include the SDL keys only if you need log ingest or parser/dashboard deploy. Set `S1_CLAUDE_MD_PATH` if you keep CLAUDE.md outside your Cowork project folder.

### Option A: Add to Claude Code

In `.mcp.json` at your project root, or `~/.mcp.json` globally. Same npx invocation, same env block:

```json
{
  "mcpServers": {
    "sentinelone-mcp": {
      "command": "npx",
      "args": ["-y", "@pmoses-s1/sentinelone-mcp"],
      "env": {
        "S1_CONSOLE_URL":       "https://usea1-yourorg.sentinelone.net",
        "S1_CONSOLE_API_TOKEN": "eyJ...your-api-token..."
      }
    }
  }
}
```

### Option A: Run from a local clone (development only)

If you are developing the MCP server itself, replace the `npx` invocation with a path to your clone:

```json
"sentinelone-mcp": {
  "command": "node",
  "args": ["/absolute/path/to/claude-skills/sentinelone-mcp/index.js"],
  "env": { "...": "..." }
}
```

### Option B: Sandbox allowlist (no MCP server)

If you prefer to run API calls from inside the Claude sandbox rather than install a local server, add `*.sentinelone.net` to the network allowlist:

1. Open Claude Desktop → Settings → Claude Code → Network Access
2. Add `*.sentinelone.net` to the allowed domains
3. Restart Claude Desktop

The skills' Python scripts (`s1_client.py`, `sdl_client.py`, etc.) will then reach the API directly. No MCP server required for the skills to work.

## Workflow: session startup

When connecting to this MCP server, start every session with:

1. Read the `soc_analyst` prompt (or the `sentinelone://soc-context` resource) to load operating instructions from CLAUDE.md.
2. Call `powerquery_enumerate_sources` to discover active SDL data sources (mandatory: never assume sources from a prior session).
3. In parallel, call `uam_list_alerts` with `filter="status=OPEN"` to pull active alerts.

The `session_init` prompt automates steps 2-3 as a structured prompt.

## Architecture

```
sentinelone-mcp/
  index.js              Raw MCP JSON-RPC over stdio (no SDK dependency)
  lib/
    credentials.js      Auto-discovers credentials.json (env vars > file > walk-up > ~/mnt/*)
    s1.js               S1 Mgmt REST API + LRQ PowerQuery + Purple AI + UAM GraphQL
    sdl.js              SDL config files (get/put/list) + V1 query + uploadLogs
  tools/
    powerquery.js       PowerQuery enumerate/run/schema-discover tools
    mgmt-console.js     S1 REST + Purple AI + UAM tools
    sdl-api.js          SDL config file + log ingestion tools
    hyperautomation.js  Hyperautomation list/get/import/export tools
  README.md
```

## Auth patterns (implemented)

| API surface | Auth header | Key |
|-------------|-------------|-----|
| S1 Mgmt REST API | `Authorization: ApiToken <jwt>` | `S1_CONSOLE_API_TOKEN` |
| LRQ PowerQuery | `Authorization: Bearer <jwt>` | Same token, different prefix |
| Purple AI GraphQL | `Authorization: ApiToken <jwt>` | `S1_CONSOLE_API_TOKEN` |
| UAM GraphQL | `Authorization: ApiToken <jwt>` | `S1_CONSOLE_API_TOKEN` |
| SDL config ops | `Authorization: Bearer <key>` | `SDL_CONFIG_WRITE_KEY` or console JWT |
| SDL uploadLogs | `Authorization: Bearer <key>` | `SDL_LOG_WRITE_KEY` only (console JWT rejected) |

## Updating CLAUDE.md

The `sentinelone://soc-context` resource and `soc_analyst` prompt load CLAUDE.md at server startup. Resolution order (highest priority wins):

1. `S1_CLAUDE_MD_PATH` env var (explicit absolute path)
2. `<cwd>/CLAUDE.md` (your Cowork project folder when launched from a project)
3. Same-dir / parent / grandparent of the server's `index.js` (when running from a git clone)

For npx installs, drop a copy of CLAUDE.md into your Cowork project folder, or set `S1_CLAUDE_MD_PATH` in the `env` block of `claude_desktop_config.json`. Restart Claude Desktop to pick up changes.
