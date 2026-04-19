# Detection rules — STAR / Custom Detection / PowerQuery Alerts

PowerQuery Alerts (and STAR / Custom Detection rules that use a PowerQuery body) have tighter limits than ad-hoc hunts. This file covers how to write detection rule bodies that are correct, cheap, and reliably fire.

## Hard limits

- **1,000 rows maximum** on any intermediate table (including inside `group` and `join`).
- **1 MB RAM** total.
- `nolimit` is not allowed.
- Subqueries are not supported (the Summary service evaluates at ingest time and can't compute inner queries).
- `compare` isn't useful here (alerts don't do timeshift).
- Depending on platform version, `transpose` may not be supported — prefer `group` + explicit columns.
- The rule should return **one row per finding** with stable, well-named columns (the detection engine maps these to alert fields).

If you hit the 1,000-row limit on an intermediate `group`, the alert silently under-counts. This is dangerous for detections — validate the filter is selective enough before saving as a rule.

## Shape of a good rule

```
<highly-selective-initial-filter>
| group
    count = count(),
    first_seen = oldest(timestamp),
    last_seen  = newest(timestamp),
    host       = any(endpoint.name),
    cmdline    = any(src.process.cmdline)
  by agent.uuid, src.process.storyline.id
| filter count >= 5            // the actual detection threshold
| sort -count
| limit 100
```

Why this shape:

- `group by agent.uuid, src.process.storyline.id` gives one row per (endpoint, activity cluster). That matches what the detection engine wants.
- `any(endpoint.name)` / `any(src.process.cmdline)` carry human-readable context through the group. Don't use `array_agg` in an alert body — arrays aren't supported by `savelookup` and bloat the 1 MB budget.
- `oldest(timestamp)` / `newest(timestamp)` are the canonical way to surface the detection window. They require *no* preceding `sort` / `group` / `limit` and must appear in the aggregation.
- `filter count >= N` is the threshold. Keeping the threshold inside the query (rather than tuning outside) keeps the rule self-contained.
- A final `limit` caps the emitted alert count per evaluation window — keeps you honest about alert fatigue.

## Patterns

### 1. Rare-event detection

Something that fires once per endpoint per unusual activity. Low threshold, high specificity.

```
indicator.name = 'EventViewerTampering'
| group
    first_seen = oldest(timestamp),
    last_seen  = newest(timestamp),
    host       = any(endpoint.name),
    count      = count()
  by agent.uuid, src.process.storyline.id
| sort -count
| limit 100
```

### 2. Threshold / rate detection

"More than N of X from one entity in the window."

```
event.login.loginIsSuccessful = false
| group
    fails     = count(),
    src_ips   = estimate_distinct(src.endpoint.ip.address),
    last_seen = newest(timestamp)
  by agent.uuid, event.login.userName
| filter fails >= 10
| sort -fails
| limit 100
```

### 3. Anomaly via combined signals

Combine filters with `and` in the initial filter, not `and` in a computed column — the initial filter is cheapest and gates what the Summary service scans.

```
event.type = 'Process Creation'
src.process.parent.name = 'winword.exe'
src.process.name in ('powershell.exe', 'pwsh.exe', 'cmd.exe', 'wscript.exe', 'cscript.exe', 'mshta.exe', 'regsvr32.exe', 'rundll32.exe')
| group
    count      = count(),
    first_seen = oldest(timestamp),
    last_seen  = newest(timestamp),
    host       = any(endpoint.name),
    cmdline    = any(src.process.cmdline)
  by agent.uuid, src.process.storyline.id
| sort -count
| limit 100
```

### 4. Allowlist via `lookup`

When a rule would otherwise fire too broadly, exclude known-good via a config-managed data table.

```
<filters producing candidate rows>
| lookup is_allowed = allowed from allowlist_hosts by endpoint.name
| filter is_allowed = null                   // kept rows had no allowlist entry
| group count = count(), last_seen = newest(timestamp) by agent.uuid, src.process.storyline.id
| sort -count
| limit 100
```

This uses `lookup` with a config data table (`/datatables/allowlist_hosts`). Keep the table ≤ 400 KB; prefer an opt-in allowlist, not an opt-out denylist, because the former is bounded.

### 5. Join-based correlation

`inner` / `left` joins work in alerts, bounded by the 1,000-row / 1 MB budget. Put strict filters inside each subquery; don't rely on the outer `filter` to prune.

```
| inner join
    lsass_access = (
      indicator.name = 'CredentialDumping'
      | group last = newest(timestamp), host = any(endpoint.name)
        by agent.uuid, src.process.storyline.id
      | sort -last
      | limit 500
    ),
    powershell = (
      event.type = 'Process Creation'
      src.process.name contains 'powershell'
      | group ps_cmdline = any(src.process.cmdline)
        by agent.uuid, src.process.storyline.id
      | limit 500
    )
    on agent.uuid, src.process.storyline.id
| columns agent.uuid, host, ps_cmdline, last
| limit 100
```

## Checklist before saving a rule

- [ ] Initial filter is specific enough that you'd expect far fewer than 1,000 intermediate rows in any realistic window.
- [ ] No `nolimit`, no `compare`, no subqueries.
- [ ] `group` carries `agent.uuid` (or equivalent) so the detection engine can map to an alert asset.
- [ ] `group` includes `oldest(timestamp)` and `newest(timestamp)` (or a `last_seen = …` single value), so the alert has a time.
- [ ] Final `| sort -count | limit N` caps alert volume.
- [ ] Threshold (`filter count >= N`) is set to something your team will actually triage, not 1.
- [ ] Tested in Event Search over a realistic 24-hour window and produces a plausible number of rows (0-5 is good for most detections).

## Mapping fields to alert properties

When a detection rule fires, the detection engine looks for these columns to populate the alert. Use them verbatim.

| Alert field | Column to emit |
|---|---|
| Asset / endpoint | `agent.uuid`, `endpoint.name` |
| Storyline | `src.process.storyline.id` |
| Timestamp | `timestamp` (or a `.timestamp`-suffixed column like `last_seen.timestamp`) |
| Evidence | `cmdline = any(src.process.cmdline)`, `path = any(tgt.file.path)`, etc. |
| Count / severity driver | `count = count()` |

Renames are fine: the engine resolves by name, so `host = any(endpoint.name)` is fine; it just helps the analyst read the row.

## Testing a rule body before deploying

1. Run it with the Purple MCP `powerquery` tool over the last 24 hours. Confirm it parses and returns 0–N rows (not an error, not thousands).
2. Confirm the threshold (`filter count >= N`) doesn't zero out the result for a known-good example — walk `N` down until you see a row, then set `N` slightly above what a benign environment would produce.
3. Run it over 7 days for baseline volume: expected row count × 7 ≈ what a week of alerting will look like.
4. If the `group`-intermediate ever exceeds 1,000 rows in a 24-hour window, tighten the initial filter.
