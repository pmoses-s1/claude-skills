# sentinelone-mgmt-console-api (Claude skill)

A Claude skill wrapping the SentinelOne Management Console API (Swagger 2.1, 781 operations, 113 tags) plus the two GraphQL surfaces the console exposes: **Unified Alert Management** (documented, for modern multi-source alert triage and bulk actions) and **Purple AI** (undocumented, for natural-language SDL queries).

## Install

Copy this folder into your user skills directory:

```bash
cp -r sentinelone-mgmt-console-api ~/.claude/skills/
```

In Cowork/Claude Code, the path is:

```
/sessions/<session>/mnt/.claude/skills/sentinelone-mgmt-console-api/
```

## Configure

Edit `config.json` and fill in the two dummy values:

```json
{
  "base_url": "https://YOURTENANT.sentinelone.net",
  "api_token": "eyJrIjoi..."
}
```

Or set env vars instead: `S1_BASE_URL`, `S1_API_TOKEN`.

Create the API token in the S1 console → Settings → Users → Service Users → Generate API Token. Scope it to the minimum permissions needed.

## Quick test

```bash
pip install requests
cd ~/.claude/skills/sentinelone-mgmt-console-api
python scripts/s1_client.py
```

Should print the first 5 accounts.

Unified Alert Management:

```bash
python scripts/call_unified_alerts.py list --filter detectionProduct=EDR --first 10
python scripts/call_unified_alerts.py facets status severity detectionProduct
```

Purple AI natural-language query (requires tenant entitlement for Purple AI):

```bash
python scripts/call_purple.py "show powershell.exe outbound connections in the last 24h, top 10"
```

Purple AI answers questions about SDL telemetry (process/network/file events, indicators, ingested logs). It does *not* answer questions about console entities (alerts, threats, agents) — those go through the REST endpoints or Unified Alert Management.

## Layout

- `SKILL.md` — instructions Claude reads when the skill triggers
- `config.json` — credentials (gitignore this; `config.json.example` is the template)
- `scripts/s1_client.py` — REST client (auth, retries, cursor pagination)
- `scripts/call_endpoint.py` — REST CLI wrapper
- `scripts/search_endpoints.py` — keyword search over the endpoint index
- `scripts/purple_ai.py` — Purple AI GraphQL wrapper (`purple_query()`, `PurpleAIError`)
- `scripts/call_purple.py` — Purple AI CLI wrapper
- `scripts/unified_alerts.py` — Unified Alert Management GraphQL wrapper (queries, mutations, triage helpers)
- `scripts/call_unified_alerts.py` — UAM CLI wrapper
- `references/` — endpoint index + per-tag reference docs; `UNIFIED_ALERTS.md` covers the GraphQL UAM surface
- `spec/` — the original Swagger JSON
