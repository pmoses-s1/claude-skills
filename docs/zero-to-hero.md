# Zero to Hero: Claude Skills for SentinelOne

A practical onboarding guide for customers and partners new to Claude Skills. Read this start to finish (~20 minutes) and you'll understand what skills are, why they matter, and how to get a working SentinelOne AI analyst running in a Cowork project.

This guide assumes no prior exposure to Claude Skills, MCP, or Cowork. It covers concepts, installation, and day-to-day use.

- [1. What are Claude Skills?](#1-what-are-claude-skills)
- [2. How to use the skills](#2-how-to-use-the-skills)
- [3. Install in 30 minutes](#3-install-in-30-minutes)
- [4. Your first session](#4-your-first-session)
- [5. Walkthroughs by use case](#5-walkthroughs-by-use-case)
- [6. When things don't work](#6-when-things-dont-work)
- [7. Going deeper](#7-going-deeper)

---

## 1. What are Claude Skills?

### The 30-second version

A **skill** is a folder containing a `SKILL.md` file that teaches Claude how to do a specific job correctly. The SKILL.md encodes confirmed API field names, validated procedures, gotchas, and the right tool to call for each operation. When your request matches a skill's trigger description, Claude loads that skill on demand and follows it.

You don't pick skills manually. You describe the outcome you want in plain English, and Claude routes to the right skill (or several) automatically.

### Why skills matter

Without a skill, Claude has to guess at the things every API has too many of: field names, endpoint paths, required parameters, output shapes, version-specific behavior. Guessing produces plausible-looking but broken code, wrong field references, and hallucinated fields. Skills replace guesswork with knowledge that has been validated against a live tenant.

For SentinelOne specifically: the Management Console exposes 781 operations across 113 tags. The SDL API has its own auth model, log ingest format, and configuration filesystem. PowerQuery has reserved-field rewrites, type-locked columns, and a per-call deadline that aggregates can blow through. STAR rules have one schema; PowerQuery Alerts have another. Skills capture all of this so Claude doesn't have to rediscover it on every request.

### The three-layer mental model

Three pieces work together in every session:

```
CLAUDE.md            SOC Analyst persona, evidence rules, session protocol
       |
       v
MCP Servers          Live API access (bypasses the Cowork sandbox proxy)
  sentinelone-mcp    19 tools: PowerQuery, SDL, Mgmt REST, UAM, Hyperautomation
  purple-mcp         Alert triage, Purple AI NLQ, Deep Visibility, assets, vulns
  threat-intel-mcp   External IOC enrichment (e.g. VirusTotal)
       |
       v
Skills (SKILL.md)    Procedural knowledge: confirmed schemas, field requirements,
                     usage patterns, validated against live tenants
```

A useful analogy: **MCP servers are hands** (they touch the API), **skills are training manuals** (they say how to use the hands), and **CLAUDE.md is the job description** (it says what kind of work to do, in what order, with what discipline).

### How Claude decides which skill to load

Every skill's frontmatter has a `description` field listing trigger phrases and example requests. When you send a message, Claude scans your text against every available skill description and loads the matching ones. Triggers are deliberately broad: "hunt for PowerShell", "show me open alerts", "write a parser for this log", "build a dashboard panel" all map cleanly.

You can also be explicit. "Use the SDL log parser skill to..." or "switch to PowerQuery and..." both work, but you almost never need to. Describing the outcome is enough.

### What ships in this repo

| Skill | What it does |
|---|---|
| sentinelone-mgmt-console-api | Query and act on the Management Console: threats, alerts, agents, sites, RemoteOps, Deep Visibility, Hyperautomation, Purple AI, UAM. Includes the source-agnostic behavioral baselining + anomaly detection pipeline. |
| sentinelone-powerquery | Write, debug, and run PowerQuery for threat hunting, STAR detection rules, SDL dashboards, and statistical baseline / anomaly detection rule bodies. |
| sentinelone-sdl-api | Ingest events, run queries, and manage configuration files (parsers, dashboards, lookups) via the Singularity Data Lake API. |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards: panels, tabs, parameters, and full dashboard JSON. |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format, with OCSF field mapping by default. |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import. |

Plus `CLAUDE.md` at the repo root, which transforms Claude into a **Principal SOC Analyst**: a structured investigator that runs the same enrichment, correlation, and reasoning process a senior analyst would, on every alert, every time.

### What this gets you (the outcomes)

| Outcome | How |
|---|---|
| Reduce L1 SOC workload by 70%+ | Automated triage, mandatory threat-intel enrichment, and verdict generation eliminate repetitive alert investigation. |
| Elevate every analyst to principal grade | Junior analysts get the same structured investigation framework as seniors. |
| External threat intelligence on every IOC | Mandatory enrichment on every IP, domain, hash, and URL before any verdict. |
| Mean investigation time under 5 minutes | 45-60 minute manual investigations compress to under 5 minutes. |
| Full data estate coverage | Queries OCSF-normalised logs, non-OCSF vendor logs, and raw syslog. Discovers field schemas dynamically per session. |
| Federated search across the data estate | Search and correlate across endpoint, network, identity, and cloud sources in a single session. |

---

## 2. How to use the skills

Your goal: ask Claude about your SentinelOne tenant in plain English and get correct, evidence-backed answers, dashboards, parsers, and workflows. You don't write any code, edit any SKILL.md files, or pick skills manually. You describe what you want and Claude routes the request.

Time to first value: about 30 minutes for the install, plus 5 minutes for your first real query.

There are three ways to interact with the skills once they're installed:

**1. Inside the Cowork project (the main path).** Open the `PrincipalSOCAnalyst` project in Claude Desktop and start a new chat. `CLAUDE.md` loads automatically, the session protocol runs (data source enumeration, alert triage in parallel), and every skill is one prompt away. This is where you'll spend almost all your time.

**2. From the terminal via Claude Code.** `cd` into the `claude-skills` folder and run `claude`. The CLI reads `CLAUDE.md` on startup and the same skills are available. Useful for scripting, batch jobs, and CI hooks.

**3. From any Claude session with the plugin installed.** Copy the contents of `CLAUDE.md` into Settings, Custom Instructions (or the equivalent system prompt field) of any Claude session that has the `sentinelone-skills` plugin installed. Useful when you want the SOC Analyst persona somewhere outside Cowork.

Continue to [Section 3: Install](#3-install-in-30-minutes) to set this up.

---

## 3. Install in 30 minutes

The full reference is [`docs/installation.md`](./installation.md). This section is the compressed walkthrough.

### Prerequisites

| Requirement | Check | Install |
|---|---|---|
| Claude desktop app | App is open | Download from [claude.com](https://claude.com) |
| Node.js 18+ | `node --version` | [nodejs.org](https://nodejs.org) |
| `uv` (for purple-mcp) | `uvx --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh`, then open a new terminal |
| SentinelOne API token | Settings, Users, Service Users | [Community guide](https://community.sentinelone.com/s/article/000005291) |
| SDL API keys | Singularity Data Lake, API Keys | [Community guide](https://community.sentinelone.com/s/article/000006763) |
| Regional endpoint URLs | n/a | [Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) |
| Threat intel API key | e.g. [virustotal.com/gui/my-apikey](https://www.virustotal.com/gui/my-apikey) | Free tier is sufficient |

### Step 1: Clone the repo and install sentinelone-mcp

```bash
git clone https://github.com/pmoses-s1/claude-skills.git
cd claude-skills/sentinelone-mcp
npm install
cd ..
```

What you got: a local Node.js MCP server with 19 tools that bypass the Cowork sandbox proxy and talk directly to your tenant. Note the absolute path to `sentinelone-mcp/index.js`; you'll paste it into the config file in Step 3.

### Step 2: Confirm uvx is on your PATH

```bash
uvx --version
```

What you got: the ability to run `purple-mcp` directly from GitHub with no local clone. `uvx` fetches and caches the package on first use.

### Step 3: Wire up the MCP servers in Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "sentinelone-mcp": {
      "command": "node",
      "args": ["/path/to/claude-skills/sentinelone-mcp/index.js"],
      "env": {
        "S1_CONSOLE_URL": "https://usea1-yourorg.sentinelone.net",
        "S1_CONSOLE_API_TOKEN": "eyJ...your-api-token...",
        "S1_HEC_INGEST_URL": "https://ingest.us1.sentinelone.net",
        "SDL_XDR_URL": "https://xdr.us1.sentinelone.net",
        "SDL_LOG_WRITE_KEY": "your-log-write-key",
        "SDL_LOG_READ_KEY": "your-log-read-key",
        "SDL_CONFIG_WRITE_KEY": "your-config-write-key",
        "SDL_CONFIG_READ_KEY": "your-config-read-key"
      }
    },
    "purple-mcp": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/Sentinel-One/purple-mcp.git",
        "purple-mcp", "--mode", "stdio"
      ],
      "env": {
        "PURPLEMCP_CONSOLE_TOKEN": "eyJ...your-api-token...",
        "PURPLEMCP_CONSOLE_BASE_URL": "https://usea1-yourorg.sentinelone.net"
      }
    },
    "virustotal": {
      "command": "mcp-virustotal",
      "env": {
        "VIRUSTOTAL_API_KEY": "your-virustotal-api-key"
      }
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": true,
    "coworkWebSearchEnabled": true
  }
}
```

Things people get wrong here:

- The `sentinelone-mcp` `args` path must be **absolute**, not relative. Resolve with `pwd` while inside the repo.
- `S1_CONSOLE_API_TOKEN` and `PURPLEMCP_CONSOLE_TOKEN` are the **same** token. One service user with read scope is enough for hunting and triage; IR Team scope or higher is needed for response actions like isolate.
- Region URLs vary. Check the [Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) article for `S1_HEC_INGEST_URL` and `SDL_XDR_URL`.
- Replace VirusTotal with your organisation's approved threat intel MCP if different. Install with `npm install -g mcp-virustotal` if you're using VirusTotal.

**Restart Claude Desktop after saving the file.**

### Step 4: Install the plugin

The plugin bundles all six skills in a single file, so there's no per-skill install to manage.

1. In Claude Desktop, open the **Cowork** tab.
2. Click **Customize** in the left sidebar.
3. Click **Browse plugins**.
4. Upload `sentinelone-skills-vX.Y.Z.plugin` from [`sentinelone-skills-plugin/dist/`](../sentinelone-skills-plugin/dist/).

If plugin upload fails, the same `dist/` folder has individual `.skill` files you can install one at a time by double-clicking them or by uploading via Browse plugins.

### Step 5: Create the Cowork project

Cowork projects are durable workspaces with their own folder, plugins, and CLAUDE.md. You'll do all your real work inside one.

1. In Claude Desktop, open **Cowork** and click **New Project**.
2. Name it `PrincipalSOCAnalyst`.
3. Click **Select Folder** and pick the `claude-skills` folder you cloned (the one containing `CLAUDE.md`).
4. Under **Add files**, add `CLAUDE.md` so Claude reads the SOC Analyst persona on every session start.
5. Confirm `sentinelone-skills` appears under **Personal plugins**, and that `sentinelone-mcp`, `purple-mcp`, and your threat intel MCP appear under **MCP Servers**.

### Step 6: Verify the install

Open the **PrincipalSOCAnalyst** project and start a new session. Claude will automatically run data source enumeration and triage open alerts. Then ask:

```
smoke test s1 skills
```

Claude verifies connectivity to every MCP, confirms each skill is loaded, and reports missing credentials or unreachable endpoints. To check the version:

```
which version of sentinelone-skills is installed?
```

If anything fails, jump to [Section 6: When things don't work](#6-when-things-dont-work).

---

## 4. Your first session

### What happens when you open the project

The moment you start a chat in `PrincipalSOCAnalyst`, Claude reads `CLAUDE.md` and runs the mandatory session protocol:

1. **Enumerates live `dataSource.name` values in your SDL.** This tells Claude exactly which sources are present (S1 internal, SentinelOne EDR, plus any third-party connectors like Okta, FortiGate, CloudTrail, Mimecast).
2. **Pulls open alerts in parallel** while enumeration runs.
3. **For any non-OCSF source it discovers, runs schema discovery** before authoring any query against it.

This isn't filler. It's why the answers you get later are correct: Claude never reuses cached field names from a previous session because parsers, reserved-field rewrites, and ingestion changes can drift between sessions.

### Three first prompts to try

Pick whichever feels most useful and run it:

**Triage**
```
Triage today's open alerts and flag anything requiring immediate action.
```
Expect a ranked list with verdicts, IOCs, threat-intel enrichment, MITRE mapping, and recommended response actions.

**Hunt**
```
Hunt for any process that opened a connection to a non-RFC1918 IP in the last 7 days, show me the top endpoints by hit count.
```
Expect a PowerQuery, validated against your data sources, executed, and a ranked endpoint table summarised in chat.

**Build**
```
Build me a SOC overview dashboard with a threat timeline by confidence,
top 10 noisiest endpoints, failed logins over time, and an outbound
connection breakdown by direction. Deploy it to /dashboards/soc-overview.
```
Expect dashboard JSON authored, queries validated against your tenant, the dashboard deployed to SDL, and a confirmation back.

### How to read what Claude is doing

A few signals tell you which skill is running and what API surface is being used:

- **Tool calls named `mcp__sentinelone-mcp__*`** are the local MCP server. Names like `powerquery_run`, `s1_api_get`, `sdl_put_file`, `uam_list_alerts`, `ha_import_workflow` map cleanly to the skill they belong to.
- **Tool calls named `mcp__purple-mcp__*`** are the Python Purple MCP. Use these for alert triage, Purple AI NLQ, vulnerabilities, inventory.
- **Tool calls named `mcp__virustotal__*`** (or your equivalent) are external threat intel.
- **Skill load indicators** appear inline: Claude will mention "loading sentinelone-powerquery" or similar before it starts authoring a query.
- **Citations** appear in Claude's prose. Every fact ties back to a specific tool call, with no fabrication.

### What good output looks like

A correct response has three properties:

1. **Evidence-backed.** Numbers, IOCs, and verdicts cite the tool call that produced them.
2. **Calibrated language.** Claude uses "confirmed" / "consistent with" / "suggests" / "possible" deliberately, scaled to the strength of the evidence.
3. **No CRITICAL verdict without independent threat intel.** This is enforced by `CLAUDE.md`. If you see a CRITICAL classification, you'll see VirusTotal (or equivalent) corroboration alongside it.

If a response is missing any of these, push back. Claude will recheck and recalibrate.

---

## 5. Walkthroughs by use case

Each subsection has a sample prompt and what to expect. Run them in your `PrincipalSOCAnalyst` project.

### Threat hunting

Skill: `sentinelone-powerquery` (plus `sentinelone-mgmt-console-api` for execution).

```
Find PowerShell scripts that encoded a Base64 command, group by endpoint,
and rank by hit count over the last 7 days.
```

What you'll get: a PowerQuery using `event.type`, `src.process.cmdline`, and `array_agg_distinct`, validated against your sources, run, and the top-N endpoints summarised. You can ask Claude to convert it to a STAR detection rule if it looks useful.

### Alert triage

Skills: `sentinelone-mgmt-console-api`, plus `purple-mcp` for richer GraphQL fields.

```
Triage alert ID abc123: get full details, check notes and history, enrich
any IOCs in VirusTotal, and give me a verdict.
```

What you'll get: the full alert payload, prior analyst notes, MDR verdict, asset criticality lookup, every IOC enriched in VirusTotal, MITRE mapping, and a calibrated verdict. If the verdict is CRITICAL or TRUE POSITIVE, you'll see the threat intel evidence inline.

### Behavioral baselining and anomaly detection

Skill: `sentinelone-mgmt-console-api` (the `baseline_anomaly.py` pipeline) plus `sentinelone-powerquery` for the rule body.

```
Build a 30-day behavioral baseline for Okta and show me anomalies for today.
Use day-of-week stratification.
```

What you'll get: schema auto-discovery to pick the right `principal_field` (e.g. `actor.user.email_addr` for Okta) and `action_field`, 30 daily slices run in parallel under the per-user 3 rps cap, a 24-hour live slice, and three anomaly classes returned: matched z-score deviations (spike or drop), silent pairs (active in baseline, zero today), and new-behavior pairs (active today, no baseline at all).

For a recurring detection, ask Claude to productionise it as a PowerQuery Alert rule with a `| savelookup` baseline and `| lookup` join.

### Dashboard authoring

Skill: `sentinelone-sdl-dashboard` (plus `sentinelone-sdl-api` for deploy and `sentinelone-powerquery` for panel queries).

```
Create a Purple AI usage dashboard showing queries by analyst over time
and a timeline of usage. Deploy it to /dashboards/purple-ai-usage.
```

What you'll get: dashboard JSON with the right panel types (timeseries, table, single value), every panel query validated against your tenant before deploy, and a confirmation that the dashboard is live in SDL.

### Log parser authoring

Skill: `sentinelone-sdl-log-parser` (plus `sentinelone-sdl-api` for end-to-end validation).

```
Write an SDL parser for this Palo Alto syslog sample, with OCSF field
mapping:

  <paste raw log here>
```

What you'll get: a complete parser definition (`formats`, `patterns`, `lineGroupers`, `rewrites`, `discardAttributes`), OCSF field mapping, deploy to `/logParsers/<name>`, ingest of a test event, and a query confirming the fields appear correctly in SDL.

### Hyperautomation workflows

Skill: `sentinelone-hyperautomation`.

```
Build a workflow that, when a Ransomware indicator fires, isolates the
affected endpoint, creates an IOC for the SHA1 hash, and sends a Slack
notification to #soc-alerts.
```

What you'll get: workflow JSON ready to import. If you ask Claude to import it, it does so via `ha_import_workflow`. Important note: workflows imported with a service user token are invisible to human users in the console UI. If the workflow needs to be visible and editable in the UI, use a personal console user token.

### SOC reporting

```
Write a SOC Leader report for this investigation as a Word document:
executive summary, incident timeline, IOC table with VT verdicts, MITRE
mapping, root cause, and recommendations.
```

What you'll get: a structured `.docx` saved to your project folder, ready to share. If you keep a `reports/` subfolder in your project, Claude saves there by default and the report persists across sessions.

---

## 6. When things don't work

### "Skill didn't trigger"

Be more specific in your prompt. "Make a thing" is ambiguous; "build a Hyperautomation workflow that..." is unmissable. You can also be explicit: "Use the sentinelone-sdl-dashboard skill to..."

If a skill should have triggered and didn't, ask Claude `which skills are loaded for this session?` to confirm the plugin is wired up.

### MCP server not connecting (red dot in Cowork)

Check, in order:

1. **Path is absolute.** `args` for `sentinelone-mcp` must be the full path to `index.js`, not `./sentinelone-mcp/index.js`.
2. **Node.js is on PATH** for Claude Desktop. Restart Claude Desktop after a fresh Node install. On macOS, `which node` should return a path; on Windows, `where node`.
3. **Dependencies installed.** `cd sentinelone-mcp && npm install` once after cloning.
4. **For `purple-mcp`: `uvx --version` works in a fresh terminal.** If not, reinstall `uv` and open a new terminal.
5. **Restart Claude Desktop** after any config change.

### 401 / 403 errors

- **Wrong region URL.** `S1_CONSOLE_URL`, `S1_HEC_INGEST_URL`, and `SDL_XDR_URL` are region-specific. Cross-check against the [Endpoint URLs by Region](https://community.sentinelone.com/s/article/000004961) article.
- **Token scope too low.** Read operations need Viewer or higher; response actions need IR Team or higher.
- **Wrong key for the operation.** `SDL_CONFIG_WRITE_KEY` does NOT grant View Logs access; using it for a query returns 403. The console JWT works for SDL config and query operations on Mgmt Z SP5+; the dedicated SDL keys are only needed for `uploadLogs` and parser/dashboard `putFile`.

### Plugin upload failed

Fall back to per-skill `.skill` files in [`sentinelone-skills-plugin/dist/`](../sentinelone-skills-plugin/dist/). Double-click each `.skill` file to install, or upload one at a time via Browse plugins. The six files are: `sentinelone-mgmt-console-api.skill`, `sentinelone-powerquery.skill`, `sentinelone-sdl-api.skill`, `sentinelone-sdl-dashboard.skill`, `sentinelone-sdl-log-parser.skill`, `sentinelone-hyperautomation.skill`.

### "I imported a workflow but I can't see it in the console UI"

Workflows imported with a service user token are invisible to human users. Generate a personal console user token, set `S1_CONSOLE_API_TOKEN` to that token in `claude_desktop_config.json`, and re-import.

### "Claude said something I don't believe"

Push back. Tell Claude you don't believe a specific claim and ask it to recheck the underlying tool call. The session protocol forbids fabrication; if Claude can't cite the evidence, it has to retract or recalibrate. This is by design.

### Need a deeper look

Ask Claude:

```
smoke test s1 skills
```

It runs through every MCP and skill, reports what's healthy, and gives a precise error for anything that isn't.

---

## 7. Going deeper

### Read the full reference docs

| Doc | When to read it |
|---|---|
| [`docs/installation.md`](./installation.md) | Full install reference, including upgrade and credentials.json fallback |
| [`docs/architecture.md`](./architecture.md) | Data flow, auth model, sandbox proxy explanation |
| [`docs/skills.md`](./skills.md) | Per-skill capability reference |
| [`docs/mcp-tools.md`](./mcp-tools.md) | Every MCP tool with usage notes |
| [`docs/credentials.md`](./credentials.md) | Every credential key and where to find it |
| [`docs/sdl-dashboard.md`](./sdl-dashboard.md) | Every supported panel type with confirmed JSON examples |
| [`docs/testing.md`](./testing.md) | Test coverage matrix and confirmed API field requirements |
| [`sentinelone-mgmt-console-api/SKILL.md`](../sentinelone-mgmt-console-api/SKILL.md) | Confirmed field schemas and required parameters per endpoint |

### Operate at scale

Once you're past first-run, the next leverage points are:

- **Schedule recurring tasks** with `coworkScheduledTasksEnabled: true` (it's already in the config snippet above). Examples: nightly behavioral baseline refresh, hourly alert digest to Slack, weekly threat summary as a `.docx`.
- **Productionise hunts as detection rules.** Anything you find useful in chat can be promoted to a recurring detection.
- **Add custom data sources.** Author a parser, deploy it, and the skills handle every other source the same way (auto-discovery means no per-source hardcoding).

### Get help

- Re-run `smoke test s1 skills` whenever something feels off.
- File issues against the repo with the smoke test output attached.
- For SentinelOne API questions, the Community articles linked throughout this guide are the canonical references.

---

You're ready. Open the `PrincipalSOCAnalyst` project, start a new chat, and ask it to triage today's alerts. Everything else builds from there.
