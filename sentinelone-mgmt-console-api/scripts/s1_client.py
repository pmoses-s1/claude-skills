"""
SentinelOne Management Console API client.

Loads credentials (in priority order):
  1. Environment variables: S1_BASE_URL, S1_API_TOKEN
  2. ~/.config/sentinelone/credentials.json
  3. <skill>/config.json  (last resort, not recommended)

Usage:
    from s1_client import S1Client
    c = S1Client()
    # list first page
    r = c.get("/web/api/v2.1/agents", params={"limit": 50})
    # paginate everything (cursor-based)
    for page in c.paginate("/web/api/v2.1/threats", params={"limit": 200}):
        for item in page["data"]:
            ...
    # fan out independent GETs in parallel (I/O-bound, thread-safe)
    results = c.get_many([
        ("/web/api/v2.1/accounts", {"limit": 1}),
        ("/web/api/v2.1/sites",    {"limit": 1}),
        ("/web/api/v2.1/groups",   {"limit": 1}),
    ])

All paths are relative to base_url. The client injects the Authorization
header automatically. Errors surface as S1APIError with status + body.

Performance:
- HTTP connection pooling via sized HTTPAdapter (pool_maxsize=32 default).
  Re-uses sockets across sequential and parallel calls — big win vs. the
  default 10 when fanning out.
- Retries on 429/5xx with exponential backoff, honoring Retry-After.
- Optional short-TTL response cache for rarely-changing read endpoints
  (accounts, sites, groups, system/info, users, rbac/roles, filters,
  service-users, tags). Disabled by default; enable with cache_ttl= in
  the constructor or env S1_CACHE_TTL.
- Parallel fan-out via get_many() using a ThreadPoolExecutor. Each thread
  shares the same pooled session; requests.Session is safe for concurrent
  use across threads when the adapter pool is sized >= worker count.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter


SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"
HOME_CREDS_PATH = Path.home() / ".config" / "sentinelone" / "credentials.json"

# Endpoints where caching is safe — they change rarely during a session.
# Prefix match, base_url stripped.
_CACHEABLE_PATHS = (
    "/web/api/v2.1/accounts",
    "/web/api/v2.1/sites",
    "/web/api/v2.1/groups",
    "/web/api/v2.1/system/info",
    "/web/api/v2.1/system/status",
    "/web/api/v2.1/users",
    "/web/api/v2.1/rbac/roles",
    "/web/api/v2.1/filters",
    "/web/api/v2.1/service-users",
    "/web/api/v2.1/tags",
)


class S1APIError(RuntimeError):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


def _load_config() -> Dict[str, Any]:
    # Layer 1: plugin-local config.json (lowest priority, not recommended)
    cfg: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"config.json is not valid JSON: {e}")

    # Layer 2: ~/.config/sentinelone/credentials.json
    # Works for GUI apps (Claude Desktop) that don't source ~/.zshenv.
    # Keys match env var names: S1_BASE_URL, S1_API_TOKEN, etc.
    if HOME_CREDS_PATH.exists():
        try:
            home_creds = json.loads(HOME_CREDS_PATH.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{HOME_CREDS_PATH} is not valid JSON: {e}")
        if home_creds.get("S1_BASE_URL"):
            cfg["base_url"] = home_creds["S1_BASE_URL"]
        if home_creds.get("S1_API_TOKEN"):
            cfg["api_token"] = home_creds["S1_API_TOKEN"]

    # Layer 3: environment variables (highest priority)
    if os.environ.get("S1_BASE_URL"):
        cfg["base_url"] = os.environ["S1_BASE_URL"]
    if os.environ.get("S1_API_TOKEN"):
        cfg["api_token"] = os.environ["S1_API_TOKEN"]
    if os.environ.get("S1_VERIFY_TLS"):
        cfg["verify_tls"] = os.environ["S1_VERIFY_TLS"].lower() not in ("0", "false", "no")
    if os.environ.get("S1_CACHE_TTL"):
        try:
            cfg["cache_ttl"] = float(os.environ["S1_CACHE_TTL"])
        except ValueError:
            pass
    return cfg


class S1Client:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_tls: Optional[bool] = None,
        timeout: Optional[float] = None,
        pool_maxsize: int = 32,
        cache_ttl: Optional[float] = None,
        token_kind: str = "default",
    ):
        """
        token_kind selects which token to read from ~/.config/sentinelone/credentials.json when no
        explicit `api_token` argument or S1_API_TOKEN env var is supplied.

          - "default"       → `api_token` (typically multi-scope).
                              Falls back to `api_token_single_scope` if
                              `api_token` is not configured.
          - "single_scope"  → `api_token_single_scope`. Required for
                              endpoints that reject multi-scope tokens
                              (e.g. /threat-intelligence/iocs). Falls back
                              to `api_token` if `api_token_single_scope`
                              is not configured — callers that strictly
                              need a single-scope token should check the
                              resulting `self.token_kind_effective`.

        Both tokens are optional in credentials.json: the skill works with
        either one alone, or both. Explicit `api_token=` or S1_API_TOKEN
        always wins over the config selection.
        """
        cfg = _load_config()
        self.base_url = (base_url or cfg.get("base_url") or "").rstrip("/")

        cfg_default = cfg.get("api_token") or ""
        cfg_single  = cfg.get("api_token_single_scope") or ""
        if token_kind == "single_scope":
            token_from_cfg = cfg_single or cfg_default
            self.token_kind_effective = (
                "single_scope" if cfg_single else
                ("default_fallback" if cfg_default else "none")
            )
        else:
            token_from_cfg = cfg_default or cfg_single
            self.token_kind_effective = (
                "default" if cfg_default else
                ("single_scope_fallback" if cfg_single else "none")
            )
        if api_token:
            self.token_kind_effective = "explicit"
        self.api_token = api_token or token_from_cfg
        self.verify_tls = cfg.get("verify_tls", True) if verify_tls is None else verify_tls
        self.timeout = timeout or cfg.get("timeout_seconds", 30)
        self.cache_ttl = cache_ttl if cache_ttl is not None else cfg.get("cache_ttl", 0)

        if not self.base_url or "REPLACE-ME" in self.base_url:
            raise RuntimeError(
                "S1 base_url is not set. Add S1_BASE_URL to ~/.config/sentinelone/credentials.json or export S1_BASE_URL."
            )
        if not self.api_token or "REPLACE" in self.api_token:
            raise RuntimeError(
                "S1 api_token is not set. Add S1_API_TOKEN to ~/.config/sentinelone/credentials.json or export S1_API_TOKEN."
            )

        # Session with pooled connection adapter — allows many parallel GETs
        # to share sockets to the same host without tearing them down.
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_maxsize,
            pool_maxsize=pool_maxsize,
            pool_block=False,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"ApiToken {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "s1-mgmt-api-skill/1.1 (+claude)",
        })

        # response cache — (path, sorted-params-tuple) -> (expires_ts, body)
        self._cache: Dict[Tuple[str, Tuple], Tuple[float, Dict[str, Any]]] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------ core
    def _cache_key(self, path: str, params: Optional[Dict[str, Any]]):
        return (path, tuple(sorted((params or {}).items())))

    def _is_cacheable(self, method: str, path: str) -> bool:
        if self.cache_ttl <= 0 or method != "GET":
            return False
        return any(path.startswith(p) for p in _CACHEABLE_PATHS)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Raw request. Retries on 429/5xx with exponential backoff."""
        if not path.startswith("/"):
            path = "/" + path

        if self._is_cacheable(method, path):
            key = self._cache_key(path, params)
            with self._cache_lock:
                entry = self._cache.get(key)
                if entry and entry[0] > time.time():
                    return entry[1]

        url = self.base_url + path
        attempt = 0
        while True:
            attempt += 1
            resp = self.session.request(
                method.upper(),
                url,
                params=params,
                json=json_body,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
            if resp.status_code < 400:
                if resp.content:
                    try:
                        body = resp.json()
                    except ValueError:
                        body = {"_raw": resp.text}
                else:
                    body = {}
                if self._is_cacheable(method, path):
                    key = self._cache_key(path, params)
                    with self._cache_lock:
                        self._cache[key] = (time.time() + self.cache_ttl, body)
                return body
            # retryable?
            retryable = resp.status_code == 429 or 500 <= resp.status_code < 600
            if retryable and attempt <= retries:
                wait = min(2 ** attempt, 30)
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = int(retry_after)
                time.sleep(wait)
                continue
            # error path
            try:
                body = resp.json()
                msg = (
                    (body.get("errors") or [{}])[0].get("detail")
                    or body.get("detail")
                    or resp.text[:500]
                )
            except Exception:
                body = resp.text
                msg = resp.text[:500]
            raise S1APIError(resp.status_code, msg, body)

    # ----------------------------------------------------------- convenience
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.request("GET", path, params=params)

    def post(self, path: str, json_body: Any = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.request("POST", path, params=params, json_body=json_body)

    def put(self, path: str, json_body: Any = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.request("PUT", path, params=params, json_body=json_body)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None, json_body: Any = None) -> Dict[str, Any]:
        return self.request("DELETE", path, params=params, json_body=json_body)

    # ------------------------------------------------------------ pagination
    def paginate(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Yields raw response pages for cursor-based list endpoints.
        Stops when `pagination.nextCursor` is missing/empty.
        """
        params = dict(params or {})
        pages = 0
        while True:
            resp = self.get(path, params=params)
            yield resp
            pages += 1
            if max_pages and pages >= max_pages:
                return
            pag = resp.get("pagination") or {}
            nxt = pag.get("nextCursor")
            if not nxt:
                return
            params["cursor"] = nxt

    def iter_items(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yields individual items across paginated responses."""
        count = 0
        for page in self.paginate(path, params=params):
            for item in page.get("data", []) or []:
                yield item
                count += 1
                if max_items and count >= max_items:
                    return

    # ------------------------------------------------------------ parallel fan-out
    def get_many(
        self,
        calls: Iterable[Tuple[str, Optional[Dict[str, Any]]]],
        max_workers: int = 8,
        on_error: Optional[Callable[[str, Dict[str, Any], Exception], None]] = None,
        retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Run many independent GETs in parallel. Each element of ``calls`` is
        ``(path, params)``. Returns one result dict per call, in input order:

            {"path": ..., "params": ..., "ok": bool, "status": int|None,
             "data": <body>|None, "error": str|None, "elapsed_ms": float}

        Thread-safe: the underlying ``requests.Session`` and pooled adapter
        are safe for concurrent use so long as pool_maxsize >= max_workers.
        """
        calls = list(calls)
        results: List[Optional[Dict[str, Any]]] = [None] * len(calls)

        def _one(i: int, path: str, params: Optional[Dict[str, Any]]):
            t0 = time.time()
            try:
                body = self.request("GET", path, params=params, retries=retries)
                return i, {
                    "path": path,
                    "params": params,
                    "ok": True,
                    "status": 200,
                    "data": body,
                    "error": None,
                    "elapsed_ms": (time.time() - t0) * 1000.0,
                }
            except S1APIError as e:
                out = {
                    "path": path,
                    "params": params,
                    "ok": False,
                    "status": e.status,
                    "data": None,
                    "error": str(e),
                    "elapsed_ms": (time.time() - t0) * 1000.0,
                }
                if on_error:
                    try:
                        on_error(path, params or {}, e)
                    except Exception:
                        pass
                return i, out
            except Exception as e:
                out = {
                    "path": path,
                    "params": params,
                    "ok": False,
                    "status": None,
                    "data": None,
                    "error": f"{type(e).__name__}: {e}",
                    "elapsed_ms": (time.time() - t0) * 1000.0,
                }
                if on_error:
                    try:
                        on_error(path, params or {}, e)
                    except Exception:
                        pass
                return i, out

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(_one, i, p, q) for i, (p, q) in enumerate(calls)]
            for f in as_completed(futs):
                i, r = f.result()
                results[i] = r
        return results  # type: ignore[return-value]

    # ------------------------------------------------------------ cache management
    def cache_clear(self) -> None:
        with self._cache_lock:
            self._cache.clear()


if __name__ == "__main__":
    # Smoke test — lists accounts, then fans out four parallel GETs
    c = S1Client(cache_ttl=60)
    r = c.get("/web/api/v2.1/accounts", params={"limit": 5})
    print("accounts page:", len(r.get("data", []) or []))
    parallel = c.get_many([
        ("/web/api/v2.1/accounts", {"limit": 1}),
        ("/web/api/v2.1/sites", {"limit": 1}),
        ("/web/api/v2.1/groups", {"limit": 1}),
        ("/web/api/v2.1/system/info", None),
    ])
    for row in parallel:
        print(f"  {row['status']} {row['elapsed_ms']:.0f}ms {row['path']}")
