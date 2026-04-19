---
name: sentinelone-powerquery
description: Use any time the user wants to author, debug, optimize, explain, or run a SentinelOne PowerQuery (PQ) — Deep Visibility / Event Search queries, XDR/EDR threat hunting, investigations, STAR / Custom Detection rule bodies, PowerQuery Alerts, or Singularity Data Lake dashboard panels. Trigger on PowerQuery, PQ, Event Search, Deep Visibility, S1QL, SDL, STAR rule, Custom Detection rule, PowerQuery Alert; on queries using fields like `event.type`, `src.process.*`, `tgt.file.*`, `indicator.*`, `agent.uuid`; on pipes like `| group`, `| filter`, `| let`, `| join`, `| parse`, `| columns`, `| compare`, `| top`, `| union`, `| lookup`, `| savelookup`, `| dataset`. Also trigger when asked to hunt a TTP, IOC, behavior, or alert pattern on a SentinelOne tenant — even casually ("find powershell reaching out to the internet", "write a detection for lsass access"). Explicitly NOT Microsoft Power Query / M / Excel and NOT Splunk SPL — this is SentinelOne's pipeline query language for security telemetry.
---

# SentinelOne PowerQuery

PowerQuery (PQ) is SentinelOne's pipeline query language for the Singularity Data Lake. It reads like `filter | command | command | …` — events that match the initial filter flow through a sequence of piped transformations (group, let, join, sort, columns, etc.).

Use this skill to write correct, efficient, runnable PowerQueries for threat hunting, investigations, detection rule bodies, and dashboards.

## Workflow

When the user asks you to write or investigate with a PowerQuery:

1. **Clarify the intent** if it's ambiguous (time range, data view, what the output should look like). A good PQ is scoped — not everything needs to be hunted over 30 days.
2. **Draft the query** following the grammar below. Favor `filter | group | sort | limit | columns` as the default shape — it's what most real investigations need.
3. **Run it against the tenant** using the Purple MCP `powerquery` tool to confirm it parses and produces plausible results. This is the single fastest way to catch syntax mistakes and wrong field names. If the user's request is clear and low-risk (read-only query), just run it; don't ask permission.
4. **Iterate**: if the query errors or returns obviously wrong results, read the error, fix, rerun. If the query returns nothing, that is a legitimate result — don't blindly loosen it; check the time range and filter logic first.
5. **Explain the result briefly** and cite any fields you're relying on. If you used a non-obvious pattern (subquery, `savelookup`, `transpose`, `compare`), explain *why* you chose it.

## The grammar in one page

```
initial-filter-expression
| command
| command
| …
```

**Initial filter** (everything before the first `|`) is the only place where `* contains "x"` and `* matches "regex"` multi-field search works. It can be empty — start the query with `|` and it is treated as "all events" (e.g., `| group ct=count() by event.type`).

**Commands** (each starts with `|`):
- `filter expr` — keep matching rows (initial filter implicit)
- `columns f1, "Renamed f2"=f2, …` — select, rename, compute output columns (creates a *new* record set — previous fields not accessible after)
- `let f = expr, …` — add computed fields without discarding existing ones
- `group agg(x), name2=agg2(y) by f1, "grouped name"=f2` — aggregate; also creates a new record set
- `sort +f1, -f2` — `-` = descending
- `limit N` — truncate (default shows 10 without it; output is capped at 1,000 rows if no `limit`/`group`)
- `parse "…$field$…" from srcField` — extract fields from unstructured text
- `lookup col, … from tableName by key=expr` — join against a CSV/JSON config data table
- `dataset 'config://datatables/<name>'` — read a lookup table as the source of the pipeline
- `savelookup 'tableName'[, 'merge']` — persist current result as a reusable lookup table
- `| [inner|left|outer|sql inner|sql left|sql outer] join (q1), (q2), … on k1, a.x = b.y` — correlate subqueries (must start `| join`, not just `join`)
- `| union (q1), (q2), …` — merge heterogeneous result sets (up to 10 queries; use when `filter (…or…)` can't express it)
- `| transpose colName on keyCol, …` — pivot a column into many columns (must be LAST command)
- `| compare [name=]timeshift('-1w')` — re-run the same query shifted in time and put both in one table (must be LAST command; only one `compare` allowed)
- `| top K agg(x) by f1, f2` — probabilistic top-N (fast on huge ranges; `count()`/`sum()` are "(estimated)", `min`/`max` exact)
- `| nolimit` — raise the row cap to 3 GB (slow; one concurrent nolimit query at a time; never use in Dashboards or PowerQuery Alerts)

**Expressions** use standard operators: `=` / `==` / `!=`, `<` / `<=` / `>` / `>=`, `&&` / `||` / `!` (or `AND` / `OR` / `NOT`), ternary `a ? b : c` (put spaces around the `:`), arithmetic `+ - * / %`, and these text operators:

| Operator | Meaning |
|---|---|
| `x contains 'sub'` | substring (case-insensitive) — also `contains ('a','b','c')` for OR |
| `x contains:matchcase 'Sub'` | case-sensitive substring |
| `x matches 'regex'` | regex (case-insensitive, double-escape) — `matches ('a','b')` for OR |
| `x matches:matchcase '…'` | case-sensitive regex |
| `x in ('a','b',123,true)` | exact equals any; case-sensitive; `in:anycase` for case-insensitive; does NOT match null |
| `x = *` | field is present/non-null |
| `!(x = *)` | field is null/missing |
| `$"regex"` | shorthand for `message matches "regex"` (initial filter only) |
| `#shortcut = 'value'` | pre-defined multi-field shortcut (e.g., `#ip`, `#hash`, `#name`, `#cmdline`, `#storylineid`, `#username`) |

Strings need quotes (`'foo'` or `"foo"`); numbers and booleans don't. Underscores in numbers are OK for readability (`1_000_000`).

## The most important rules (learned the hard way)

These are where queries go wrong. Internalize them before writing.

1. **`*` is NOT a valid standalone initial filter.** `* | limit 5` returns a 500 error on many tenants. Use `| limit 5` (empty initial filter, start with a pipe) or target a real field like `event.type=*`. The `*` wildcard only works as `field = *` (not-null), `* contains '…'`, or `* matches '…'`.
2. **Double-escape regex almost everywhere.** `src.process.cmdline matches "\\d+"`, `tgt.file.path matches '^C:\\\\Windows\\\\Temp\\\\[a-z]{8}\\.tmp$'`. The only place you don't double-escape is the `$"…"` shorthand (searches `message`).
3. **After `columns` or `group`, previous fields are gone.** These commands create an entirely new record set. If you'll need a field later, carry it through: `group ct=count(), host=any(endpoint.name) by src.process.storyline.id` — don't expect `endpoint.name` to still be addressable after that `group` unless you aggregate it.
4. **Subqueries can't go after `group`, `sort`, or `limit`.** And the subquery must itself produce the column named in the `in (...)` expression (via `columns` or `group`). `user in (action='login' | group 1 by user)` is valid; `user in (action='login')` is not.
5. **`compare` and `transpose` must be the LAST command.** Put `sort` before `compare` if you want to order the non-shifted side.
6. **`join` must start with a pipe.** `| join (…), (…) on x` — without the `|`, "join" is interpreted as a search term. Inner/left joins allow up to 10 subqueries; `sql inner` and `sql left` allow only 2.
7. **`null` behaves like false in boolean context.** `filter x = null` works after the field is defined by a prior command; before then, use `!(x = *)` for is-null and `x = *` for is-not-null.
8. **`contains` is case-insensitive by default; `in` is case-sensitive by default.** The `:matchcase` / `:anycase` suffixes reverse this.
9. **Performance: filter early, group narrow.** Push filters above the first pipe when possible. In `group`, prefer low-cardinality fields; for long ranges, consider `| top K …` instead (probabilistic but orders of magnitude faster).
10. **Alerts and Dashboards have tighter limits.** A PowerQuery Alert is capped at 1,000 rows intermediate / 1 MB RAM. Don't put `nolimit` in a dashboard panel.
11. **Shortcut fields (`#cmdline`, `#name`, `#hash`, …) don't work as initial filters on every tenant.** They're documented but return 500 on many deployments. Prefer explicit field names (`src.process.cmdline contains 'x'`) — they're as terse and always work. Save shortcuts for exploratory Event Search where you're not scripting against the API.
12. **Aggregates to prefer: `min_by` / `max_by` over `first` / `last`.** `first(x)` and `last(x)` are sometimes listed as aggregates but fail on many tenants. Use `min_by(x, timestamp)` and `max_by(x, timestamp)` — they're explicit about ordering and always work.
13. **Percentiles: use `p50`/`p95`/`p99`, not `percentile(x, N)`.** The latter isn't a real function and returns 500.
14. **Null-filter at the wrong stage: `filter x = null` before `x` is computed returns 500.** Use `filter !(x = *)` for is-null until after a `let`/`join`/`lookup` has produced `x`.

## Running queries via Purple MCP

The `mcp__purple-mcp__powerquery` tool runs your query against the tenant. It needs ISO-8601 `start_datetime` and `end_datetime` with a timezone (e.g., `2026-04-19T06:00:00Z`). Use `mcp__purple-mcp__get_timestamp_range(hours=24)` to get a relative-time range.

Default to the last 24 hours. Longer ranges are fine but slower and more likely to hit the 5-minute query timeout. If a query is heavy, tighten the range before adding `nolimit`.

When the user describes a hunt in natural language and you're unsure of the right fields or shape, `mcp__purple-mcp__purple_ai` can produce a PowerQuery — useful as a starting point. When it returns one, run it as-is (don't rewrite it blindly), then iterate on the result.

## Reference files — read as needed

Don't read these upfront. Read the one you need.

- `references/syntax-and-operators.md` — full operator reference, identifier rules, shortcut fields, regex dialect, date/time formats, short-circuit `||`.
- `references/commands-reference.md` — deep dive on every command (join variants, subqueries, lookup / dataset / savelookup, transpose, compare, top, nolimit). Read before writing anything non-trivial with join, transpose, or compare.
- `references/functions-reference.md` — all built-in functions: string, numeric, JSON, network, URL, aggregate, array (method chaining), geolocation, timestamp, time, string-formatting. Read when you need a function and can't remember the name.
- `references/fields-and-schema.md` — common EDR/XDR field paths (`src.process.*`, `tgt.file.*`, `event.login.*`, `dst.ip.*`, `indicator.*`, etc.) and OCSF conventions. Read when you're not sure what field holds the thing you want.
- `references/detection-rules.md` — how to author PowerQuery Alerts / STAR / Custom Detection rule bodies, including the 1,000-row / 1 MB alert constraints and which PQ features are supported in alert context.
- `references/pitfalls.md` — curated list of common failures and their fixes (the `*`-as-filter trap, forgetting `|` before `join`, subquery position errors, memory-limit messages, etc.).

## Examples library — read when a hunt matches

- `examples/investigations.md` — ready-to-run investigation queries (PowerShell outbound, suspicious cmdline patterns, lateral movement, LOLBins, credential access, defense evasion, user-activity baselines, endpoint heartbeat, indicator prevalence). Each example includes a brief "what this finds" note and the full PQ.
- `examples/detection-library.md` — PQ bodies ready to paste into a STAR / Custom Detection / PowerQuery Alert, sized to stay within the 1,000-row/1 MB alert budget. Each entry names the MITRE technique and gives a `threshold` suggestion.

## When to reach for join vs union vs subquery

These three blur together. Quick rules:

- **Subquery** (`field in (inner | columns field)`) — single-field "is this value in that set" filtering. Simplest and usually fastest. Use for allowlist / denylist / top-N-and-pivot patterns.
- **Join** — multi-field correlation where columns from both sides of a row must match each other (`on a.user = b.user, a.host = b.host`) *or* you need to bring extra columns from the second query into your output.
- **Union** — heterogeneous result sets that you want stacked as rows, possibly with rename/unification. Handy when the same logical event lives in two different log sources with different field names.

Prefer subqueries for exclusion/inclusion; reach for `join` when a row must "know" multiple things at once.

## Writing detection rules vs ad-hoc hunts

A PowerQuery used as a detection rule body (STAR / Custom Detection / PowerQuery Alert) is more constrained than a hunt query:

- Intermediate and output tables must stay under 1,000 rows and 1 MB of RAM.
- No `nolimit`.
- No `compare`, usually no `transpose` (depends on version).
- The rule should produce one row per finding, with stable columns the detection engine can map to alert fields (e.g., `agent.uuid`, `endpoint.name`, `src.process.storyline.id`, `timestamp`).
- Keep the initial filter as specific as possible — this is what's evaluated in the summary service and is what gates cost.

For detection rule patterns and a checklist, see `references/detection-rules.md` and `examples/detection-library.md`.

## A minimal but realistic example

Hunt: PowerShell that made an outbound connection to a non-RFC1918 IP in the last 24 hours, with command line.

```
src.process.name contains 'powershell' dst.ip.address = *
| let is_private = net_rfc1918(dst.ip.address)
| filter is_private = false
| group hits = count(),
        ips  = array_agg_distinct(dst.ip.address, 20),
        cmdline = any(src.process.cmdline)
  by endpoint.name, src.process.storyline.id
| sort -hits
| limit 50
```

Notice: filter early (`dst.ip.address = *` prunes events without a destination IP), `net_rfc1918` is the right way to split internal vs external (don't hand-roll CIDRs), `array_agg_distinct` caps the array so the row stays small, `any(src.process.cmdline)` grabs a representative cmdline since we're collapsing per storyline.
