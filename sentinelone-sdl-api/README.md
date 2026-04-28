# sentinelone-sdl-api (Claude skill)

A Claude skill wrapping the SentinelOne **Singularity Data Lake (SDL) API** — ingest, query, and manage configuration files on a Scalyr/SDL/XDR tenant. Covers all 10 SDL methods with a Python client, a CLI, and per-method reference docs.

## Install

Copy this folder into your user skills directory:

```bash
cp -r sentinelone-sdl-api ~/.claude/skills/
```

In Cowork/Claude Code, the path is:

```
/sessions/<session>/mnt/.claude/skills/sentinelone-sdl-api/
```

## Configure

The SDL API has four scoped key types plus (optionally) the same management-console API token used by `sentinelone-mgmt-console-api` (`S1_CONSOLE_API_TOKEN`). Drop a `credentials.json` directly into your Cowork project folder with the keys you need (see [`credentials.example.json`](../credentials.example.json) for all available keys). The plugin's SessionStart hook auto-discovers it; run `bash scripts/bootstrap_creds.sh` to refresh manually:

```json
{
  "SDL_XDR_URL":          "https://xdr.us1.sentinelone.net",
  "S1_CONSOLE_API_TOKEN":          "eyJ...your-token...",
  "SDL_LOG_WRITE_KEY":     "0Z1Fy0...",
  "SDL_LOG_READ_KEY":      "0tzj/CPYT...",
  "SDL_CONFIG_READ_KEY":   "0MQTxgj...",
  "SDL_CONFIG_WRITE_KEY":  "0mXas6PD..."
}
```

| Key | Methods unlocked |
|-----|-----------------|
| Log Write Access   | `uploadLogs`, `addEvents` |
| Log Read Access    | `query`, `numericQuery`, `facetQuery`, `timeseriesQuery`, `powerQuery` |
| Configuration Read | Log Read + `getFile`, `listFiles` |
| Configuration Write| Everything above + `putFile` |
| Console user token | All query + config methods. **NOT** `uploadLogs`. |

Generate SDL keys in SDL Console → your-user menu → **API Keys**. Scope-specific (a site-scoped key only sees that site).

### Which fields do I need?

- **`base_url`** — always required.
- **SDL keys** — fill in only the ones that match what you want the skill to do. Ingesting? `log_write_key`. Running queries? `log_read_key`. Reading parsers/dashboards? `config_read_key`. Editing/deleting them? `config_write_key`. If you only ever need to query, you can skip the other three.
- **`S1_CONSOLE_API_TOKEN`**: optional alternative to SDL keys. The same management-console JWT used by `sentinelone-mgmt-console-api` works for every SDL method **except** `uploadLogs`. Useful if you already have a console token and don't want to generate a second set of keys. Leave blank if you're using the scoped SDL keys. (Legacy alias `SDL_CONSOLE_API_TOKEN` is still recognised but emits a deprecation warning.)
- **`SDL_S1_SCOPE`**: only relevant when `S1_CONSOLE_API_TOKEN` is set **and** that user has access to multiple sites or accounts. Format: `<accountId>:<siteId>` for site scope, `<accountId>` for account scope. Ignored when SDL keys are used.

The client picks the narrowest matching key per method (principle of least privilege). If you fill in all 4 SDL keys, each config field maps to one method group:

| Key | Primary method(s) in the client |
|---|---|
| `log_write_key`    | `uploadLogs` (required — console tokens rejected here), `addEvents` |
| `log_read_key`     | `query`, `numericQuery`, `facetQuery`, `timeseriesQuery`, `powerQuery` |
| `config_read_key`  | `listFiles`, `getFile` |
| `config_write_key` | `putFile` |

`console_api_token` is only used as a fallback for any of the above (except `uploadLogs`) when the matching SDL key is blank.

Environment variables (`SDL_XDR_URL`, `SDL_LOG_WRITE_KEY`, etc.) override the credentials file if set.

## Quick test

```bash
pip install requests
cd ~/.claude/skills/sentinelone-sdl-api
python tests/smoke_test.py
```

The smoke test exercises every method end-to-end: ingests via `uploadLogs` + `addEvents`, runs `query` / `facetQuery` / `numericQuery` / `timeseriesQuery` / `powerQuery`, then `listFiles` + `getFile` + a full `putFile` create→update→delete round-trip on a throwaway `/lookups/sdl_skill_smoke_…` path. Reports a per-method pass/fail line.

## CLI

```bash
python scripts/sdl_cli.py list-files
python scripts/sdl_cli.py get-file /parsers/uploadLogs

python scripts/sdl_cli.py power-query "dataset='accesslog' | group count() by status" --start 1h
python scripts/sdl_cli.py query "tag='ingestionFailure'" --start 1h --max 20
python scripts/sdl_cli.py facet-query srcIp --filter "status >= 400" --start 1h
python scripts/sdl_cli.py numeric-query --function count --start 1h --buckets 30
python scripts/sdl_cli.py timeseries-query --function count --filter "*" --start 1h --buckets 60

python scripts/sdl_cli.py upload-logs --text "hello sdl" --parser demo-parser --server-host dev
python scripts/sdl_cli.py upload-logs --file ./data.log --parser demo-parser

python scripts/sdl_cli.py add-events --message "user login" --attr user=prithvi --attr latencyMs=42
python scripts/sdl_cli.py put-file /lookups/MyTable --content-file ./table.json
python scripts/sdl_cli.py put-file /lookups/Stale --delete
```

## Python

```python
import sys; sys.path.insert(0, "scripts")
from sdl_client import SDLClient

c = SDLClient()

# Pipeline query (preferred general-purpose tool)
r = c.power_query("status >= 100 status <= 599 | group count() by status", start_time="24h")

# Stream every raw match across continuation tokens
for m in c.iter_query(filter="tag='ingestionFailure'", start_time="24h", max_total=500):
    ...

# Structured ingest — one session for the life of the process
sess = c.new_session_id()
c.add_events(
    session=sess,
    session_info={"serverHost": "dev-box", "serverType": "frontend"},
    events=[{"ts": c.now_ns(), "attrs": {"message": "user login", "latencyMs": 42}}],
)

# Plain-text ingest — requires a real Log Write Access key (console tokens rejected)
c.upload_logs("hello\nworld", parser="my-parser", server_host="dev-box")

# Configuration files
paths  = c.list_files()["paths"]
parser = c.get_file("/parsers/MyParser")
c.put_file("/parsers/MyParser", content="// parser body", expected_version=parser["version"])
```

The client picks the right key per method automatically, retries on 429/5xx/`error/server/backoff` with exponential backoff honouring `Retry-After`, and returns parsed JSON. Errors surface as `SDLAPIError` with `.status` and `.body`.

## Layout

- `SKILL.md` — instructions Claude reads when the skill triggers
- `<project folder>/credentials.json` — credentials (set `SDL_XDR_URL` and the keys you need); auto-discovered by the plugin's SessionStart hook
- `scripts/bootstrap_creds.sh` — idempotent helper to copy workspace creds into the sandbox-local path
- `scripts/sdl_client.py` — `SDLClient` (auto key selection across 4 scoped keys + console token, `Bearer` auth, retries, `iter_query` pagination)
- `scripts/sdl_cli.py` — shell CLI covering every method
- `references/methods.md` — per-method reference (params, defaults, response shape, gotchas)
- `references/auth_and_limits.md` — key matrix, console-token + S1-Scope rules, CPU leaky-bucket model, daily caps, 2026-03-19 8 QPS cap
- `references/integration_patterns.md` — `addEvents` session discipline, structured vs unstructured events, the official binary-exponential-backoff loop with `discardBuffer` handling
- `tests/smoke_test.py` — end-to-end test that hits every method

## Why this is separate from `sentinelone-mgmt-console-api`

The SDL API is a different surface: JSON over `Bearer` (not `ApiToken`), a different URL namespace (`/api/...` not `/web/api/v2.1/...`), and its own key system. It's the only path for ingesting custom telemetry, running PowerQueries against SDL, and editing parsers/dashboards/alerts/lookups programmatically. For agents, threats, sites, Mgmt Console resources — use `sentinelone-mgmt-console-api`. For authoring PQ query bodies — use `sentinelone-powerquery`.
