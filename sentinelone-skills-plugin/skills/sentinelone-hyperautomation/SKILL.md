---
name: sentinelone-hyperautomation
description: >
  Use this skill whenever a user wants to create, design, build, generate, write, or export a
  SentinelOne Hyperautomation workflow in JSON format. Triggers include: any mention of
  "Hyperautomation", "workflow", "automation", "SOAR", "playbook", "alert response", "trigger",
  "scheduled workflow", "webhook workflow", or any request to automate a SentinelOne-related
  security task. Also triggers when the user asks to import, export, test, validate, or submit
  a workflow to a SentinelOne console via API. Always use this skill for any task involving
  SentinelOne workflow JSON — even if phrased casually (e.g., "build me a thing that disables
  a user when an alert fires"). When in doubt about whether this skill applies, use it.
---

# SentinelOne Hyperautomation Skill

This skill enables Claude to design and generate valid SentinelOne Hyperautomation workflow
JSON, explain the logic behind workflows, and optionally submit them to a live console via API.

> **Sandbox proxy blocked?** If import/export API calls to `*.sentinelone.net` fail with a connection or proxy error inside the Claude sandbox, use the `sentinelone-mcp` server instead. It runs locally via `node` and bypasses the sandbox proxy entirely. Setup: add it to `claude_desktop_config.json` (see `claude-skills/sentinelone-mcp/README.md`). The MCP server exposes `ha_list_workflows`, `ha_get_workflow`, `ha_import_workflow`, and `ha_export_workflow` — all running from your machine against the Hyperautomation API.

## How to use this skill

When a user asks to build a workflow, follow this process:

### Step 1 — Understand the intent
Ask (or infer from context):
- What should trigger the workflow? (alert, schedule, webhook, manual, email)
- What integrations are needed? (SentinelOne, M365, Slack, VirusTotal, etc.)
- What is the desired outcome? (enrich alert, disable user, send notification, etc.)
- Should the workflow run automatically or on-demand?

### Step 2 — Warn about integrations
**CRITICAL**: Before generating JSON, identify any integration-backed actions (tag = "integration").
These require pre-configured connections in the console that CANNOT be created via API.
Always tell the user: *"This workflow uses the [X, Y, Z] integrations. Before importing, you must
configure connections for these in your Hyperautomation → Integrations section."*

Integration-backed actions have `"tag": "integration"` and a non-null `integration_id`.
Core actions (Variable, Loop, Condition, Delay, Send Email, HTTP Request without integration,
Break Loop, Snippet, Wait for Slack, Create Interaction) have `"tag": "core_action"`.

### Step 3 — Generate the JSON
Read `references/workflow-schema.md` to produce a valid workflow JSON.
Read `references/building-blocks.md` for the correct action type structures.
Read `references/functions-reference.md` for available functions and their syntax.

### Step 4 — Validate before outputting
Self-check against `references/validation-rules.md` before presenting the workflow.

### Step 5 — API submission (optional)
If the user wants to submit to a live console, read `references/api-integration.md`.

**Credentials**: The plugin's SessionStart hook auto-discovers a `credentials.json`
dropped directly into the user's Cowork project folder at the start of every session.
If the file is missing, ask the user to drop a `credentials.json` into their project folder.

Resolution priority (highest wins):

1. Environment variables `S1_CONSOLE_URL` / `S1_CONSOLE_API_TOKEN`
2. `<project folder>/credentials.json` (auto-discovered)
3. Ask the user to provide their console URL and personal Console User API token

To read credentials in Python:
```python
import json, os
from pathlib import Path
_creds = {}
for candidate in (
    Path.home() / ".claude" / "sentinelone" / "credentials.json",
    Path(os.environ.get("COWORK_WORKSPACE", "")) / ".sentinelone" / "credentials.json"
        if os.environ.get("COWORK_WORKSPACE") else None,
    Path(os.environ.get("CLAUDE_CONFIG_DIR", "")) / "sentinelone" / "credentials.json"
        if os.environ.get("CLAUDE_CONFIG_DIR") else None,
    Path.home() / ".config" / "sentinelone" / "credentials.json",
):
    if candidate and candidate.is_file():
        _creds = json.loads(candidate.read_text())
        break
S1_CONSOLE_URL  = os.environ.get("S1_CONSOLE_URL")  or _creds.get("S1_CONSOLE_URL")  or None
S1_CONSOLE_API_TOKEN = os.environ.get("S1_CONSOLE_API_TOKEN") or _creds.get("S1_CONSOLE_API_TOKEN") or None
```

Once resolved, validate them using the two-step test in `references/api-integration.md`
(system health check + token permission check). Only proceed with import/trigger/activate
after both checks pass. Always use a personal Console User API token, not a Service User
token — see `references/api-integration.md` for the reason.

---

## Reference files — when to read each

| File | Read when... |
|------|-------------|
| `references/workflow-schema.md` | Always when generating JSON — defines the envelope and action structure |
| `references/building-blocks.md` | Need the exact shape of a specific action type (trigger, loop, condition, etc.) |
| `references/building-blocks-catalog.md` | **Picking what to use** for a given step / composing multi-action idioms / bootstrapping a SOAR recipe. Mined from 643 active production workflows. Read FIRST when designing a new workflow. |
| `references/functions-reference.md` | Using `{{Function.X()}}` syntax or PowerQuery patterns |
| `references/validation-rules.md` | Before outputting any workflow — run the checklist |
| `references/api-integration.md` | User wants to import/export/submit to a live console |

## Decision guide: pick the right pattern by use case

The catalog (`references/building-blocks-catalog.md`) names every reusable block. Use this
table to jump straight to the right starting point:

| User says... | Start with | Composite patterns to layer on |
|--------------|-----------|--------------------------------|
| "When an alert fires, do X" | A1 (Singularity Response Trigger) + recipe C1 | B1 safe-field DEFAULT chain, B2 success/fail branch, B6 add-note |
| "Every day / every N hours, do X" | A3 (Scheduled Trigger) + recipe C2 | B7 SDL ingest, B9 IOC create, B5 JQ shaping |
| "When a webhook hits, do X" | A4 (HTTP Trigger) + recipe C3 | B2 status-code branch, B11 Slack ack |
| "Let an analyst kick this off with parameters" | A2 dynamic Manual Trigger + recipe C4 | B5 JQ shaping, B4 APPEND accumulator |
| "Wait for analyst approval before remediating" | recipe C5 (Slack approval) | B11 Slack interactive, B6 add-note |
| "Periodic posture / UEBA report" | A3 + recipe C6 | B8 PowerQuery, B7 SDL ingest |
| "Page through a paginated API" | B3 (cursor + break_loop) | B4 APPEND accumulator |
| "Summarize this evidence with an LLM" | B12 (OpenAI) | B6 add-note |
| "Create a Threat Intelligence indicator" | B9 (TI IOC create) | B4 accumulator inside loop |
| "Add a note on the alert" | B6 (UAM GraphQL addAlertNote) | always wrap text in `Function.HTML_ENCODE` |

When in doubt, the load-bearing 17 atoms are:
`http_request`, `variable`, `condition`, `loop`, `singularity_response_trigger`,
`data_formation`, `send_email`, `snippet`, `break_loop`, `manual_trigger`, `wait_for_slack`,
`delay`, `http_trigger`, `scheduled_trigger`, `create_interaction`, `wait_for_interaction`,
`email_trigger`. Anything outside this set is exotic; confirm it exists before generating.

## Example workflows (in references/examples/)
Annotated real examples to use as structural references:
- `simple-linear.md` — simple trigger → action → note pattern
- `branching.md` — condition with true/false branches + success/fail notes
- `loop-pattern.md` — loop with APPEND and BREAK logic
- `integration-pattern.md` — integration-backed HTTP request with connection placeholders

---

## Quick reference — action name → slugified reference

When referencing a previous action in `{{...}}` syntax, use the kebab-case version of the
action's `name` field. Examples:
- Action named "Get Agents with Active Threat" → `{{get-agents-with-active-threat.body.data}}`
- Action named "SDL Query" → `{{sdl-query.body.matches[0].attributes.actor_user_email_addr}}`
- Action named "Singularity Response Trigger" → `{{singularity-response-trigger.data.id}}`
- Action named "Loop the list of IPv4" → `{{loop-the-list-of-ipv4.item}}`

The rule: lowercase, spaces become hyphens, special characters dropped.

---

## Integration warning template

Use this when the workflow contains integration-backed actions:

> ⚠️ **Pre-requisite integrations to configure before importing:**
> - **[Integration Name]** — used for [action name(s)]. Configure at Hyperautomation → Integrations → [Integration Name] → Add Connection.
> - *(repeat for each)*
>
> Once configured, note the connection name — you may need to update the `connection_name` field in the JSON before importing.

---

## Common mistakes to avoid

- ❌ Defining multiple variables in a single Variable action when one references another — they evaluate simultaneously and will fail with "variable not found"
  ✅ Always use one Variable action per variable when chaining references. One var → one action, always.
- ❌ Forgetting `Function.HTML_ENCODE` on note text passed to UAM GraphQL. Any quote, ampersand, or angle bracket breaks the mutation string.
  ✅ Always wrap: `\\\"{{Function.HTML_ENCODE(local_var.note)}}\\\"`.
- ❌ Encoding `compared_value` for `comparison_operator: "in"` as a raw JSON array.
  ✅ JSON-string-encode it: `"[\"HIGH\",\"CRITICAL\"]"`.
- ❌ `condition_type: "simple"`: never used in active corpus. Always emit `"multi"`.
- ❌ `wait_for_interaction` using `interaction_id` / `value` field names (older docs).
  ✅ Real fields are `identifier` / `time_value`.
- ❌ Hard-coding site IDs in TI IOC creates: breaks on tenant transfer.
  ✅ Pull from a Variable, Manual Trigger param, or `singularity-response-trigger.data.scopeId`.
- ❌ Importing with a Service User token: workflows become invisible to humans in the UI.
  ✅ Always use a personal Console User API token for `S1_CONSOLE_API_TOKEN`.


## Workflow import via sentinelone-mcp

Workflow import, export, and listing use the `sentinelone-mcp` MCP server, which bypasses the
Cowork sandbox proxy entirely. Use `ha_list_workflows`, `ha_get_workflow`, `ha_import_workflow`,
and `ha_export_workflow` directly instead of falling back to the `sentinelone-mgmt-console-api`
skill scripts. The MCP server runs locally on your machine and makes direct HTTPS calls to
`*.sentinelone.net` without proxy interference.
