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

```json
{
  "title": "About this dashboard",
  "graphStyle": "markdown",
  "content": "## SOC Overview\nThis dashboard tracks **threat activity** across all managed endpoints.\n\n[Open Event Search](/logs)"
}
```

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

### EDR / XDR telemetry (endpoint events)
```
dataSource.category = 'security'
event.category in ('process', 'file', 'ip', 'dns', 'indicators', 'logins', 'url', 'registry')
```

### Activity feed (console audit log)
```
dataSource.name='ActivityFeed'
activity_type in ("17", "43", ...)    // use quoted strings for activity_type
```

### Third-party sources
```
dataSource.vendor = 'Microsoft'        // O365, Azure AD
dataSource.name = 'FortiGate'          // Fortinet
metadata.product.name = 'SharePoint'
```

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
