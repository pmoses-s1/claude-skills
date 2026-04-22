# Common workflows

Ready-to-adapt multi-step recipes for the most common pre-sales / SecOps requests. Each lists the minimum set of endpoints you need to orchestrate, with the params that actually matter. All are written for the Python client (`S1Client`); for one-shot CLI use, translate to `scripts/call_endpoint.py`.

---

## 1. Threat triage — what fired in the last N hours?

```python
from datetime import datetime, timezone, timedelta
since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

threats = list(c.iter_items(
    "/web/api/v2.1/threats",
    params={"createdAt__gte": since, "resolved": False, "limit": 200},
))
agent_ids = sorted({t["agentDetectionInfo"]["agentId"] for t in threats if t.get("agentDetectionInfo")})
agents = list(c.iter_items(
    "/web/api/v2.1/agents", params={"ids": ",".join(agent_ids[:500]), "limit": 500}
))
```

Key params: `createdAt__gte` (ISO-8601), `resolved=false`, `incidentStatuses=unresolved`, `confidenceLevels=malicious,suspicious`, `mitigationStatuses=not_mitigated`.

---

## 2. Endpoint inventory — what's deployed, by site, with health?

```python
rows = []
for a in c.iter_items("/web/api/v2.1/agents", params={"limit": 1000}):
    rows.append({
        "id": a["id"], "name": a["computerName"], "site": a["siteName"],
        "os": a["osType"], "version": a["agentVersion"],
        "isActive": a["isActive"], "isDecommissioned": a["isDecommissioned"],
        "lastActive": a["lastActiveDate"],
        "infected": a["infected"], "encryptedApplications": a["encryptedApplications"],
    })
```

Useful filters: `isActive=true`, `osTypes=windows,macos,linux`, `siteIds=...`, `agentVersions__contains=24`.

---

## 3. Endpoint isolation (one or many)

**Always confirm blast radius first.**

```python
filt = {"computerName__contains": "laptop-", "isActive": True}
count = c.get("/web/api/v2.1/agents/count", params=filt)
# show user: count["data"]["total"]
# then — after explicit confirmation —
c.post("/web/api/v2.1/agents/actions/disconnect",
       json_body={"filter": filt})
# undo
c.post("/web/api/v2.1/agents/actions/connect",
       json_body={"filter": filt})
```

Destructive: network quarantine has no undo beyond the corresponding `connect` action. Prefer filter-based bulk ops over per-ID loops — the API is designed for them.

---

## 4. Deep Visibility / PowerQuery hunt via LRQ

The Deep Visibility endpoints (`/dv/init-query`, `/dv/query-status`, `/dv/events`, `/dv/events/pq`, `/dv/events/pq-ping`) are deprecated and sunset on 2027-02-15. Use the **Long Running Query (LRQ) API** for every programmatic query, whether S1QL log search or PowerQuery.

```python
import time, requests
from urllib.parse import urljoin

# Auth: the same S1Client.api_token works; swap the ApiToken prefix for Bearer
jwt = c.api_token
base = c.base_url.rstrip("/")  # tenant's own console host, not xdr.us1.*

body = {
    "queryType": "PQ",          # or "LOG" for S1QL log search
    "tenant": True,             # query every account the token can reach
    "startTime": since, "endTime": now,
    "queryPriority": "HIGH",
    "pq": {
        "query": (
            "dataSource.name='SentinelOne' dataSource.category='security' "
            "event.type='Process Creation' src.process.name='powershell.exe' "
            "| group ct=count() by endpoint.name, src.process.cmdline "
            "| sort -ct | limit 100"
        ),
        "resultType": "TABLE",
    },
}

# Launch
r = requests.post(urljoin(base, "/sdl/v2/api/queries"),
                  headers={"Authorization": f"Bearer {jwt}"}, json=body,
                  timeout=30)
r.raise_for_status()
qid = r.json()["id"]
fwd = r.headers["X-Dataset-Query-Forward-Tag"]  # must echo on every GET/DELETE

# Poll (expires 30s after launch or 30s after last poll, so keep polling)
steps_seen = 0
while True:
    p = requests.get(urljoin(base, f"/sdl/v2/api/queries/{qid}"),
                     params={"lastStepSeen": steps_seen},
                     headers={"Authorization": f"Bearer {jwt}",
                              "X-Dataset-Query-Forward-Tag": fwd},
                     timeout=30)
    p.raise_for_status()
    js = p.json()
    steps_seen = js.get("stepsCompleted", steps_seen)
    if js.get("stepsTotal") and steps_seen >= js["stepsTotal"]:
        break
    time.sleep(1)

columns = js["data"]["columns"]             # list of column names
rows    = js["data"]["values"]              # 2-D array of rows

# Always clean up (releases concurrent-query budget)
requests.delete(urljoin(base, f"/sdl/v2/api/queries/{qid}"),
                headers={"Authorization": f"Bearer {jwt}",
                         "X-Dataset-Query-Forward-Tag": fwd},
                timeout=30)
```

Key points:
- `queryType: "PQ"` runs a PowerQuery; `queryType: "LOG"` runs S1QL log search. Both replace the old `/dv/*` endpoints.
- The `X-Dataset-Query-Forward-Tag` response header from the launch must be echoed on every subsequent GET/DELETE. GET/DELETE without it is rejected.
- Per-user rate cap is 3 rps. For multi-slice parallel runs over long windows (7d+), see the `sentinelone-powerquery` skill's `references/lrq-api.md` for slicing, two-JWT round-robin, and merge patterns.
- For interactive hunts over short windows, the Purple MCP `powerquery` tool is simpler; fall back to this LRQ pattern when the MCP times out or the window is longer than a few days.

---

## 5. RemoteOps script execution (destructive - confirm)

```python
# discover scripts
scripts = c.get("/web/api/v2.1/remote-scripts", params={"limit": 50})
# guardrails check first (read-only, safe)
check = c.post("/web/api/v2.1/remote-scripts/guardrails/check",
               json_body={"data": {"scriptId": SCRIPT_ID, "filter": {"ids": [AGENT_ID]}}})
# execute after user consents
c.post("/web/api/v2.1/remote-scripts/execute",
       json_body={"data": {"scriptId": SCRIPT_ID,
                           "taskDescription": "ad-hoc by Prithvi",
                           "filter": {"ids": [AGENT_ID]},
                           "outputDestination": "SentinelCloud"}})
# poll status
c.get(f"/web/api/v2.1/remote-scripts/tasks",
      params={"ids": TASK_ID})
```

---

## 6. Audit trail - who did what, when

```python
since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
events = list(c.iter_items("/web/api/v2.1/activities", params={
    "createdAt__gte": since,
    "activityTypes": "1100,1101,1102",   # filter by type; see /activities/types
    "limit": 500,
}))
```

Types are listed at `GET /web/api/v2.1/activities/types`. `1001` = threat created, `51`/`52` = agent uninstall, etc.

---

## 7. Tenant structure - accounts -> sites -> groups -> agents

```python
accounts = c.get("/web/api/v2.1/accounts", params={"limit": 100})
sites    = c.get("/web/api/v2.1/sites",    params={"limit": 1000})
groups   = c.get("/web/api/v2.1/groups",   params={"limit": 1000})
```

Many mutating endpoints require `accountIds` / `siteIds` / `groupIds`; always list these first to get the right scope.

---

## 8. Exclusions & blocklist inspection

```python
hashes = list(c.iter_items("/web/api/v2.1/restrictions",
                           params={"type": "black_hash", "limit": 500}))
paths  = list(c.iter_items("/web/api/v2.1/exclusions",
                           params={"type": "path", "limit": 500}))
```

Exclusions v2.1 (`/exclusions-v2`) is the newer API — prefer it on modern tenants.

---

## 9. Report a tenant's capability snapshot (perfect for pre-sales demos)

Run the read-only smoke test sweep and capture which endpoints are reachable on this tenant:

```bash
python scripts/smoke_test_queries.py --workers 12
# writes references/tenant_capabilities.{json,md}
```

Then filter future searches to only what works:

```bash
python scripts/search_endpoints.py "threats" --only-works
```

Useful when demoing to a prospect: "here are the 164 Mgmt API endpoints your token has access to right now, grouped by tag."

---

## Anti-patterns to avoid

- **Looping per-ID calls** when a `…/actions/...` filter-based endpoint exists. S1 is built for bulk filter ops; looping will hit rate limits fast.
- **Manual `skip`/`limit` math**: the cursor cap kicks in at 1000 items. Use `client.paginate()` / `iter_items()` which cursor-pages automatically.
- **Using the legacy `/dv/init-query` + `/dv/query-status` + `/dv/events` flow**: deprecated and sunset 2027-02-15. Use LRQ with `queryType="LOG"` instead (see Section 4).
- **Trusting `totalItems`** on restricted-scope accounts: it reflects what the token can see, not the tenant total.
- **Re-reading `spec/swagger_2_1.json`** (14 MB) into context. Use the per-tag reference file or `search_endpoints.py`.
