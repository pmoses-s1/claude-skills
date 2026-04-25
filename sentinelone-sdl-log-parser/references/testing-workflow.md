# Validation Workflow — Using `sentinelone-sdl-api` to Test a Parser

There is **no dedicated `testParser` REST endpoint** on the SDL tenant. The in-console `Test Parser` button at `/logImportTester` runs the parser client-side in JavaScript. To validate end-to-end you must deploy the parser, ingest a sample through it, and query the result back. This doc is the recipe.

## Prerequisites

- `sentinelone-sdl-api` skill is installed.
- `credentials.json` is dropped into a folder Cowork can access (recommended: `$COWORK_WORKSPACE/.sentinelone/credentials.json`) and contains at minimum `SDL_CONFIG_WRITE_KEY`, `SDL_LOG_WRITE_KEY`, and `SDL_LOG_READ_KEY`, or `S1_CONSOLE_API_TOKEN` (the same management-console JWT; legacy `SDL_CONSOLE_API_TOKEN` is also accepted). The plugin's SessionStart hook copies it to `$HOME/.claude/sentinelone/credentials.json` inside the sandbox. Check with:

```bash
cat "$HOME/.claude/sentinelone/credentials.json"
```

- You have a draft parser JSON and a sample log file.

## Full loop

```python
import sys, time, uuid, json, pathlib
sys.path.insert(0, "/sessions/dazzling-ecstatic-volta/mnt/.claude/skills/sentinelone-sdl-api/scripts")
from sdl_client import SDLClient

c = SDLClient()

PARSER_NAME = "claude_test_fortigate_cef"    # claude_test_ prefix so cleanup is a one-liner
parser_body = pathlib.Path("draft_parser.json").read_text()
sample      = pathlib.Path("sample.log").read_text()

# --- 1. Deploy ------------------------------------------------------------
#    Use expected_version=0 on first deploy to refuse overwriting a parser
#    that already exists; drop expected_version on iterative edits.
try:
    existing = c.get_file(f"/logParsers/{PARSER_NAME}")
    version  = existing["version"]
except Exception:
    version = None

put_kwargs = {"content": parser_body}
if version is not None:
    put_kwargs["expected_version"] = version
c.put_file(f"/logParsers/{PARSER_NAME}", **put_kwargs)

# --- 2. Ingest a sample --------------------------------------------------
#    A unique host tag per run lets you isolate this test's events from
#    every other thing flowing through the tenant.
host_tag = f"parser-test-{uuid.uuid4().hex[:8]}"
nonce    = str(uuid.uuid4())
c.upload_logs(
    sample,
    parser=PARSER_NAME,
    server_host=host_tag,
    logfile="parser_validation.log",
    nonce=nonce,
)

# --- 3. Query back -------------------------------------------------------
#    Sleep long enough that the event is durable and searchable.
time.sleep(8)

EXPECTED = ["timestamp", "src", "dst", "spt", "dpt", "proto", "act"]
pq = f"host='{host_tag}' | columns " + ", ".join(["message"] + EXPECTED)
res = c.power_query(query=pq, start_time="10m")
print(json.dumps(res, indent=2))
```

## What success looks like

- `put_file` → `{"status": "success", ...}`.
- `upload_logs` → `{"status": "success", ...}` (a `bytesCharged` number appearing is normal).
- `power_query` returns at least one row per line in the sample, and every expected field is present (not null) for at least the lines where it should be.

A duplicate-`Nonce` response (`status: "success", message: "ignoring request, due to duplicate nonce..."`) means the ingest was deduped — advance to a fresh nonce on iteration.

## Common failure modes

| Symptom | Likely cause |
|---|---|
| `put_file` → `error/client/badParam` | JSON syntax error. Run the body through a JSON5-tolerant validator; watch for unmatched braces or trailing commas inside format strings. |
| `upload_logs` → `error/client/badParam` with "unknown parser" | Wrong `parser:` header name, or putFile hadn't replicated yet (retry after a few seconds). |
| `power_query` returns rows but expected fields are null | Line format didn't match. Check: regex escaping (`\\d` not `\d`), delimiter mismatches, `halt: true` on an earlier format eating the line, `message`-as-field-name mistake. |
| `power_query` returns zero rows | `host_tag` isn't set (upload header `server-host` missing) or too short a `start_time` window. Widen to 30m. |
| Field X populated sometimes, null others | The format works for some variants and not others. Add a fragment format for the other shape, or widen the regex. |

## Isolating which format matched

Add a per-format constant attribute so the query can tell you which branch fired:

```js
formats: [
  { id: "tcp", attributes: { _matched: "tcp" }, format: "... proto=TCP ...", halt: true },
  { id: "udp", attributes: { _matched: "udp" }, format: "... proto=UDP ...", halt: true }
]
```

Then query `| columns _matched, ...` to see which format each line hit. Remove the `_matched` tags once the parser stabilizes.

## Cleanup

```python
# Throwaway test: delete
c.put_file(f"/logParsers/{PARSER_NAME}", delete=True)

# Keep and rename
content = c.get_file(f"/logParsers/{PARSER_NAME}")["content"]
c.put_file("/logParsers/FortiGate_CEF", content=content)
c.put_file(f"/logParsers/{PARSER_NAME}", delete=True)
```

Ask the user before promoting a `claude_test_` parser to a canonical name — it's their tenant.
