# Skills Reference

Each skill is a folder containing a `SKILL.md` that Claude reads when a relevant request triggers it. The SKILL.md encodes confirmed API schemas, field requirements, and procedural knowledge. All six skills are bundled in the `sentinelone-skills` plugin.

---

## sentinelone-mgmt-console-api

**Triggers on:** S1 console operations: agents, threats, alerts, sites, groups, policies, IOCs, detection rules, exclusions, RemoteOps, Deep Visibility, Hyperautomation, UAM, Purple AI.

**What it provides:**

- Generic REST wrapper (`s1_api_get/post/put/patch/delete`) over 781 Management Console operations across 113 API tags
- Unified Alert Management (UAM): GraphQL-based multi-source alert inbox with filter, triage, note, status, and verdict mutations
- Purple AI: natural-language query interface over SDL telemetry (NLQ → PowerQuery → results)
- Hyperautomation: workflow list/get/import/export/archive
- UAM Alert Interface: OCSF-format alert and indicator ingest via HEC
- Behavioral baselining + anomaly detection pipeline (`baseline_anomaly.py`): source-agnostic, auto-discovers principal/action fields, day-of-week stratification, three anomaly classes (spike, drop, silent pair, new behavior)

**Key scripts:**

| Script | Purpose |
|---|---|
| `scripts/s1_client.py` | REST client: auth, pooled HTTP, retries, cursor pagination, parallel `get_many()` |
| `scripts/smoke_test_queries.py` | Non-destructive sweep of all GETs; outputs `tenant_capabilities.md` |
| `scripts/search_endpoints.py` | Ranked keyword search over endpoint index (`--only-works` filter) |
| `scripts/unified_alerts.py` | UAM GraphQL wrapper (queries, mutations, triage helpers) |
| `scripts/purple_ai.py` | Purple AI GraphQL wrapper |
| `scripts/baseline_anomaly.py` | Behavioral baselining + anomaly detection |

**Test coverage:** 15 lifecycle test scripts covering IOCs, UAM alerts, exclusions, detection rules (scheduled + events / STAR), Hyperautomation import, XDR graph queries, and more. See [testing.md](./testing.md).

**API field requirements validated through live testing (examples):**
- `queryType=scheduled` detection rules require `isLegacy=false` on GET
- Unified Exclusions POST requires 7 fields including `modeType`, `type`, `engines`, `scopeLevel`, `scopeLevelId`, `value`, and `recommendation`; returns `data` as a list
- Hyperautomation: list response uses nested `workflow.id`, `nextCursor` returns string `"null"` (truthy in Python)
- UAM `addAlertNote` returns `mgmt_note_id` required for `deleteAlertNote`

Full field reference: `sentinelone-mgmt-console-api/SKILL.md`

---

## sentinelone-powerquery

**Triggers on:** PowerQuery authoring, debugging, optimization, STAR/Custom Detection rule bodies, SDL dashboard panels, behavioral baseline building, threat hunting queries.

**What it provides:**

- PowerQuery syntax reference and best practices for SDL/Deep Visibility queries
- STAR rule body authoring (streaming detection, `queryType=events`)
- PowerQuery Alert rule bodies (scheduled detection, `queryType=scheduled`)
- SDL dashboard panel query authoring
- Behavioral baseline building blocks using `| savelookup` + `| lookup` pattern
- Schema-safe patterns: `number()` cast for type-locked columns, `array_agg_distinct` for enumeration

**Key examples:** `sentinelone-powerquery/examples/behavioral-baselines.md`: full PQ building blocks for the baseline + anomaly detection rule body pattern.

---

## sentinelone-sdl-api

**Triggers on:** SDL API operations: log ingest, configuration file management (parsers, dashboards, lookups, datatables), SDL query via API.

**What it provides:**

- SDL log ingest via HEC (`sdl_upload_logs`), requires `SDL_LOG_WRITE_KEY`
- SDL config file CRUD (`sdl_list_files`, `sdl_get_file`, `sdl_put_file`, `sdl_delete_file`)
- SDL V1 query (full-event JSON, used for schema discovery)

**Auth note:** `SDL_CONFIG_WRITE_KEY` does not grant log read access. Force-clear scoped keys to fall through to the console JWT for V1 queries:

```python
c.keys["log_read_key"] = ""
c.keys["config_read_key"] = ""
```

---

## sentinelone-sdl-dashboard

**Triggers on:** SDL dashboard creation, editing, deployment, debugging.

**What it provides:**

- Complete SDL dashboard JSON schema: tabs, panels, parameters, time range controls
- Panel type reference: timeseries, count, table, honeycomb, pie, bar, single value
- PowerQuery integration: panel query validation against tenant sources before deployment
- Dashboard deployment via `sdl_put_file` to `/dashboards/<name>`

**Workflow:** Author dashboard JSON → validate queries against live tenant sources → deploy via SDL API → confirm via `sdl_list_files`.

---

## sentinelone-sdl-log-parser

**Triggers on:** SDL log parser authoring, editing, validation, testing.

**What it provides:**

- SDL parser JSON schema (`formats`, `patterns`, `lineGroupers`, `rewrites`, `discardAttributes`)
- OCSF field mapping guidance by log format (CEF, syslog, JSON key=value, multi-line, CSV)
- Timestamp normalization patterns
- End-to-end validation: `sdl_put_file` → `sdl_upload_logs` (ingest test event) → `powerquery_run` (confirm fields appear)

**Workflow:** Parse raw log sample → generate parser JSON → deploy to SDL → ingest test event → confirm field extraction in query results.

---

## sentinelone-hyperautomation

**Triggers on:** Hyperautomation workflow creation, design, generation, import, export.

**What it provides:**

- Hyperautomation workflow JSON schema: triggers, actions, connections, conditions, loops
- Trigger types: manual, scheduled, HTTP/webhook, email, S1 alert, Singularity response
- Action types: HTTP request, S1 isolate/remediate, send email, Slack/Teams, condition branch, loop, wait
- Workflow import via `ha_import_workflow` (requires `Hyper Automate.write` permission)

**Token note:** Workflows imported with a service user token are invisible to human users in the console UI. Use a personal console user token if the workflow needs to be visible and editable in the UI.

---

## CLAUDE.md: SOC Analyst persona

`CLAUDE.md` is not a skill in the plugin sense; it is the operating persona loaded at session start.

It defines:

- **Mandatory session init:** enumerate SDL sources, triage open alerts in parallel, discover schemas per-source before writing any query
- **Evidence rules:** no fabrication, cite every fact to its tool call, mark every assumption explicitly
- **Anomaly checklist:** frequency, timing, geolocation, baseline deviation, new entity, privilege, chain
- **Classification gate:** no CRITICAL or TRUE POSITIVE verdict without independent threat intelligence confirmation
- **Confidence language:** "confirmed" / "consistent with" / "suggests" / "possible", calibrated to evidence weight
- **Investigation workflow:** triage → enrichment → infrastructure pivot → cross-source correlation → MITRE mapping → composite risk score → report

`sentinelone-mcp` exposes it as an MCP resource (`sentinelone://soc-context`) and prompt (`soc_analyst`). Edit `claude-skills/CLAUDE.md` and restart the MCP server to change Claude's operating behavior.
