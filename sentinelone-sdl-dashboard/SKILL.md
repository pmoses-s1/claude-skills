---
name: sentinelone-sdl-dashboard
author: Prithvi Moses <prithvi.moses@sentinelone.com>
description: >
  Use this skill any time the user wants to create, edit, design, generate, deploy, or debug a SentinelOne Singularity Data Lake (SDL) dashboard. Triggers include: "build me a dashboard", "create a dashboard panel", "write dashboard JSON", "add a panel to my dashboard", "deploy a dashboard to SDL", "I want a dashboard that shows...", "can you make a dashboard for...", "threat dashboard", "SOC dashboard", "network dashboard", "audit dashboard", "O365 dashboard", "hunting dashboard", or any request that involves SDL/Scalyr dashboard JSON. Also triggers when the user pastes dashboard JSON and wants help fixing, improving, or extending it. Use alongside sentinelone-sdl-api to deploy dashboards, and alongside sentinelone-powerquery to validate or compose the queries inside panels. Always use this skill when dashboards, dashboard panels, or SDL visualization is involved — even if the user just says "show me [metric] over time" in a security/SDL context.
---

# SentinelOne SDL Dashboard Skill

This skill helps you design, author, and deploy Singularity Data Lake (SDL) dashboards — from a single panel to a full multi-tab SOC dashboard. Dashboards live as configuration files in SDL and are authored as JSON (or a relaxed JavaScript-literal superset of it). You deploy them via the `sentinelone-sdl-api` skill's `put_file` method.

## Workflow

1. **Understand the ask** — What data should the dashboard show? Who is the audience (SOC analyst, manager, customer POC)? What time range makes sense?
2. **Design the structure** — Choose tabs (if multi-topic), then panels per tab. Match panel type to the data shape.
3. **Write the JSON** — Use the panel type reference below and real examples in `references/community-examples.md`.
4. **Validate queries** — Each panel's `query` or `filter` should be tested first. Use the `sentinelone-powerquery` skill to run queries interactively.
5. **Deploy** — Use the `sentinelone-sdl-api` skill to `put_file` to a path like `/dashboards/my-dashboard`.
6. **Iterate** — Show the user what was built, explain each panel, offer to tweak.

## Dashboard JSON structure

A dashboard is a JSON object (SDL also accepts unquoted keys — JavaScript-literal format). Three top-level shapes:

### Single-tab dashboard
```json
{
  "duration": "4h",
  "description": "Optional text shown below the title",
  "graphs": [ /* array of panel objects */ ]
}
```

### Multi-tab dashboard
```json
{
  "configType": "TABBED",
  "duration": "24h",
  "description": "",
  "tabs": [
    { "tabName": "Overview", "graphs": [ /* panels */ ] },
    { "tabName": "Details",  "graphs": [ /* panels */ ] }
  ]
}
```

### Top-level properties

| Property | Description |
|---|---|
| `duration` | Default time range: `"30m"`, `"4h"`, `"1 day"`, `"7 days"` |
| `description` | Subtitle shown under the dashboard title |
| `graphs` | Array of panel objects (single-tab) |
| `tabs` | Array of `{tabName, graphs}` objects when `configType: "TABBED"` |
| `configType` | Set to `"TABBED"` for multi-tab dashboards |
| `parameters` | Array of `{name, values, defaultValue}` — creates dropdown/text filters |
| `options` | `{"layout": {"fixed": 1}}` to lock drag-and-drop |
| `teamEmails` | Array of account emails whose data is pooled |

## Panel types and JSON

Every panel is an object inside `graphs`. The `graphStyle` property picks the panel type.

### Layout
Every panel can include a `layout` object placed by the GUI. For hand-authored JSON, you can set `w` (width, max 60) and `h` (height, ~14 units per half-page). The x/y are auto-computed if omitted.

```json
"layout": { "w": 30, "h": 14, "x": 0, "y": 0 }
```

---

### Line / Area chart (time-series, multi-plot)

`graphStyle`: `"line"` or `"area"` (or `"stacked"` for stacked area)

Best for: event rates over time, multi-metric comparison, trend lines.

```json
{
  "title": "Threat confidence over time",
  "graphStyle": "area",
  "lineSmoothing": "straightLines",
  "yScale": "linear",
  "plots": [
    { "filter": "event.category='indicators' indicator.category='Ransomware'", "label": "Ransomware", "facet": "count()" },
    { "filter": "event.category='indicators' indicator.category='Exploitation'", "label": "Exploitation", "facet": "count()" }
  ]
}
```

For a **PowerQuery-driven** line chart (needed for complex grouping):
```json
{
  "title": "Login attempts over time",
  "graphStyle": "line",
  "lineSmoothing": "straightLines",
  "query": "event.login.loginIsSuccessful=false | group count() by timestamp=timebucket('1h'), endpoint.name | transpose endpoint.name on timestamp"
}
```

---

### Stacked bar chart

`graphStyle`: `"stacked_bar"` or `"bar"`

Best for: category breakdowns over time, per-group counts.

```json
{
  "title": "Threats by confidence level per day",
  "graphStyle": "stacked_bar",
  "xAxis": "time",
  "yScale": "linear",
  "query": "index='activities' activity_type in ('18','19','20') | group count=count() by timestamp=timebucket('1 day'), data.confidence_level | transpose data.confidence_level on timestamp"
}
```

For a **grouped-data X-axis** (not time):
```json
{
  "graphStyle": "stacked_bar",
  "xAxis": "grouped_data",
  "query": "event.category='indicators' | group count=count() by indicator.category | sort -count"
}
```

---

### Pie / Donut chart

`graphStyle`: `"pie"` or `"donut"`

Query **must return exactly one text column and one numeric column**.

```json
{
  "title": "Top indicator types",
  "graphStyle": "donut",
  "maxPieSlices": 10,
  "dataLabelType": "PERCENTAGE",
  "query": "event.category='indicators' | group count() by indicator.category"
}
```

---

### Table panel

`graphStyle`: `"table"` (or omit — table is the default for PowerQuery panels)

Best for: raw event lists, top-N tables, IOC lookups.

```json
{
  "title": "Outbound PowerShell connections",
  "graphStyle": "table",
  "query": "src.process.name contains 'powershell' dst.ip.address=* | let rfc1918 = not (dst.ip.address matches '((127\\..*)|(192\\.168\\..*)|(10\\..*)|(172\\.1[6-9]\\..*)|(172\\.2[0-9]\\..*)|(172\\.3[0-1]\\..*)).*') | filter rfc1918=true | group hits=count() by IP=dst.ip.address | sort -hits"
}
```

---

### Number panel (gauge)

`graphStyle`: `"number"`

Query must reduce to a single number (use `group count()`, `estimate_distinct()`, etc.).

```json
{
  "title": "Distinct active endpoints",
  "graphStyle": "number",
  "query": "| group estimate_distinct(agent.uuid)",
  "options": {
    "backgroundColor": "white",
    "color": "black",
    "precision": "0",
    "format": "auto",
    "suffix": " endpoints"
  }
}
```

With trend indicator (S-25.1.5+):
```json
{
  "graphStyle": "number",
  "trendConfig": {
    "enabled": true,
    "indicators": {
      "number": { "calculationType": "PERCENTAGE", "enabled": true },
      "arrow":  { "enabled": true },
      "upwardsMeaning": "POSITIVE"
    }
  },
  "query": "...",
  "title": "Alert volume (vs previous period)"
}
```

---

### Honeycomb panel (heat map)

`graphStyle`: `"honeycomb"`

Query must return at least one text column and one numeric column. Good for per-site or per-endpoint heatmaps.

```json
{
  "title": "File creation activity by endpoint",
  "graphStyle": "honeycomb",
  "query": "src.process.tgtFileCreationCount=* | group total=sum(src.process.tgtFileCreationCount) by site=site.id, endpoint=agent.uuid | let max=overall_max(total), min=overall_min(total) | let normalized=((total-min)/(max-min))*100 | columns Site=site, Endpoint=endpoint, Normalized=normalized",
  "honeyCombColor": { "hover": "#8ED4FB", "label": "Blue", "value": "#0998E7" },
  "honeyCombThresholds": ["0","25","50","75"],
  "honeyCombGroupBy": "Site",
  "honeyCombLinkTo": "/dash?page=Endpoints+-+Overview&params=site%3D[Site]%26endpoint%3D[Endpoint]"
}
```

---

### Distribution graph

`graphStyle`: `"distribution"`

Shows frequency distribution of a numeric field (X = value range, Y = count). Use `filter` and `facet` (not `query`).

```json
{
  "title": "Distribution of outbound destination ports",
  "graphStyle": "distribution",
  "filter": "event.network.direction='OUTGOING'",
  "facet": "src.port.number"
}
```

---

### Markdown panel

`graphStyle`: `"markdown"`

Accepts GitHub-flavored Markdown. Good for section headers, links, or explanations.

> **CRITICAL:** the body field is `markdown`, **not** `content`. A panel with
> `"content": "..."` is created successfully and renders as a **blank tile with
> no error** — the API accepts it, the UI just has nothing to display. Always
> use `"markdown": "..."`.

```json
{
  "title": "About this dashboard",
  "graphStyle": "markdown",
  "markdown": "## SOC Overview\nThis dashboard tracks **threat activity** across all managed endpoints.\n\n[Open Event Search](/logs)"
}
```

---

## Common rendering pitfalls

These are silent failures — the API accepts the JSON, the panel mounts, but
either nothing draws or the panel hangs on the spinner. Apply the fix
preemptively when authoring panels of these shapes.

| Symptom | Root cause | Fix |
|---|---|---|
| Markdown panel renders blank, no error | Wrong body field | Use `markdown:` (NOT `content:`) — see Markdown panel section above |
| `area` chart with `query` field shows an indefinite spinner; no error in UI | `graphStyle: "area"` is built around the `plots: [...]` pattern. A query-driven multi-series chart that ends in `transpose` does not render under `area`. | Switch to `graphStyle: "stacked_bar"` (or `"line"`) with `xAxis: "time"`. The query body stays the same. |
| `Couldn't load content` — `"transpose" can only be used as the last command in a query` | `transpose` is the terminal command in the PQ pipeline; nothing can follow it | Remove any `\| limit N` / `\| sort` / `\| filter` placed AFTER `transpose`. If you need a limit, apply it pre-transpose via a subquery or a column-list filter |
| `Couldn't load content` — `Identifier "x-y" is ambiguous. To subtract, add spaces: "x - y". Otherwise, add backslashes: "x\-y"` | The PQ parser reads hyphenated text as a single identifier, not as subtraction | Add spaces around `-` in arithmetic: `total - min`, `max - min`, `(a - b) / (c - d)`. Same applies to all PQ panels and rule bodies. |
| Dashboard panel times out, indefinite spinner | A subquery inside the main query forces the engine to scan-and-aggregate twice. Dashboards rerun panels on every load, so the cost compounds. | Don't gate a panel query on a subquery if you can avoid it. Hardcode top-N values via inline OR clauses, or accept the full cardinality (often small after the initial filter). If a subquery is unavoidable, prefer a `lookup` against a precomputed datatable. |
| Number panel slow on a busy index | Engine keeps scanning after the answer is computed | Always terminate number panels with `\| limit 1` after the `\| group` that reduces to one row |
| Wide range + fine `timebucket` = thousands of points per series | E.g. `timebucket("10m")` over 7d = 1,008 points × N series | Match bucket to duration: 1d → `10m`, 7d → `1h` (minimum), 30d → `1 day` minimum |
| Two near-identical dashboards appear in *Configuration files* under `/dashboards/<name>` and `/dashboards/id/<dashboardId>/<name>` | The SDL UI's **Save** button writes to `/dashboards/id/<dashboardId>/<name>`. `put_file("/dashboards/<name>")` writes to the simpler path. Both render in the UI and both are visible to the file API; neither is access-controlled. | Pick one canonical path **before** the first deploy. Recommend the UI-native `/dashboards/id/<id>/<name>` if the dashboard already exists in the UI; otherwise `/dashboards/<name>`. Don't mix the two — each `put_file` to the alternate path creates a silent duplicate alongside the UI-saved copy. |
| `columns resources[0].name` or `vulnerabilities[0].cve.uid` returns HTTP 500 | PowerQuery does not accept bracket-array indexing in `columns`. The V1 query API exposes nested arrays as flattened keys (`resources[0].name`) for display, but those flattened keys are NOT valid PowerQuery field paths. | Use top-level scalar fields only (`severity_id`, `finding_info.title`, `metadata.product.name`, `class_name`, `time`). For first-element access inside a query, use `array_get(resources, 0).name` only inside `let`. For richer drill-down, switch from PowerQuery to the V1 query API (returns full event JSON) — see `sentinelone-sdl-api` skill. |

---

## Parameters (dynamic filters)

Parameters create dropdowns or text boxes that filter all panels. Reference them in queries with `#name#`.

```json
{
  "parameters": [
    { "name": "site", "values": ["us-east", "us-west", "eu-central"] },
    { "name": "endpoint", "defaultValue": "" }
  ],
  "graphs": [
    {
      "title": "Threats on #site# / #endpoint#",
      "graphStyle": "table",
      "query": "event.category='indicators' site.name='#site#' endpoint.name='#endpoint#' | group count=count() by indicator.name | sort -count"
    }
  ]
}
```

For user-friendly dropdown labels:
```json
{ "name": "region",
  "values": [
    { "label": "East Coast", "value": "us-east-1" },
    { "label": "West Coast", "value": "us-west-1" }
  ]
}
```

Hide a parameter from the UI (use as a constant):
```json
{ "name": "base_search", "options": { "display": "hidden" }, "defaultValue": "dataSource.name='MySource'" }
```

---

## Common SDL data sources and event patterns

> ⚠️ **Schemas drift between sessions and tenants.** The patterns below are
> starting points, not a registry. **Run live schema discovery (V1 query via
> `sentinelone-sdl-api` skill) on every source you'll query before authoring
> panels.** PowerQuery's default projection is `timestamp + message` only — it
> cannot discover schemas. Use the V1 `query` method which returns full event
> JSON.

### S1 internal SDL sources are OCSF-rich (NOT stubs)

`dataSource.name` values `alert`, `vulnerability`, `misconfiguration`, `asset`,
`Identity`, and `ActivityFeed` carry **rich OCSF events**, not metadata
stubs. The fields that *look* like they should exist based on the source name
(`alert.severity`, `alert.classification`, `vulnerability.kevAvailable`,
`misconfiguration.severity`) frequently do NOT exist — the actual queryable
fields are OCSF-namespaced.

| Source | OCSF class_uid | Severity field | Endpoint linkage | Notes |
|---|---|---|---|---|
| `alert` | 99602001 (S1 Security Alert) | `severity_id` (numeric 0-5) | `resources[].name`, `resources[].s1_metadata.site_name` (NOTE: `resources[N]` only readable via V1 query, not PowerQuery `columns`) | `finding_info.title` = alert name. `metadata.product.name` ∈ {STAR, EDR, Identity, CWS, EPP}. `class_name` = "S1 Security Alert" |
| `vulnerability` | 2002 (Vulnerability Finding) | `severity_id` + `severity_` (string, often empty) | `resource.s1_metadata.*`, `resource.uid` | `vulnerabilities[].cve.uid`, `vulnerabilities[].affected_packages[].{name,version,vendor_name}`. **No `kevAvailable` field in SDL** — KEV/EPSS metadata lives in the management console only |
| `misconfiguration` | 2003 (Compliance Finding) | `severity_id` | `resources[].s1_metadata.*` | `compliance.standards[]` (CIS_AKS, CIS_KUBERNETES, etc.), `compliance.requirements[]`, `policy.{name,uid,desc}`, `cloud.provider`, `finding_info.title` |
| `asset` | 3004 (Device Inventory) | `severity_id` (asset risk) | `device.agent.uuid`, `entity.uid` | `entity_result.data.console_metrics.is_connected` for online state. Does NOT have `agent.health.online` field. `operation` = OPERATION_UPSERT |
| `ActivityFeed` | n/a (custom audit) | n/a | `data.scope_*`, `site_id` | `activity_type` (numeric ID, NOT string), `primary_description`, `secondary_description`. No `activityType` (camelCase) field |
| `Identity` | 3002 (Authentication) | `severity_id`, `status_id` | `user.name`, `user.domain`, `src_endpoint.ip`, `dst_endpoint.hostname` | `auth_protocol` (Kerberos, NTLM), `ref_event_code` (Win Event ID like 4624), `unmapped.type` ("Logon Success"/"Logon Failure"), `type_name` ("Authentication: Logon") |
| `finding` | n/a — **NOT security findings** | n/a | n/a | `dataSource.category='metrics'`, `tag='ingestionHealth'`, `processor='ocsf-findings'`. This source is OCSF processor latency/batch metrics, not findings |

**OCSF severity_id mapping:** 0=Unknown, 1=Informational, 2=Low, 3=Medium,
4=High, 5=Critical, 6=Fatal. Filter via `severity_id >= 4` for High+Critical.

### Reserved-field rewrite (trailing underscore)

Field names ending in `_` (e.g. `severity_`, `status_`, `classification_`) are
SDL's auto-rename when source data carries a field name colliding with an SDL
reserved name. The underscored form **IS** the canonical, queryable field —
not a sparse alternate. The numeric OCSF variants (`severity_id`, `status_id`,
`class_uid`) live alongside the underscored string fields. The `severity_`
string can be case-mixed (`Critical` and `CRITICAL` both appear) — see
`sentinelone-powerquery/references/pitfalls.md` for handling.

### EDR / XDR telemetry (endpoint events from `dataSource.name='SentinelOne'`)
```
dataSource.category = 'security'
event.category in ('process', 'file', 'ip', 'dns', 'indicators', 'logins', 'url', 'registry')
```

`event.type='Behavioral Indicators'` carries `indicator.category`,
`indicator.name`, `agent.uuid`, `endpoint.name`, `src.process.{user,cmdline,image.path}`.

### Third-party sources
```
dataSource.vendor = 'Microsoft'        // O365, Azure AD
dataSource.name = 'FortiGate'          // unmapped.action='deny', src_endpoint.ip, dst_endpoint.ip, app_name, category_name
dataSource.name = 'Okta'               // unmapped.eventType='user.session.start', status='FAILURE'/'SUCCESS', actor.user.name, src_endpoint.ip, src_endpoint.location.country
dataSource.name = 'Zscaler Internet Access'   // http_request.url.categories
metadata.product.name = 'SharePoint'
```

Re-validate every third-party source schema in Step 2b of session init —
field namespaces vary by parser version and tenant.

### Common PowerQuery patterns for panels

**Top-N table** (always add a bar column with `showBarsColumn: "true"`):
```
event.category='indicators' | group count=count() by indicator.name | sort -count | limit 20
```

**Timeline line chart** (use `timebucket` + `transpose`):
```
event.type='process' | group count=count() by timestamp=timebucket('1h'), endpoint.os | transpose endpoint.os on timestamp
```

**Single number** (estimate_distinct for cardinality):
```
| group estimate_distinct(agent.uuid)
```

**Geo enrichment**:
```
| group count=count() by country=geo_ip_country(src.ip.address) | sort -count
```

**URL deep-link in table**:
```
| let Threat_URL = format("https://your-console.sentinelone.net/incidents/threats/%s/overview", threat_id)
| columns Computer=data.computer_name, Threat_URL, Path=data.file_path
```

---

## Deploying a dashboard via API

Use the `sentinelone-sdl-api` skill to deploy. Dashboard config files live at paths like `/dashboards/my-dashboard-name`.

```python
import sys
sys.path.insert(0, "/path/to/sentinelone-sdl-api/scripts")
from sdl_client import SDLClient
import json

client = SDLClient()
dashboard_json = { ... }  # your dashboard dict

# List existing dashboards
files = client.list_files(path="/dashboards")

# Upload / overwrite a dashboard
result = client.put_file(
    path="/dashboards/soc-overview",
    content=json.dumps(dashboard_json, indent=2)
)
print(result)
```

After deploying, open in the SDL UI: **Visibility Enhanced → Dashboards** → select the dashboard by name.

---

## Reference files in this skill

- `references/panel-type-cheatsheet.md` — One-line summary of every panel type + gotchas
- `references/community-examples.md` — Full real-world dashboard JSON examples (console audit, threat stats, alert investigation, O365, Fortinet)
- `references/common-queries.md` — Ready-to-paste PowerQuery snippets for common security use cases

Read the community examples before creating a new dashboard — they show the patterns for tabs, filters, parameters, and layout that work in production.

---

## Query performance tips

Dashboard panels run their queries in the SDL console's built-in rendering engine — not via LRQ or any external API. Every panel loads when the user opens the dashboard, so slow queries directly delay the page. Apply these rules to every query you write.

### 1. Use `net_rfc1918()` — never hand-roll CIDR regex

**Slow (avoid):**
```
| let rfc1918 = not (dst.ip.address matches '((127\\..*)|(192\\.168\\..*)|(10\\..*)|(172\\.1[6-9]\\..*)|(172\\.2[0-9]\\..*)|(172\\.3[0-1]\\..*)).*')
| filter rfc1918 = true
```
**Fast:**
```
dst.ip.address = *
| let is_external = not net_rfc1918(dst.ip.address)
| filter is_external = true
```
The built-in function is evaluated natively; the regex is evaluated as a string per event.

### 2. Always add `| limit 1` to number panels

Number panels reduce to a single row. Without `| limit 1`, the engine continues scanning after finding the answer. Always terminate:
```json
"query": "dataSource.name='ActivityFeed' activity_type in (\"133\",\"134\") | group count() | limit 1"
```

### 3. Add explicit `| limit N` to every table panel

Unbounded tables force a full scan. Always cap results:
- Detail tables (time-sorted raw events): `| limit 200`
- Aggregated top-N tables: `| limit 20` or `| limit 25`
- Donut/pie panels: `| sort -count | limit 10`

### 4. Use `event.category = *` not `event.category != ''`

`!= ''` requires evaluating the field value as a string comparison. `= *` is a cheaper is-not-null predicate:
```
dataSource.category = 'security' event.category = *
| group count=count() by timestamp=timebucket("1 day"), event.category
```

### 5. Match `timebucket` granularity to your dashboard duration

Too-fine granularity creates thousands of data points per series, slowing both query and render:

| Dashboard duration | Minimum safe timebucket |
|---|---|
| 1 day | `"10m"` (144 points) |
| 7 days | `"1h"` (168 points) |
| 30 days | `"1 day"` (30 points) |

**Never use `timebucket("10m")` on a 7-day dashboard** — that's 1,008 points per series.

### 6. Push filters early — before the first pipe

The initial filter (before the first `|`) is evaluated as an index predicate. Conditions placed there are far cheaper than `| filter` commands applied after a full scan:
```
// Good — index-level filter
event.category = 'ip' event.network.direction = 'OUTGOING' dataSource.category = 'security'
| group count=count() by dst.ip.address | sort -count | limit 20

// Bad — scans all events then filters
dataSource.category = 'security'
| filter event.category = 'ip' && event.network.direction = 'OUTGOING'
| group count=count() by dst.ip.address | sort -count | limit 20
```

### 7. Use `estimate_distinct()` for cardinality — not `count(distinct …)`

`estimate_distinct()` uses HyperLogLog and is orders of magnitude faster on high-cardinality fields like `agent.uuid`, `threat_id`, `src.process.storyline.id`.

### 8. Avoid `nolimit` in dashboard panels

`nolimit` raises the row cap to 3 GB and blocks concurrent queries. It is never appropriate in a dashboard panel — always use an explicit `| limit N` instead.

---

## Design tips

- **Use tabs** for dashboards covering multiple topics (threat overview, policy changes, user activity). Keep each tab focused.
- **Start with number panels** at the top for KPIs, then tables and charts below.
- **Avoid breakdown graphs** in production dashboards — they can time out and can't be pre-cached. Use explicit labeled plots instead.
- **Lock layout** with `options: {"layout": {"fixed": 1}}` to prevent accidental repositioning.
- **Use `showBarsColumn: "true"`** on table panels with a count column to get inline bar charts.
- **Time range**: set `duration` to match how "fresh" the data needs to be. `"4h"` for operations, `"7 days"` for trend dashboards.
- **Test queries first** with the `sentinelone-powerquery` skill before embedding them in dashboard JSON.
- **Use `estimate_distinct()`** for cardinality counts — exact distinct is expensive on large datasets.
- **Add a markdown panel** to each tab explaining what it covers — this helps both users and future editors understand the dashboard at a glance.
