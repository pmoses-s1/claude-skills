---
name: sentinelone-mgmt-console-api
description: Use this skill whenever the user wants to query or act on a SentinelOne Management Console — threats, alerts, agents, sites, accounts, groups, exclusions, firewall, device control, RemoteOps, Deep Visibility, Hyperautomation, Unified Alert Management (UAM), Purple AI, or any other S1 Mgmt API resource. Trigger on "SentinelOne", "S1", "Singularity", "Unified Alerts", "UAM", "Purple AI", "/web/api/v2.1/...", S1 agent/threat/site/account IDs, or requests like "list my endpoints", "triage alerts", "add a note to an alert", "resolve these STAR alerts", "isolate an endpoint", "disconnect agent", "run RemoteOps script", "pull DV query results", or "ask Purple AI a natural-language question". Also trigger for reports, bulk actions, or anything automating a SentinelOne tenant. The skill wraps the full S1 Mgmt REST API (781 ops, 113 tags, v2.1) plus the UAM GraphQL and Purple AI GraphQL endpoints, with a Python client, cursor pagination, a searchable index, and natural-language + alert-triage wrappers.
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

1. **Find the right endpoint.** Use `scripts/search_endpoints.py` with a keyword matching the user's intent. This returns method + path + tag + summary. If the result set is large, narrow with `--tag` (e.g. `Threats`, `Agents`, `Sites`).
2. **Read the per-tag reference.** Open `references/tags/<Tag>.md` (names match the table in `references/TAG_INDEX.md`) to see full parameter lists, descriptions, required permissions, and response codes for that group. Only read the tag file(s) relevant to the task — don't read them all.
3. **Call the endpoint.** Either use `scripts/call_endpoint.py` for one-off calls, or import `S1Client` from `scripts/s1_client.py` in a Python script for anything that needs loops, joins, or transforms.
4. **Paginate correctly.** S1 list endpoints use cursor-based pagination. The client's `paginate()` and `iter_items()` handle this automatically — prefer them over manual `skip`/`limit` math, which caps at 1000 items.
5. **Summarize the result for the user.** Don't dump raw JSON unless asked. Prefer a short prose summary plus a table or CSV/XLSX if the volume warrants.

## Files in this skill

- `config.json` — credentials (user updates these).
- `scripts/s1_client.py` — importable Python client. Handles auth, retries on 429/5xx, pagination.
- `scripts/call_endpoint.py` — CLI for one-shot calls: `python scripts/call_endpoint.py GET /web/api/v2.1/agents --param limit=5`.
- `scripts/search_endpoints.py` — keyword search over the endpoint index: `python scripts/search_endpoints.py "isolate"`.
- `scripts/purple_ai.py` — Purple AI natural-language wrapper over `POST /web/api/v2.1/graphql` (undocumented endpoint). Exports `purple_query()` and `PurpleAIError`.
- `scripts/call_purple.py` — CLI wrapper: `python scripts/call_purple.py "show powershell.exe outbound connections"`.
- `scripts/unified_alerts.py` — Unified Alert Management (UAM) GraphQL wrapper over `POST /web/api/v2.1/unifiedalerts/graphql`. Covers the full query + mutation surface (list/filter/group/notes/history/trigger-actions). See `references/UNIFIED_ALERTS.md`.
- `scripts/call_unified_alerts.py` — CLI for UAM: `python scripts/call_unified_alerts.py list --filter detectionProduct=EDR --first 10`, `... add-note <id> "…"`, `... set-status --scope <acct> --alert-id <id> RESOLVED`.
- `references/UNIFIED_ALERTS.md` — UAM reference: operation catalogue, schema quirks, filter patterns, action catalogue, worked recipes.
- `references/TAG_INDEX.md` — table of all 113 tags with file pointers and op counts. Start here when you don't know which tag owns an endpoint.
- `references/endpoint_index.json` — compact machine-readable index (one entry per op). Used by `search_endpoints.py` but can be read directly if you need to filter programmatically.
- `references/tags/<Tag>.md` — per-tag reference with parameters, descriptions, and required permissions. Load only the files you need.
- `references/common_params.md` — shared query params (`skip`, `limit`, `cursor`, `sortBy`, etc.) and the pagination pattern.
- `spec/swagger_2_1.json` — the original full Swagger spec (14 MB). Use only when the per-tag reference is insufficient — e.g. to resolve a deeply nested request-body schema by `$ref`. Never read this whole file into context.

## Using the client in Python

```python
import sys
sys.path.insert(0, "scripts")  # or set PYTHONPATH
from s1_client import S1Client, S1APIError

c = S1Client()

# single page
r = c.get("/web/api/v2.1/threats", params={"limit": 100, "resolved": False})

# full iteration
for threat in c.iter_items("/web/api/v2.1/threats", params={"limit": 200}):
    ...

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

## Unified Alert Management (UAM) — alert triage and bulk actions

SentinelOne exposes a documented GraphQL endpoint at `POST /web/api/v2.1/unifiedalerts/graphql` for the Unified Alerts product — the modern, multi-source alerts inbox that spans EDR, XDR, Identity, STAR, Cloud, NGFW, and ingested third-party telemetry (Palo Alto, Netskope, Mimecast, Proofpoint, etc.). Auth is the same `Authorization: ApiToken` header as REST; no extra credentials. Full reference in `references/UNIFIED_ALERTS.md`.

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

## Common high-value workflows

- **Unified alert triage** — `list_alerts(...)` from `unified_alerts` for the modern multi-source alerts inbox (EDR + XDR + Identity + cloud + third-party); use `facets`/`group-by` for volume rollups; `set_alert_status` / `set_analyst_verdict` / `assign_alerts` for triage decisions; `add_alert_note` for context.
- **Threat triage (legacy)** — `GET /threats` filtered by `createdAt__gte` + `resolved=false`; enrich with agent details from `/agents?ids=...`; output a table.
- **Endpoint isolation** — find agent IDs (`/agents` with name/IP filter), confirm count, `POST /agents/actions/disconnect` with filter.
- **Hunt across DV** — `POST /dv/init-query` → poll `/dv/query-status/{queryId}` → `GET /dv/events`.
- **Natural-language hunt via Purple AI** — `purple_query(c, "...")` → review the generated PQ → execute via DV/PowerQuery. Only for SDL-telemetry questions; route entity questions to REST.
- **Site/Group inventory** — `/sites`, `/groups`, `/accounts` are the tenant-structure endpoints; many resources require filtering by `siteIds` / `accountIds`.
- **Bulk action audit** — `/activities` is the system-wide audit log; filter by `activityTypes` and `createdAt__gte`.

Consult the per-tag reference files for exact parameter names — the above are orientation, not copy-paste ready.
