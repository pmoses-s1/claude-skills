# SDL Parser Syntax — Full Reference

SDL parsers are **augmented JSON**: unquoted keys are allowed, string values can span lines, and `//` / `/* */` comments are supported. The file is stored at `/logParsers/<NAME>` on the SDL tenant and applied by name via `uploadLogs` (`parser: <NAME>` header) or `addEvents` (`attrs.parser`).

## Table of contents

1. [Top-level keys](#top-level-keys)
2. [Formats](#formats)
3. [Field-matcher syntax](#field-matcher-syntax)
4. [Patterns](#patterns)
5. [Attributes (tagging)](#attributes-tagging)
6. [Line groupers (multi-line)](#line-groupers-multi-line)
7. [Rewrites](#rewrites)
8. [Special fields: timestamp, severity, message](#special-fields-timestamp-severity-message)
9. [Discard, halt, repeat, skipNumericConversion, intermittentTimestamps](#behavior-flags)
10. [Associations (correlate non-adjacent lines)](#associations)
11. [Aliases](#aliases)
12. [Parse limits](#parse-limits)

---

## Top-level keys

```js
{
  timezone: "UTC",
  attributes: { vendor: "FortiNet", dataset: "fortigate" },
  patterns:  { ts: "\\d{4}-\\d{2}-\\d{2}T[0-9:.]+Z" },
  lineGroupers: [ { start: "^\\[", continueThrough: "^\\s+at " } ],
  formats: [ /* see below */ ],
  mappings: { mappings: [ /* see references/mappers.md */ ] },
  aliasTo: "otherParser"   // short-circuit: everything else ignored
}
```

- `timezone` applies when the parsed timestamp itself has no offset. Prefer IANA names (`America/New_York`) so DST is respected; avoid `EST` / `PST` which are fixed offsets.
- `attributes` at the top level apply to every event this parser produces.
- `aliasTo` is mutually exclusive with the rest — it re-points this name to another parser file. Aliases cannot chain.

## Formats

`formats` is a list; each item can be a raw string (shorthand for `{ format: "..." }`) or a full object:

```js
{
  id: "tcp-body",
  attributes: { protocol: "tcp" },
  format: ".*proto=TCP $src$:$spt$ -> $dst$:$dpt$",
  discard: false,
  halt: true,
  repeat: false
}
```

Formats are tried in declaration order against the **whole line**. A format that doesn't match simply doesn't apply; a format that matches merges its captures into the event. When `halt: true`, matching stops after the first match.

### Fragment formats

A format that starts with `.*` matches *anywhere* in the line, not just the start. This is the "line fragment" idiom used to share captures across related event variants. Combined with `halt: true` it's how you build "first match wins" logic.

## Field-matcher syntax

Inside a format string, `$name=pattern{opt1}{opt2}$` captures a named field. All parts except `$name$` are optional:

```
$fieldName  = patternName  {parse=json}  {regex=\\d+}  {attrWhitelist=foo.*}  {timezone=UTC}  $
```

- **`patternName`** — a name from `patterns:`, or a predefined pattern: `digits`, `number`, `alphanumeric`, `identifier`, `quotable`, `quotableNoEscape`, `quoteOrSpace`, `quoteOrSpaceNoEscape`, `json` (brace-matched with nesting support).
- **`{regex=...}`** — inline regex. Metacharacters **must be double-escaped** (augmented JSON eats one backslash): `\\d`, `\\s`, `\\.`, `\\\\`.
- **`{parse=directive}`** — apply a sub-parser to the captured value. See `parse-directives.md`.
- **`{attrWhitelist=rx}` / `{attrBlacklist=rx}`** — after a sub-parse, filter which generated subfields are kept.
- **`{timezone=...}`** — field-level override when the field is `timestamp`.

### Default pattern quirks

A `$field$` followed by a **space** with no explicit pattern defaults to the `quotable` pattern (stops at whitespace, honors embedded quotes). A `$field$` followed by **`\"`** enables backslash-escape handling in the capture. Adjacent `$a$$b$` with no delimiter is invalid unless `$a$` has a pattern or regex that bounds it.

### Reserved field names

- `message` — the raw event text. Cannot be captured into from a format. Can be dropped with `discardAttributes: ["message"]`.
- `timestamp` — parsed as the event time (see *Special fields*).
- `severity` — mapped to 0–6 (see *Special fields*).
- `parser` — filled in by the ingest pipeline.
- `host` / `serverHost` — set from the `server-host` upload header.

### Escaping literals

- Literal `$`: `\$$` (backslash, dollar, terminator).
- Literal single space: `\\ ` (backslash-space); a bare space matches `\s+`.
- Literal backslash: `\\\\`.

## Patterns

Named regex fragments. Define once, reuse in many formats:

```js
patterns: {
  ts:      "\\d{4}-\\d{2}-\\d{2}T[0-9:.]+Z",
  ipv4:    "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
  ipv46:   "(\\d{1,3}(\\.\\d{1,3}){3}|[0-9a-f:]+)"
},
formats: [
  "$timestamp=ts$ $src=ipv46$ -> $dst=ipv46$"
]
```

The predefined patterns (no need to declare):

| Name | Matches |
|---|---|
| `digits` | `\d+` |
| `number` | integer or float, signed |
| `alphanumeric` | `[A-Za-z0-9]+` |
| `identifier` | `[A-Za-z_][A-Za-z0-9_.-]*` |
| `quotable` | bare token, or balanced double-quoted string with `\"` escape |
| `quotableNoEscape` | same but `\` is literal |
| `quoteOrSpace` | value up to next space or matching quote |
| `quoteOrSpaceNoEscape` | same, no escape handling |
| `json` | brace-matched JSON object with nesting |

## Attributes (tagging)

```js
attributes: { vendor: "FortiNet", dataset: "fortigate" }
```

Constant key/value pairs attached to every matching event. Can live at the top level (applies to all formats in this parser) or on an individual format (applies only when that format matches). Use for vendor/product tagging, tenant stamps, and dataset routing.

### Per-format override

A format's `attributes:` block **overrides** the top-level attributes for events that match that format. This is the idiomatic way to produce multiple OCSF classes from one parser (e.g., Abnormal Security's parser emits `class_uid: 2001` for email events and `class_uid: 3002` for authentication events from the same parser) — set the common attributes at top level, then let each format override `class_uid`, `activity_id`, `severity_id`, and `activity_name`.

The 4 mandatory attributes (`dataSource.category` hardcoded to `"security"`, `dataSource.name`, `dataSource.vendor`, `metadata.version`) should live at the parser-root `attributes:` block, not per-format. OCSF subtype fields (`activity_id`, `activity_name`, per-subtype `severity_id`) should live per-format. Per-format `attributes:` override parser-root `attributes:`, which is the mechanism for one parser fanning out to multiple OCSF classes (e.g. Windows Event 4624 → Authentication, 4720 → Account Change). `metadata.version` may also be overridden per-event from inside a `mappings.constant` op when the source carries its own schema version.

### `class_uid` string vs integer

OCSF defines these as integers. Many ai-siem catalog parsers emit them as strings (`"class_uid": "4001"`). Both survive ingest. Prefer integers in new work — integer form keeps PowerQuery filters simple (`class_uid = 4001` rather than `class_uid = '4001'`).

## Line groupers (multi-line)

Combine adjacent lines into one logical event *before* formats run. Max 100,000 chars per joined event.

```js
lineGroupers: [
  {
    start: "^\\[\\d+-\\d+-\\d+ ",     // required: the "new event starts here" regex
    continueThrough: "^\\s+at "        // OR continuePast / haltBefore / haltWith
  }
]
```

| Continuation mode | Behavior |
|---|---|
| `continueThrough` | Keep accumulating while following lines match the pattern (e.g., stack traces indented). |
| `continuePast` | Accumulate matches, then one more line (e.g., `\`-terminated continuation). |
| `haltBefore` | Stop *before* the next line matching the pattern (new-message marker). |
| `haltWith` | Stop *at and including* the line matching the pattern (e.g., statement `;` terminator). |

## Rewrites

Applied *after* formats extract fields. Array on a format object:

```js
rewrites: [
  { input: "message", match: "password=[^& ]*", replacement: "password=[REDACTED]", replaceAll: true },
  { input: "rawTs",   match: "^(\\d+)-(\\d+)-(\\d+)T(.*)$", replacement: "$1/$2/$3 $4", output: "timestamp" },
  { input: "message", match: "user=(\\w+)", replacement: "$1", output: "user", outputIfNoMatch: false },

  // Time between two timestamps (seconds):
  { action: "timeDelta", startTime: "connStart", endTime: "connEnd", output: "durationSec" },

  // PowerQuery-driven enrichment (S-24.4.5+):
  { action: "computeFields",
    expression: "| lookup city_code from geo_table by src_ip | let risk_score = if(severity >= 5, 10, 1)" }
]
```

Notes:
- `$1..$n` reference regex capture groups.
- `replaceAll: true` replaces every match, not just the first.
- `outputIfNoMatch: false` suppresses the output field when the regex doesn't match (default is to copy `input` verbatim).
- `timeDelta` doesn't yet support a per-rule `timezone` — set it at parser level or inline in the source timestamp.
- `computeFields` can read from lookup tables, add/overwrite fields, and drop events via `discard: { filter: "..." }` on the format. Supported PQ subset: `columns`, `filter`, `let`, `lookup`, `parse` plus most Array/Geolocation/Network/Numeric/String/Time/Timestamp functions. Excluded array functions: `array_agg`, `array_agg_distinct`, `array_from_json`, `array_to_json`, `extract_matches`, `extract_matches_matchcase`.

## Special fields: timestamp, severity, message

**`timestamp`** — the event time. SDL recognizes most common forms. Timezone precedence: a parsed `timezone` field > `{timezone=...}` option on the `$timestamp$` matcher > parser-level `timezone` > GMT. Prefer UTC at the source.

**`severity`** — mapped to an internal integer + label:

| String | Int | Label |
|---|---|---|
| `fatal` | 6 | Critical |
| `error` | 5 | Critical |
| `warn` | 4 | High |
| `info` | 3 | Medium |
| `fine` | 2 | Low |
| `finer` | 1 | Info |
| `finest` | 0 | No severity |

Missing → `info` (3).

**`message`** — raw event text, reserved. Cannot be captured into. Rewrite rules can modify a portion (a rule whose regex matches the entire value is silently ignored). Drop it via `discardAttributes: ["message"]` — highly recommended for JSON-parsed logs to reduce storage.

## Behavior flags

- `discard: true` on a format — drop events matching the format. Discarded events don't count toward log volume.
- `discard: { filter: "keep = false" }` (S-24.4.5+) — conditional drop driven by a `computeFields` rewrite that sets a boolean field.
- `halt: true` — after this format matches, stop trying further formats on the same line.
- `repeat: true` — keep re-applying this format at the position after the last match (required for key/value catch-alls).
- `skipNumericConversion: true` — preserve string values that look numeric (e.g., postal code `00187`). Per-format flag.
- `intermittentTimestamps: true` — parser-level; for logs that emit a timestamp only when the clock rolls over. Lines without a timestamp inherit the most recent one instead of the ingest time.

## Associations

Join non-adjacent lines that share a correlation key (e.g., request-start + request-end). Possibly deprecated — check with Support before relying on it. Association state is purged ~60 seconds after first sighting.

```js
{
  format: "started req $requestId$",
  association: { tag: "req", keys: ["requestId"], store: ["src"] }
},
{
  format: "ended req $requestId$",
  association: { tag: "req", keys: ["requestId"], fetch: ["src"] }
}
```

## Aliases

```js
{ aliasTo: "json" }
```

Mutually exclusive with everything else. Aliases cannot chain (target must be a real parser).

## Parse limits

- Per-event parse limit: **just under 50,000 characters.** Oversize events are truncated *before* parsing.
- Per-joined event via line groupers: **100,000 characters.**
- Per `uploadLogs` body: **6 MB.**
- Per tenant, per day via `uploadLogs`: **10 GB.** Use `addEvents` for higher volume.
