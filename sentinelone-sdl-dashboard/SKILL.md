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
3. **Write the JSON** — Use the panel type reference below and real examples in `references/community-examples.md`. Compute explicit `x`/`y`/`w`/`h` for every panel.
4. **Validate queries** — Sample 3-5 events per source/event-ID to confirm field semantics. Test each panel query via the `sentinelone-powerquery` skill. Run the parallel load test (see **Pre-deploy validation**) — acceptance thresholds: slowest panel ≤ 2s, wall-clock ≤ 5s.
5. **Deploy** — Use the `sentinelone-sdl-api` skill to `put_file` to a path like `/dashboards/my-dashboard`. Save a backup of the prior JSON first. Sleep 3s, then `get_file` to verify the version bumped.
6. **Iterate** — Show the user what was built, explain each panel, offer to tweak. If the dashboard hangs, follow the escalation ladder in **Pre-deploy validation**.

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
Every panel **must** have explicit `x`, `y`, `w`, `h` in its `layout` object. Dashboards with many panels (observed at 18+) where `x`/`y` are omitted can hang the browser renderer indefinitely — the auto-layout pass appears to loop on collision detection when panels stack at the implicit (0,0) origin. The symptom is the browser tab becoming unresponsive before any query fires.

```json
"layout": { "w": 30, "h": 14, "x": 0, "y": 0 }
```

Use this helper to pack panels into the 60-wide grid when generating JSON:

```python
class Grid:
    def __init__(self, width=60):
        self.W = width; self.x = 0; self.y = 0; self.row_h = 0
    def place(self, w, h):
        if self.x + w > self.W:
            self.y += self.row_h; self.x = 0; self.row_h = 0
        layout = {"w": w, "h": h, "x": self.x, "y": self.y}
        self.x += w; self.row_h = max(self.row_h, h)
        return layout
    def newline(self):
        if self.x > 0:
            self.y += self.row_h; self.x = 0; self.row_h = 0
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
  "query": "| group estimate_distinct(agent.uuid) | limit 1",
  "options": {
    "format": "auto",
    "precision": "0",
    "suffix": " endpoints"
  }
}
```

> **Options — stick to the minimal set.** Production reference dashboards only set `{format, precision, suffix}`. Fields like `backgroundColor` and `color` are documented in some places but are not consistently honoured by the renderer — at best silently ignored, at worst the panel renders blank or hangs. Do not add them until tested against the specific tenant.

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
| `transpose <field> on timestamp` hangs the renderer when field values contain hyphens (e.g. `db-prod-01`, ISO dates, UUIDs, container names) | The renderer must parse the transposed values as column names for the chart legend. The PQ parser reads `db-prod-01` as subtraction and throws `Identifier is ambiguous` — or hangs silently. The V1 API tolerates this; the renderer does not. | **Option A** — pre-process: `\| let host_safe = replace_all(host_raw, '-', '_')` then transpose on `host_safe`. **Option B (preferred for by-host charts)** — avoid transpose: use `"xAxis": "grouped_data"` with a grouping query. Loses time dimension but renders reliably. **Option C** — only use `transpose` on fields whose values are guaranteed free of hyphens (numeric codes, single-token labels like `Success`/`Failure`). |
| Number panel, table panel, or whole dashboard slow to load on first open | "All API queries pass" ≠ "dashboard loads fast". The browser fires all panel queries in parallel; total load time ≈ slowest single panel. Serial validation in a script wildly overestimates wall-clock load time. | Run a parallel load test before every `put_file` — see **Pre-deploy validation** section below. Acceptance thresholds: slowest single panel ≤ 2s, wall-clock ≤ 5s, zero failures. |
| `get_file` returns HTTP 404 immediately after a successful `put_file` | `put_file` is synchronous but the file propagates across replicas with eventual consistency (~2-3s). | Always `time.sleep(3)` between `put_file` and the subsequent `get_file` verification call. |
| `min(timestamp)` / `max(timestamp)` displays as a giant integer like `1.777e18` | Aggregating over `timestamp` returns raw nanoseconds. The renderer has no implicit date formatter for aggregate output. | Wrap with `simpledateformat(min(timestamp), 'yyyy-MM-dd HH:mm:ss z', '<TZ>')`. For millisecond-typed fields (e.g. `time` on `dataSource.name='asset'`), multiply by 1000000 first: `simpledateformat(max(time) * 1000000, ...)`. Functions that do NOT exist: `format_timestamp`, `formatTimestamp`, `iso8601`, `date_format`. |
| Hostname/value-list filter is slow or behaves differently in the renderer vs API | `field matches '(host-a\|host-b)'` is evaluated as a regex per event, and hyphenated literals inside alternation can interact with the parser. | Use `field in ('host-a', 'host-b', 'host-c')` for any fixed list. Faster (indexed lookup), no escaping needed, consistent across renderer and API. Fall back to `matches` only when a true regex pattern is needed. |
| "User" panels dominated by machine accounts (e.g. `host123$`, `dc-prod-01$`) | Machine accounts carry a trailing `$` and appear in the same fields as human accounts. | Add `\| filter !(field matches '.*\\$$')` after the event filter and before the group. Verify with 5-10 sample rows that no machine accounts leak through. |
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

| Dashboard duration | Safe `timebucket` | Points per series |
|---|---|---|
| `1h`  | `'1m'`  | 60 |
| `4h`  | `'5m'`  | 48 |
| `24h` | `'1h'`  | 24 |
| `7d`  | `'1h'`  | 168 |
| `14d` | `'1d'`  | 14 |
| `30d` | `'1d'`  | 30 |

For a 24h dashboard, `'10m'` (144 points) can work for low-cardinality single-series panels but should not be the default — use `'1h'`. For a multi-series transpose, the data-point count compounds: `timebucket('10m')` on a 24h dashboard with a 7-series transpose = 1,008 cells per chart.

**Never use `timebucket('10m')` on a 7-day dashboard** — that's 1,008 points per series.

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

### 9. Wrap string-prone numeric fields with `number()` before arithmetic

SDL/Scalyr column types are locked at first ingest. A field that *should* be numeric — `severity_id`, `traffic.bytes_in/out`, `traffic.packets_in/out`, `unmapped.duration` — can be string-typed at the index level (because a parser declared `type: "string"` for many tenant generations, or the field was first-written before the type was set). When that happens, `sum()` / `avg()` / `max()` / `>=` predicates return NaN or fail silently *even though the values are populated and visible in Event Search*.

**Failsafe pattern for every dashboard panel that does numeric work:**

```
dataSource.name='alert' severity_id=*
| let sev = number(severity_id)
| filter sev >= 4
| group hits=count() by sev
| sort sev
```

```
dataSource.name='FortiGate' unmapped.action='close'
| let bytes_out_n = number(traffic.bytes_out)
| let bytes_in_n  = number(traffic.bytes_in)
| group sessions=count(),
        bytes_out=sum(bytes_out_n),
        bytes_in=sum(bytes_in_n),
        max_session=max(bytes_out_n)
| limit 1
```

`number(x)` returns 0 for null/missing and NaN for unparseable strings. Already-numeric data is unaffected. Cost is one `let` per panel; benefit is the dashboard keeps working when a parser pushes a string-typed write or a tenant column is locked. Apply this to every numeric counter / severity / port / duration field unless this session's schema discovery proved the column type with a successful unwrapped `sum()`.

See `sentinelone-powerquery/references/pitfalls.md` for the full discussion of column-type lock and when the `parse "$x{regex=\\d+}$"` extraction is preferable to `number()`.

---

## Pre-deploy validation

### The browser renderer is a separate execution path

The SDL engine has three query surfaces: the V1 query API, the LRQ async API, and the in-browser dashboard renderer. The renderer has different timeouts, a stricter column-name parser, and a different concurrency model. A query that returns results instantly via the API can still hang the renderer. "All API queries pass" is necessary but not sufficient. The renderer is the only path that matters for dashboards, and it cannot be tested directly except by deploying and opening the page.

The learnings below let you predict and eliminate renderer failures before deploy.

### Parallel load test (run before every `put_file`)

The browser fires all panel queries in parallel on load. Total dashboard load time ≈ slowest single panel + small per-panel render overhead. Always run a parallel load test before deploying a new or significantly modified dashboard:

```python
import concurrent.futures, time

def run_one(panel_query):
    c = SDLClient()
    # auth setup ...
    t0 = time.time()
    try:
        res = c.power_query(query=panel_query, start_time="24h")
        return ("OK", time.time() - t0, res.get("matchingEvents") or 0)
    except Exception as e:
        return ("FAIL", time.time() - t0, str(e)[:200])

queries = [p["query"] for tab in dashboard["tabs"] for p in tab["graphs"]
           if p.get("graphStyle") != "markdown" and p.get("query")]

wall_t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(run_one, queries))
wall_clock = time.time() - wall_t0

print(f"  Total serial:        {sum(r[1] for r in results):.1f}s")
print(f"  Wall-clock parallel: {wall_clock:.1f}s   <- expect this in browser")
print(f"  Slowest single:      {max(r[1] for r in results):.1f}s")
```

**Acceptance thresholds:** slowest single panel ≤ 2s, wall-clock parallel ≤ 5s, zero failures. If the slowest panel exceeds 2s, identify it and rewrite: replace `group` with `top K`, narrow the initial filter, raise the timebucket granularity, or split the dashboard.

### Deploy-and-verify: sleep before re-fetching

`put_file` returns `{"status": "success"}` synchronously, but the file propagates across replicas with eventual consistency. Calling `get_file` ~100ms after a successful PUT can return HTTP 404. Always wait:

```python
res = c.put_file(path=DASH_PATH, content=new_content, expected_version=cur_version)
assert res.get("status") == "success"

import time
time.sleep(3)            # eventual-consistency window

post = c.get_file(DASH_PATH)
assert post.get("version") != cur_version  # version bumped
```

Without the sleep, verification looks like a deploy failure even when the deploy succeeded.

---

## Field semantics: verify before grouping

Two patterns cause panels to look broken silently:

**Subject vs target in Windows logon events.** For event 4624 on a domain controller, `subjectUserName` is almost always the machine account or `-`. The account that actually logged on is in `targetUserName`. A panel that groups by `subjectUserName` renders mostly empty rows.

**Same field name, different semantic per event ID.** `targetUserName` in 4624 is the human account; in 4771 (Kerberos pre-auth failure) it includes machine accounts (`host123$`). 4625 and 4740 may use `subjectUserName` depending on the failure path.

Always sample 3-5 events per event ID before authoring a grouping query:

```python
res = c.query(
    filter=f"dataSource.name=='<source>' <event-id-filter> <host-filter>",
    max_count=5, start_time="1h",
)
for m in res.get("matches") or []:
    attrs = m.get("attributes", {})
    for k in sorted(attrs.keys()):
        if any(s in k.lower() for s in ("user","subject","target","domain","logonid")):
            print(f"  {k} = {str(attrs[k])[:80]}")
```

This is the same V1-query schema-discovery pattern from the `sentinelone-sdl-api` skill — apply it per-event-ID, not just per-source.

---

## Escalation ladder when a deployed dashboard hangs

1. **Hard refresh** (`Ctrl+Shift+R` / `Cmd+Shift+R`). Eliminates cached state from a previous broken version. Resolves ~10% of "still hung" reports.
2. **Check dev-tools network tab.** If panel queries are NOT being fired, the renderer is stuck before any HTTP call. Cause is structural (layout/options/JSON parse), not query performance. If queries ARE firing, record the slowest and move to step 3.
3. **Run the slow panel's query in isolation via the V1 API.** If it returns fast, the issue is renderer-side (column names, `transpose`, panel options). If it is slow, optimise the query.
4. **Reduce panel count by 50%.** If the dashboard now loads, the issue was concurrency or memory in the renderer. Add panels back 25% at a time until a regression isolates the offender.
5. **Diff against a working reference dashboard in the same tenant.** `list_files /dashboards/`, `get_file` on a working dashboard, compare top-level keys, panel `layout` shape, `options` keys, and `graphStyle`-specific fields. Working dashboards in the same tenant are more reliable ground truth than any external documentation, because rendering rules drift between SDL releases.
6. **Roll back.** Always keep a backup of the prior dashboard JSON before `put_file`-ing a new version. Restore via `put_file(expected_version=current)` to unblock analysts while iterating offline.

---

## Pre-deploy checklist

Run this before every `put_file`:

```
[ ] Every panel has explicit x, y, w, h in layout
[ ] No panel uses `transpose <field> on timestamp` where <field> values can contain hyphens
[ ] All number panels end with `| limit 1`
[ ] All table panels end with explicit `| limit N`
[ ] All time-series panels use a timebucket appropriate for duration (see table above)
[ ] min/max(timestamp) columns wrapped in simpledateformat(...) with tz
[ ] Any millisecond-typed time field multiplied by 1000000 before simpledateformat
[ ] Hostname/value-list filters use `field in (...)` not `field matches '(...)'`
[ ] Number panels use only {format, precision, suffix} in options
[ ] Markdown panels use `markdown:` field, not `content:`
[ ] 3-5 sample events checked to verify which field carries the user semantic per event ID
[ ] Machine-account filter applied on user-facing panels
[ ] Parallel load test passes: wall-clock <= 5s, slowest panel <= 2s, zero failures
[ ] Backup of current dashboard JSON saved (for rollback)
[ ] put_file called with expected_version of the current deployed copy
[ ] sleep(3) before re-fetching to verify deploy
```

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


## Sandbox proxy blocked? Use Desktop Commander

Dashboard deployment uses `sdl_client.py` from the `sentinelone-sdl-api` skill, which
makes direct HTTPS calls to `*.sentinelone.net`. If you see `SandboxProxyBlockedError`
or `OSError: Tunnel connection failed: 403 Forbidden`, the Cowork sandbox proxy is
blocking those calls.

The fix: write the dashboard JSON to `/tmp/` via `mcp__Desktop_Commander__write_file`,
then deploy with `mcp__Desktop_Commander__start_process` running `sdl_client.py` on the
host Mac. `credentials.json` is at the project root folder
(`~/Documents/Claude/Projects/Prithvi/`). See the `sentinelone-sdl-api` skill for
full Desktop Commander fallback instructions.
