---
name: sentinelone-sdl-api
author: Prithvi Moses <prithvi.moses@sentinelone.com>
description: Use whenever the user wants to read or write data through the SentinelOne Singularity Data Lake (SDL) API — ingest events, run queries, or manage configuration files (parsers, dashboards, alerts, lookups, datatables) on a Scalyr/SDL/XDR tenant. Trigger on "SDL", "SDL API", "Singularity Data Lake", "Scalyr", "DataSet", "xdr.us1.sentinelone.net" or any "*.sentinelone.net/api/*" URL, and on the method names "uploadLogs", "addEvents", "query", "powerQuery", "facetQuery", "timeseriesQuery", "numericQuery", "getFile", "putFile", "listFiles". Also trigger on tasks like "ingest a log file into SDL", "send a JSON event to the data lake", "run a powerQuery", "list configuration files", "edit my parser via API", "deploy a dashboard JSON", "compute the rate of failures over time", or anything involving Log Read / Log Write / Configuration Read / Configuration Write SDL keys, Bearer-token auth, or the S1-Scope header. Wraps every SDL method with a Python client and CLI.
---

# SentinelOne SDL API

Wraps the Singularity Data Lake API (10 methods across log ingestion, query, and configuration files) with a pre-built Python client, a CLI runner, and a per-method reference.

The SDL API is distinct from the Management Console API. It speaks JSON over `Bearer` tokens (not `ApiToken`) and is the canonical path for ingesting custom telemetry and editing parsers/dashboards/alerts/lookups directly.

## IMPORTANT: query methods are deprecated — and LRQ is NOT available here

The query methods on this skill (`query`, `powerQuery`, `facetQuery`, `timeseriesQuery`, `numericQuery`) wrap the V1 SDL endpoints (`/api/query`, `/api/powerQuery`, etc.) at the centralized host `xdr.us1.sentinelone.net`. Those endpoints are **deprecated and sunset on 2027-02-15** (also applies to the Deep Visibility `/web/api/v2.1/dv/events/pq` endpoint).

**The LRQ API is NOT a replacement available through this skill.** LRQ runs at `POST /sdl/v2/api/queries` on the tenant's own **Management Console** host (e.g. `your-tenant.sentinelone.net`) — it is part of the Mgmt Console API surface, not the SDL API (`xdr.us1.sentinelone.net`). To run PowerQueries programmatically, use the **`sentinelone-mgmt-console-api`** skill which holds the LRQ runner, auth pattern, and slicing strategy.

**SDL dashboard panels do not use LRQ either.** Dashboard panel queries are executed by the SDL console's own built-in rendering engine when a user loads the dashboard in their browser. The panel JSON just stores the query string — no API call is needed. Do not attempt to test or run dashboard panel queries via LRQ.

| Task | Correct skill / path |
|------|------|
| PowerQuery programmatically (any range) | **`sentinelone-mgmt-console-api`** → LRQ at `POST /sdl/v2/api/queries` on console host |
| Dashboard panel queries | SDL console renders them in-browser — no API needed |
| Quick one-off stats under 24h (deprecated) | V1 methods on this skill still work until 2027-02-15 |
| `upload_logs` / `add_events` (ingestion) | **This skill** — LRQ is query-only and on the console host |
| `get_file` / `put_file` / `list_files` (parsers, dashboards, lookups) | **This skill** |

## Setup — configure credentials first

Drop a file at `$COWORK_WORKSPACE/.sentinelone/credentials.json` (or any folder Cowork has access to under `.sentinelone/credentials.json`) with the keys you need:

```json
{
  "SDL_XDR_URL":          "https://xdr.us1.sentinelone.net",
  "S1_CONSOLE_API_TOKEN": "eyJ...your-token...",
  "SDL_LOG_WRITE_KEY":    "0Z1Fy0...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD1Zvg..."
}
```

The plugin's SessionStart hook auto-copies the file to `$HOME/.claude/sentinelone/credentials.json` inside the sandbox at the start of every session, so the SDL client picks it up with no preflight. To trigger a manual refresh:

```bash
bash scripts/bootstrap_creds.sh   # idempotent, returns the destination path
```

Each key type unlocks a specific set of methods (matrix below). The client picks the right key per method automatically; callers never hand-pick a token.

| Key | Methods unlocked |
|-----|-----------------|
| Log Write Access        | `uploadLogs`, `addEvents` |
| Log Read Access         | `query`, `numericQuery`, `facetQuery`, `timeseriesQuery`, `powerQuery` |
| Configuration Read      | All Log Read methods, plus `getFile`, `listFiles` |
| Configuration Write     | All of the above, plus `putFile` |
| `S1_CONSOLE_API_TOKEN` (mgmt-console JWT)  | All query + config methods (NOT `uploadLogs`); set `SDL_S1_SCOPE` if multi-site/account. Same JWT used by `S1Client`. (Legacy alias `SDL_CONSOLE_API_TOKEN` still recognised.) |

Environment variables (`SDL_XDR_URL`, `S1_CONSOLE_API_TOKEN`, `SDL_LOG_WRITE_KEY`, etc.) still override the credentials file if set. Legacy paths (`~/.config/sentinelone/credentials.json`, `~/.claude/sentinelone/credentials.json`, `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json`) are read as fallbacks.

Before running anything, confirm `SDL_XDR_URL` is set and at least one key for the operation chain is present. If not, stop and ask the user to drop `credentials.json` into a folder Cowork can access.

## Workflow

When the user asks for something involving the SDL API:

1. **Pick the method.** Check `references/methods.md` for the right call. For **ingestion** (`upload_logs`, `add_events`) and **configuration files** (`get_file`, `put_file`, `list_files`), this skill is the right tool. For **queries**, use the V1 methods on this skill only for quick one-off stats under 24h; for anything programmatic or multi-day, switch to the **`sentinelone-mgmt-console-api`** skill and the LRQ API — LRQ is NOT available at the SDL API host (`xdr.us1.sentinelone.net`).
2. **Use the client.** `from sdl_client import SDLClient` then call the named method (`upload_logs`, `add_events`, `query`, `power_query`, `facet_query`, `timeseries_query`, `numeric_query`, `list_files`, `get_file`, `put_file`). The client picks the correct key, handles JSON encoding, retries 429/5xx/`error/server/backoff`, and returns parsed JSON. Note: `query` and `power_query` hit the deprecated V1 endpoints — they work until 2027-02-15 for quick lookups but should not be used for production query pipelines.
3. **For ad-hoc shots, use the CLI.** `python scripts/sdl_cli.py <method> [args]`. The CLI mirrors the client.
4. **Summarize for the user.** Don't dump raw JSON unless asked. For query results, prefer a concise table or CSV; for ingestion, confirm `bytesCharged` and the session ID; for config files, show path + version + (truncated) content.

## Files in this skill

- `$COWORK_WORKSPACE/.sentinelone/credentials.json` — credentials (set `SDL_XDR_URL` and the keys you need; see Setup above). Auto-copied to `$HOME/.claude/sentinelone/credentials.json` inside the sandbox by the plugin's SessionStart hook.
- `scripts/bootstrap_creds.sh` — idempotent helper that copies workspace creds into the sandbox-local path. Wired to the plugin's SessionStart hook; safe to re-run manually.
- `scripts/sdl_client.py` — importable Python client (`SDLClient`). Picks the right key per method, retries with exponential backoff, exposes ergonomic method names.
- `scripts/sdl_cli.py` — CLI runner: `python scripts/sdl_cli.py power-query "dataset='accesslog' | group count() by status" --start 1h`.
- `references/methods.md` — single per-method reference (parameters, defaults, response shape, gotchas) for all 10 SDL endpoints.
- `references/auth_and_limits.md` — key matrix, console-token rules, S1-Scope, leaky-bucket CPU rate-limit model, retry guidance, daily caps.
- `references/integration_patterns.md` — addEvents session/sessionInfo discipline, batching, structured vs unstructured events, fault-tolerance loop pseudo-code.

## Using the client

```python
import sys
sys.path.insert(0, "scripts")
from sdl_client import SDLClient

c = SDLClient()

# ---- Log read ----
# PowerQuery — best general-purpose tool
res = c.power_query(
    query="dataset='accesslog' status >= 400 | group count() by status",
    start_time="1h",
)
# res = {"status": "success", "matchingEvents": ..., "columns": [...], "values": [[...], ...]}

# Raw event search
matches = list(c.iter_query(filter="error", start_time="15m", max_total=500))

# Top-N values
top_ips = c.facet_query(field="srcIp", filter="status >= 400", start_time="24h", max_count=20)

# Numeric / timeseries (1 query)
ts = c.timeseries_query(queries=[
    {"filter": "serverHost contains 'frontend'", "function": "count", "startTime": "1h", "buckets": 60}
])

# ---- Log write ----
# Plain text upload (uploadLogs requires a Log Write key, NOT a console token)
c.upload_logs("Log line 1\nLog line 2", parser="my-parser", server_host="dev-box")

# Structured ingest with addEvents — session ID must persist for the life of the upload process
sess = c.new_session_id()
c.add_events(
    session=sess,
    session_info={"serverHost": "demo-host", "serverType": "frontend"},
    events=[
        {"ts": c.now_ns(), "sev": 3,
         "attrs": {"message": "user login", "user": "prithvi", "latencyMs": 42}},
    ],
)

# ---- Configuration files ----
# Parsers live under /logParsers/<name> — the SDL API also accepts /parsers/<name>
# but the Log Parsers UI only reads /logParsers/, so PUTs at /parsers/ are invisible
# in the console. Use /logParsers/<name> by default.
files = c.list_files()                        # {"status":"success","paths":["/foo", ...]}
parser = c.get_file("/logParsers/MyParser")   # {"status":"success","content":"...","version":7,...}
c.put_file("/logParsers/MyParser", content="// new parser body")
c.put_file("/logParsers/Stale", delete=True)
```

## Authentication

Every request sets `Authorization: Bearer <token>`. The client picks the key per method using these chains (first non-empty wins):

- `log_write` (addEvents):   `log_write_key` → `console_api_token`
- `log_write_strict` (uploadLogs): `log_write_key` only — uploadLogs rejects console tokens
- `log_read`:    `log_read_key` → `config_read_key` → `config_write_key` → `console_api_token`
- `config_read`: `config_read_key` → `config_write_key` → `console_api_token`
- `config_write` (putFile): `config_write_key` → `console_api_token`

If a `console_api_token` is used and the user has access to multiple sites or accounts, set `s1_scope` (e.g. `"<account_id>:<site_id>"` for site scope, `"<account_id>"` for account scope). The client adds `S1-Scope` automatically when both conditions hold.

A 401 with `error/client/noPermission` means the token is wrong or expired. SDL keys do not expire by default, but console user tokens do — for ingestion, prefer a Log Write Access key.

## Rate limits and retries

The client retries automatically on HTTP 429, 5xx, and SDL `status: error/server/backoff` (which can come back inside a 200), honouring `Retry-After`. Things to know up-front:

- **Query budget is a leaky bucket of CPU seconds.** When `cpuUsageSecondsToWait` shows in a 429, back off by that many seconds. `priority: "low"` (the default) gets a more generous bucket than `"high"`. See `references/auth_and_limits.md` for the bucket model.
- **From 19 March 2026, all query methods cap at 8 queries/sec per tenant.**
- **`uploadLogs` is hard-capped at 10 GB/day** and 6 MB per request. For higher volume use `add_events`.
- **`addEvents` sessions:** keep ≤ 2.5 MB/s per session, 10 MB/s max, ≤ 50K sessions per 5-min window. Only one in-flight request per session — if you parallelise, use multiple sessions, not one shared session.
- **Concurrency cap:** 12 simultaneous requests per API key (non-query). For loops, throttle in code.

For long-running ingest, use the binary truncated exponential backoff loop in `references/integration_patterns.md` rather than the client's default retries — it is designed to stop on `discardBuffer` and to slowly relax wait times after success.

## Destructive actions — confirm first

`put_file(delete=True)` and `put_file(content=...)` overwriting an existing path can wipe a parser, dashboard, alert, or lookup table. Before any `putFile` write or delete:

- Run `get_file` first to read current `version` and content. Pass that version as `expected_version` on the write to fail-fast on a concurrent edit (`error/client/versionMismatch`).
- For deletes, summarise the path and last-modified date and get explicit confirmation.
- Keep a backup in the working directory before overwriting non-trivial parsers or dashboards.

There is no undo. Configuration files are versioned but accidental deletes still take effect immediately.

## Common high-value workflows

- **Hunt with PowerQuery.** Use the **`sentinelone-mgmt-console-api`** skill, which holds the LRQ runner at `POST /sdl/v2/api/queries` on your console host. LRQ is NOT reachable via the SDL API (`xdr.us1.sentinelone.net`). This skill's `c.power_query()` hits the deprecated V1 endpoint and should only be used for a quick ad-hoc one-off before 2027-02-15.
- **Webhook → SDL.** Stateless ingest from a Lambda/CF Worker: `c.upload_logs(json.dumps(event), parser="my-webhook-parser", nonce=event_id)`. Reuse the same nonce on retries to dedupe.
- **Bulk structured ingest.** Generate one session ID at process start, batch events to ~5 MB, call `add_events(session=sess, events=batch)` in a loop. Honour the backoff pattern.
- **Promote a parser/dashboard.** `get_file("/logParsers/Foo")` from staging → `put_file("/logParsers/Foo", content=..., expected_version=N)` on production. The `expected_version` guard catches concurrent edits. (Parser path is `/logParsers/` — `/parsers/` is API-accepted but not UI-visible.)
- **Audit configuration drift.** `list_files()` then `get_file()` for each path; diff against a checked-in copy.
- **Quick stats panel.** `facet_query(field="srcIp", filter="status >= 500", start_time="1h")` returns the top offenders fast.

For complex hunts and detection authoring use the `sentinelone-powerquery` skill for the query body, then call `c.power_query()` from this skill to execute it. For Mgmt Console resources (agents, threats, sites) use `sentinelone-mgmt-console-api`.
