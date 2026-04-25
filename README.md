# claude-skills

SentinelOne skills for Claude. Install the plugin to get everything — no individual skill setup needed.

## Quick start

1. Download the latest `.plugin` file from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/)
2. In Cowork, go to **Settings → Capabilities → Plugin** and click **Upload**, then select the `.plugin` file
3. Create `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` with your tenant credentials (see [Configuration](#configuration) below)

That's it. All six skills are active immediately.

## What's included

The plugin bundles every skill in this repo — installing the plugin is sufficient, there is no need to install skills individually.

| Skill | What it does |
|-------|-------------|
| sentinelone-mgmt-console-api | Query and act on the Management Console: threats, alerts, agents, sites, RemoteOps, Deep Visibility, Hyperautomation, Purple AI, UAM |
| sentinelone-powerquery | Write, debug, and run PowerQuery for threat hunting, STAR detection rules, and SDL dashboards |
| sentinelone-sdl-api | Ingest events, run queries, and manage configuration files (parsers, dashboards, lookups) via the Singularity Data Lake API |
| sentinelone-sdl-dashboard | Design, author, and deploy SDL dashboards — panels, tabs, parameters, and full dashboard JSON |
| sentinelone-sdl-log-parser | Author and validate SDL log parsers for any log format, with OCSF field mapping by default |
| sentinelone-hyperautomation | Design and generate Hyperautomation workflow JSON, with optional live console import |

## What you can do

These skills turn Claude into a hands-on SentinelOne analyst and engineer. Once the plugin is installed and credentials are configured, you can talk to your tenant in plain English — Claude handles the API calls, query writing, and JSON authoring and explains what it found or built.

**Threat hunting and investigation** — ask Claude to hunt for specific TTPs, IOCs, or behaviours across your SDL telemetry. It writes and runs PowerQuery automatically, pages through results, and summarises findings. You can go from a vague question ("any PowerShell reaching out to the internet?") to a ranked table of suspicious endpoints in one message.

**Alert and threat management** — list open threats, triage UAM alerts, add analyst notes, change status, or isolate an endpoint, all by describing what you want. Claude maps your intent to the right Management Console API calls and confirms what it did.

**Dashboard authoring** — describe the panels you want ("a SOC overview with threat timeline, top noisy endpoints, and outbound connection breakdown") and Claude produces deployment-ready SDL dashboard JSON, with queries validated against your tenant before it deploys.

**Log parser authoring** — paste a raw log sample and Claude writes a complete SDL parser definition, maps fields to OCSF, validates it against the parser engine, ingests a test event, and confirms the fields appear correctly — end to end in one session.

**Automation and response** — describe a response workflow in natural language ("when a high-severity alert fires on a server, isolate the endpoint, create an IOC for any hash in the alert, and notify the team") and Claude generates the Hyperautomation workflow JSON ready to import.

**Data lake operations** — ingest custom telemetry, list and manage configuration files, deploy or update parsers and dashboards, and run arbitrary queries through the SDL API.

---

## Example questions

These are real questions you can ask. Claude will pick the right skill automatically.

### Threat hunting

- *"Hunt for any process that opened a connection to a non-RFC1918 IP in the last 7 days — show me top endpoints by hit count"*
- *"Write a PowerQuery that finds lsass memory reads by non-system processes"*
- *"Are there any HIFI indicators for Mimikatz or BloodHound on my tenant in the last 30 days?"*
- *"Find PowerShell scripts that encoded a Base64 command, group by endpoint"*
- *"Show me the top 20 destination IPs for outbound connections from Windows servers this week"*
- *"Write a STAR detection rule that fires when a script interpreter spawns a network tool"*

### Alert and threat management

- *"List all open threats created in the last 24 hours, sorted by confidence"*
- *"Show me unresolved UAM alerts with severity High or Critical from today"*
- *"Add a note to threat ID `abc123` saying it was reviewed and is a false positive"*
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
- *"I have a CEF log from CrowdStrike — create a parser with OCSF field mapping"*
- *"My FortiGate parser isn't extracting the destination IP correctly, here's the JSON: `<paste parser>`"*
- *"Check the ai-siem catalog and see if there's already a parser for Okta logs"*
- *"Validate my parser and ingest a test event to confirm the fields look right"*

### Data lake operations

- *"List all configuration files on my SDL tenant under `/dashboards/`"*
- *"Ingest this JSON array of events into SDL with the source name `custom-app`"*
- *"Run this PowerQuery against my tenant and return the results as a table: `<query>`"*
- *"Download the current version of my `/logParsers/fortinet-fortigate` parser"*

### Hyperautomation workflows

- *"Build a workflow that isolates an endpoint and sends a Slack notification when a Ransomware indicator fires"*
- *"Create a scheduled workflow that runs every morning and sends a summary of overnight threats by email"*
- *"Write a webhook workflow that creates an IOC from an incoming threat intel feed payload"*
- *"Design a playbook: on a Critical alert, add a note, escalate the site status, and page the on-call analyst"*

---

## Installing

**Plugin (recommended)** — download from [`sentinelone-skills-plugin/dist/`](./sentinelone-skills-plugin/dist/), then in Cowork go to **Settings → Capabilities → Plugin → Upload** and select the file. All six skills are installed in one step.

**Individual skills (for development only)** — drop a skill folder into `~/.claude/skills/`. Claude will pick it up on next session.

## Configuration

All skills read credentials from a single JSON file. The recommended path that works everywhere — both inside Cowork and from your terminal — is:

```
~/.claude/sentinelone/credentials.json
```

> **Why this path?** `~/.claude/` is your home-level Claude config directory. It's always accessible from your terminal without needing to know `CLAUDE_CONFIG_DIR`, and Cowork picks it up automatically too.

Full credential resolution order (highest priority wins):
1. Environment variables (`S1_BASE_URL`, `S1_API_TOKEN`, `SDL_*`)
2. `$CLAUDE_CONFIG_DIR/sentinelone/credentials.json` — Cowork session config (set automatically)
3. `~/.claude/sentinelone/credentials.json` — **recommended persistent path**
4. `~/.config/sentinelone/credentials.json` — legacy terminal fallback

**macOS / Linux:**

```bash
mkdir -p ~/.claude/sentinelone
cat > ~/.claude/sentinelone/credentials.json << 'EOF'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
EOF
```

**Windows (PowerShell):**

```powershell
# In Cowork: use $CLAUDE_CONFIG_DIR/sentinelone/credentials.json (set automatically)
# In terminal, use:
$dir = "$env:USERPROFILE\.config\sentinelone"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
@'
{
  "S1_BASE_URL": "https://usea1-acme.sentinelone.net",
  "S1_API_TOKEN": "eyJ...your-management-console-api-token...",
  "SDL_BASE_URL": "https://xdr.us1.sentinelone.net",
  "SDL_CONSOLE_API_TOKEN": "eyJ...your-sdl-console-api-token...",
  "SDL_LOG_WRITE_KEY": "0Z1Fy0...your-log-write-key...",
  "SDL_CONFIG_WRITE_KEY": "0mXas6PD...your-config-write-key..."
}
'@ | Set-Content "$dir\credentials.json" -Encoding UTF8
```

A fully annotated example with all optional keys is in [`credentials.example.json`](./credentials.example.json).

| Credential key | Required for | How to get it |
|---|---|---|
| `S1_BASE_URL` | All management console skills | Your console URL, e.g. `https://usea1-acme.sentinelone.net` |
| `S1_API_TOKEN` | `sentinelone-mgmt-console-api`, `sentinelone-powerquery` | Settings → Users → Service Users → Create New Service User → copy the API token. See [Creating service users](https://community.sentinelone.com/s/article/000005291) |
| `SDL_BASE_URL` | `sentinelone-sdl-api`, `sentinelone-sdl-dashboard`, `sentinelone-sdl-log-parser` | Your SDL tenant URL, e.g. `https://xdr.us1.sentinelone.net` |
| `SDL_CONSOLE_API_TOKEN` | SDL query and config methods (not `uploadLogs`) | Same token as `S1_API_TOKEN` — console tokens support the SDL API from Management version Z SP5+. See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `SDL_LOG_WRITE_KEY` | `uploadLogs` only | In Singularity Data Lake → menu next to username → API Keys → Log Access Keys → New Key (Log Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |
| `SDL_CONFIG_WRITE_KEY` | Deploying parsers/dashboards via `putFile` | In Singularity Data Lake → menu next to username → API Keys → Configuration Access Keys → New Key (Configuration Write Access). See [SDL API Keys](https://community.sentinelone.com/s/article/000006763) |

Environment variables override the credentials file if set.

## sentinelone-skills-plugin

The [`sentinelone-skills-plugin/`](./sentinelone-skills-plugin/) directory contains the distributable Claude plugin that bundles all six skills (including `sentinelone-hyperautomation` by Marco Rottigni). The built `.plugin` file lives in `sentinelone-skills-plugin/dist/`.

To rebuild after syncing skill changes:

```bash
cd sentinelone-skills-plugin
bash scripts/build.sh
```

To rebuild from scratch (removes old dist files first):

```bash
cd sentinelone-skills-plugin
bash scripts/build.sh --clean
```

## Windsurf

This repo includes Windsurf workflow files in `.windsurf/workflows/`. Each workflow is a thin pointer that directs Cascade to read the canonical `SKILL.md` and reference docs in the matching skill folder — no duplicated content.

- `sentinelone-api.md` — Management Console API (agents, threats, alerts, sites, Purple AI, UAM).
- `sentinelone-powerquery.md` — PowerQuery authoring, debugging, and detection rules.
- `sentinelone-sdl-api.md` — Singularity Data Lake API (ingest, query, config files).
- `sentinelone-sdl-log-parser.md` — SDL log parser authoring with OCSF mapping.
