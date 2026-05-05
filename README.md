# SentinelOne AI Analyst: Claude Skills

A full-stack AI analyst for SentinelOne, built as a set of Claude skills, two MCP servers, and an operating persona (CLAUDE.md). Install once and Claude can hunt threats, triage alerts, write detections, deploy dashboards, author parsers, and build automation workflows, entirely from natural language.

- [Architecture overview](#architecture-overview)
- [What's included](#whats-included)
- [PrincipalSOCAnalyst Project](#principalsocanalyst-project)
  - [What it delivers](#what-it-delivers)
  - [Setting up the PrincipalSOCAnalyst project](#setting-up-the-principalsocanalyst-project)
  - [How to activate in other environments](#how-to-activate-in-other-environments)
  - [What happens in a session](#what-happens-in-a-session)
- [What you can do](#what-you-can-do)
- [Behavioral baselining + anomaly detection](#behavioral-baselining--anomaly-detection)
- [Example questions](#example-questions)
- [Installing and upgrading](#installing-and-upgrading)
- [Configuration](#configuration)
- [Windsurf](#windsurf)
- [Documentation](#documentation)

---

## Architecture overview

Three layers work together in every session:

```
CLAUDE.md            SOC Analyst persona: session protocol, evidence rules,
                     investigation workflow, classification gates
       │
       ▼
MCP Servers          Live API access, outside the Cowork sandbox proxy
  sentinelone-mcp    19 tools: PowerQuery, SDL, Mgmt Console REST, UAM, Hyperautomation
  purple-mcp         Alert triage, Purple AI NLQ, Deep Visibility, assets, vulnerabilities
  threat-intel-mcp   External IOC enrichment (required for CRITICAL classification)
       │
       ▼
Skills (SKILL.md)    Procedural knowledge: confirmed API schemas, field requirements, usage patterns
  sentinelone-mgmt-console-api   Mgmt Console REST + UAM + Purple AI + HA
  sentinelone-powerquery          PowerQuery authoring and execution
  sentinelone-sdl-api             SDL log ingest and config file ops
  sentinelone-sdl-dashboard       Dashboard JSON authoring and deployment
  sentinelone-sdl-log-parser      Parser authoring and validation
  sentinelone-hyperautomation     Workflow JSON authoring and import
```

**Skills** encode confirmed API behavior, including field schemas and usage patterns validated against live tenants, so Claude doesn't guess field names. **MCP servers** bypass the Cowork sandbox proxy to reach `*.sentinelone.net` directly. **CLAUDE.md** defines the operating persona that instructs how to investigate, what evidence to gather, and how to classify findings.

Full architecture details: [docs/architecture.md](./docs/architecture.md)

---

## What's included

The plugin bundles every skill; installing it is sufficient. No individual skill setup needed.

| Skill | What it does |
|---|---|
| sentinelone-mgmt-console-api | Query and act on the Management Console: threats, alerts, agents, sites, RemoteOps, Deep Visibility, Hyperautomation, Purple AI, UAM. Includes the source-agnostic behavioral baselining + anomaly detection pipeline (`baseline_anomaly.py`) |
| sentinelone-powerquery | Write, debug, and run PowerQuery for threat hunting, STAR detection rules, SDL dashboards, and statistical baseline / anomaly detection rule bodies |
| sentinelone-sdl-api | Ingest events, run queries, and manage configuration files (parsers, dashboards, lookups) via the Singularity Data Lake API |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards: panels, tabs, parameters, and full dashboard JSON. See [docs/sdl-dashboard.md](./docs/sdl-dashboard.md) for all supported panel types |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format, with OCSF field mapping by default |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

---

## PrincipalSOCAnalyst Project

`CLAUDE.md` at the root of this repo transforms Claude into a **Principal SOC Analyst**: a structured investigator that runs the same enrichment, correlation, and reasoning process a senior analyst would, on every alert, every time. Set it up once as a named Cowork project and every session starts fully briefed.

### What it delivers

| Outcome | How |
|---|---|
| **Reduce L1 SOC workload by 70%+** | Automated triage, mandatory VirusTotal enrichment, and verdict generation eliminate repetitive alert investigation. L1 analysts focus on exceptions, not routine. |
| **Elevate every analyst to principal grade** | Junior analysts get the same structured investigation framework, enrichment depth, and analytical reasoning that only senior staff possess today. |
| **External threat intelligence on every IOC** | Mandatory VirusTotal enrichment on every IP, domain, hash, and URL, with 70+ AV engines, threat actor attribution, and full infrastructure mapping on every finding. |
| **Mean investigation time under 5 minutes** | Investigation workflows that take 45-60 minutes manually compress to under 5 minutes. Continuous hunting catches threats between analyst shifts. |
| **Full data estate coverage** | Queries OCSF-normalised logs, non-OCSF vendor logs, and raw syslog. Discovers field schemas dynamically at session start, with no hardcoded assumptions about what sources are present. |
| **Fast-track detection creation** | Natural language detection authoring across any data source. Recommends new STAR rules and custom detections as threats are identified during investigation. |
| **Deliver the capability today** | Purple AI becomes even more powerful when orchestrated through this multi-layer architecture, combining deep enrichment, cross-source correlation, and external threat intelligence in every investigation. |
| **Federated search across the data estate** | Search, correlate, and hunt across endpoint, network, identity, and cloud log sources via MCP/API in a single session. Cross-source correlation connects signals that are invisible in any one source. |

**Key metrics:** `< 5 min` mean investigation time · `100%` IOC enrichment coverage · `Real-time` MITRE ATT&CK mapping · `70%+` L1 capacity freed

---

### Setting up the PrincipalSOCAnalyst project

Full install instructions, including sentinelone-mcp setup, prerequisite checks, MCP server config, plugin install, and project creation: [docs/installation.md](./docs/installation.md)

**Start a session**

Open the **PrincipalSOCAnalyst** project and start a new chat. Claude reads `CLAUDE.md` automatically and immediately runs:
- Data source enumeration: discovers every log source present in your SDL
- Alert triage: pulls open alerts in parallel while enumeration runs

> **Tip:** Keep a `reports/` subfolder inside your project folder. When Claude generates a SOC report, save it there so it persists across sessions.

---

### How to activate in other environments

**Claude Code (terminal)**
```bash
cd ~/path/to/claude-skills   # any folder containing CLAUDE.md
claude                        # CLAUDE.md is read automatically on startup
```

**Any Claude session**

Copy the contents of `CLAUDE.md` into Settings → Custom Instructions (or equivalent system prompt field) of any Claude session that has the plugin installed.

---

### What happens in a session

**Session initialisation (automatic, every session)**
1. Enumerates all live `dataSource.name` values in SDL, confirming which log sources are actually present and queryable
2. Runs alert triage in parallel, pulling open/critical alerts while enumeration executes
3. For any non-OCSF source discovered, runs schema discovery before writing any query

**Investigation workflow**
- Triage and context gathering: alert details, analyst notes, MDR verdicts, asset criticality
- VirusTotal enrichment: every IP, domain, hash, and URL enriched before any verdict; no finding classified CRITICAL without independent TI confirmation
- Infrastructure pivoting: C2 infrastructure, threat actor attribution, SSL certificate reuse, sibling domains, dropped payloads, execution chain reconstruction
- Cross-source correlation: IOC found in any source is immediately hunted across all other connected sources
- Anomaly analysis: every query result checked for frequency, timing, geolocation, baseline, volume, new entity, privilege, and chain anomalies
- MITRE ATT&CK mapping: every finding mapped to tactic and technique; kill chain gaps identified
- Composite risk scoring: cross-source anomaly scores determine escalation priority

**Report generation**

At the end of any significant investigation, ask Claude to produce a SOC report. It generates a structured `.docx` file containing: executive summary, incident timeline, affected assets, full IOC table with VT verdicts, threat actor profile, MITRE ATT&CK mapping, root cause analysis, VirusTotal intelligence summary, actions taken, and recommendations.

**Example session starters**
```
Start a new investigation session
```
```
Triage today's open alerts and flag anything requiring immediate action
```
```
Investigate alert ID <id>: full enrichment, verdict, and recommended response
```
```
Hunt for lateral movement across all connected sources in the last 24 hours
```
```
Write a SOC Leader report for this investigation as a Word document
```

---

## What you can do

These skills turn Claude into a hands-on SentinelOne analyst and engineer. Once the plugin is installed and credentials are configured, you can talk to your tenant in plain English. Claude handles the API calls, query writing, and JSON authoring and explains what it found or built.

**Threat hunting and investigation**: ask Claude to hunt for specific TTPs, IOCs, or behaviours across your SDL telemetry. It writes and runs PowerQuery automatically, pages through results, and summarises findings. You can go from a vague question ("any PowerShell reaching out to the internet?") to a ranked table of suspicious endpoints in one message.

**Alert and threat management**: list open threats, triage UAM alerts, add analyst notes, change status, or isolate an endpoint, all by describing what you want. Claude maps your intent to the right Management Console API calls and confirms what it did.

**Dashboard authoring**: describe the panels you want ("a SOC overview with threat timeline, top noisy endpoints, and outbound connection breakdown") and Claude produces deployment-ready SDL dashboard JSON, with queries validated against your tenant before it deploys.

**Log parser authoring**: paste a raw log sample and Claude writes a complete SDL parser definition, maps fields to OCSF, validates it against the parser engine, ingests a test event, and confirms the fields appear correctly, end to end in one session.

**Automation and response**: describe a response workflow in natural language ("when a high-severity alert fires on a server, isolate the endpoint, create an IOC for any hash in the alert, and notify the team") and Claude generates the Hyperautomation workflow JSON ready to import.

**Data lake operations**: ingest custom telemetry, list and manage configuration files, deploy or update parsers and dashboards, and run arbitrary queries through the SDL API.

**Behavioral baselining and anomaly detection**: build per-(principal, action) statistical baselines on any data source (Okta, FortiGate, CloudTrail, SentinelOne, Mimecast, Zeek, or anything else ingested into SDL) and surface deviations automatically. The skill auto-discovers the right principal field (user, host, IP, role) and action field (event.type, activity_name, action) per source so you don't hardcode field names. See [Behavioral baselining](#behavioral-baselining--anomaly-detection) below.

---

## Behavioral baselining + anomaly detection

A source-agnostic pipeline for building behavioral baselines and surfacing statistical anomalies on any log source ingested into SDL. Lives in `sentinelone-mgmt-console-api/scripts/baseline_anomaly.py`; documented PQ building blocks are in `sentinelone-powerquery/examples/behavioral-baselines.md`.

### What it does

For any `dataSource.name`, the pipeline:

1. **Auto-discovers the schema** via `inspect_source.discover_schema()` and picks `principal_field` (user / host / IP / role) and `action_field` (event.type / activity_name / action) from what the source actually carries, with no per-source hardcoding.
2. **Slices the baseline window into N daily LRQ queries** (default 30 days), running 3 in parallel under the per-user 3 rps cap. Each slice produces (action, principal, count) rows for that day. Daily slicing avoids the LRQ per-call deadline that single 7d/30d aggregates routinely exceed.
3. **Runs one 24h live slice** in the same shape.
4. **Merges client-side** with one of two strategies:
   - **`pooled`**: all daily samples in one bucket per (action, principal). Simple, but flags weekend silence as anomalous.
   - **`dow`**: separate bucket per (action, principal, day-of-week). Eliminates the weekday/weekend false-positive cleanly and is the production tier.
5. **Surfaces three anomaly classes** on every run:
   - **Matched z-score deviations**: pair active in both windows but live count differs from baseline avg by more than `Z_THRESHOLD * stddev` (SPIKE or DROP).
   - **Silent pairs**: pair active in baseline but with zero live events. Catches "user X went dark on a day they're normally active."
   - **New-behavior pairs**: pair seen live but with no baseline at all. Could be a new user, fresh recon activity, or attacker noise, routed to a separate triage queue.

### Why this matters

Three production failure modes that a basic moving-avg baseline misses, and this pipeline catches:

- **Silent pairs are dropped by the basic two-side join.** A critical user account that was active every weekday and is silent today never enters the join output. The pipeline walks the baseline keys explicitly to surface them.
- **Pooled baselines flag every weekend.** A 30-day pooled baseline with 22 weekday + 8 weekend samples produces a high stddev, but on a Sunday every weekday-only pair looks anomalous. Day-of-week stratification makes the comparison apples-to-apples.
- **One-size-fits-all principal field doesn't work.** Okta uses `actor.user.email_addr`. CloudTrail uses `actor.user.name` (role). FortiGate uses `device.name` or `src.ip.address`. SentinelOne uses `src.process.user`. The schema-discovery step picks the right one per source.

### How to use it

**One-shot CLI:**

```bash
# Auto-discover principal/action, 30-day DoW-stratified baseline, default Z=2.0
python sentinelone-mgmt-console-api/scripts/baseline_anomaly.py --source "Okta"

# Network source: auto-discover picks device.name + event.type
python sentinelone-mgmt-console-api/scripts/baseline_anomaly.py --source "FortiGate" --days 14

# Override fields if you know better
python sentinelone-mgmt-console-api/scripts/baseline_anomaly.py --source "Zscaler Internet Access" \
    --principal src.ip.address --action unmapped.action

# Pooled (no DoW stratification) and a tighter threshold
python sentinelone-mgmt-console-api/scripts/baseline_anomaly.py --source "CloudTrail" \
    --stratify pooled --z 3.0
```

State is checkpointed to `<plugin>/baselines/baseline_anomaly_<slug>_state.json` so the script is resumable across short shell budgets. Final results land in `baseline_anomaly_<slug>_result.json`.

**In a Cowork chat session:**

Just ask. The PowerQuery skill delegates to the mgmt-console-api skill automatically.

```
Build a 30-day behavioral baseline for Okta and show me anomalies for today.
Find users behaving differently from their typical pattern across all SaaS sources.
Run anomaly detection on FortiGate: which devices have unusual traffic today vs the last two weeks?
Which CloudTrail roles are silent today that were active every day last week?
```

### Productionising as a STAR / PowerQuery Alert rule

For a recurring detection (rather than ad-hoc), the production pattern persists the baseline and reads it at detection time:

1. Schedule a Hyperautomation workflow nightly to run the daily slices and write the DoW-stratified baseline to a config-managed lookup table via `| savelookup '<source>_baseline_dow', 'merge'`.
2. Author a PowerQuery Alert rule body that runs the live query, joins the baseline table via `| lookup`, and filters on `(live_count - avg) / sd >= 3.0 OR <= -3.0`.
3. Tier the threshold: `|z| >= 3.0` for auto-page, `|z| >= 2.0` for analyst review queue, separate path for silent pairs and new-behavior pairs.

Full PQ building blocks and the rule-body shape are in `sentinelone-powerquery/examples/behavioral-baselines.md`.

---

## Example questions

These are real questions you can ask. Claude will pick the right skill automatically.

### Threat hunting

- *"Hunt for any process that opened a connection to a non-RFC1918 IP in the last 7 days; show me top endpoints by hit count"*
- *"Write a PowerQuery that finds lsass memory reads by non-system processes"*
- *"Are there any HIFI indicators for Mimikatz or BloodHound on my tenant in the last 30 days?"*
- *"Find PowerShell scripts that encoded a Base64 command, group by endpoint"*
- *"Show me the top 20 destination IPs for outbound connections from Windows servers this week"*
- *"Write a STAR detection rule that fires when a script interpreter spawns a network tool"*

### Behavioral baselining and anomaly detection

- *"Build a 30-day behavioral baseline for Okta and show me anomalies for today"*
- *"Run a day-of-week-stratified baseline on FortiGate and surface devices with unusual traffic patterns"*
- *"Which CloudTrail roles are silent today that were active every day last week?"*
- *"Find users in Google Workspace whose activity volume today is more than 3 standard deviations from their typical day"*
- *"Detect anomalies across all my SaaS sources and rank them by composite z-score"*
- *"Establish a baseline for SentinelOne process activity per endpoint and find spikes since this morning"*
- *"Build me a STAR rule body that uses a stored baseline lookup table to detect login spikes"*

### Alert and threat management

- *"List all open threats created in the last 24 hours, sorted by confidence"*
- *"Show me unresolved UAM alerts with severity High or Critical from today"*
- *"Add a note to alert ID `abc123` saying it was reviewed and is a false positive"*
- *"Isolate endpoint `DESKTOP-XYZ` and create an IOC for its SHA1 hash `aabbcc...`"*
- *"How many threats were mitigated vs unresolved this week, broken down by site?"*
- *"Get me the details for alert ID `xyz` including any associated agent and threat info"*

### Dashboards

- *"Build me a SOC overview dashboard with: threat timeline by confidence, top 10 noisiest endpoints, failed logins over time, and outbound connection breakdown by direction"*
- *"Create a Purple AI usage dashboard showing queries by analyst and a timeline of usage"*
- *"Add a honeycomb panel to my dashboard showing file creation activity by endpoint"*
- *"Build an O365 tab for my audit dashboard with login failures by user and country"*
- *"Deploy my dashboard JSON to SDL at `/dashboards/soc-overview`"*

### Log parsers

- *"Write an SDL parser for this Palo Alto syslog sample: `<paste log>`"*
- *"I have a CEF log from CrowdStrike: create a parser with OCSF field mapping"*
- *"My FortiGate parser isn't extracting the destination IP correctly, here's the JSON: `<paste parser>`"*
- *"Validate my parser and ingest a test event to confirm the fields look right"*

### Data lake operations

- *"List all configuration files on my SDL tenant under `/dashboards/`"*
- *"Ingest this JSON array of events into SDL with the source name `custom-app`"*
- *"Run this PowerQuery against my tenant and return the results as a table: `<query>`"*
- *"Download the current version of my `/logParsers/fortinet-fortigate` parser"*

### SOC investigation and triage

- *"Start a new investigation session: enumerate live data sources and pull today's open alerts"*
- *"Triage alert ID `abc123`: get the full details, check notes and history, enrich any IOCs in VirusTotal, and give me a verdict"*
- *"Enrich this file hash `aabbccdd...`: detection ratio, behavioral analysis, C2 infrastructure, and threat actor attribution"*
- *"Pivot on IP `1.2.3.4`: what malware communicates with it, what domains resolve to it, and is it associated with any APT group?"*
- *"Cross-correlate this IOC across all connected data sources: check firewall, Okta, Zeek, and CloudTrail for any trace of `1.2.3.4`"*
- *"Check endpoint `DESKTOP-XYZ` for anomalies: run the full anomaly checklist across process, network, and identity data"*
- *"Apply the MITRE ATT&CK framework to what we've found so far: what techniques are mapped and where are the detection gaps?"*
- *"Score the current investigation using the cross-source anomaly framework and tell me if we should escalate to IR"*

### Reporting

- *"Write a SOC Leader report for this investigation as a Word document: executive summary, incident timeline, IOC table with VT verdicts, MITRE mapping, root cause, and recommendations"*
- *"Generate a weekly threat summary for SOC leadership covering alerts triaged, true positives confirmed, top IOCs, and any active campaigns"*
- *"Produce an IOC table for all indicators found in the last 24 hours, including VirusTotal verdict, detection ratio, and threat actor attribution"*
- *"Give me an executive-level summary of the firewall beaconing pattern we found: one paragraph, business risk focus, no jargon"*

### Hyperautomation workflows

- *"Build a workflow that isolates an endpoint and sends a Slack notification when a Ransomware indicator fires"*
- *"Create a scheduled workflow that runs every morning and sends a summary of overnight threats by email"*
- *"Write a webhook workflow that creates an IOC from an incoming threat intel feed payload"*
- *"Design a playbook: on a Critical alert, add a note, escalate the site status, and page the on-call analyst"*

---

## Installing and upgrading

See [docs/installation.md](./docs/installation.md) for the complete guide: prerequisites, sentinelone-mcp setup, plugin install, credential config, and upgrade steps.

---

## Configuration

**If you are using `sentinelone-mcp` (recommended):** credentials are passed as environment variables in `claude_desktop_config.json`. See [docs/installation.md](./docs/installation.md) for the full MCP config block. You do not need a `credentials.json` file in your project folder.

**If you are using the skills directly without `sentinelone-mcp`** (or for backwards compatibility): the skills also read credentials from a `credentials.json` file placed in your Cowork project folder. The plugin's SessionStart hook auto-discovers it and makes it available to every skill in the session.

**Setup is two commands.** Copy [`credentials.example.json`](./sentinelone-skills-plugin/credentials.example.json) from this repo into your Cowork project folder, renaming it to `credentials.json`, then edit it.

**macOS / Linux:**

```bash
# 1. Pick your Cowork project folder.
PROJECT_DIR=~/Documents/Claude/Projects/MyProject

# 2. Copy the example, renaming to credentials.json.
cp sentinelone-skills-plugin/credentials.example.json "$PROJECT_DIR/credentials.json"

# 3. Edit it: replace the placeholder values with your real ones.
${EDITOR:-nano} "$PROJECT_DIR/credentials.json"
```

**Windows (PowerShell):**

```powershell
# 1. Pick your Cowork project folder.
$projectDir = "$env:USERPROFILE\Documents\Claude\Projects\MyProject"

# 2. Copy the example, renaming to credentials.json.
Copy-Item .\sentinelone-skills-plugin\credentials.example.json "$projectDir\credentials.json"

# 3. Edit it: replace the placeholder values with your real ones.
notepad "$projectDir\credentials.json"
```

If you only downloaded the `.plugin` file (not the full repo), extract `credentials.example.json` from the plugin zip with any unzip tool, or grab it directly from the repo at [`sentinelone-skills-plugin/credentials.example.json`](./sentinelone-skills-plugin/credentials.example.json).

| Credential key | Required for | How to get it |
|---|---|---|
| `S1_CONSOLE_URL` | All management console skills | Your console URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_CONSOLE_API_TOKEN` | `sentinelone-mgmt-console-api`, `sentinelone-powerquery`, plus SDL query and config methods (not `uploadLogs`) | Settings → Users → Service Users → Create New Service User → copy the API token. The same JWT works for the SDL API from Management version Z SP5+. See [Creating service users](https://community.sentinelone.com/s/article/000005291) and [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `S1_HEC_INGEST_URL` | UAM alert/indicator ingest and log ingest via HEC | The SentinelOne HEC ingest host for your region, e.g. `https://ingest.us1.sentinelone.net`. Look up your region's URL in [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `SDL_XDR_URL` | `sentinelone-sdl-api`, `sentinelone-sdl-dashboard`, `sentinelone-sdl-log-parser` | Your SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net`. Region-specific; see [SentinelOne Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| `SDL_LOG_WRITE_KEY` | `uploadLogs` only | In Singularity Data Lake → menu next to username → API Keys → Log Access Keys → New Key (Log Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `SDL_CONFIG_WRITE_KEY` | Deploying parsers/dashboards via `putFile` | In Singularity Data Lake → menu next to username → API Keys → Configuration Access Keys → New Key (Configuration Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |

Resolution order (highest priority wins):
1. Environment variables set in `claude_desktop_config.json` via `sentinelone-mcp` (recommended)
2. `<project folder>/credentials.json` (backwards-compatible fallback for direct skill usage)
3. `~/.config/sentinelone/credentials.json` (terminal fallback)

Full credential reference including all SDL keys and MCP server config: [docs/credentials.md](./docs/credentials.md)

---

## Windsurf

This repo includes Windsurf workflow files in `.windsurf/workflows/`. Each workflow is a thin pointer that directs Cascade to read the canonical `SKILL.md` and reference docs in the matching skill folder, with no duplicated content.

- `sentinelone-api.md`: Management Console API (agents, threats, alerts, sites, Purple AI, UAM).
- `sentinelone-powerquery.md`: PowerQuery authoring, debugging, and detection rules.
- `sentinelone-sdl-api.md`: Singularity Data Lake API (ingest, query, config files).
- `sentinelone-sdl-log-parser.md`: SDL log parser authoring with OCSF mapping.

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/installation.md](./docs/installation.md) | Step-by-step install and upgrade guide: prerequisites, sentinelone-mcp setup, plugin install, credential config, project creation |
| [docs/architecture.md](./docs/architecture.md) | How the three layers fit together, data flow, auth patterns, sandbox proxy explanation |
| [docs/skills.md](./docs/skills.md) | Per-skill capability reference, key scripts, and field requirements |
| [docs/mcp-tools.md](./docs/mcp-tools.md) | All sentinelone-mcp and purple-mcp tools with usage notes and which to use when |
| [docs/credentials.md](./docs/credentials.md) | Every credential key, where to find it, full `claude_desktop_config.json` reference |
| [docs/testing.md](./docs/testing.md) | Full test coverage matrix, MCP tool validation results, and confirmed API field requirements |
| [docs/sdl-dashboard.md](./docs/sdl-dashboard.md) | All supported panel types and dashboard features with confirmed JSON examples |
| [sentinelone-mgmt-console-api/SKILL.md](./sentinelone-mgmt-console-api/SKILL.md) | Deep reference: confirmed field schemas and required API parameters per endpoint |
| [sentinelone-mgmt-console-api/tests/README.md](./sentinelone-mgmt-console-api/tests/README.md) | Reversible lifecycle test patterns and per-test field notes |
