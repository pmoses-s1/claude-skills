# Pitfalls and fixes

Curated failure modes. When a PowerQuery is misbehaving, check this list before reaching for exotic explanations.

## Syntax / grammar

### `*` alone as a filter returns 500

```
*                           ← NOT a valid initial filter on many tenants
* | limit 5                 ← same
```

Fix: start with an empty filter (just `|`) or use a non-empty filter.

```
| limit 5                                    // "all events, first 5"
event.type = *  | limit 5                    // "events with a type"
event.type = 'Process Creation' | limit 5
```

`* contains "x"` and `* matches "regex"` ARE valid but only as the *initial* filter (before the first `|`) and only in Event Search / PowerQuery, not in Alerts.

### `join` without a leading pipe

```
join (q1), (q2) on x         ← "join" is interpreted as a search keyword
```

Fix: `| join (q1), (q2) on x`. The same rule applies to `union`.

### `compare` or `transpose` not last

```
| compare last_week = timeshift('1w')
| sort -count                ← too late; compare must be LAST
```

Fix: move `sort` before `compare`. The display ordering is applied to the main results; the shifted column sits alongside.

### Subquery after `group` / `sort` / `limit`

```
| group count() by user
| filter user in (role='admin' | columns user)     ← invalid
```

Fix: move the subquery into the initial filter position.

```
user in (role='admin' | columns user)
| group count() by user
```

### Subquery doesn't define the filter column

```
user in (action='login')                                                     ← fails
user in (action='login' | group count() by ip)                               ← fails ("user" column not produced)
```

Fix: produce the column.

```
user in (action='login' | columns user)
user in (action='login' | group 1 by user)
user in (action='login' | top 10 count() by user)
```

### Shortcut fields as initial filter return 500

```
#cmdline contains 'python'              ← 500 on many tenants
#name = 'bash'                           ← 500
#hash = *                                ← 500
```

The docs list `#cmdline`, `#name`, `#hash`, `#ip`, `#storylineid`, `#username`, `#dns` as multi-field shortcuts. In practice, they're unreliable across tenants — in this deployment they all return 500 as initial filters. Fix: use the explicit field.

```
src.process.cmdline contains 'python'
src.process.name = 'bash'
tgt.file.sha256 = *
```

The explicit form is only a few characters longer and always works. Save shortcuts for interactive Event Search, not scripted queries.

### `parse` with the wrong argument order

```
| parse src.process.cmdline, "$bin$ $args$"       ← 500
```

Fix: the source goes at the end with `from`.

```
| parse "$bin$ $args$" from src.process.cmdline
```

### `first(x)` / `last(x)` / `percentile(x, N)` return 500

Some docs list these as aggregate functions, but they fail on many tenants. Use the reliable forms instead:

- `first(x)` → `min_by(x, timestamp)`
- `last(x)` → `max_by(x, timestamp)`
- `percentile(x, 0.95)` → `p95(x)` (also `p50`, `p99`)

### Ternary parsed as an identifier

```
cond?x:y                     ← ":" may be glued into an identifier
```

Fix: spaces around the `:`.

```
cond ? x : y
```

### `(field = *) ? a : b` inside `let` returns 500

PQ has no `coalesce()`. The intuitive way to fall back across multiple
fields breaks because `field = *` is a filter operator, not a boolean
expression usable in a computed column.

```
| let user_id = (actor.user.email_addr = *) ? actor.user.email_addr
                                            : actor.user.name        ← HTTP 500
```

Fix — bare-field truthy test (the field's null-or-truthy value drives the
ternary directly):

```
| let user_id = actor.user.email_addr
              ? actor.user.email_addr
              : (actor.user.name ? actor.user.name : src.process.user)
```

This is the working coalesce idiom. Chain ternaries to fall back across
N fields. Use the same pattern any time you'd reach for `coalesce` /
`ifnull` / `nvl` in SQL.

### `sum(if(...))` for conditional counts — use `count(predicate)` instead

```
| group critical = sum(if(severity_ in:anycase ('Critical'), 1, 0)) by host    ← invalid
```

PowerQuery does not accept `if(...)` as an aggregate body. The right idiom is
to pass a predicate directly to `count()`:

```
| group critical = count(severity_id == 5),
        high     = count(severity_id == 4),
        medium   = count(severity_id == 3),
        total    = count() by host
```

`count(<predicate>)` evaluates the predicate per row and sums the truthy ones.
Works for any boolean expression, including `in:anycase`, `contains`,
`matches`, and arithmetic comparisons.

### `severity_` (and other trailing-underscore fields) — SDL reserved-field rewrite

When a parser ingests source data carrying a field name that collides with an
SDL reserved name (`severity`, `status`, `classification`, `category`, etc.),
the field is automatically renamed by appending `_`. The underscored form
`severity_` IS the canonical, queryable field — not a sparse alternate to
`severity`.

There is no non-underscored `severity` field on alert / vulnerability /
misconfiguration / asset / Identity sources. Don't go looking for one. Same
rule applies to `status_`, `classification_`, `category_`, and any other
trailing-underscore field name encountered in raw events. The numeric OCSF
variants (`severity_id` 0-5, `status_id`, `class_uid`) live alongside the
underscored string fields and are usually the better choice for filters.

### `severity_` carries mixed casing — `transpose` produces 8 columns instead of 4

Same source pipeline, different upstream casing — values like `Critical`,
`CRITICAL`, `High`, `HIGH`, `Medium`, `MEDIUM`, `Low`, `LOW` co-exist in the
same `severity_` column.

```
| group count() by timestamp = timebucket('1h'), severity_
| transpose severity_ on timestamp                 ← produces 8 columns
```

Fix — normalise before grouping:

```
| let sev = lowercase(severity_)
| group count() by timestamp = timebucket('1h'), sev
| transpose sev on timestamp                       ← 4 clean columns
```

Or skip the string field entirely and use the numeric OCSF `severity_id` for
filters:

```
severity_id >= 4
| group count() by timestamp = timebucket('1h'), severity_id
| transpose severity_id on timestamp               ← columns are 4, 5
```

### Numeric counters indexed as string — column-type lock — wrap in `number()` as a failsafe

SDL/Scalyr indexes columns at first-write and locks the type. Once a numeric
field has been written as string (because a parser declared `type: "string"` or
the source data has been ingested untyped), the column stays string forever.
Subsequent writes — even from a parser declaring `type: "long"` — get coerced
back to string at index time. Numeric aggregation then breaks silently:

```
dataSource.name='FortiGate' unmapped.action='close'
| group sessions=count(), bytes_out=sum(traffic.bytes_out)         ← NaN, even though values are populated
| limit 1
```

The values ARE there (you can see them in Event Search), but `sum()` /
`avg()` / `max()` / `>=` predicates can't operate on a string-typed column.

**Failsafe pattern — cast at query time with `number()`:**

```
dataSource.name='FortiGate' unmapped.action='close'
| let bytes_out_n = number(traffic.bytes_out)
| let bytes_in_n  = number(traffic.bytes_in)
| group sessions=count(),
        bytes_out=sum(bytes_out_n),
        bytes_in=sum(bytes_in_n),
        max_session_bytes_out=max(bytes_out_n) | limit 1
```

`number(x)` returns 0 for null/missing and NaN for unparseable strings, so the
defensive cast is cheap and never breaks already-numeric data. Apply it
preemptively to:

| Field family | Why |
|---|---|
| `severity_id`, `status_id`, `class_uid`, `type_uid`, `category_uid` | OCSF numerics, but column-type can drift between tenants |
| `traffic.bytes_in`, `traffic.bytes_out`, `traffic.packets_in`, `traffic.packets_out`, `unmapped.duration` | FortiGate marketplace parser declared these as `string` for many tenant generations — string column lock is widespread |
| Any vendor field carrying counts or sizes | If a parser ever wrote a non-numeric token (`"-"`, `"unknown"`, blank), the column is locked string |

Same trick works for arithmetic comparisons and sorts:

```
| let sev = number(severity_id)
| filter sev >= 4
| group n=count() by sev
| sort sev
```

The previous tenant-specific workaround using `parse "$x{regex=\\d+}$"` still
works and is slightly more robust against fields like `"42 KB"` (where you
want the digits, not a NaN), but `number()` is shorter and is the
recommended default for OCSF counter fields.

### Bracket array indexing in `columns` returns HTTP 500

```
dataSource.name='alert'
| columns severity_id, resources[0].name, vulnerabilities[0].cve.uid     ← HTTP 500
```

PowerQuery does not accept `[N]` array indexing in `columns`. The V1 `query`
API (used for schema discovery) flattens nested arrays into display keys like
`resources[0].name` — those flattened keys are NOT valid PowerQuery field
paths.

Fix — for first-element access inside a query, use `array_get` in a `let`:

```
| let first_resource = array_get(resources, 0)
| let first_resource_name = first_resource.name
```

For analytics over array fields, prefer top-level scalar fields
(`severity_id`, `finding_info.title`, `metadata.product.name`, `class_name`),
or step out of PowerQuery to the V1 query API which exposes the full event
JSON.

## Escaping

### Regex backslashes eaten

```
src.process.cmdline matches "\d+"         ← only one level of escaping; often matches nothing
```

Fix: double-escape everywhere except the `$"…"` shorthand.

```
src.process.cmdline matches "\\d+"
```

Windows paths — four-ish backslashes for a literal `\`:

```
tgt.file.path matches '^C:\\\\Windows\\\\Temp\\\\[a-z]{8}\\.tmp$'
```

### Case sensitivity flip

- `contains` and `matches` default to **case-insensitive**. `contains:matchcase`, `matches:matchcase` to make them case-sensitive.
- `in` and `=` (for strings) default to **case-sensitive**. `in:anycase` to make `in` case-insensitive.

If a query "misses" something you can see in the data, check whether case was the issue. `lower(field) contains 'x'` is a pragmatic workaround when the field isn't suited to `contains:matchcase`.

## Logic

### Null fields

- `field = *` → field is present (non-null).
- `!(field = *)` → field is null / missing.
- `field = null` — only valid as a boolean test *after* the field has been computed by a preceding command (e.g., a left join or a `let`).
- `in (…)` cannot match null. If null should count as a match, use `OR !(field = *)`.

### `count(x)` doesn't count nulls; does count zero / false

`count()` counts rows. `count(expr)` counts rows where `expr` is truthy. Zero, `false`, and empty string are falsy — they DON'T count. But null is also falsy, so this matches intuition.

If you want "count of rows where `login_success = false`", write `count(login_success = false)`, not `count(login_success) - count(login_success = true)`.

### `if x = y and z = w` short-circuits — but so does `or`

`||` returns the first truthy *value*, not a boolean. `a || b` with `a = "0"` returns `"0"` (non-empty string, truthy), not a boolean `true`. If you want boolean behavior, wrap with `bool(…)`.

### `newest()` / `oldest()` after `sort` fails silently

These functions require the original timestamp ordering of events. If you `sort` (or `group`, or `limit`) before using them, they produce null or wrong results. Use them in the same `group` as the aggregation — don't aggregate in two stages.

## Performance / memory

### "Memory limits" message

```
213,408 of 37,059,484 matching events (0.576%) were omitted due to memory limits.
```

Intermediate `group` table hit 100,000 rows. Fixes in order of preference:

1. Tighten the initial filter.
2. Group on a lower-cardinality field (group by `host` instead of `(host, cmdline)`, or `net_url_path(url)` instead of full URL).
3. Pre-filter with `| filter … | group 1 by key` as a subquery to prune before the heavy group.
4. Switch to `| top K` (probabilistic).

If all else fails and you need exact numbers over a long range, `| nolimit` — but this is slow and serializes across the tenant.

### Long time range timing out

The query timeout is 5 minutes. If a 30-day query times out:

- Narrow the initial filter (almost always the biggest lever).
- Use `top` instead of `group`.
- Consider running the query over 7-day chunks and `savelookup`-ing each, then `union`-ing.

### Reaching for `message contains` on a JSON-blob source

Some data sources (O365 audit, generic webhook ingest, custom HEC sources) keep most fields inside a raw JSON `message` blob rather than as parsed top-level columns. The first instinct is to write `message contains 'value'`, but that forces a substring scan of the entire blob and falls off a performance cliff fast: queries that work at 1 day routinely time out at 7.

Fix: use the multi-field shortcut `* contains 'value'` (or `* matches 'regex'`) in the initial filter. It searches across all indexed fields, including parsed scalars from the source, and is dramatically faster than scanning a single concatenated blob.

```
// slow — single-column substring scan
dataSource.name='<source>' message contains 'value'

// fast — multi-field index search
dataSource.name='<source>' * contains 'value'
```

Same rule applies to value-anywhere lookups regardless of the source: when a user asks for "all column search", "search all fields", "search all data", or "anywhere in the event", the canonical idiom is `* contains` / `* matches` in the initial filter, not `message contains`.

Three caveats worth remembering:

- `* contains` / `* matches` only work in the **initial** filter — before the first `|`. They cannot be used in `| filter …` after a pipe, in Alerts, or after a `| group` / `| columns` that has reshaped the row.
- If the value really only lives inside a JSON blob (e.g., a deeply nested key not exposed as a parsed field), neither `* contains` nor `message contains` will surface it efficiently. Pull rows with a narrower predicate (event type, actor, time slice) and post-process the blob in Python.
- Negation against a JSON blob (e.g., "recipients NOT in `<owned_domain>`") is not expressible inline. Filter by the positive predicate, then post-process to apply the exclusion.

### High-cardinality `by`

Grouping by full URL or full command line yields one row per variant — useless for summaries and likely to hit memory limits. Prefer:

- URL path instead of full URL (`net_url_path(url.address)`).
- `src.process.name` instead of `src.process.cmdline`.
- `src.process.storyline.id` as a "session" key that groups related process lineage.

### `lookup` before `group`

A `lookup` before a `group` is evaluated per-event. Once per-group is always cheaper:

```
// ← slower
| lookup os_version from machineinfo by endpoint.name
| group count() by endpoint.name, os_version

// ← faster
| group count() by endpoint.name
| lookup os_version from machineinfo by endpoint.name
```

## Alert-specific issues

### Rule silently under-counts

The 1,000-row intermediate cap in Alerts means a heavy `group` silently drops rows. Validate the filter is narrow enough that you'd never exceed 1,000 rows in a reasonable window.

### Rule uses `compare` or a subquery

Alerts don't support these. Move the correlation logic into a `join` (bounded) or rewrite as a single-pass `group`.

### Array or very wide string breaks 1 MB

`array_agg(large_string_field)` can blow the 1 MB budget even with < 100 rows. Replace with `any(…)` (one value per group) or cap the array aggressively: `array_agg(…, 20)`.

## Result-quality issues

### Empty results from a correct-looking query

Before blaming the query:

1. Time range: are you sure events exist in the window?
2. Data view: `EDR` doesn't have integrated sources; `XDR` does; `All Data` adds Collector.
3. Case: are you using `contains` (ci) or `in` / `=` (cs)?
4. Field name: does the field exist on this schema? Run `| limit 1 | columns …` to inspect one event.

Don't keep re-running slightly rephrased versions — the Purple MCP docs warn explicitly against that. If the data isn't there, no rewrite finds it.

### Results look plausible but wrong magnitude

Common cause: grouping dropped a field you assumed was still present, or duplicate rows from a `union`. Add `columns` at the end to make the exact shape explicit, then re-inspect.
