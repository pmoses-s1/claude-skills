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
