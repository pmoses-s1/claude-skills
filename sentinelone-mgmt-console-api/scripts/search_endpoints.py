"""
Search the endpoint index for matching operations.

Usage:
    python scripts/search_endpoints.py "threats"
    python scripts/search_endpoints.py --tag "Agents" --method GET
    python scripts/search_endpoints.py --path "/web/api/v2.1/threats"

Prints a compact table so Claude can pick the right endpoint without
loading the full spec.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "references" / "endpoint_index.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="", help="free-text match against summary/path/operationId")
    ap.add_argument("--tag", help="exact tag filter (e.g. Threats)")
    ap.add_argument("--method", help="GET/POST/PUT/DELETE")
    ap.add_argument("--path", help="substring match on path")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    data = json.loads(INDEX.read_text())
    q = args.query.lower()
    method = (args.method or "").upper()

    def matches(e):
        if args.tag and e["tag"] != args.tag:
            return False
        if method and e["method"] != method:
            return False
        if args.path and args.path.lower() not in e["path"].lower():
            return False
        if q:
            hay = " ".join([e["path"], e["summary"] or "", e["operationId"] or "", e["tag"]]).lower()
            if q not in hay:
                return False
        return True

    hits = [e for e in data if matches(e)]
    print(f"{len(hits)} match(es)" + (f" — showing first {args.limit}" if len(hits) > args.limit else ""))
    for e in hits[: args.limit]:
        print(f"  {e['method']:6} {e['path']:60} [{e['tag']}] — {e['summary']}")


if __name__ == "__main__":
    main()
