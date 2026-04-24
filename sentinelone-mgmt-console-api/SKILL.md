---
name: sentinelone-mgmt-console-api
author: Prithvi Moses <prithvi.moses@sentinelone.com>
description: Use whenever the user wants to query, update, create, or act on a SentinelOne Management Console — threats, alerts, agents, sites, accounts, groups, exclusions, RemoteOps, Deep Visibility, Hyperautomation, Unified Alert Management (UAM), Purple AI, IOCs, or any other S1 Mgmt API resource. Trigger on "console", "query/update/create console", "SentinelOne", "S1", "Singularity", "UAM", "Purple AI", "/web/api/v2.1/...", S1 agent/threat/site IDs, or asks like "list endpoints", "triage alerts", "add note to alert", "create an IOC", "isolate endpoint", "run RemoteOps", "pull DV results". For alerts the PRIMARY API is GraphQL UAM at /web/api/v2.1/unifiedalerts/graphql; REST /cloud-detection/alerts is SECONDARY (older, cloud-detection scoped, int64 IDs). Defer to Purple MCP if the user says "purple mcp" or "mcp"; this skill is the backup then. Wraps the S1 Mgmt REST API (781 ops, 113 tags, v2.1) plus UAM GraphQL and Purple AI GraphQL, with a Python client, searchable index, and reversible tests.
---

# SentinelOne Management Console API

Wraps the SentinelOne Management Console API (Swagger 2.0, spec version 2.1, 781 operations) with a pre-built Python client, a compact endpoint index, and per-tag reference files.

## Setup — configure credentials first

Credentials are loaded from `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json`. The two required fields are:

```json
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-api-token..."
}
```

`S1_BASE_URL` is the tenant console URL (no trailing slash, no `/web/api/v2.1`). `S1_API_TOKEN` is an API User token from Settings → Users → Service Users in the S1 console.

Environment variables (`S1_BASE_URL`, `S1_API_TOKEN`, `S1_VERIFY_TLS`) override the credentials file if set.

Before running anything, confirm credentials are configured. If not, stop and ask the user to create `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json`.

## Workflow

When the user asks for something involving the S1 API, follow this pattern:

1. **Find the right endpoint.**
   - If the user's ask is verb-shaped ("list / count / isolate / hunt …") and you need orientation, read `references/CAPABILITY_MAP.md` first — it's a compact per-tag summary of what verbs each resource supports.
   - For a specific multi-step task ("threat triage", "endpoint isolation", "DV hunt"), `references/WORKFLOWS.md` has ready-to-adapt recipes.
   - Otherwise go straight to `scripts/search_endpoints.py` with a keyword matching the user's intent. It now ranks results by relevance (path segment hits + verb intent + tag) and supports synonyms ("isolate" → "disconnect", "endpoint" → "agent"). Add `--only-works` to restrict to endpoints confirmed reachable on this tenant by the most recent smoke test.
2. **Read the per-tag reference.** Open `references/tags/<Tag>.md` (names match the table in `references/TAG_INDEX.md`) to see full parameter lists, descriptions, required permissions, and response codes for that group. Only read the tag file(s) relevant to the task — don't read them all.
3. **Call the endpoint.** Either use `scripts/call_endpoint.py` for one-off calls, or import `S1Client` from `scripts/s1_client.py` in a Python script for anything that needs loops, joins, or transforms. For independent GETs, prefer `c.get_many([(path, params), ...])` — it fans out in parallel over the client's pooled connection and is ~3× faster than a sequential loop.
4. **Paginate correctly.** S1 list endpoints use cursor-based pagination. The client's `paginate()` and `iter_items()` handle this automatically — prefer them over manual `skip`/`limit` math, which caps at 1000 items.
5. **Summarize the result for the user.** Don't dump raw JSON unless asked. Prefer a short prose summary plus a table or CSV/XLSX if the volume warrants.

## Probing a new tenant

When starting on an unfamiliar tenant, run the non-destructive smoke test once:

```
python scripts/smoke_test_queries.py --workers 12
```

It enumerates every GET plus a curated allow-list of read-only query POSTs, records which ones return 200/403/404/etc., and writes `references/tenant_capabilities.md` and `.json`. Useful for "what's this token actually allowed to do" and as a pre-sales capability snapshot. The sweep is read-only — no writes, no agent actions — so tenant start-state and end-state are identical.

## Files in this skill

- `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` — credentials (set `S1_BASE_URL` and `S1_API_TOKEN`; see Setup above).
- `scripts/s1_client.py` — importable Python client. Handles auth, pooled HTTP connections, retries on 429/5xx, pagination, parallel fan-out via `get_many()`, and optional short-TTL response caching for rarely-changing reads (accounts, sites, groups, system/info, etc.).
- `scripts/call_endpoint.py` — CLI for one-shot calls: `python scripts/call_endpoint.py GET /web/api/v2.1/agents --param limit=5`.
- `scripts/search_endpoints.py` — ranked keyword search over the endpoint index, with synonym expansion and an `--only-works` filter that restricts to endpoints confirmed reachable on this tenant.
- `scripts/smoke_test_queries.py` — non-destructive sweep of every GET + safe query POST. Writes `references/tenant_capabilities.{json,md}`. Read-only; tenant state unchanged.
- `scripts/purple_ai.py` — Purple AI natural-language wrapper over `POST /web/api/v2.1/graphql` (undocumented endpoint). Exports `purple_query()` and `PurpleAIError`.
- `scripts/call_purple.py` — CLI wrapper: `python scripts/call_purple.py "show powershell.exe outbound connections"`.
- `scripts/unified_alerts.py` — Unified Alert Management (UAM) GraphQL wrapper over `POST /web/api/v2.1/unifiedalerts/graphql`. Covers the full query + mutation surface (list/filter/group/notes/history/trigger-actions). See `references/UNIFIED_ALERTS.md`.
- `scripts/call_unified_alerts.py` — CLI for UAM: `python scripts/call_unified_alerts.py list --filter detectionProduct=EDR --first 10`, `... add-note <id> "…"`, `... set-status --scope <acct> --alert-id <id> RESOLVED`.
- `references/UNIFIED_ALERTS.md` — UAM reference: operation catalogue, schema quirks, filter patterns, action catalogue, worked recipes.
- `references/TAG_INDEX.md` — table of all 113 tags with file pointers and op counts. Start here when you don't know which tag owns an endpoint.
- `references/CAPABILITY_MAP.md` — per-tag verb-and-resource summary (L=list, G=get-one, C=count, E=export, A=action, F=filter, S=search, X=mutate) plus an "I want to…" quick lookup. Your fastest orientation when you know the verb but not the path.
- `references/WORKFLOWS.md` — ready-to-adapt multi-step recipes: threat triage, endpoint isolation, DV / PowerQuery hunt, RemoteOps, audit trail, tenant capability snapshot, etc. Each lists the endpoints you actually need and the params that matter.
- `references/tenant_capabilities.{json,md}` — auto-generated by `smoke_test_queries.py`: per-endpoint status (200/403/404/etc.) for the configured tenant. Regenerate whenever the token or tenant changes. The committed copy is a worked example from the Purple demo tenant.
- `references/endpoint_index.json` — compact machine-readable index (one entry per op). Used by `search_endpoints.py` but can be read directly if you need to filter programmatically.
- `references/tags/<Tag>.md` — per-tag reference with parameters, descriptions, and required permissions. Load only the files you need.
- `references/common_params.md` — shared query params (`skip`, `limit`, `cursor`, `sortBy`, etc.) and the pagination pattern.
- `references/POWERQUERY_RECIPES.md` — PowerQuery / SDL query recipes tested on-tenant: indicator prevalence, PowerShell outbound to public IPs, failed-login triage, storyline activity summary, UAM-indicator SDL crosscheck, endpoint heartbeat. For full PQ language reference use the dedicated `sentinelone-powerquery` skill.
- `spec/swagger_2_1.json` — the original full Swagger spec (14 MB). Use only when the per-tag reference is insufficient — e.g. to resolve a deeply nested request-body schema by `$ref`. Never read this whole file into context.
- `tests/test_ioc_lifecycle.py` — reversible CREATE → LIST → DELETE → VERIFY round-trip for Threat Intelligence IOCs. Uses a unique run-tag per invocation, scopes to a single account, and cleans up before exit. Covers the one "create content" path against the S1 detection surface.
- `tests/test_alerts_dual_api.py` — dual-API round-trip for alerts: GraphQL list/detail/addNote/notes/deleteNote plus a parallel REST `/cloud-detection/alerts` read. Demonstrates that UAM GraphQL is the PRIMARY alert surface and REST is SECONDARY, with the note mutation cleaned up before exit (handles the `mgmt_note_id` propagation delay).
- `scripts/pq.py` — foolproof PowerQuery runner over the LRQ API. Wraps launch/poll/cancel, auth flip to `Bearer`, `X-Dataset-Query-Forward-Tag` capture, exponential backoff on 5xx/429/connection errors, and a best-effort cancel. One call: `run_pq(client, "<query>", hours=24)` returns `{row_count, columns, rows, matchCount, ...}`. Also exposes `list_data_sources(client, hours=24)` for the first-response "does this data source actually exist on this tenant?" check. Use this any time a user says "query logs", "run a PQ", "search for events" via the mgmt console API.
- `scripts/inspect_source.py` — source-agnostic schema discovery. For any `dataSource.name`, samples raw events via the LRQ `LOG` queryType (or sync `/sdl/api/query` when available) and classifies every attribute the parser emits into `principal_user` / `principal_host` / `principal_ip` / `action` / `temporal` / `network` / `file` / `process` / `grouping_candidate` / `other`. Picks `prim_key` + `action_key` from whatever the source actually carries, so downstream code never hardcodes field names. Exports `discover_schema(client, source, hours, sample, extra_filter, backend, escalate)` and `pick_keys(schema)`; CLI: `python scripts/inspect_source.py --source "<name>" --window 24h`. See "Data source + schema discovery" below.
- `scripts/uam_alert_interface.py` — UAM (Unified Alert Management) Alert Interface client for pushing OCSF indicators + alerts INTO UAM via `POST /v1/indicators` and `POST /v1/alerts` on `ingest.us1.sentinelone.net`. Handles the gzip-compressed concatenated-JSON body, `Bearer` auth (the endpoint rejects `ApiToken`), and the `S1-Scope` header. Exposes `UAMAlertInterfaceClient`, plus `build_file_indicator()`, `build_process_indicator()`, `build_network_indicator()`, and `build_alert_referencing()` payload helpers. URL defaults to `https://ingest.us1.sentinelone.net`; legacy key `ingestion_gateway_url` is still honored as a fallback.
- `tests/test_uam_alert_interface_single.py` — minimum-viable reversible write-side round-trip: POST one OCSF FileSystem-Activity indicator + one SecurityAlert referencing it, poll UAM GraphQL until the alert surfaces, verify the indicator is stitched in, then close the alert via bulk-ops (status=RESOLVED, analystVerdict=TRUE_POSITIVE_BENIGN). Covers the single-indicator happy path into UAM.
- `tests/test_uam_alert_interface_batch.py` — comprehensive reversible round-trip: batched POST of 3 indicators (OCSF classes 1001 FileSystem Activity, 1007 Process Activity, 4001 Network Activity) each carrying 3+ observables, referenced by a single SecurityAlert via `finding_info.related_events[]`. Verifies all 3 metadata.uids and their observable names surface in `alert.rawIndicators`, then closes the alert. Covers batching, multi-observable, and multi-indicator linkage.
- `scripts/ingestion_gateway.py` + `tests/test_ingestion_gateway_alert_with_indicator.py` — deprecated back-compat shims. The helper re-exports from `uam_alert_interface`; the test prints a pointer to the renamed file and exits non-zero.
- `scripts/build_source_report.py`: collector for the CTO report pipeline. Runs dimension probes + per-principal mix + timeline for a named data source via `scripts/pq.py` and writes `reports/<slug>_<window>/data.json`. Outputs to a per-source subfolder so multiple sources and windows coexist cleanly.
- `scripts/render_charts.py`: pure-function renderer. `data.json` in, PNG charts out under `reports/<slug>_<window>/charts/`. No tenant calls.
- `scripts/build_docx.py` / `scripts/build_pptx.py`: source-agnostic renderers that read `data.json` and emit `<Slug>_CTO_Report_<window>.docx` and `<Slug>_CTO_Deck_<window>.pptx`. Every section is gated on `dims` so dimension-sparse sources render cleanly. See "CTO report generation pipeline" below for the full contract and renderer gotchas.
- `reports/<slug>_<window>/`: per-run artefact directory. Holds `data.json`, `charts/`, and the rendered `.docx` / `.pptx`. Treat this as the portable unit: move or archive the whole folder.

## Using the client in Python

```python
import sys
sys.path.insert(0, "scripts")  # or set PYTHONPATH
from s1_client import S1Client, S1APIError

c = S1Client(cache_ttl=60)   # optional 60s cache for accounts/sites/groups/system-info

# single page
r = c.get("/web/api/v2.1/threats", params={"limit": 100, "resolved": False})

# full iteration
for threat in c.iter_items("/web/api/v2.1/threats", params={"limit": 200}):
    ...

# parallel fan-out — independent GETs over pooled connections (~3× faster)
results = c.get_many([
    ("/web/api/v2.1/accounts", {"limit": 1}),
    ("/web/api/v2.1/sites",    {"limit": 1}),
    ("/web/api/v2.1/groups",   {"limit": 1}),
    ("/web/api/v2.1/system/info", None),
], max_workers=8)
# -> [{"path":..., "ok":True, "status":200, "data":..., "elapsed_ms":...}, ...]

# action endpoint
c.post("/web/api/v2.1/agents/actions/disconnect", json_body={"filter": {"ids": ["AGENT_ID"]}})
```

## Authentication

The API uses header auth: `Authorization: ApiToken <token>`. The client injects this automatically — do not hand-roll headers.

Token scopes are enforced server-side. Each endpoint in the per-tag references lists `Required permissions` — if a 403 comes back, the token lacks one of those scopes, and the fix is a new token (not a code change). Surface this clearly to the user.

## Rate limits and retries

The client retries automatically on 429 and 5xx with exponential backoff (max 30s), honoring `Retry-After` when present. For bulk operations across thousands of entities, prefer a single filtered action endpoint (`/agents/actions/...`) over a loop of per-ID calls — the API is designed around filter-based bulk ops.

## Destructive actions — confirm first

Many endpoints are destructive or operationally sensitive: disconnect/reconnect agent, uninstall, isolate, shutdown, decommission, script execution via RemoteOps, policy changes, user mutations, account/site deletion. Before firing any `POST`/`PUT`/`DELETE` that affects agents, policies, or tenant config, summarize exactly what will happen (endpoint, filter, estimated scope) and get explicit user confirmation. A 200 response on a wrong filter can isolate thousands of endpoints — there is no undo on many of these.

The safe pattern: run the matching `GET` with `countOnly=true` first to show the blast radius, then the mutating call.

## Purple AI — natural-language query

> **Precedence:** if the user explicitly mentions "purple mcp" or "mcp", prefer the Purple MCP tools (`mcp__purple-mcp__purple_ai`, `mcp__purple-mcp__powerquery`, etc.) — this skill is the backup path in that case. Use the wrapper below when the user has asked for the S1 console/API directly, when Purple MCP is unavailable, or when you need to script a raw GraphQL call.

SentinelOne exposes an undocumented GraphQL endpoint at `POST /web/api/v2.1/graphql` that powers the console's Purple AI chat. The skill wraps the `purpleLaunchQuery` operation so workflows can ask Purple AI in natural language and receive a structured response (summary text plus a generated PowerQuery).

Auth is identical to REST — the same `Authorization: ApiToken <token>` header. No extra credential setup beyond `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json`.

```python
import sys
sys.path.insert(0, "scripts")
from s1_client import S1Client
from purple_ai import purple_query, PurpleAIError

c = S1Client()
try:
    r = purple_query(
        c,
        "Show powershell.exe processes making outbound connections in the last 24h, top 10.",
        view_selector="EDR",   # EDR | IDENTITY | CLOUD | NGFW | DATA_LAKE
        hours=24,
    )
except PurpleAIError as e:
    # entitlement or permission failure — the token's role can't use Purple AI,
    # or the tenant isn't entitled. These return HTTP 200 with an in-body error.
    print(f"purple error: {e} (type={e.error_type})")
else:
    print(r["message"])           # natural-language answer
    print(r["power_query"])       # generated PQ (may be None — see below)
    print(r["suggested_questions"])
```

CLI equivalent:

```
python scripts/call_purple.py "show powershell.exe outbound connections, top 10"
python scripts/call_purple.py --selector CLOUD --hours 48 "show s3 downloads by user"
python scripts/call_purple.py --json "..."   # machine-readable normalized result
python scripts/call_purple.py --raw  "..."   # full GraphQL response
```

### Purple AI's domain boundary — important

Purple AI answers questions about **SDL telemetry**: process events, network events, file events, indicators, and ingested third-party logs. It does **not** answer questions about **console entities** — alerts, threats, agents, sites, policies. Those are REST resources; use the matching REST endpoint (e.g. `GET /web/api/v2.1/threats`, `GET /web/api/v2.1/cloud-detection/alerts`) instead.

Out-of-domain questions return HTTP 200 with `result_type: "MESSAGE"` and a scope refusal like *"Purple can query for threat indicators, OS events, and some third-party vendor logs ingested into the Singularity Data Lake."* — this is Purple's own guardrail, not a skill failure. When the user's ask is about an entity and Purple refuses, switch to the REST path and tell them why.

### Interpreting the response

Key fields in the normalized dict:

- `result_type`: `"POWER_QUERY"` means Purple generated an executable PQ (check `power_query`). `"MESSAGE"` means docs/RAG mode — `message` has the answer, `power_query` will be None.
- `state`: `"COMPLETED"` is the successful path. Any other state is unexpected.
- `power_query`: the PQ Purple generated. Do **not** auto-execute it without showing it to the user first — Purple can hallucinate fields and execution has a tenant cost. Prefer: render it → confirm with user → then run it through the existing DV/PowerQuery endpoints.
- `suggested_questions`: the "you might also ask" chips from the UI.

### Caveats

- The GraphQL endpoint is **undocumented** and not a committed public API. Field names, schema, and behavior can change between console releases. Flag this when building anything production-grade on top.
- Entitlement and permission failures come back as HTTP 200 with `status.error` populated. The wrapper raises `PurpleAIError` on these so they don't masquerade as empty results — surface the `error_type` to the user verbatim (it's the best hint we have for "re-issue the token with Purple AI permission" vs "the tenant isn't licensed for Purple").
- `teamToken` and `accountId` in the request body are UI-session artifacts; empty strings are accepted for API-token auth.

## Querying logs via the mgmt console API — the foolproof procedure

Every time somebody rolls their own `requests.post(...)` for a PowerQuery, one of the same six things goes wrong: wrong auth prefix, wrong endpoint path, missing `tenant: true`, missing `X-Dataset-Query-Forward-Tag`, no retry on transient 5xx, or 0 rows and the wrong debugging reflex. The fix is: do not hand-roll the call. Use `scripts/pq.py`.

### Step 0 — pick the right surface before you write a query

| The user wants… | Use | Why |
|---|---|---|
| Raw event telemetry (EDR, third-party logs, SDL data) | **`scripts/pq.py`** (LRQ PowerQuery) | This is what SDL/PowerQuery is for. All `dataSource.*`, `event.*`, `src.process.*`, `tgt.file.*`, `i.scheme="edr"` filters. |
| Triage/filter/note/status on an existing alert | `scripts/unified_alerts.py` (UAM GraphQL) | Alerts are entities, not log events. UAM filter syntax is GraphQL `FilterInput`, NOT PowerQuery. Do not confuse the two. |
| Legacy STAR/cloud-detection alert REST shape | `/web/api/v2.1/cloud-detection/alerts` | Only when you need `agentDetectionInfo` / `sourceProcess` etc. Otherwise UAM. |
| A console entity — threat, agent, site, policy, IOC, group | REST via `s1_client.py` | Not a log query. `GET /web/api/v2.1/{threats,agents,sites,...}`. |
| Natural-language hunt that can be hand-reviewed | `purple_ai.purple_query(...)` then LRQ-execute the returned PQ | Purple generates PQ text; `pq.py` runs it. |

If the user names a vendor ("Prompt Security", "Zscaler", "Okta", "FortiGate") and says "query" or "search logs", that is always the PQ path, never UAM filter syntax.

### Step 1 — use `scripts/pq.py`, not inline `requests`

```python
import sys
sys.path.insert(0, "scripts")
from s1_client import S1Client
from pq import run_pq, list_data_sources, PQError

c = S1Client()

# One call. Handles launch, polling, forward-tag, cancel, retry, the lot.
res = run_pq(
    c,
    "dataSource.name = 'Prompt Security' "
    "| group ct = count() by event.type "
    "| sort -ct "
    "| limit 50",
    hours=24,
)
print(res["matchCount"], "events ->", res["row_count"], "rows")
for row in res["rows"]:
    print(row)
```

The helper does ALL of this for you, so there is nothing to remember:

- `Authorization: Bearer <jwt>` (flipped from the REST `ApiToken` prefix; same JWT, different scheme).
- `POST /sdl/v2/api/queries` on the tenant console host. **NOT** `/web/api/v2.1/sdl/v2/api/queries`, **NOT** `xdr.us1.sentinelone.net`. Do not "fix" a 404 by adding `/web/api/v2.1` — that path does not exist; the fix is the shorter path.
- Captures `X-Dataset-Query-Forward-Tag` from the POST response and echoes it on every GET / DELETE (mandatory for shard routing; without it you get rejections).
- Sets `queryType: "PQ"`, `tenant: true`, `pq: {query, resultType: "TABLE"}` (omit `tenant` and you silently get `matchCount=0`).
- Polls at 1s (query expires 30s after the last poll — slower polling means you lose the query).
- Retries 5xx / 429 / connection errors with exponential backoff. Honors `Retry-After`. The DNS-cache-overflow 503s behind some egress proxies are exactly what this is for.
- Cancels on every exit path (success, deadline, failure) to release the per-account concurrent-query budget.

### Step 2 — if you get 0 rows, follow the ladder, do NOT widen the window first

`run_pq` returning `row_count=0` has an ordered diagnostic. Burning time by widening the window first is the most common failure mode; the window is almost never the cause.

1. **Enumerate the data sources.** If your filter names a vendor / product, first confirm it exists on THIS tenant and you have the string right. Spelling, case, and punctuation matter — the filter is a literal string match.

   ```python
   sources = list_data_sources(c, hours=24)
   for s in sources[:30]:
       print(s["dataSource.name"], s["dataSource.category"], s["ct"])
   ```

   If "Prompt Security" isn't in the list, the tenant isn't ingesting it — no amount of widening the window will help. If it's there under a different spelling (`"PromptSecurity"`, `"Prompt Sec"`), use the exact string.
2. **Compare `matchCount` vs `row_count`.** `matchCount=0` means the initial filter discarded everything before any aggregation — the filter is too tight (or naming the wrong thing). `matchCount > 0` with `row_count = 0` means a post-pipe stage (`| group`, `| filter after group`) ate the rows — inspect the pipe.
3. **Only after the above come back clean**, widen the time window — in that order: 24h → 7d → 30d.

### Step 3 — for large windows / heavy aggregates, slice

For ranges past 2-3 days with `event.type=*`-scale aggregates, slice the window and run slices in parallel. Full reference, measured perf (30d 574M-event aggregate lands in ~29s with two service-user JWTs), and the two-JWT runner recipe are in the `sentinelone-powerquery` skill at `references/lrq-api.md`. `run_pq` is the single-slice primitive underneath.

### Step 3a — timeseries: DO NOT use `timebucket(...)`

The PQ engine does not expose a `timebucket` function. Any pipeline of the form `| group n=count() by timebucket('1d'), action` fails with HTTP 500 `"undefined field 'timebucket'"`. The fix is client-side day slicing:

```python
from datetime import datetime, timedelta, timezone
import concurrent.futures as cf

def slice_day(c, base, start, end):
    iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return run_pq(c, base + " | group n=count() by action | sort -n",
                  start_time=iso(start), end_time=iso(end),
                  poll_deadline_s=90)

end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
days = [(end - timedelta(days=i+1), end - timedelta(days=i)) for i in range(7)]
with cf.ThreadPoolExecutor(max_workers=3) as ex:   # 3rps user cap
    results = list(ex.map(lambda se: slice_day(c, base, *se), days))
```

7 daily slices run in ~20s wall-clock (vs ~2 min for a 7d aggregate) and respect the per-user 3 rps cap. For hourly buckets over a 24h window use 24 slices at the same concurrency; for 30d use hourly slicing with 2 JWTs (see `sentinelone-powerquery` skill).

### Step 3b — window-scaling playbook (performance by period)

| Window | Recommended runner | Why |
|---|---|---|
| seconds to 1h | single `run_pq(hours=1)` | server returns in <5s |
| 1h to 24h | single `run_pq(hours=24)` | 5-30s depending on filter selectivity |
| 24h to 7d | single call OK for selective filters; for `event.type=*`-scale aggregates, 7 x 1d slices in parallel (max_workers=3) | single-call ~2 min; sliced ~20s |
| 7d to 30d | mandatory slicing (daily buckets) + 2 JWTs | two-JWT runner in `sentinelone-powerquery` |
| 30d+ | hourly slicing + 2-3 JWTs, cache results | 574M-event aggregate at 30d = ~29s with two JWTs |

### Step 3c — LRQ response-shape gotchas (handled by `run_pq`)

If you ever have to read a raw LRQ response (e.g. debugging), know:

- `columns` is a list of dicts `{name, cellType, decimalPlaces}`, not a list of strings. Zipping values by `col["name"]` (not `str(col)`) is mandatory.
- `matchCount` lives inside the `data` block (`response["data"]["matchCount"]`), not at top level. Default to that path; fall back to top-level for older engines.
- `values` is an array of arrays (one per row); `run_pq` pairs it with column names for you.

### Step 4 — when NOT to use `pq.py`

- If the user said "purple mcp" or "mcp", defer to `mcp__purple-mcp__powerquery` first; this is the backup path when the MCP times out or 5xxs.
- If the user is working with alerts as entities (listing, filtering, note, status), that's UAM GraphQL (`unified_alerts.py`), not PowerQuery. UAM filter syntax is `[{fieldId, stringEqual: {...}}]`; it is NOT PowerQuery `| filter` syntax. Mixing them is a common trap in screenshot-driven debugging.

### Checklist before running a PQ programmatically

- [ ] You called `run_pq` / `list_data_sources`, not inline `requests.post`.
- [ ] Base URL is the tenant console (e.g. `https://usea1-purple.sentinelone.net`), not `xdr.us1.sentinelone.net`.
- [ ] Endpoint path is `/sdl/v2/api/queries` (short form). If you see 404s, do NOT add `/web/api/v2.1` — that's wrong.
- [ ] If you're filtering on EDR data (`src.process.*`, `event.type=*`, `tgt.file.*`), prepend `dataSource.name='SentinelOne' dataSource.category='security'` — on mixed tenants the default scope carries Scalyr/infra logs too and wide filters silently return `matchCount=0`.
- [ ] 0 rows → ran `list_data_sources` and checked `matchCount` vs `row_count` BEFORE widening the window.

## Unified Alert Management (UAM) — PRIMARY alert API

> **Alert API precedence — important:**
> 1. **PRIMARY — GraphQL UAM** at `POST /web/api/v2.1/unifiedalerts/graphql`. This is the modern, multi-source alerts inbox (EDR, XDR, Identity, STAR, Cloud, NGFW, and ingested third-party telemetry). IDs are UUIDs (e.g. `019db24c-8b6d-7451-8697-b1b2e1a270f1`). Use this for any alert listing, filtering, triage, note, status, verdict, assignment, group-by, facet, or CSV-export task.
> 2. **SECONDARY — REST** at `GET /web/api/v2.1/cloud-detection/alerts`. Older surface, scoped to cloud-detection events (STAR rule hits, EDR overflow). IDs are int64 (e.g. `2055164731151448891`). Use only when you specifically need the denormalized REST payload (`agentDetectionInfo`, `sourceProcess`, `targetProcess`, `ruleInfo`) or when UAM is unavailable. These are **parallel surfaces, not redundant** — the same alert will have different IDs in each.
> 3. **No `createAlert`.** S1 does not expose a mutation for creating alerts directly. Alerts are server-side byproducts of detection engines — create a STAR/Custom Detection rule (`POST /web/api/v2.1/cloud-detection/rules`), upload an IOC that matches live telemetry (`POST /web/api/v2.1/threat-intelligence/iocs`), or generate synthetic endpoint activity. `addAlertNote` is the closest reversible content-creation path against an existing alert.

Auth is the same `Authorization: ApiToken` header as REST; no extra credentials. Full reference in `references/UNIFIED_ALERTS.md`. The end-to-end dual-API round-trip test is `tests/test_alerts_dual_api.py`.

Use UAM whenever the user is working with *alerts* as first-class entities — triaging, filtering, adding notes, resolving, bulk-assigning — rather than the older `GET /web/api/v2.1/threats` surface.

```python
import sys
sys.path.insert(0, "scripts")
from s1_client import S1Client
import unified_alerts as uam

c = S1Client()

# discover: fieldIds, enum values, which views have data
cols = uam.column_metadata(c)
avail = uam.view_data_availability(c)

# triage: top 20 NEW CRITICAL EDR alerts from the last day
page = uam.list_alerts(c, filters=[
    uam.build_filter(fieldId="detectionProduct", stringEqual={"value": "EDR"}),
    uam.build_filter(fieldId="status",   stringEqual={"value": "NEW"}),
    uam.build_filter(fieldId="severity", stringEqual={"value": "CRITICAL"}),
], first=20)

# act: bulk resolve a specific list of alerts, with a note
account = uam.scope(["<account_id>"])
uam.set_alert_status(
    c, scope_input=account,
    alert_ids=["<alert1>", "<alert2>"],
    status="RESOLVED",
    note="Auto-closed: part of campaign tracked in JIRA-1234",
)
```

CLI equivalents:

```
python scripts/call_unified_alerts.py list --filter detectionProduct=EDR --first 20
python scripts/call_unified_alerts.py facets status severity detectionProduct
python scripts/call_unified_alerts.py notes <alert-id>
python scripts/call_unified_alerts.py add-note <alert-id> "Investigating"
python scripts/call_unified_alerts.py set-status --scope <account-id> --alert-id <id1> <id2> RESOLVED --note "..."
python scripts/call_unified_alerts.py csv-export --filter severity=CRITICAL -o crit.csv
```

### UAM domain — what belongs here vs REST

UAM owns everything in the modern Alerts inbox, including alert notes, alert history, mitigation results, trigger-actions, and Cursor-paginated group-by / facet views. The older `/web/api/v2.1/threats` REST surface still exists and covers the classic endpoint-protection threat lifecycle — when the user says "alerts", "unified alerts", "alert notes", or mentions XDR / multi-source detections, route to UAM. When they say "threat", "threat group", "incident", or reference `/threats`, stay on REST.

### Important quirks (hidden by the wrapper, but mind them if writing raw GraphQL)

- The `alerts` query takes a flat `filters: [FilterInput!]` (AND-joined); mutations and `alertAvailableActions` take `filter: OrFilterSelectionInput` shaped as `{ or: [{ and: [FilterInput, ...] }, ...] }`. Mixing these up is a validation error. The wrapper exposes `build_filter(...)`, `or_filter(...)`, and `scope(...)` helpers so callers don't have to hand-assemble them.
- `updateAlertNote` and `deleteAlertNote` fail for ~30–90s after a note is freshly created (`"Alert Note with ID ... does not have mgmt_note_id set, unable to [edit|delete], try again later!"`) because the management-console backend is still propagating an internal id. The wrapper retries automatically with backoff — callers don't need to sleep.
- `aiInvestigations` has no `data` wrapper, but `alertNotes` / `alertFiltersCount` / `alertGroupByCount` / `alertAvailableActions` / `alertMitigationActionResults` / CSV exports all do. `alerts` / `alertHistory` / `alertTimeline` / `alertGroups` use connection shape (`edges`/`pageInfo`/`totalCount`).
- Full list of traps — including the `SortOrderType` enum name, `alertGroupByCount` using `limit` (not `first`), subselection requirements on `CsvResponse` / `ActionsError`, and the actual shape of `alertsViewDataAvailability` — is in `references/UNIFIED_ALERTS.md` under "Schema quirks".

### Destructive actions — blast radius

`alertTriggerActions` is the single mutation that can touch many alerts at once. Passing `filter: null` means *every alert in scope* — potentially hundreds of thousands. The safe pattern is the same as REST bulk actions:

1. Use `list_alerts(..., first=1)` with the proposed filter and read `totalCount`.
2. Show the user the exact filter + action list + count.
3. Only after explicit confirmation, call `trigger_actions(...)` or one of the `set_alert_status` / `set_analyst_verdict` / `assign_alerts` convenience wrappers (all of which constrain the filter to an explicit alert-id list by default).

## UAM Alert Interface (Unified Alert Management) -- pushing OCSF indicators + alerts INTO UAM

Everything else in this skill talks to `<tenant>.sentinelone.net/web/api/v2.1/...` (the Mgmt Console) and is read-or-mutate on pre-existing server state. The **UAM Alert Interface** (formerly "Ingestion Gateway") is a separate API family on a separate host for the write-side path: it lets you push OCSF-formatted indicators and alerts INTO UAM so they show up in the console as real alerts with attached indicators. Use it when a user asks to "create an alert", "ingest indicators", "send alerts from my pipeline", or "test alert ingestion".

**Host and wire contract:**

- Prod (US1): `https://ingest.us1.sentinelone.net`. Override via `uam_alert_interface_url` in `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` or the `--uam-url` flag / `S1_UAM_ALERT_INTERFACE_URL` env var. The legacy config key `ingestion_gateway_url` and env var `S1_IGW_URL` are still honored as fallbacks.
- Auth: `Authorization: Bearer <JWT>`. NOT `ApiToken`. The mgmt-console JWT from `S1_API_TOKEN` works; the endpoint rejects `ApiToken ...` with HTTP 401 `"Unsupported auth type"`.
- Body: concatenated JSON (one or more objects back-to-back, optionally newline-separated), gzip-compressed. `Content-Encoding: gzip` is mandatory. zstd also accepted.
- Scope: `S1-Scope: <accountId>` or `<accountId>:<siteId>[:<groupId>]` is mandatory.
- Success shape: `202 Accepted` with `{"details":"Success","status":202}`.

**Endpoints:**

- `POST /v1/indicators` -- raw behavioral indicators. Each must carry `metadata.profiles = ["s1/security_indicator"]` and a unique `metadata.uid` (this is the join key). Batching: send many indicators in one call by passing a list; the client concatenates + gzips.
- `POST /v1/alerts` -- SecurityAlert wrappers. Each references its indicator(s) via `finding_info.related_events[].uid == indicator.metadata.uid`. A single alert can reference multiple indicators (one entry per indicator). The server stitches them into `alert.rawIndicators` / the UAM Indicators tab once both land. **Call with ONE alert per POST.** The wire format accepts multi-alert bodies and the gateway returns HTTP 202, but the stitcher silently drops all but one alert in a multi-alert batch (usea1-purple 2026-04-22); loop one at a time, or use `post_alert_with_indicators` which enforces the safe pattern.

**Supported indicator classes (via builders):**

- `build_file_indicator(...)` -- OCSF class 1001 FileSystem Activity. Observables: Hostname, File Name, Hash (SHA-256/MD5), User Name, IP Address.
- `build_process_indicator(...)` -- OCSF class 1007 Process Activity. Observables: Hostname, Process Name, Resource UID (pid), User Name, IP Address, plus parent process.
- `build_network_indicator(...)` -- OCSF class 4001 Network Activity. Observables: Hostname, src/dst IP Address, URL, User Name.

**Python usage:**

```python
import sys, time, uuid
sys.path.insert(0, "scripts")
from s1_client import S1Client
from uam_alert_interface import (
    UAMAlertInterfaceClient,
    build_file_indicator, build_process_indicator, build_network_indicator,
    build_alert_referencing,
)

mgmt = S1Client()
uam_iface = UAMAlertInterfaceClient(bearer_token=mgmt.api_token)

now_ms = int(time.time() * 1000)
ind_uid_a, ind_uid_b, alert_uid = (str(uuid.uuid4()) for _ in range(3))

ind_a = build_file_indicator(
    indicator_uid=ind_uid_a, file_name="payload.iso",
    file_sha256="0"*64, device_uid=str(uuid.uuid4()),
    device_hostname="host-1", device_ip="192.0.2.10",
    user_uid=str(uuid.uuid4()), now_ms=now_ms,
)
ind_b = build_process_indicator(
    indicator_uid=ind_uid_b, process_name="powershell.exe",
    process_pid=4242, process_cmd_line="powershell -enc ...",
    parent_process_name="explorer.exe",
    device_uid=str(uuid.uuid4()), device_hostname="host-1",
    user_uid=str(uuid.uuid4()), now_ms=now_ms,
)
alert = build_alert_referencing(
    alert_uid=alert_uid, indicators=[ind_a, ind_b], now_ms=now_ms,
    title="Ingested alert", description="...",
)

# Preferred safe path. Posts the indicators, sleeps 3s (so each
# metadata.uid registers before the stitcher resolves related_events),
# then posts the single alert. For many alerts, LOOP this call -- do
# NOT pass multiple alerts to post_alerts() in one go (see constraints
# below).
uam_iface.post_alert_with_indicators(
    alert, [ind_a, ind_b], scope=f"{account_id}:{site_id}")
# Then poll UAM GraphQL (unified_alerts.list_alerts) to see it surface.
```

**Validation:** after ingest, find the alert via UAM GraphQL (`unified_alerts.list_alerts` filtered by name, or `get_alert(alert_id)` once you know it). `get_alert_with_raw_indicators(c, alert_id)` returns the raw indicator dict(s) so you can confirm every `metadata.uid` and its observable names made it through.

**Cleanup:** ingested alerts are not hard-deletable via public API. The standard reversibility pattern is to set `status=RESOLVED` and `analystVerdict=TRUE_POSITIVE_BENIGN` via the bulk-ops mutations in `unified_alerts` so the alert exits the active SOC queue and is tagged as synthetic.

**Multi-indicator alert constraints** (empirically confirmed on
`usea1-purple` 2026-04-22):

- **One alert per `POST /v1/alerts` call.** The wire format accepts
  concatenated JSON for N alerts in one body and the gateway returns
  HTTP 202, but the stitcher silently drops all but one of the alerts.
  Callers with many alerts MUST loop. `post_alerts` emits a
  `RuntimeWarning` when `len(alerts) > 1` to flag the hazard. Use
  `post_alert_with_indicators(alert, indicators, ...)` for the safe
  one-at-a-time path.
- **Sleep between `POST /v1/indicators` and `POST /v1/alerts`.** If
  the alert is posted immediately after its indicators, the stitcher
  can resolve `finding_info.related_events[].uid` before the indicator's
  `metadata.uid` is registered on the scope and silently drop the alert
  (HTTP 202 still returned). A ~3s sleep between the two POSTs avoids
  this; reducing below ~2s has been observed to regress on loaded
  tenants. `post_alert_with_indicators` builds the sleep in; callers
  using the low-level `post_indicators` + `post_alerts` path MUST add
  it manually. `test_uam_alert_interface_batch.py` encodes this exact
  sequence.
- Alerts with multiple `resources[]` entries (i.e. indicators spanning
  different `device.uid` values) are silently dropped by the stitcher.
  Return: HTTP 202 at the wire, NEVER surfaces in UAM. The builder
  collapses to a single `resources[]` entry (first indicator's device)
  to avoid this. If you truly need per-indicator assets, emit separate
  alerts.
- Each `finding_info.related_events[]` entry MUST carry `class_uid`,
  `type_uid`, `category_uid`, `activity_id`, `severity_id`, `time`,
  `message`, and enriched `observables[]` (each with `type` +
  `typeName` alongside `type_id`/`name`/`value`). `build_alert_referencing()`
  populates all of these. Omitting any of them tends to cause the
  stitcher to silently drop the alert.
- **`file.hashes` MUST be an OCSF Fingerprint array, not a dict.**
  OCSF 1.6.0 defines `file.hashes` as `Array of Fingerprint objects`:
  `[{"algorithm_id": 3, "algorithm": "SHA-256", "value": "<hex>"}, ...]`.
  Posting `{"sha256": "<hex>"}` (dict form) causes the stitcher to
  silently drop the file indicator even though POST returns 202.
  `build_file_indicator()` emits the correct array shape; custom
  payload builders must follow the same convention (algorithm_id 2=MD5,
  3=SHA-256, 4=SHA-1, 5=SHA-512).
- Multi-indicator stitching is asynchronous. Alerts surface within
  ~30s; individual indicators appear in `alert.rawIndicators` over a
  window of 2-120s. Tests must poll with a grace window, not assert
  immediately.
- **Server-side rendering quirk in `alertWithRawIndicators` GraphQL:**
  when an alert has multiple stitched rawIndicators, the flat-key
  representation (`observables[N].name`/`.value`/`.type_id`) has
  shuffled VALUES on all but the last entry in the array -- keys are
  stable, values get mixed with other fields (e.g. `observables[2].name`
  may return `"smoke-product"` because it was populated from
  `metadata.product.name`). Does NOT affect stitching -- `metadata.uid`
  is correct and the UI reads from a different code path. Programmatic
  consumers should assert on `metadata.uid` presence, not on flattened
  `observables[N].name` fields, in batch mode.

**Tested on `usea1-purple` 2026-04-22:**

- `tests/test_uam_alert_interface_single.py` -- CONFIRMED WORKING end-to-end. 1 indicator + 1 alert, indicator stitches inside 30s, cleanup verified.
- `tests/test_uam_alert_interface_batch.py` -- CONFIRMED WORKING end-to-end. 3 indicators batched into one POST, alert with 3 related_events surfaces in UAM, all 3 indicators stitch into `alert.rawIndicators` within 2-5s, cleanup verified. Per-observable name assertion treated as informational due to GraphQL server-side rendering quirk noted above.

See `tests/test_uam_alert_interface_single.py` for the minimum-viable worked example, and `tests/test_uam_alert_interface_batch.py` for a batched 3-indicator / multi-observable / multi-class round-trip.

### Asset linkage on ingested alerts

Ingested alerts always create a synthetic `assets[]` entry derived from `resources[]`; they **never** populate `assets[].agentUuid`. That linkage to real tenant inventory is only established when the alert originates from an installed S1 agent (real detection, STAR rule hit, or Hyperautomation `sendCustomEvent`). No OCSF field combination on the ingest path (tested: `resources[].agent_list`, `device.agent_uuid`, matching real agent UUIDs, `os.type_id` hints, etc.) reconciles against inventory.

What IS controllable is the asset classification. `metadata.product.name` + `metadata.product.vendor_name` on the alert envelope drive `assets[].category` / `assets[].subcategory`:

- Defaults (`smoke-product` / `smoke-vendor`) classify as "Device / Other Device"
- `SentinelOne` / `SentinelOne` classifies as "Server / Virtual Machine"

Pass these via `build_alert_referencing(detection_product=..., detection_vendor=...)` when you want a demo alert to visually resemble an agent-generated alert. `get_alert` now defaults to `_ALERT_DETAIL_FIELDS` which includes the `assets { ... }` block; `list_alerts` / `paginate_alerts` still default to `_ALERT_CORE_FIELDS` (cheap) and accept an explicit `fields=_ALERT_DETAIL_FIELDS` override when callers want the asset join on every edge.

Full empirical matrix including per-field behavior and probing recipes: `references/ASSET_LINKAGE.md`.

## Data source + schema discovery

Before you write queries, dashboards, or detections against an SDL data source, discover two things: (1) what sources exist on this tenant and which are actively ingesting, and (2) for a given source, what attributes the parser actually emits. Hardcoded field lists are the number-one reason queries return 0 rows on a new tenant. This workflow replaces them.

### Step 1 — enumerate sources (`dataSource.name = *`)

```python
from pq import list_data_sources
sources = list_data_sources(client, hours=24, limit=200)
# -> [{"dataSource.name": "SentinelOne", "dataSource.category": "security", "ct": 18304051}, ...]
```

CLI: `python scripts/inspect_source.py --list` prints a ranked table of every source that ingested in the last 24h. If a name the user asked for isn't in the list, fuzzy-match and surface candidates rather than running a query that will return 0.

Rules of thumb:
- There can be multiple rows with the same `dataSource.name` under different `dataSource.category` values (e.g. `SentinelOne / security`, `SentinelOne / None`, `SentinelOne / telemetry`). Treat category as metadata, not part of the name.
- A source with non-zero `ct` in 24h is live. Anything else is either decommissioned, in a different time window, or scoped out of the current token.

### Step 2 — discover the schema for one source (`discover_schema`)

```python
from inspect_source import discover_schema, pick_keys

schema = discover_schema(
    client, "Prompt Security",
    hours=24, sample=150,
    extra_filter="(tag != 'logVolume' OR !(tag = *))",  # ALWAYS exclude logVolume
    backend="auto",   # sync SDL first, LRQ LOG fallback
    escalate=True,    # 1h -> 4h -> 24h until min_events rung satisfied
)
prim_key, action_key = pick_keys(schema)
```

CLI: `python scripts/inspect_source.py --source "<name>" --window 24h`.

Key points:
- Uses the LRQ `LOG` queryType (not PowerQuery). PQ has no wildcard column projection; `| columns *` errors and `| limit N` only returns `timestamp + message`. `LOG` returns every flat attribute the parser emits under `matches[].values`, which is how the Event Search UI populates its "Event properties" panel.
- Sync SDL `/sdl/api/query` is ~30% faster than async LRQ on usea1-purple. The dispatcher prefers it and falls back to LRQ LOG on HTTP 404/401/403. Force a backend with `backend="sdl"` or `backend="lrq"` if benchmarking.
- Escalating window (1h -> 4h -> 24h -> requested) keeps busy sources ~3s. Only sparse sources (audit, low-volume demos) pay the full widening cost. Override with `escalate=False` for a single-rung run at `hours=`.
- Each field is classified: `principal_user` / `principal_host` / `principal_ip` / `action` / `temporal` / `network` / `file` / `process` / `grouping_candidate` / `other`. `pick_keys(schema)` returns `(prim_key, action_key)` picked from whatever is populated, preferring `user > hostname > IP`, then shortest name, then exact-name action hits (`action`, `event.type`, `outcome`, `result`, `severity`, ...) in that priority.
- `extra_filter` is passed through verbatim and appended to the base `dataSource.name='...'` filter.

### ALWAYS exclude `tag='logVolume'` from discovery samples

Many SentinelOne parsers emit metric events alongside real data, tagged `tag='logVolume'`. They have `metric`, `value`, `path1` fields and nothing else useful. If you don't exclude them, they crowd out real events in a sample window and the classifier picks `severity` as the action key because it's the only field at 100% populated. Pass:

```python
extra_filter="(tag != 'logVolume' OR !(tag = *))"
```

The `OR !(tag = *)` half keeps sources that don't emit `tag` at all (rather than excluding them as null). `build_source_report.py` always passes this filter. Do the same in any new caller.

### Benchmarked results (5 sources, usea1-purple, 24h ceiling)

| Source | Wall | Effective | n sampled | attrs | prim_key | action_key |
|---|---|---|---|---|---|---|
| SentinelOne | 2.9s | 1h | 150 | 333 | `src.process.eUserName` | `event.type` |
| Windows Event Logs | 3.1s | 1h | 150 | 148 | `winEventLog.data.event.eventData.subjectUserName` | `event.type` |
| FortiGate | 2.5s | 1h | 150 | 247 | `device.name` | `event.type` |
| Zscaler Internet Access | 2.5s | 1h | 150 | 47 | `None` | `action` |
| Prompt Security | 16.8s | 24h | 133 | 59 | `user` | `action` |

Four of five land in ~3s because busy sources satisfy the `min_events=50` threshold on the 1h rung. Only low-volume sources (demo Prompt Security) pay the full escalation cost (1h -> 4h -> 24h = 3 rungs). Reproduce with `python scripts/bench_5_sources.py`.

Zscaler returning `prim_key=None` is a real classifier gap: its user-ish fields are named `deviceowner` / `department` without a separator, so they don't match the `principal_user` regex. This is visible, not hidden. Operators can inspect the `other` class in the report and manually set the prim_key for downstream queries.

### Using the discovered schema in code

```python
base = f"dataSource.name = '{source}' (tag != 'logVolume' OR !(tag = *))"

# volume-by-action breakdown (always safe; default to count() if no action key)
if action_key:
    q = f"{base} | group n=count() by {action_key} | sort -n"
else:
    q = f"{base} | group n=count()"

# per-principal mix (skip if no principal)
if prim_key and action_key:
    q = f"{base} | group n=count() by {prim_key}, {action_key} | sort -n | limit 60"
elif prim_key:
    q = f"{base} | group n=count() by {prim_key} | sort -n | limit 25"
```

`build_source_report.py` is the reference consumer of this pattern. Read it before writing a new pipeline that needs the same keys.

### When to re-run discovery

- Before writing any query against a source you haven't touched on this tenant.
- When a previously-working query starts returning 0 rows (parser may have changed field names after a platform update).
- On tenant handover — different customers enable different parser versions, especially for XDR connectors.
- Before authoring a detection rule body (STAR / Custom Detection / PowerQuery Alert), to confirm the fields the rule references actually exist. Pass the discovered schema through to the rule author in the body of the request.

## CTO report generation pipeline

A source-agnostic pipeline for producing CTO-grade Word + PowerPoint reports on any SDL data source. Three scripts, one JSON artefact.

1. `scripts/build_source_report.py --source "<vendor>" --window <7d|24h|...>`. Runs dimension probes, a unified per-principal query, and a timeline aggregate against the tenant via `scripts/pq.py`, then writes `reports/<slug>_<window>/data.json`. Probes which of `user`, `src.ip.address`, `src.hostname`, `action`, `event.type` actually carry values, so the renderer can skip sections that would otherwise be empty.
2. `scripts/render_charts.py <data.json>`. Emits PNG charts into `reports/<slug>_<window>/charts/`. Pure function of the JSON, no tenant calls.
3. `scripts/build_docx.py <data.json>` and `scripts/build_pptx.py <data.json>`. Read the same JSON, emit `<Slug>_CTO_Report_<window>.docx` and `<Slug>_CTO_Deck_<window>.pptx` next to it. Every chart, section, stat card, and recommendation is gated on `data["dims"]` so a dimension-sparse source (e.g. Windows Event Logs has only `event.type`) produces a shorter but coherent report, not a broken one with empty tiles.

### Data.json contract (renderers depend on this shape)

- `source`, `slug`, `window_label`, `window_start`, `window_end`, `base_filter`.
- `dims`: boolean-per-dimension probe result.
- `summary`: derived metrics. Key fields are `total`, `intervention_rate` (only meaningful if `dims.action`), `prim_key` (name of the principal field actually used: `user`, `src.hostname`, `src.ip.address`, or null), `top_principal_key`, `top_user`, `by_action`, `rank_24h`, `n_slices`.
- `per_user_mix_top10`: the unified top-N-principals-by-action-mix result. The renderer slices this into `by_user`, `by_action_blocks`, `by_user_bypass` rather than running three separate queries. Collector does one PQ; renderer derives the rest.

### Principal key fallback

Order: `user`, then `src.hostname`, then `src.ip.address`, then none. The collector picks the first dim that returned non-null; the renderer reads `summary.prim_key` and labels stat cards and takeaways accordingly (e.g. "Dominant host" vs "Dominant user").

### Renderer gotchas (learned the hard way)

- **Never use em-dashes or en-dashes in any commentary string.** They read as AI-generated. Use commas, colons, or parentheses.
- **Stat card overflow.** Long labels (e.g. "Windows Event Log Creation") wrap through the card edge at 40pt. Use length-based font sizing: len<=7 gets 40pt, <=12 gets 28pt, <=18 gets 20pt, else 16pt.
- **Chart title "dayly" is not a word.** `f"{kind}ly"` where kind="day" is wrong. Use a lookup: `{"day": "Daily", "hour": "Hourly", "week": "Weekly", "month": "Monthly"}`.
- **X-axis label crowding on hourly charts.** A 24-slice timeline rotates 24 timestamps into each other. Sparsify with `ax.set_xticks(ticks[::step])` where `step = max(1, int(len(dates) / 10))`, BEFORE `autofmt_xdate`.
- **Single-series legend clutter.** Gate `ax.legend(...)` on `n_series > 1`. A one-series chart needs no legend; the title carries the meaning.
- **Bar data-labels overlap on dense charts.** Skip them when `len(dates) > 12`. The Y-axis scale is enough for dense timelines.
- **Adaptive title on dimensionless sources.** `title_suffix = "volume by action" if has_action else "volume"`. Don't claim action breakdown when there is none.
- **Recommendations grid leaves empty bottom cell.** With 2 cards, use a single row (not 2x2). With 1 card, full width.
- **Fallback bullets when both `action` and `top_user` are missing.** Otherwise the "CTO takeaways" section renders empty. Fall back to dominant `prim_key`, tenant rank (24h), and the data-lake story.

### Commentary generators

`_intervention_note()`, `_concentration_note()`, `_bypass_note()` in `build_docx.py` and `build_pptx.py` take metric values and return commentary strings gated on thresholds (>=40 high, >=10 moderate, else low). The thresholds are tuned for LLM-app traffic; if they feel off for a new source, edit the thresholds rather than the template strings.

### Running the whole thing

```
# From the skill root, with $CLAUDE_CONFIG_DIR/sentinelone/credentials.json configured.
python scripts/build_source_report.py --source "<vendor>" --window <7d|24h|...>
python scripts/render_charts.py reports/<slug>_<window>/data.json
python scripts/build_docx.py    reports/<slug>_<window>/data.json
python scripts/build_pptx.py    reports/<slug>_<window>/data.json
```

The collector creates `reports/<slug>_<window>/` on first run. The `reports/` directory is `.gitignored`; this skill ships with the framework only, not sample outputs.

## Common high-value workflows

- **Unified alert triage** — `list_alerts(...)` from `unified_alerts` for the modern multi-source alerts inbox (EDR + XDR + Identity + cloud + third-party); use `facets`/`group-by` for volume rollups; `set_alert_status` / `set_analyst_verdict` / `assign_alerts` for triage decisions; `add_alert_note` for context.
- **Threat triage (legacy)** — `GET /threats` filtered by `createdAt__gte` + `resolved=false`; enrich with agent details from `/agents?ids=...`; output a table.
- **Endpoint isolation** — find agent IDs (`/agents` with name/IP filter), confirm count, `POST /agents/actions/disconnect` with filter.
- **Hunt across DV / PowerQuery** -- `POST /sdl/v2/api/queries` with `queryType="LOG"` (S1QL) or `queryType="PQ"` (PowerQuery), then poll `GET /sdl/v2/api/queries/{id}` echoing the `X-Dataset-Query-Forward-Tag` response header. Auth is Bearer, not ApiToken. Legacy `/dv/init-query` + `/dv/query-status` + `/dv/events` + `/dv/events/pq` flows are deprecated (sunset 2027-02-15). See `references/WORKFLOWS.md` Section 4 for the canonical runner.
- **Natural-language hunt via Purple AI** -- `purple_query(c, "...")` to generate a PQ, review, then execute via LRQ. Only for SDL-telemetry questions; route entity questions to REST.
- **Site/Group inventory** — `/sites`, `/groups`, `/accounts` are the tenant-structure endpoints; many resources require filtering by `siteIds` / `accountIds`.
- **Bulk action audit** — `/activities` is the system-wide audit log; filter by `activityTypes` and `createdAt__gte`.
- **Push alerts + indicators INTO UAM** -- build OCSF payloads, then call `UAMAlertInterfaceClient.post_alert_with_indicators(alert, [...])` once per alert (loop for many). The helper posts indicators, sleeps 3s, and posts the single alert in the one sequence proven to surface cleanly on US1 tenants. See "UAM Alert Interface" section above for the two silent-drop failure modes (multi-alert POST, no sleep) it prevents. Use for pipeline integrations, synthetic-alert generation, and detection testing.
- **CTO report for a data source** -- `python scripts/build_source_report.py --source "<vendor>" --window <7d|24h>` then `scripts/render_charts.py`, `scripts/build_docx.py`, `scripts/build_pptx.py` on the resulting `reports/<slug>_<window>/data.json`. Works for any SDL data source; the renderer gates every section on `dims` so dimension-sparse sources (e.g. Windows Event Logs with only `event.type`) still produce a coherent deck. See "CTO report generation pipeline" for the data contract and renderer gotchas.

Consult the per-tag reference files for exact parameter names — the above are orientation, not copy-paste ready.
