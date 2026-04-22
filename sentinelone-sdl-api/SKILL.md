---
name: sentinelone-sdl-api
description: Use whenever the user wants to read or write data through the SentinelOne Singularity Data Lake (SDL) API — ingest events, run queries, or manage configuration files (parsers, dashboards, alerts, lookups, datatables) on a Scalyr/SDL/XDR tenant. Trigger on "SDL", "SDL API", "Singularity Data Lake", "Scalyr", "DataSet", "xdr.us1.sentinelone.net" or any "*.sentinelone.net/api/*" URL, and on the method names "uploadLogs", "addEvents", "query", "powerQuery", "facetQuery", "timeseriesQuery", "numericQuery", "getFile", "putFile", "listFiles". Also trigger on tasks like "ingest a log file into SDL", "send a JSON event to the data lake", "run a powerQuery", "list configuration files", "edit my parser via API", "deploy a dashboard JSON", "compute the rate of failures over time", or anything involving Log Read / Log Write / Configuration Read / Configuration Write SDL keys, Bearer-token auth, or the S1-Scope header. Wraps every SDL method with a Python client and CLI.
---

# SentinelOne SDL API

Wraps the Singularity Data Lake API (10 methods across log ingestion, query, and configuration files) with a pre-built Python client, a CLI runner, and a per-method reference.

The SDL API is distinct from the Management Console API. It speaks JSON over `Bearer` tokens (not `ApiToken`) and is the canonical path for ingesting custom telemetry and editing parsers/dashboards/alerts/lookups directly.

## IMPORTANT: query methods are deprecated, use LRQ

The query methods on this skill (`query`, `powerQuery`, `facetQuery`, `timeseriesQuery`, `numericQuery`) wrap the V1 SDL endpoints (`/api/query`, `/api/powerQuery`, etc.) at the centralized host `xdr.us1.sentinelone.net`. Those endpoints are **deprecated and sunset on 2027-02-15** (also applies to the Deep Visibility `/web/api/v2.1/dv/events/pq` endpoint). The replacement is the **Long Running Query (LRQ) API** at `POST /sdl/v2/api/queries` on the tenant's own console host.

**Default to LRQ for every new query.** It is async, handles queries that would otherwise time out, supports cursor paging to effectively unlimited rows, raises the per-account rate cap to 100 rps, and is the only path that stays supported after 2027-02-15. Measured on `usea1-purple` for a 30-day count-by-event.type over 574M events: 166s serial baseline drops to 28.5s with a two-service-user-JWT round-robin at pool=6.

When to use LRQ vs this skill:

| Task | Path |
|------|------|
| PowerQuery (any range, especially multi-day or high-volume) | **LRQ** via `sentinelone-powerquery` skill (`references/lrq-api.md`) |
| Log search (`query`/`iter_query`) for long windows or large result sets | **LRQ** (queryType="LOG") |
| Quick one-off stats (`facet_query`, `timeseries_query`, `numeric_query`) under 24h | Either - V1 still works until 2027-02-15 |
| `upload_logs` / `add_events` (ingestion) | **This skill** - LRQ is query-only |
| `get_file` / `put_file` / `list_files` (parsers, dashboards, lookups, datatables) | **This skill** - LRQ doesn't cover config files |

The canonical LRQ runner, body schema, auth, forward-tag routing, rate-limit strategy, and measured benchmark live in the `sentinelone-powerquery` skill at `references/lrq-api.md`. Read that before writing a programmatic query runner.

## Setup — configure credentials first

Credentials live in `config.json` at the skill root. Fill in the fields you need:

```json
{
  "base_url": "https://xdr.us1.sentinelone.net",
  "log_write_key":   "0Z1Fy0...",
  "log_read_key":    "0tzj/CPYTZX6...",
  "config_read_key": "0MQTxgjueeKjo...",
  "config_write_key":"0mXas6PD1Zvg...",
  "console_api_token": "",
  "s1_scope": ""
}
```

Each key type unlocks a specific set of methods (matrix below). The client picks the right key per method automatically — callers never hand-pick a token.

| Key | Methods unlocked |
|-----|-----------------|
| Log Write Access        | `uploadLogs`, `addEvents` |
| Log Read Access         | `query`, `numericQuery`, `facetQuery`, `timeseriesQuery`, `powerQuery` |
| Configuration Read      | All Log Read methods, plus `getFile`, `listFiles` |
| Configuration Write     | All of the above, plus `putFile` |
| Console User API token  | All query + config methods (NOT `uploadLogs`); set `s1_scope` if multi-site/account |

Environment variables override `config.json`: `SDL_BASE_URL`, `SDL_LOG_WRITE_KEY`, `SDL_LOG_READ_KEY`, `SDL_CONFIG_READ_KEY`, `SDL_CONFIG_WRITE_KEY`, `SDL_CONSOLE_API_TOKEN`, `SDL_S1_SCOPE`, `SDL_VERIFY_TLS`.

Before running anything, confirm `base_url` is set and at least one key for the operation chain is present. If not, stop and ask the user.

## Workflow

When the user asks for something involving the SDL API:

1. **Pick the method.** Check `references/methods.md` for the right call (search/ingest/file). For **queries**, default to the LRQ API via the `sentinelone-powerquery` skill - see the deprecation table above. For **ingestion** (`upload_logs`, `add_events`) and **configuration files** (`get_file`, `put_file`, `list_files`), this skill is still the right tool. For quick one-off stats under 24h (`facet_query`, `timeseries_query`, `numeric_query`), either path works until 2027-02-15.
2. **Use the client.** `from sdl_client import SDLClient` then call the named method (`upload_logs`, `add_events`, `query`, `power_query`, `facet_query`, `timeseries_query`, `numeric_query`, `list_files`, `get_file`, `put_file`). The client picks the correct key, handles JSON encoding, retries 429/5xx/`error/server/backoff`, and returns parsed JSON. Note: `query` and `power_query` go to the V1 deprecated endpoints - for production query work, route through LRQ instead.
3. **For ad-hoc shots, use the CLI.** `python scripts/sdl_cli.py <method> [args]`. The CLI mirrors the client.
4. **Summarize for the user.** Don't dump raw JSON unless asked. For query results, prefer a concise table or CSV; for ingestion, confirm `bytesCharged` and the session ID; for config files, show path + version + (truncated) content.

## Files in this skill

- `config.json` — credentials. The user updates these.
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

- **Hunt with PowerQuery.** Route through the LRQ API, not `c.power_query()`. Use the `sentinelone-powerquery` skill - it covers the PQ syntax and the LRQ runner pattern (auth, body, forward-tag, rate limits, slicing). Only fall back to `c.power_query()` on this skill for a quick ad-hoc one-off; even then, the V1 `/api/powerQuery` endpoint is deprecated and will retire 2027-02-15.
- **Webhook → SDL.** Stateless ingest from a Lambda/CF Worker: `c.upload_logs(json.dumps(event), parser="my-webhook-parser", nonce=event_id)`. Reuse the same nonce on retries to dedupe.
- **Bulk structured ingest.** Generate one session ID at process start, batch events to ~5 MB, call `add_events(session=sess, events=batch)` in a loop. Honour the backoff pattern.
- **Promote a parser/dashboard.** `get_file("/logParsers/Foo")` from staging → `put_file("/logParsers/Foo", content=..., expected_version=N)` on production. The `expected_version` guard catches concurrent edits. (Parser path is `/logParsers/` — `/parsers/` is API-accepted but not UI-visible.)
- **Audit configuration drift.** `list_files()` then `get_file()` for each path; diff against a checked-in copy.
- **Quick stats panel.** `facet_query(field="srcIp", filter="status >= 500", start_time="1h")` returns the top offenders fast.

For complex hunts and detection authoring use the `sentinelone-powerquery` skill for the query body, then call `c.power_query()` from this skill to execute it. For Mgmt Console resources (agents, threats, sites) use `sentinelone-mgmt-console-api`.
