---
name: sentinelone-sdl-log-parser
author: Prithvi Moses <prithvi.moses@sentinelone.com>
description: Use whenever the user wants to author, edit, debug, validate, or explain a SentinelOne Singularity Data Lake (SDL) log parser — the augmented-JSON files at /logParsers/ that extract fields from raw log text before ingestion. Trigger on "SDL parser", "Skylight parser", "log parser", "parser editor", "write a parser", "test parser", or any pasted raw log the user wants turned into structured fields. Also trigger on parser-DSL keywords like `formats:`, `patterns:`, `lineGroupers:`, `rewrites:`, `discardAttributes:`, `aliasTo:`, `{parse=...}`, `{regex=...}`. Especially trigger when the user pastes a raw log (CEF, syslog, JSON, key=value, multi-line, CSV) and asks to extract fields, normalize timestamps, or drop noise. If the project is SDL/Singularity/Scalyr and the user says "parse this log", use this skill. Always validates end-to-end via sentinelone-sdl-api (putFile → uploadLogs → query). NOT for PowerQuery (use sentinelone-powerquery), NOT for plain ingest without a parser (use sentinelone-sdl-api).
---

# SentinelOne SDL Log Parser Authoring

This skill turns raw log samples into deployed, validated SDL parser definitions. A parser is an *augmented-JSON* file at `/logParsers/<name>` on the SDL tenant that extracts fields from each ingested line. The parser editor and the `Test Parser` button in the console run the parser client-side in JavaScript; this skill mirrors that workflow programmatically and finishes by ingesting a sample through the deployed parser to confirm the actual ingest path works.

> **Sandbox proxy blocked?** If `putFile` or `uploadLogs` calls to `*.sentinelone.net` fail with a connection or proxy error inside the Claude sandbox, use the `sentinelone-mcp` server instead. It runs locally via `node` and bypasses the sandbox proxy entirely. Setup: add it to `claude_desktop_config.json` (see `claude-skills/sentinelone-mcp/README.md`). Use `sdl_put_file` to deploy the parser and `sdl_upload_logs` to run the ingest validation step — both execute from your machine, not the sandbox.

## Two hard rules (every parser, every time)

These two rules apply to every parser you write or edit, regardless of source, regardless of whether you're starting from scratch or copying from the catalog. Violating either produces a non-conformant parser even if extraction works.

**Rule 1: The 4 mandatory attributes are always present.**

```js
attributes: {
  "dataSource.category": "security",   // hardcoded constant, never any other value
  "dataSource.name":     "Corelight",  // specific product/service name
  "dataSource.vendor":   "Corelight",  // parent vendor / company name
  "metadata.version":    "1.0.0"       // semver; bump on substantive parser changes
}
```

`dataSource.category` is fixed at `"security"`. Not `application`, not `network`, not `system`, not `audit`. The catalog has parsers that violate this; you do not.

`metadata.version` is mandatory and follows semver (`MAJOR.MINOR.PATCH`, with optional pre-release suffix like `-rc1` or `-beta1`). **Increment it on every build.** Patch bump for fixes, minor for additive changes, major for breaking schema changes. It can also be set inside `mappings` via a `constant` op when the source itself carries a vendor schema version you'd rather propagate per-event:

```js
{ constant: { field: "metadata.version", value: "<your-current-version>" } }
```

A `constant` in `mappings` overrides the parser-root `attributes:` value when it fires, which is useful when one parser handles multiple vendor schema versions and you want each event tagged with the right one.

**Rule 2: Every OCSF field name comes from `references/ocsf-schema-documentation.md`.**

Before emitting any OCSF dotted path (`src_endpoint.ip`, `actor.user.name`, `metadata.product.vendor_name`, etc.), grep `references/ocsf-schema-documentation.md` for the exact string. Do not invent field names. Do not copy from a catalog parser without verifying. Do not rely on memory. The reference is the single source of truth for the ~25,759 documented OCSF field names across the 7 categories.

The rest of this skill assumes both rules are upheld. If either is unclear for a given parser, stop and resolve before continuing.

## When to use this skill

Use this skill when the user wants to turn raw log text into structured SDL events. Common triggers:

- "Write a parser for this <vendor> log."
- "Why isn't `<field>` showing up after ingest?"
- A pasted log line — CEF, syslog, JSON-per-line, key=value, multi-line, vendor-specific.
- Edits to an existing parser ("add a rewrite that masks the password", "tag every event with `dataset=fortinet`").
- Migration ("alias the new parser to the old one").

Do **not** use this skill for PowerQuery authoring (use `sentinelone-powerquery`) or for plain-text ingestion that does not need a parser (use `sentinelone-sdl-api` directly).

## Workflow

Follow this loop. Skipping steps 1 (catalog check) and 5 (end-to-end validation) are the two most common reasons a parser goes live with surprises, so do not skip them.

1. **Check the ai-siem catalog first.** Before writing anything, search <https://github.com/Sentinel-One/ai-siem/tree/main/parsers> for the vendor/product. The repo has ~150 community + marketplace parsers; most common sources (Cloudflare, FortiGate, Palo Alto, Corelight, AWS RDS, Okta, Abnormal, Juniper, pfSense, Cisco ASA, etc.) are already there. If a parser exists, download it and diff against the user's requirements — far less work than authoring from scratch. See `references/ai-siem-catalog.md` for the recipe and a map of template parsers by shape.
2. **Inspect the sample.** Read every line the user pasted. Look for: leading priority/timestamp/host (syslog framing), the body shape (CEF | JSON | key=value | positional CSV | freeform), any obvious sub-structures (`uri=...`, embedded JSON, base64), and whether multiple physical lines belong to one logical event (stack traces, MySQL slow queries, Postgres SQL).
3. **Decide on strategy.** See *Strategy decision tree* below. Most logs are one of: alias an existing built-in, single line format with `$field$` markers, repeating key/value catch-all, JSON parser with `discardAttributes`, line-grouper for multi-line, or a mapper for OCSF-style restructuring.
4. **Draft the parser.** Use the templates in `examples/` as starting points, or (from step 1) a catalog parser as a base. Always start minimal — extract the *outer* frame first (timestamp + host + body), then add fragment formats or `{parse=...}` directives to crack the body open.
5. **Validate end-to-end.** Use the `sentinelone-sdl-api` skill to deploy the parser, ingest the sample, and query for the extracted fields. See *Validation* below for the exact recipe. **Do not call this skill done before this step succeeds.**
6. **Iterate.** If a field is missing or wrong, identify which format/rewrite was responsible, edit, redeploy, re-ingest with a fresh `Nonce`, re-query.
7. **Hand off.** Show the user the final parser file (path + version), the sample they gave, and the parsed fields the query returned.

## Required default attributes on every parser (MANDATORY)

**Four attributes are MANDATORY on the top-level `attributes:` block of every parser**, regardless of source. These are non-negotiable:

```js
"dataSource.category": "security",    // ALWAYS hardcoded to "security": fixed constant, never change
"dataSource.name":     "Corelight",   // specific product/service name (example value)
"dataSource.vendor":   "Corelight",   // parent vendor / company name (example value)
"metadata.version":    "1.0.0"        // semver; required on every parser
```

These four are required by the downstream SDL pipeline (Marketplace routing, parser catalog, content-pack grouping). Omitting any of them produces a non-conformant parser even when field extraction is correct.

**`dataSource.category` MUST always be hardcoded to `"security"`.** This is not a taxonomy pick, it is a fixed constant. Never substitute another value (`application`, `network`, `system`, `audit`) regardless of the source type. Empirical audit of the ai-siem catalog (2026-04) shows ~17% of community parsers violate this rule with values like `application`, `network`, `system`, `audit`. Fix on copy.

`dataSource.vendor` is the parent company (`Cisco` for Umbrella, `Microsoft` for Azure AD). `dataSource.name` is the specific product (`Cisco Umbrella`, `Azure AD`). For single-product vendors both can be the same string (`Corelight` / `Corelight`).

`metadata.version` is semver (`MAJOR.MINOR.PATCH` with optional `-rcN` / `-betaN` suffix). **Always increment on a new build** so content-pack tooling can detect drift. Patch for fixes, minor for additive changes, major for breaking schema changes. May also be emitted from inside `mappings` via:

```js
{ constant: { field: "metadata.version", value: "<your-current-version>" } }
```

A `mappings.constant` overrides the parser-root `attributes:` value when its predicate fires. This is the right pattern when one parser handles multiple vendor schema versions and you want each event labeled with the schema-version it actually came from.

**Catalog-parser audit step.** When you start from a catalog parser, the very first edits you make are to confirm all four fields are present, that `dataSource.category` is `"security"`, and that `metadata.version` exists and reflects the change you're about to make. About 1/3 of the community parsers in `Sentinel-One/ai-siem` are missing `dataSource.category` outright; many that include it use a non-security value. Fix before doing anything else.

## Default output schema: OCSF (mandatory reference)

Unless the user explicitly asks for vendor-native names, **emit OCSF-shaped events**. This means:

- Name captured fields with their OCSF dotted paths (e.g. `src_endpoint.ip`, `dst_endpoint.port`, `connection_info.protocol_num`, `app_name`, `actor.user.name`).
- Tag every event with the class metadata on `attributes`: `class_uid`, `class_name`, `category_uid`, `category_name`, and `metadata.product.vendor_name` / `metadata.product.name` / `metadata.log_provider`, all IN ADDITION TO the four mandatory attributes above.
- Put the per-event subtype (`activity_id` + `activity_name`) on the **format**, not the top-level attributes, because one parser often handles multiple subtypes (SESSION_CREATE vs SESSION_CLOSE).

**OCSF mapping MUST always be done using `references/ocsf-schema-documentation.md`.** This file is the authoritative SentinelOne community-documented OCSF field catalog (7 categories, 96 articles, ~25,759 field entries across every event class). Before emitting any OCSF field name, grep this file for the exact dotted path. Do **not** invent field names, do **not** copy from memory, do **not** trust catalog parsers to have the right name (many community parsers in ai-siem use vendor-native or stale OCSF names that need correcting). Workflow:

1. Pick the OCSF class (see Quick picker below).
2. Open `references/ocsf-schema-documentation.md` and grep for the class number / category to find the field block.
3. Copy the dotted path verbatim into your parser.
4. If unsure between two candidate fields, confirm with the user rather than guessing.

`references/ocsf-mapping.md` covers the two authoring idioms (capture-directly-into-dotted vs capture-vendor-then-rename) and the most common class-specific tables (Network Activity, Authentication, File Activity).

Why this matters: downstream PowerQuery hunts, STAR rules, dashboards, and Marketplace integrations assume OCSF. Vendor-native names force every consumer to learn each source format and break portability. A wrong dotted path (`source.ip` instead of `src_endpoint.ip`, `dst.port` instead of `dst_endpoint.port`) is silently wrong: it ingests, but every downstream consumer fails to match.

Quick picker (use this to find the class number, then look up fields in `ocsf-schema-documentation.md`):

- Network firewall / NAT / flow → `4001` Network Activity
- HTTP / web / proxy → `4002` HTTP Activity
- DNS → `4003` DNS Activity
- DHCP → `4004` DHCP Activity
- RDP / SSH session → `4005` RDP Activity
- TLS / SSL handshake → `4006` SSH Activity (TLS uses connection_info under 4001/4002)
- Email → `4009` Email Activity
- Authentication → `3002` Authentication
- Account change → `3001` Account Change
- API activity → `6003` API Activity
- File system ops → `1001` File System Activity
- Kernel ops → `1003` Kernel Activity
- Memory ops → `1004` Memory Activity
- Module ops → `1005` Module Activity
- Process ops → `1007` Process Activity
- Registry ops → `201001` (Windows Registry)
- Detection finding → `2004` Detection Finding
- Compliance finding → `2003` Compliance Finding
- Vulnerability finding → `2002` Vulnerability Finding
- Inventory / device → `5001` Device Inventory Info
- Email / file finding → `2007` (Email Finding) / `2006` (File Hosting Finding)

When the source could reasonably belong to multiple classes (proxy logs, EDR alerts), confirm with the user rather than picking silently.

## Top-level parser structure

A parser file is augmented JSON (unquoted keys allowed, `//` and `/* */` comments allowed). Top-level keys:

```js
{
  timezone: "UTC",                                  // fallback for timestamp parsing
  attributes: {
    // REQUIRED defaults on every parser
    "metadata.version":    "1.0.0",
    "dataSource.category": "security",    // always "security" — hardcoded, never change
    "dataSource.name":     "Juniper SRX",
    "dataSource.vendor":   "Juniper",
    // OCSF class metadata + vendor product metadata
    "metadata.product.vendor_name": "Juniper",
    "metadata.product.name":        "SRX",
    "metadata.log_provider":        "rt_flow",
    "class_uid":      4001,
    "class_name":     "Network Activity",
    "category_uid":   4,
    "category_name":  "Network Activity"
  },
  patterns:   { tsPattern: "\\w+\\s+\\d+\\s+[0-9:]+" },  // named regex shortcuts
  lineGroupers: [ { start: "...", continueThrough: "..." } ],  // multi-line glue
  formats: [
    {
      id: "happy-path",
      attributes: { activity_id: 1, activity_name: "Open" },  // per-subtype tagging
      format: "$time=tsPattern$ $src_endpoint.hostname$ $body$",
      discard: false,
      halt: true,                                   // stop after first match
      repeat: false                                 // re-apply until no progress
    }
  ],
  // Advanced (not always present):
  mappings: { mappings: [ /* rename vendor-native fields to OCSF dotted names */ ] }
}
```

`formats` is the primary engine. Everything else either feeds into it (patterns, lineGroupers) or runs after it (rewrites, mappings, discardAttributes).

## Field-matcher syntax inside a format string

```
$fieldName=patternName{parse=...}{regex=...}{attrWhitelist=...}{attrBlacklist=...}{timezone=...}$
```

Rules that bite people often:

- `$field$` alone uses the `quotable` pattern by default, which stops at whitespace or quote boundaries.
- `$field{regex=\\d+}$` inlines a regex — backslash metacharacters double-escape (`\\d` not `\d`).
- Two adjacent `$a$$b$` with no delimiter between them require a pattern or regex on `$a$` so it knows when to stop.
- `message` is reserved — it's the raw event text. You cannot capture into `message` from a format. You *can* `discardAttributes: ["message"]` to drop it.
- A literal `$` in the log requires `\$$` (escape the dollar, then close the field).
- Any space in the format matches `\s+`. To match a single literal space use `\\ ` (backslash-space).

For the full directive list see `references/syntax.md` and `references/parse-directives.md`.

## Canonical reference parsers by input shape

When you've identified the shape of the source log, jump straight to the canonical catalog parser for that shape and start from it. These are battle-tested in production:

| Input shape | Canonical parser | What to learn from it |
|---|---|---|
| Pure JSON-per-line (flat or nested) | `community/abnormal_security_logs-latest/` | `${parse=gron}$` capture, then mappings to OCSF |
| JSON with envelope (`<ts> <host> <json>`) | `community/json_generic-latest/` (or `examples/02-json-with-envelope.json`) | `dottedJson` on the body |
| JSON, nested, multi-class | `sentinelone/marketplace-cloudflare-latest/` | gron + format IDs + enum cast + tree ops, all in v1 mappings |
| Already-OCSF JSON | `community/okta_ocsf_logs-latest/` | Pass-through with light renames |
| CEF over syslog | `community/generic_access_logs-latest/` (or `examples/01-cef-over-syslog.json`) | Pipe-delimited header + KV extension |
| LEEF over syslog | `community/leef_template_logs-latest/` | Multi-format header + KV body |
| Pure key=value freeform | `sentinelone/marketplace-fortinetfortigate-latest/` | `repeat: true` catch-all, attrBlacklist, observables array |
| Positional CSV (100+ columns) | `sentinelone/marketplace-paloaltonetworksfirewall-latest/` | `commaSeparatedvalues`, `skipNumericConversion`, `attr[N]` indexed access in v1 mappings |
| Positional space-delimited | `sentinelone/marketplace-awsvpcflowlogs-latest/` | `intermittentTimestamps`, fixed columns |
| Pipe-delimited (non-CEF) | `sentinelone/marketplace-zscalerinternetaccess-latest/` | `pipeSeparatedValues` parse directive |
| Multi-line stack / SQL | `community/sql_database_logs-latest/` and `sentinelone/marketplace-awsrdslogs-latest/` | `lineGroupers` start/continueThrough, format-id sentinels for sub-shapes |
| Windows Event XML | `community/microsoft_windows_eventlog-latest/` | XML with `\\t` / `\\n` escapes, per-EventID sub-parsers (4624, 4625, 4720, 4728, 1102) |
| HTTP access logs | `community/apache_http_logs-latest/` | Built-in `accessLog` alias-or-extend |
| pfSense / iptables freeform firewall | `community/pfsense_firewall_logs-latest/` | Frame → subtype → protocol cascade with `discard: true` for IPv6 |
| Rewrites-only legacy style | `community/okta_logs-latest/` | Minimal-diff edits when you can't migrate to mappings |
| Gron-capture + everything-in-mappings | `community/PARSER_TEMPLATE/` (and `examples/08-gron-capture-template.json`) | The most general scaffold; use when you want all transformations in one block |

When in doubt, `marketplace-cloudflare-latest/` is the most complete reference for "modern v1 parser doing everything right" (gron, format IDs, enum cast, tree ops, OCSF tagging). Start there if you're not sure.

## Strategy decision tree

Apply in order — first match wins:

1. **Is there a parser in the ai-siem catalog?** Search `Sentinel-One/ai-siem` for the vendor/product name. If so, start from that parser (see `references/ai-siem-catalog.md` for the fetch recipe and per-shape template map). On copy, immediately audit and fix:
   - The **4 mandatory attributes** (`dataSource.category` hardcoded to `"security"`, `dataSource.name`, `dataSource.vendor`, `metadata.version`). About 1/3 of community parsers miss `dataSource.category` outright; many that include it use `application`/`network`/`system`/`audit` instead of `"security"`. Force them to `"security"`. Add `metadata.version` if missing, bump it if you're changing the parser.
   - All OCSF field names against `references/ocsf-schema-documentation.md`. Catalog parsers frequently use vendor-native names (`source_ip`, `dst_port`) where OCSF dotted paths (`src_endpoint.ip`, `dst_endpoint.port`) are required. Rewrite via `mappings.rename` or change the capture name directly.
   - Stale tenant-specific attributes (e.g. hardcoded `site.id`).
   - `class_uid` should be an integer, not a string.
   - Bump `metadata.version`.
2. **Is there a built-in parser?** Web access logs → `accessLog`. Pure JSON-per-line → `json` or `dottedJson`. Syslog → `systemLog`. Key=value pairs → `keyValue`. Heroku logplex → `heroku-logplex`. MySQL/Postgres → their dedicated parsers. CloudFront/ELB/S3/Redshift → AWS parsers. See `references/builtin-parsers.md`. If a built-in fits, recommend it and (optionally) just author an alias parser: `{ aliasTo: "json" }`.
3. **Is the log JSON-per-line but with a vendor envelope?** Use one format that captures the envelope and applies `{parse=json}` (or `dottedJson`/`escapedJson`/`urlEncodedJson`/`base64EncodedJson`) on the embedded body. Add `discardAttributes: ["message"]` to save storage.
4. **Is the whole line an OCSF/JSON blob you want flattened?** Use the gron-capture-then-mappings idiom: `format: "$unmapped.{parse=gron}$"` at the top, then rename/copy/cast everything in a `mappings` block. See `examples/08-gron-capture-template.json` and the `community/PARSER_TEMPLATE/` reference.
5. **Is the body a sequence of `key=value` pairs?** Use the two-format key/value idiom (leading static fields, then a repeating catch-all with `$_=identifier$=$_=quoteOrSpace$`). The `_` field name means "use the captured token as the field name".
6. **Is it CEF or LEEF?** Treat the header as a positional pipe-delimited line, then apply key/value catch-all to the extension. See `examples/01-cef-over-syslog.json`.
7. **Is it positional / CSV / TSV?** Use `commaSeparatedValues` / `commaSeparatedvalues` or `pipeSeparatedValues` parse directives with `skipNumericConversion: true`, and name the columns in a `mappings` block by positional index (`attr[N]`). Palo Alto Networks Firewall in ai-siem is the canonical reference.
8. **Does the source emit multiple distinct event shapes** (e.g. MySQL error vs MySQL general vs Postgres from one RDS stream)? Give each `format` an `id:` and fan mapping entries out with `predicate: "<id>='true'"`. See the AWS RDS marketplace parser.
9. **Are events multi-line?** Add a `lineGroupers` block with `start` + one of `continueThrough` / `continuePast` / `haltBefore` / `haltWith`. Then write formats against the joined event. **Beware** `uploadLogs` newline splitting (see ingest-path gotchas). Canonical multi-line examples: `parsers/community/sql_database_logs-latest/` (Postgres SQL) and `parsers/sentinelone/marketplace-awsrdslogs-latest/` (RDS mysql/postgres mixed stream).
10. **Is the source Windows Event Log XML?** Use the per-EventID sub-parser idiom from `parsers/community/microsoft_windows_eventlog-latest/`: a `lineGroupers` block joins multi-line XML, then one format per EventID (4624, 4625, 4720, 4728, 1102, etc.) extracts EventID-specific fields. Remember the `\\t` / `\\n` double-escape gotcha. Class fan-out: 4624/4625 → `class_uid: 3002` Authentication, 4720/4728 → `class_uid: 3001` Account Change, 1102 → `class_uid: 6004` Web Resources Activity (or whatever fits).
11. **Do you need to restructure to OCSF or another schema?** Use `mappings` (gron-style mappers). See `references/mappers.md` for the two equivalent syntaxes (v1 singular / v0 marketplace). For new parsers prefer v1; only stay on v0 when extending an existing v0 parser. **Always look up dotted paths in `references/ocsf-schema-documentation.md` before emitting them.**
12. **None of the above?** Hand-write a line format. Look for stable delimiters and use named patterns when delimiters are insufficient (e.g., a timestamp containing spaces). Drop events you never want (`discard: true` on the format) rather than letting them fall through to a looser format.

## Common gotchas (memorize)

- **Double-escape every regex metacharacter.** `\\d`, `\\s`, `\\.`, `\\\\`. The augmented-JSON layer eats one backslash before the regex engine sees it.
- **`severity` is a RESERVED field coerced to 0–6 integer.** The ingest pipeline maps `info`/`warn`/`error` strings to 0–6 using its own vocabulary. OCSF labels like `"Informational"` / `"Medium"` collide and get rewritten. For the OCSF string, emit `severity_name` (or any non-colliding name); for the integer, emit `severity_id` directly (int, 0–6). Tenant-validated April 2026.
- **gron-captured dotted keys are FLAT, not nested.** A source JSON key like `"user.email": "alice"` becomes `unmapped.user.email` as a single flat field — mappings must reference it with `from: "unmapped.user.email"` (no escaping). `from: "unmapped.user\\.email"` does NOT match on current tenants, contrary to the escape-the-dots pattern in ai-siem's PARSER_TEMPLATE.conf.
- **Saved parsers apply only to newly ingested events.** Historical logs are not re-parsed. So during iteration you must re-ingest the sample after every parser edit.
- **`halt: true` stops the format engine after a match.** Use it for mutually exclusive formats (e.g., TCP vs UDP variants in pfSense). Without it, all matching formats merge their captures.
- **`repeat: true` reapplies the same format from where it left off.** Required for the key/value catch-all idiom, otherwise only the first pair is captured.
- **Per-event parse limit is just under 50,000 chars.** Long events get truncated *before* parsing.
- **Line groupers max 100,000 chars per joined event.** Above that, the grouper still emits but truncated.
- **`intermittentTimestamps: true`** is required for logs (like MySQL general query log) that emit a timestamp only on the second they roll over. Without it, every line missing a timestamp gets the ingest time.
- **Regex alternation cannot wrap a `$...$` token.** `($a$|$b$)` is invalid. Use multiple line fragments instead.
- **SDL regex engine does NOT support lookarounds.** `(?=...)`, `(?!...)`, `(?<=...)`, `(?<!...)` all fail silently. Use explicit token delimiters or split into multiple formats.
- **`$pri{parse=syslogPriority}$` can cause silent event drops on some tenants.** If you suspect priority parsing is the culprit, capture the priority as a plain field (`$pri{regex=\\d+}$`) and skip the parse directive.
- **Indexed positional access `attr[N]` only works in `mappings.version: 1`.** v0 mappings reject `attr[0]`/`attr[1]` syntax. If the source is positional CSV (Palo Alto Firewall is the canonical case), use v1. Reference: `parsers/sentinelone/marketplace-paloaltonetworksfirewall-latest/`.
- **`{parse=gron}` flattens nested JSON to dotted keys, but the keys themselves contain dots.** A source `{"Resource": {"Id": 5}}` becomes the single flat field `unmapped.Resource.Id` (one key with two dots), not a nested object. To rename it use `from: "unmapped.Resource.Id"` (no escapes). To rename a whole subtree use `rename_tree: { from: "unmapped.Resource", to: "resource" }` and the engine walks the dotted-prefix subtree. Reference: `parsers/sentinelone/marketplace-cloudflare-latest/`.
- **`attrBlacklist={field1,field2}` only filters subfields produced by a `{parse=...}` directive.** It does NOT filter top-level captured fields you named explicitly in the format string. To drop a top-level field use `discardAttributes: ["fieldname"]` at the parser root. Reference: `parsers/sentinelone/marketplace-fortinetfortigate-latest/`.
- **`skipNumericConversion: true` is required when columns contain numeric strings you want preserved as strings.** Without it, `commaSeparatedvalues` and `pipeSeparatedValues` parse will coerce `"00123"` → `123` (loses leading zeros), `"0xDEADBEEF"` → `3735928559`, and `"1.0"` → `1`. Set `skipNumericConversion: true` on the format whenever any column is an opaque ID or a hex/octal string. Canonical: Palo Alto Firewall.
- **`intermittentTimestamps: true` is the only fix for sources where only the first record on each second has a timestamp.** Common with MySQL general query log, AWS RDS, sometimes VPC flow logs. Without it, every line that lacks a timestamp gets the ingest timestamp, not the inferred one. Reference: `parsers/sentinelone/marketplace-awsvpcflowlogs-latest/` and `parsers/community/sql_database_logs-latest/`.
- **`enum` cast in v1 mappings without `enum_default` leaves unmapped values UNCHANGED, not null.** If you want unknowns to map to a known sentinel, set `enum_default: <value>` on the cast. Cloudflare uses `enum_default: 99` ("Unknown") consistently — copy that pattern.
- **`severity_id` is an integer 0–6 reserved by ingest, just like `severity`.** Setting `severity_id: 999` silently fails. Use `severity` for the normalized integer (preferred), `severity_name` for the OCSF label string. Do not emit BOTH `severity` and `severity_id` from the same parser.
- **Rewrites run during format parsing; mappings run after all formats.** A field renamed in `mappings.rename` cannot be referenced by a `rewrites:` block on a later format on the same line because `rewrites:` runs per-format during capture. If you need a derived field from a renamed one, do the derivation inside `mappings` (use `copy` then `cast`, or `replace`).
- **Mixing `mappings.version: 0` and `mappings.version: 1` syntax in the same block is a hard error.** The engine rejects with "expected list got object" or "unsupported event mapper version -1". Pick one version per parser and stick to it.
- **Windows Event Log XML payloads ship with double-escaped tabs/newlines.** A parser for Windows EventLog in the catalog (`parsers/community/microsoft_windows_eventlog-latest/`) deals with `\\t` and `\\n` literals embedded inside XML strings; capturing them needs `\\\\t` / `\\\\n` (four backslashes) at the augmented-JSON layer.
- **Some catalog parsers ship without `dataSource.category` at all (~33% of community).** When you copy from `Sentinel-One/ai-siem`, audit the top-level `attributes:` block. If `dataSource.category` is missing, add it as `"security"`. If present with another value, change it to `"security"`. Same audit for `dataSource.name` and `dataSource.vendor`.
- **`$_=identifier$=$_=quoteOrSpace$` repeating idiom requires `repeat: true` AND a leading anchor.** Without an explicit anchor, the format will match starting at the first `=` it finds and miss earlier pairs. The common pattern is to capture the static prefix in a sibling format (with `halt: false`), then let the repeating format walk the rest.
- **Conditional class assignment (one parser, multiple OCSF classes) is best done by stamping `class_uid`/`class_name` on each `format`'s `attributes:` block, not on the parser root.** The root attributes are baseline; per-format attributes override. Reference for fan-out via format-id sentinel + mapping predicates: `parsers/sentinelone/marketplace-awsrdslogs-latest/`.

### Ingest-path gotchas (discovered empirically via live validation)

These are quirks of the ingest pipeline itself, not the parser DSL. They bite you at validation time even when the parser JSON is syntactically perfect.

- **`uploadLogs` splits on `\n` BEFORE the parser runs.** Multi-line events (stack traces, MySQL slow queries) get chopped up and `lineGroupers` cannot re-fold them. Workarounds:
  1. Fold multi-line events client-side into a single line with a sentinel character (e.g. `\x1e`), then have your parser split on that sentinel.
  2. Use `addEvents` instead of `uploadLogs` and send each logical event as one `events[]` item — `addEvents` preserves newlines inside the event body.
- **The `server-host` upload header is unreliable for isolating a test.** SDL sometimes overrides the header to the literal string `"uploadLogs"`, and if the parser extracts a `host` field from the log itself that wins too. Do NOT filter your validation query by `host='parser-test-<uuid>'` alone. Safer: filter by `parser='claude_test_<name>'` and `_bytes > 0`, and use a unique nonce in the payload to double-check isolation.
- **`{parse=dottedJson}` prefixes subfields when the field has a non-empty name.** `$payload{parse=dottedJson}$` on `{"user":"alice"}` yields `payload.user = "alice"`. If you want top-level fields, capture into an empty name: `${parse=dottedJson}$`. Same applies to `json`, `escapedJson`, `urlEncodedJson`, `base64EncodedJson`.
- **`getFile` on a missing config path raises HTTP 404**, it does not return `success=false` with `noSuchFile`. Wrap existence checks in a try/except when scripting cleanup.

### `mappings` block gotchas

Two syntaxes coexist on live tenants and both work. You must commit to one per parser — mixing them in the same mappings block produces confusing "expected list got object" errors.

**v1 (singular, preferred for new parsers, tenant-validated April 2026):**

- **`mappings.version: 1` is mandatory.** Without it the tenant returns `unsupported event mapper version -1`.
- **Each transformation is `{<op>: {...body}}`**, where the op name is the **outer key** (e.g. `{rename: {from, to}}`). The public-doc form `{op: "rename", from: ..., to: ...}` is rejected.
- **`rename.from` is a single string**, not a list. Use `copy` (which does accept a list) if you need "first of N".
- **`cast` uses `type:`**, not `to:`. Example: `{cast: {field: "x", type: "int"}}`.
- **`cast` overwrites the source field.** There is no `output:` parameter — `copy` first, then `cast` the copy.
- **Predicates use `==`** (double equals).

**v0 (plural-grouped, used by most S1 Marketplace parsers — AWS RDS, Corelight, Cloudflare, FortiGate):**

- **`mappings.version: 0`**. Same block, different body shape.
- **Ops are plural arrays on the mapping entry**: `renames: [...]`, `copies: [...]`, `constants: [...]`. No `transformations:` wrapper.
- **Every op entry uses `inputs: [list]` + `output:` + `type:`** — even `rename`. `type: "string"` is the safe default.
- **Predicates use `=`** (single equals) in v0, both on the mapping entry and inside `constants`.

If you inherit a marketplace parser, keep it on v0 rather than rewriting. For new parsers, pick v1. See `references/mappers.md` for the full side-by-side.

**`constant` / `constants` op** (both versions) is the workhorse for conditional OCSF class/activity assignment — give it a `predicate` and it only fires when matched, so you can fan one vendor-native state code (`conn_state`, `action`, etc.) out into `activity_id` + `activity_name` + `type_uid` triples.

**Format-id-as-sentinel predicate**: `format: { id: "mySqlErrorLog", ... }` auto-sets a boolean-string field `mySqlErrorLog='true'` on events that matched that format. Use `predicate: "mySqlErrorLog='true'"` (v0) or `"mySqlErrorLog == 'true'"` (v1) to fan mapping entries out to sub-shapes. Quote the `'true'` — it's a string, not a bare boolean.

### `computeFields` gotchas

- **Use PowerQuery ternary `a ? b : c`**, not `if(a, b, c)`. The latter returns `Unknown function 'if'`.
- **Use `==` for equality**, not `=`.
- **Cannot reference dashed field names.** `protocol-id` is parsed as subtraction. Rename via `mappings` first, or do the translation entirely in the mappings block.
- **Place the rewrite on the format that captures the source field.** If a repeating key/value sub-format is what produces the field, the rewrite belongs on the sub-format — not on the frame format above it.

### Interaction between `halt: true` and repeat formats

- **`halt: true` stops ALL further format matching on that line** — including repeating key/value catch-alls. If you have a two-format pattern (frame + repeating extractor), do NOT put `halt: true` on the frame format; the extractor will never fire.

## Validation (mandatory)

Always validate against the live tenant via the `sentinelone-sdl-api` skill. Do not rely solely on the syntactic plausibility of the JSON — the only authoritative test is "did the field actually appear in a query after ingest." This is what the in-console `Test Parser` button approximates client-side; doing it through the API exercises the real ingest pipeline.

```python
import sys, time, uuid, json
sys.path.insert(0, "/sessions/dazzling-ecstatic-volta/mnt/.claude/skills/sentinelone-sdl-api/scripts")
from sdl_client import SDLClient

c = SDLClient()
PARSER_NAME = "claude_test_<descriptive_name>"   # use a claude_test_ prefix so cleanup is easy
parser_body = open("/path/to/draft.json").read()
sample = open("/path/to/sample.log").read()

# 1. Deploy
c.put_file(f"/logParsers/{PARSER_NAME}", content=parser_body)

# 2. Ingest a sample with a unique nonce + host so we can isolate it
host_tag = f"parser-test-{uuid.uuid4().hex[:8]}"
c.upload_logs(sample, parser=PARSER_NAME, server_host=host_tag, nonce=str(uuid.uuid4()))

# 3. Wait briefly, then query back
time.sleep(8)  # ingest-to-search latency
res = c.power_query(
    query=f"host='{host_tag}' | columns timestamp, message, <expected_fields>",
    start_time="5m",
)
print(json.dumps(res, indent=2))
```

A successful validation means: (a) `putFile` returned `success`, (b) `uploadLogs` returned `success`, (c) the `power_query` returned at least as many rows as you ingested, (d) the expected fields are populated and not null.

If a field is missing, do NOT just retry — diagnose. Common causes: wrong escape level on a regex, a delimiter that didn't match (the format silently fails to apply), `halt: true` on an earlier format catching the line first, or `discardAttributes` dropping the field by mistake.

### Cleanup

After validation, decide with the user whether to keep, rename, or delete the parser. For throwaway tests:

```python
c.put_file(f"/logParsers/{PARSER_NAME}", delete=True)
```

For something the user wants to keep, rename to a non-`claude_test_` name (`get_file` → `put_file` new name → delete old).

## Bundled references

When a question goes deeper than this file, read the relevant reference. Each is a focused deep-dive — load only what you need.

- `references/ai-siem-catalog.md` — **Check this first** before writing a new parser. Map of the public S1 parser repo (~150 parsers across community + marketplace), per-shape template recommendations, style-variance cheat sheet, and the fetch recipe.
- `references/ocsf-mapping.md` — **Then start here** for any new parser. OCSF class quick-pick (4001/4002/3002/1001/etc.), field-to-dotted-path mapping tables for Network Activity, Authentication, and File Activity, and the two authoring idioms: capture directly into dotted names vs capture vendor-native then rename via a `mappings` block. Also covers boolean/enum normalization (`YES`/`NO`/`UNKNOWN` → `tls.is_encrypted`). Points at `ocsf-schema-documentation.md` for authoritative field names.
- `references/ocsf-schema-documentation.md` — **Authoritative OCSF field catalog** — the full SentinelOne community-documented schema: 7 categories × 96 articles × ~25,759 field entries across every OCSF event class (System Activity, Findings, IAM, Network Activity, Discovery, Application Activity, Unified Alert Management). Grep this file for any OCSF field name you're about to emit — don't invent names. Always check this before choosing a dotted path, especially for classes beyond Network/Auth/File.
- `references/syntax.md` — Full augmented-JSON parser syntax: formats, patterns, attributes, lineGroupers, rewrites (including `computeFields` and `timeDelta`), special fields (timestamp/severity/message), discard, halt, repeat, association, intermittentTimestamps, skipNumericConversion. Read when authoring anything beyond a simple line format.
- `references/parse-directives.md` — Every `{parse=...}` sub-parser (json/dottedJson/escaped/urlEncoded/base64Encoded variants, strict variants for arrays, uri/uriMultivalue/uriAttributes, commaKeyValues, commaSeparated/pipeSeparated, sqlToSignature, syslogPriority, dateTime{Seconds,Ms,Ns}, hoursMinutesSeconds, seconds/milliseconds, bytes/kb/mb/gb, plus per-directive `attrWhitelist`/`attrBlacklist` rules). Read whenever the body of a field is itself structured.
- `references/builtin-parsers.md` — Catalog of all 16 built-in parsers (`accessLog`, `cloudfront`, `json`, `dottedJson`, `dottedEscapedJson`, `elb-access`, `heroku-logplex`, `keyValue`, `leveldbLog`, `mysqlGeneralQueryLog`, `mysqlSlowQueryLog`, `postgresLog`, `redshift`, `s3_bucket_access`, `spot_instance_data`, `systemLog`) and when to alias vs override. Read first when sizing up a new log source — you may not need to write a parser at all.
- `references/mappers.md` — `mappings` block (gron-style transformations: `cast`, `copy`, `copy_tree`, `drop`, `drop_tree`, `hash`, `reduce_array`, `rename`, `rename_tree`, `replace`, `zip`), array index syntax, predicate semantics. Read when restructuring events to OCSF or another target schema.
- `references/testing-workflow.md` — Detailed validation recipe with the `sentinelone-sdl-api` skill, including how to scope queries with a unique host tag, how to interpret common error responses, and how to clean up.

## Bundled examples

Annotated, runnable parser definitions. Copy and adapt rather than starting from scratch.

- `examples/01-cef-over-syslog.json` — Syslog-framed CEF (`<PRI>timestamp host CEF:0|...|...|key=value`). Demonstrates: `syslogPriority` parse, named timestamp pattern, positional pipe-delimited CEF header, key/value catch-all on the extension.
- `examples/02-json-with-envelope.json` — `<timestamp> <host> {"...json..."}`. Demonstrates: timestamp + host extraction, `{parse=dottedJson}` on the body, `discardAttributes: ["message"]`.
- `examples/03-key-value.json` — Pure `key=value` lines. Demonstrates: the `$_=identifier$=$_=quoteOrSpace$` repeating idiom and a leading static prefix.
- `examples/04-multiline-stack.json` — Java/Python stack traces. Demonstrates: `lineGroupers` with `continueThrough`, attribute tagging.
- `examples/05-rewrite-and-mask.json` — Single line format plus `rewrites` to mask `password=...` values and compute a derived field via `computeFields`.
- `examples/06-alias.json` — One-line alias parser (`{ aliasTo: "json" }`) for the case where a built-in already does the job.
- `examples/07-juniper-srx-rtflow-ocsf.json` — Juniper SRX RT_FLOW_SESSION_CREATE (structured-data syslog, RFC 5424-ish). Demonstrates: the **vendor-native capture + `mappings.rename` to OCSF** idiom end-to-end (source-address → `src_endpoint.ip`, nat-source-address → `connection_info.src_translated.ip`, etc.), repeating key/value catch-all on the structured-data body, `computeFields` for protocol-id → `connection_info.protocol_name` and encrypted YES/NO → `tls.is_encrypted`, Network Activity 4001 class tagging.
- `examples/08-gron-capture-template.json` — The PARSER_TEMPLATE shape lifted from `ai-siem`: capture the entire event with `$unmapped.{parse=gron}$`, then do every rename/copy/cast/constant in a single v1 `mappings` block. Ideal scaffold for JSON-shaped sources when you want all OCSF work in one place.
- `examples/README.md` — When to pick which template.

## Summary of the contract you're holding

When a user pastes a log and asks you to parse it, you owe them: (1) a parser file written against the SDL augmented-JSON DSL, (2) proof it actually extracts the right fields when ingested through the live SDL pipeline (not just the editor preview), (3) a clean handoff (final path, fields, sample query). The bundled references and examples exist so you don't have to hold the entire DSL in your head — load them as needed and reach for the templates first.


## Parser deployment via sentinelone-mcp

Parser deployment and validation use the `sentinelone-mcp` MCP tools, which bypass the
Cowork sandbox proxy entirely. Use `sdl_put_file`, `sdl_get_file`, `sdl_list_files`,
and `sdl_upload_logs` directly instead of falling back to the `sentinelone-sdl-api`
skill scripts. The MCP tools run locally on your machine and make direct HTTPS calls
to `*.sentinelone.net` without proxy interference.
