---
name: sentinelone-mgmt-console-api
description: Use whenever the user wants to query, update, create, or act on a SentinelOne Management Console — threats, alerts, agents, sites, accounts, groups, exclusions, RemoteOps, Deep Visibility, Hyperautomation, Unified Alert Management (UAM), Purple AI, IOCs, or any other S1 Mgmt API resource. Trigger on "console", "query/update/create console", "SentinelOne", "S1", "Singularity", "UAM", "Purple AI", "/web/api/v2.1/...", S1 agent/threat/site IDs, or asks like "list endpoints", "triage alerts", "add note to alert", "create an IOC", "isolate endpoint", "run RemoteOps", "pull DV results". For alerts the PRIMARY API is GraphQL UAM at /web/api/v2.1/unifiedalerts/graphql; REST /cloud-detection/alerts is SECONDARY (older, cloud-detection scoped, int64 IDs). Defer to Purple MCP if the user says "purple mcp" or "mcp"; this skill is the backup then. Wraps the S1 Mgmt REST API (781 ops, 113 tags, v2.1) plus UAM GraphQL and Purple AI GraphQL, with a Python client, searchable index, and reversible tests.
---

# SentinelOne Management Console API

Wraps the SentinelOne Management Console API (Swagger 2.0, spec version 2.1, 781 operations) with a pre-built Python client, a compact endpoint index, and per-tag reference files.

## Setup — configure credentials first

Credentials live in `config.json` at the skill root. Users update two fields:

```json
{
  "base_url": "https://REPLACE-ME.sentinelone.net",
  "api_token": "REPLACE_WITH_YOUR_API_TOKEN"
}
```

The `base_url` is the user's tenant console URL (no trailing slash, no `/web/api/v2.1`). The `api_token` is an API User token from Settings → Users → Service Users in the S1 console.

Environment variables override the file: `S1_BASE_URL`, `S1_API_TOKEN`, `S1_VERIFY_TLS`.

Before running anything, confirm `config.json` has been filled in. If the placeholder strings are still present, stop and ask the user to update them.

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

- `config.json` — credentials (user updates these).
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
- `references/tenant_capabilities.{json,md}` — auto-generated by `smoke_test_queries.py`: per-endpoint status (200/403/404/etc.) for the tenant in `config.json`. Regenerate whenever the token or tenant changes. The committed copy is a worked example from the Purple demo tenant.
- `references/endpoint_index.json` — compact machine-readable index (one entry per op). Used by `search_endpoints.py` but can be read directly if you need to filter programmatically.
- `references/tags/<Tag>.md` — per-tag reference with parameters, descriptions, and required permissions. Load only the files you need.
- `references/common_params.md` — shared query params (`skip`, `limit`, `cursor`, `sortBy`, etc.) and the pagination pattern.
- `references/POWERQUERY_RECIPES.md` — PowerQuery / SDL query recipes tested on-tenant: indicator prevalence, PowerShell outbound to public IPs, failed-login triage, storyline activity summary, UAM-indicator SDL crosscheck, endpoint heartbeat. For full PQ language reference use the dedicated `sentinelone-powerquery` skill.
- `spec/swagger_2_1.json` — the original full Swagger spec (14 MB). Use only when the per-tag reference is insufficient — e.g. to resolve a deeply nested request-body schema by `$ref`. Never read this whole file into context.
- `tests/test_ioc_lifecycle.py` — reversible CREATE → LIST → DELETE → VERIFY round-trip for Threat Intelligence IOCs. Uses a unique run-tag per invocation, scopes to a single account, and cleans up before exit. Covers the one "create content" path against the S1 detection surface.
- `tests/test_alerts_dual_api.py` — dual-API round-trip for alerts: GraphQL list/detail/addNote/notes/deleteNote plus a parallel REST `/cloud-detection/alerts` read. Demonstrates that UAM GraphQL is the PRIMARY alert surface and REST is SECONDARY, with the note mutation cleaned up before exit (handles the `mgmt_note_id` propagation delay).
- `scripts/uam_alert_interface.py` — UAM (Unified Alert Management) Alert Interface client for pushing OCSF indicators + alerts INTO UAM via `POST /v1/indicators` and `POST /v1/alerts` on `ingest.us1.sentinelone.net`. Handles the gzip-compressed concatenated-JSON body, `Bearer` auth (the endpoint rejects `ApiToken`), and the `S1-Scope` header. Exposes `UAMAlertInterfaceClient`, plus `build_file_indicator()`, `build_process_indicator()`, `build_network_indicator()`, and `build_alert_referencing()` payload helpers. URL is configurable via `uam_alert_interface_url` in `config.json` (defaults to `https://ingest.us1.sentinelone.net`; legacy key `ingestion_gateway_url` is still honored as a fallback).
- `tests/test_uam_alert_interface_single.py` — minimum-viable reversible write-side round-trip: POST one OCSF FileSystem-Activity indicator + one SecurityAlert referencing it, poll UAM GraphQL until the alert surfaces, verify the indicator is stitched in, then close the alert via bulk-ops (status=RESOLVED, analystVerdict=TRUE_POSITIVE_BENIGN). Covers the single-indicator happy path into UAM.
- `tests/test_uam_alert_interface_batch.py` — comprehensive reversible round-trip: batched POST of 3 indicators (OCSF classes 1001 FileSystem Activity, 1007 Process Activity, 4001 Network Activity) each carrying 3+ observables, referenced by a single SecurityAlert via `finding_info.related_events[]`. Verifies all 3 metadata.uids and their observable names surface in `alert.rawIndicators`, then closes the alert. Covers batching, multi-observable, and multi-indicator linkage.
- `scripts/ingestion_gateway.py` + `tests/test_ingestion_gateway_alert_with_indicator.py` — deprecated back-compat shims. The helper re-exports from `uam_alert_interface`; the test prints a pointer to the renamed file and exits non-zero.

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

Auth is identical to REST — the same `Authorization: ApiToken <token>` header. No extra credential setup beyond `config.json`.

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

## Long Running Query (LRQ) - canonical PowerQuery / log-search path

For any programmatic PowerQuery or log search against this tenant, use the **Long Running Query API** at `POST /sdl/v2/api/queries` on the tenant's own console host. It supersedes `/api/powerQuery` (SDL v1) and the Deep Visibility `/dv/events/pq` endpoint (mgmt REST). Both older paths are deprecated and sunset on 2027-02-15. LRQ is async, parallelizes cleanly, has higher limits, and is the only path that stays supported after sunset. Full reference and canonical Python runner live in the `sentinelone-powerquery` skill at `references/lrq-api.md`.

**Crucially, the S1Client's JWT doubles as the LRQ Bearer token** - only the auth prefix changes:

```python
from s1_client import S1Client
c = S1Client()
# REST / GraphQL:  Authorization: ApiToken <jwt>   (c.api_token)
# LRQ:             Authorization: Bearer   <jwt>   (same value, Bearer prefix)
```

Use this in two situations:

1. **Fallback when the Purple MCP `powerquery` tool times out.** The MCP has tight per-call timeouts and no parallelism. When it returns a timeout or 5xx for anything past 24h or with wide filters, re-run the same query through LRQ with the existing `S1Client.api_token`. Don't shrink the time range to fit the MCP budget - LRQ will handle what the MCP can't.
2. **Any multi-slice, long-window, or programmatic PowerQuery.** Default to LRQ rather than `/dv/events/pq` or `/api/powerQuery`, especially for ranges > 24h.

Minimal fallback pattern (inline, no extra client class required):

```python
import time, requests
from s1_client import S1Client

c = S1Client()
jwt = c.api_token
base = c.base_url  # e.g. https://usea1-purple.sentinelone.net
headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
body = {
    "queryType": "PQ", "tenant": True,
    "startTime": "2026-04-21T00:00:00Z", "endTime": "2026-04-22T00:00:00Z",
    "queryPriority": "HIGH",
    "pq": {"query": "<your PQ>", "resultType": "TABLE"},
}
r = requests.post(f"{base}/sdl/v2/api/queries", headers=headers, json=body, timeout=30)
qid = r.json()["id"]
forward_tag = r.headers["X-Dataset-Query-Forward-Tag"]
# poll every 1-2s, cancel on completion - see the powerquery skill's lrq-api.md
```

For anything beyond a single slice (ranges > 2-3 days, heavy aggregates, 100M+ event scans), use the full runner at `/sessions/great-serene-euler/pq_30d_max_lrq_v2.py` (two-JWT round-robin, ~29s on a 30d 574M-event aggregate) rather than hand-rolling poll/cancel. The measured perf and slicing recipes are in `references/tenant_capabilities.md` (bottom) and in the sentinelone-powerquery skill's `references/lrq-api.md`.

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

- Prod (US1): `https://ingest.us1.sentinelone.net`. Override via `uam_alert_interface_url` in `config.json` or the `--uam-url` flag / `S1_UAM_ALERT_INTERFACE_URL` env var. The legacy config key `ingestion_gateway_url` and env var `S1_IGW_URL` are still honored as fallbacks.
- Auth: `Authorization: Bearer <JWT>`. NOT `ApiToken`. The mgmt-console JWT in `config.json` works; the endpoint rejects `ApiToken ...` with HTTP 401 `"Unsupported auth type"`.
- Body: concatenated JSON (one or more objects back-to-back, optionally newline-separated), gzip-compressed. `Content-Encoding: gzip` is mandatory. zstd also accepted.
- Scope: `S1-Scope: <accountId>` or `<accountId>:<siteId>[:<groupId>]` is mandatory.
- Success shape: `202 Accepted` with `{"details":"Success","status":202}`.

**Endpoints:**

- `POST /v1/indicators` -- raw behavioral indicators. Each must carry `metadata.profiles = ["s1/security_indicator"]` and a unique `metadata.uid` (this is the join key). Batching: send many indicators in one call by passing a list; the client concatenates + gzips.
- `POST /v1/alerts` -- SecurityAlert wrappers. Each references its indicator(s) via `finding_info.related_events[].uid == indicator.metadata.uid`. A single alert can reference multiple indicators (one entry per indicator). The server stitches them into `alert.rawIndicators` / the UAM Indicators tab once both land.

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

# One batched POST per resource; alert references both indicators via
# finding_info.related_events[].uid.
uam_iface.post_indicators([ind_a, ind_b], scope=f"{account_id}:{site_id}")
uam_iface.post_alerts    ([alert],        scope=f"{account_id}:{site_id}")
# Then poll UAM GraphQL (unified_alerts.list_alerts) to see it surface.
```

**Validation:** after ingest, find the alert via UAM GraphQL (`unified_alerts.list_alerts` filtered by name, or `get_alert(alert_id)` once you know it). `get_alert_with_raw_indicators(c, alert_id)` returns the raw indicator dict(s) so you can confirm every `metadata.uid` and its observable names made it through.

**Cleanup:** ingested alerts are not hard-deletable via public API. The standard reversibility pattern is to set `status=RESOLVED` and `analystVerdict=TRUE_POSITIVE_BENIGN` via the bulk-ops mutations in `unified_alerts` so the alert exits the active SOC queue and is tagged as synthetic.

**Multi-indicator alert constraints** (empirically confirmed on
`usea1-purple` 2026-04-22):

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

## Common high-value workflows

- **Unified alert triage** — `list_alerts(...)` from `unified_alerts` for the modern multi-source alerts inbox (EDR + XDR + Identity + cloud + third-party); use `facets`/`group-by` for volume rollups; `set_alert_status` / `set_analyst_verdict` / `assign_alerts` for triage decisions; `add_alert_note` for context.
- **Threat triage (legacy)** — `GET /threats` filtered by `createdAt__gte` + `resolved=false`; enrich with agent details from `/agents?ids=...`; output a table.
- **Endpoint isolation** — find agent IDs (`/agents` with name/IP filter), confirm count, `POST /agents/actions/disconnect` with filter.
- **Hunt across DV / PowerQuery** -- `POST /sdl/v2/api/queries` with `queryType="LOG"` (S1QL) or `queryType="PQ"` (PowerQuery), then poll `GET /sdl/v2/api/queries/{id}` echoing the `X-Dataset-Query-Forward-Tag` response header. Auth is Bearer, not ApiToken. Legacy `/dv/init-query` + `/dv/query-status` + `/dv/events` + `/dv/events/pq` flows are deprecated (sunset 2027-02-15). See `references/WORKFLOWS.md` Section 4 for the canonical runner.
- **Natural-language hunt via Purple AI** -- `purple_query(c, "...")` to generate a PQ, review, then execute via LRQ. Only for SDL-telemetry questions; route entity questions to REST.
- **Site/Group inventory** — `/sites`, `/groups`, `/accounts` are the tenant-structure endpoints; many resources require filtering by `siteIds` / `accountIds`.
- **Bulk action audit** — `/activities` is the system-wide audit log; filter by `activityTypes` and `createdAt__gte`.
- **Push alerts + indicators INTO UAM** -- build OCSF payloads, `UAMAlertInterfaceClient.post_indicators([...])` then `.post_alerts([...])` (see "UAM Alert Interface" section above). Use for pipeline integrations, synthetic-alert generation, and detection testing.

Consult the per-tag reference files for exact parameter names — the above are orientation, not copy-paste ready.
