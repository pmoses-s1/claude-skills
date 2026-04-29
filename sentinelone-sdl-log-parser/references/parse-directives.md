# `{parse=...}` Sub-parser Directives

A `{parse=X}` directive inside a field matcher runs a secondary parser on the captured value, generating additional fields prefixed with the parent field name (e.g., a field `uri` with `{parse=uri}` generates `uriPath`, `uriQuery_*`). Use `{attrWhitelist=rx}` / `{attrBlacklist=rx}` to filter which generated subfields are kept.

> **`attrWhitelist` / `attrBlacklist` scope** — these only filter the SUBFIELDS produced by the `{parse=...}` directive, not top-level fields you captured by name in the format string. To drop a top-level field you named explicitly, use `discardAttributes: ["fieldname"]` at the parser root, NOT a blacklist on the parse directive. Catalog parsers like `cisco_firewall-latest` show liberal use of blacklists to drop noisy nested arrays (`{attrBlacklist=(targetResources)}`, `{attrBlacklist=(threatsInfoMap|messageParts)}`); the same authors use `discardAttributes: ["message"]` separately to drop the raw event body.

> **Pipe vs parenthesized list syntax for `attrBlacklist=`** — both work in the wild:
> - Parenthesized: `{attrBlacklist=(field1|field2|field3)}` — common in Microsoft Eventhub parsers.
> - Bare list: `{attrBlacklist=field1|field2|field3}` — common in FortiGate / Cisco parsers.
> - Single field: `{attrBlacklist=tranip}` — no delimiters needed.
> Pick one style per parser for consistency.

## URI and URL-like values

| Directive | Behavior |
|---|---|
| `uri` | Split a URL into `Path` plus each query parameter as its own field. |
| `uriMultivalue` | Same but duplicate query keys become comma-joined strings instead of overwriting. |
| `uriAttributes` | URL-encoded `k=v&k=v` string with no path. |
| `urlAttributes` | Alias of `uriAttributes`. |
| `uriAttributesMultivalue` / `urlAttributesMultivalue` | Multivalue variants. |

## JSON bodies

| Directive | Flattening |
|---|---|
| `json` | CamelCase: `{"a":{"b":1}}` → `ab=1`. |
| `dottedJson` | Dotted: `{"a":{"b":1}}` → `a.b=1`. |
| `gron` | Like `dottedJson` but emits empty-prefix keys when captured into an empty name. Used by the PARSER_TEMPLATE "capture everything into `unmapped.*` then mappings" pattern. |
| `escapedJson` | Strip one backslash-escape layer before parsing. |
| `dottedEscapedJson` | Dotted + one-layer unescape. |
| `urlEncodedJson` | URL-decode first. |
| `dottedUrlEncodedJson` | Dotted + URL-decode. |
| `base64EncodedJson` | Base64-decode first. |
| `dottedBase64EncodedJson` | Dotted + base64. |

### The gron-capture idiom

```js
formats: [
  { format: "$unmapped.{parse=gron}$",
    rewrites: [ { input: "unmapped.timestamp", output: "timestamp",
                  match: ".*", replace: "$0" } ] }
],
mappings: {
  version: 1,
  mappings: [{
    predicate: "true",
    transformations: [
      { rename: { from: "unmapped.source.ip", to: "src_endpoint.ip" } },
      { rename: { from: "unmapped.action",    to: "activity_name" } }
      // ...all renames/copies/casts/constants here
    ]
  }]
}
```

This is how the community PARSER_TEMPLATE captures the entire event into `unmapped.*` and does every OCSF mapping in one place.

**Dotted source keys are flat, not nested.** When a source JSON key literally contains a dot (e.g. `"user.email": "alice@example.com"`), gron flattens it into `unmapped.user.email` as a FLAT field name. In mappings, reference it with the literal path — `from: "unmapped.user.email"` — and do NOT escape the dots. `from: "unmapped.user\\.email"` will NOT match on current tenants (tenant-validated April 2026). This contradicts the escape-the-dots guidance in the upstream PARSER_TEMPLATE.conf in ai-siem; prefer the tenant-validated form.

See `references/ai-siem-catalog.md` §"Useful reference parsers by shape" for the canonical example, and `examples/08-gron-capture-template.json` for a ready-to-use scaffold.

### Strict variants (keep arrays parseable by PowerQuery)

Non-strict variants flatten arrays into human-readable but lossy strings that `array_from_json()` cannot consume. If you plan to run PowerQuery array functions on the parsed output, use the `strict*` variant:

- `strictJson`, `strictDottedJson`
- `strictEscapedJson`, `strictDottedEscapedJson`
- `strictUrlEncodedJson`, `strictDottedUrlEncodedJson`
- `strictBase64EncodedJson`, `strictDottedBase64EncodedJson`

Non-array behavior is identical to the non-strict variant.

## Language-flavored dictionaries

| Directive | Syntax |
|---|---|
| `pythonDict` | `{'key': 'value', ...}` (single quotes, Python literals). |
| `rubyHash` | `{:key=>value, ...}` (Ruby hash rockets and symbols). |
| `dict` | Permissive catch-all for loose dict notation. |

## Key/value and separated values

| Directive | Behavior |
|---|---|
| `commaKeyValues` | `key=value, key=value, ...`. |
| `commaSeparatedValues` | Positional; rename columns via a `mappings` section on the format. |
| `pipeSeparatedValues` | Same but pipe-delimited. Ideal for CEF headers. |

### Positional value example

```js
formats: [
  { format: "$csv=.*{parse=commaSeparatedValues}$",
    mappings: { positions: ["timestamp","host","action","user"] } }
]
```

## SQL normalization

| Directive | Behavior |
|---|---|
| `sqlToSignature` | Replace string / numeric literals with `?` so similar queries aggregate. |
| `sqlWithDoubleQuotesToSignature` | Same, but preserves `"..."` as identifiers (Postgres-style). |

Useful on `mysqlGeneralQueryLog`, `postgresLog` and any slow-query stream.

## Syslog priority

`syslogPriority` decodes a numeric PRI value like `134` into three fields: `facility`, `rawSeverity`, and scaled `severity`. Most useful as `{parse=syslogPriority}` on the `<PRI>` capture from a line start.

## Date/time conversion

| Directive | Input | Output |
|---|---|---|
| `dateTimeSeconds` | Textual datetime | epoch seconds |
| `dateTimeMs` | Textual datetime | epoch milliseconds |
| `dateTimeNs` | Textual datetime | epoch nanoseconds |
| `hoursMinutesSeconds` | `hh:mm:ss[.sss]` | total seconds (float) |

## Numeric durations and sizes

Accept optional unit suffixes and normalize to a base unit:

| Directive | Base unit | Recognized suffixes |
|---|---|---|
| `seconds` | seconds | `s`, `ms`, `min`, `m`, `h`, `d` |
| `milliseconds` | milliseconds | same set |
| `bytes` | bytes | `b`, `kb`, `mb`, `gb`, `tb` |
| `kb`, `mb`, `gb` | the named unit | same |

## Subfield filtering

After a structural parse, the generated subfields may explode your schema. Filter them:

```
$payload{parse=dottedJson}{attrWhitelist=user\\.(id|email|name)}$
```

Only subfields matching the regex are kept. `attrBlacklist` is the inverse.

## When to pick which

- Embedded JSON → `json` (camel) vs `dottedJson` (dotted) based on downstream query preference. Add `strict*` if you need arrays.
- CEF / LEEF extension → `commaKeyValues` for LEEF, space-separated key=value catch-all for CEF.
- HTTP access log request line → `uri`.
- Firewall-like positional pipes → `pipeSeparatedValues` + `mappings.positions`.
- SQL log bodies → `sqlToSignature`.
- Unix/Java timing → `dateTimeMs` or `dateTimeNs` as appropriate.
