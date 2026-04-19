# sentinelone-mgmt-console-api (Claude skill)

A Claude skill wrapping the SentinelOne Management Console API (Swagger 2.1, 781 operations, 113 tags).

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

## Layout

- `SKILL.md` — instructions Claude reads when the skill triggers
- `config.json` — credentials (gitignore this)
- `scripts/` — Python client + CLI helpers
- `references/` — endpoint index + per-tag reference docs
- `spec/` — the original Swagger JSON
