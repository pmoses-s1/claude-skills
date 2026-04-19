---
name: sentinelone-mgmt-console-api
description: Use this skill whenever the user wants to query or act on a SentinelOne Management Console — threats, alerts, agents, sites, accounts, groups, exclusions, firewall, device control, RemoteOps, Deep Visibility, Hyperautomation, or any other S1 Mgmt API resource. Trigger on mentions of "SentinelOne", "S1", "S1 console", "Singularity", "/web/api/v2.1/...", S1 agent IDs, threat IDs, site IDs, account IDs, or requests like "list my endpoints", "get threats from the last 24h", "isolate an endpoint", "disconnect agent", "run RemoteOps script", "pull DV query results". Also trigger when the user asks to build reports, run bulk actions, or automate anything involving a SentinelOne tenant. The skill wraps the full S1 Mgmt Console API (781 operations across 113 tags, spec v2.1) with a ready-to-use Python client, cursor-based pagination, and a searchable endpoint index.
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

## Common high-value workflows

- **Threat triage** — `GET /threats` filtered by `createdAt__gte` + `resolved=false`; enrich with agent details from `/agents?ids=...`; output a table.
- **Endpoint isolation** — find agent IDs (`/agents` with name/IP filter), confirm count, `POST /agents/actions/disconnect` with filter.
- **Hunt across DV** — `POST /dv/init-query` → poll `/dv/query-status/{queryId}` → `GET /dv/events`.
- **Site/Group inventory** — `/sites`, `/groups`, `/accounts` are the tenant-structure endpoints; many resources require filtering by `siteIds` / `accountIds`.
- **Bulk action audit** — `/activities` is the system-wide audit log; filter by `activityTypes` and `createdAt__gte`.

Consult the per-tag reference files for exact parameter names — the above are orientation, not copy-paste ready.
