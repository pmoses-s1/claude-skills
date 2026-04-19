"""
SentinelOne Management Console API client.

Loads credentials (in priority order):
  1. Environment variables: S1_BASE_URL, S1_API_TOKEN
  2. <skill>/config.json

Usage:
    from s1_client import S1Client
    c = S1Client()
    # list first page
    r = c.get("/web/api/v2.1/agents", params={"limit": 50})
    # paginate everything (cursor-based)
    for page in c.paginate("/web/api/v2.1/threats", params={"limit": 200}):
        for item in page["data"]:
            ...

All paths are relative to base_url. The client injects the Authorization
header automatically. Errors surface as S1APIError with status + body.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import requests


SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"


class S1APIError(RuntimeError):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


def _load_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"config.json is not valid JSON: {e}")
    # env wins
    if os.environ.get("S1_BASE_URL"):
        cfg["base_url"] = os.environ["S1_BASE_URL"]
    if os.environ.get("S1_API_TOKEN"):
        cfg["api_token"] = os.environ["S1_API_TOKEN"]
    if os.environ.get("S1_VERIFY_TLS"):
        cfg["verify_tls"] = os.environ["S1_VERIFY_TLS"].lower() not in ("0", "false", "no")
    return cfg


class S1Client:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_tls: Optional[bool] = None,
        timeout: Optional[float] = None,
    ):
        cfg = _load_config()
        self.base_url = (base_url or cfg.get("base_url") or "").rstrip("/")
        self.api_token = api_token or cfg.get("api_token") or ""
        self.verify_tls = cfg.get("verify_tls", True) if verify_tls is None else verify_tls
        self.timeout = timeout or cfg.get("timeout_seconds", 30)

        if not self.base_url or "REPLACE-ME" in self.base_url:
            raise RuntimeError(
                "S1 base_url is not set. Edit config.json or export S1_BASE_URL."
            )
        if not self.api_token or "REPLACE" in self.api_token:
            raise RuntimeError(
                "S1 api_token is not set. Edit config.json or export S1_API_TOKEN."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"ApiToken {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------ core
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
                        return resp.json()
                    except ValueError:
                        return {"_raw": resp.text}
                return {}
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


if __name__ == "__main__":
    # Smoke test — lists accounts
    c = S1Client()
    r = c.get("/web/api/v2.1/accounts", params={"limit": 5})
    print(json.dumps(r, indent=2)[:2000])
