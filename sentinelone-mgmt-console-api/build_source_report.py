"""
Source-agnostic collector for the CTO report pipeline.

Given a data-source name and a window, runs the queries the renderers
need and writes:

    reports/<slug>_<window>/data.json

Then:

    python render_charts.py --data reports/<slug>_<window>/data.json
    python build_docx.py    --data reports/<slug>_<window>/data.json
    python build_pptx.py    --data reports/<slug>_<window>/data.json

Design notes:

- **Preflight**. Before running anything, enumerates `dataSource.name`
  over the last 24h and fuzzy-matches the requested source. If it is
  not ingesting, prints the closest candidates and exits with code 2,
  so downstream agents stop instead of chasing 0-row widening attempts.
- **No `timebucket`**. The LRQ engine does not expose `timebucket` and
  returns HTTP 500 "undefined field 'timebucket'". All time-series
  buckets are built client-side, one PQ per slice.
- **Schema discovery via LOG queryType**. Delegates to
  inspect_source.discover_schema(), which runs a LRQ LOG query and
  reads every attribute the parser actually emits from
  matches[].values. No hardcoded field list. Each attribute is
  classified (principal_user / principal_host / principal_ip /
  action / temporal / network / file / process / grouping_candidate /
  other) so renderers can gate sections on class, not name.
- **Principal fallback**. prim_key = best principal_user ->
  principal_host -> principal_ip -> None, picked from whatever is
  populated in the sample. Collector uses the chosen key as the
  grouping key for per_user_mix_top10; renderer labels the axis.
- **One unified per-principal query**. per_user_mix_top10 is grouped
  by (prim_key, action_key), 60 rows; renderer derives by_user /
  block-by-user / bypass-by-user from it without re-querying.

Run from the skill root with `config.json` filled in.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "scripts")
from s1_client import S1Client
from pq import run_pq, list_data_sources, PQError  # type: ignore
from inspect_source import discover_schema, pick_keys  # type: ignore


# ---- window parsing -------------------------------------------------------

# <= 48h => hourly slices (up to 48 slices); otherwise daily slices.
# Explicit aliases for common windows.
WINDOW_ALIASES: Dict[str, Tuple[int, str]] = {
    "1h": (1, "hour"),
    "6h": (6, "hour"),
    "12h": (12, "hour"),
    "24h": (24, "hour"),
    "48h": (48, "hour"),
    "3d": (24 * 3, "day"),
    "7d": (24 * 7, "day"),
    "14d": (24 * 14, "day"),
    "30d": (24 * 30, "day"),
}


def parse_window(s: str) -> Tuple[int, str]:
    if s in WINDOW_ALIASES:
        return WINDOW_ALIASES[s]
    m = re.fullmatch(r"(\d+)([hdw])", s.strip().lower())
    if not m:
        raise ValueError(
            f"bad --window '{s}'. Use 24h, 7d, 30d, or <N>h / <N>d.")
    n = int(m.group(1))
    unit = m.group(2)
    hours = {"h": n, "d": 24 * n, "w": 24 * 7 * n}[unit]
    slice_kind = "hour" if hours <= 48 else "day"
    return hours, slice_kind


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s or "source"


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- PQ wrappers ----------------------------------------------------------

def _run(client, name: str, query: str,
         hours: Optional[int] = None,
         start: Optional[datetime] = None,
         end: Optional[datetime] = None,
         poll_deadline_s: int = 120) -> Dict[str, Any]:
    try:
        kwargs: Dict[str, Any] = {"poll_deadline_s": poll_deadline_s,
                                  "poll_interval_s": 1.5}
        if start and end:
            kwargs["start_time"] = iso(start)
            kwargs["end_time"] = iso(end)
        else:
            kwargs["hours"] = hours
        res = run_pq(client, query, **kwargs)
        return {
            "matchCount": res["matchCount"],
            "row_count": res["row_count"],
            "columns": res["columns"],
            "rows": res["rows"],
        }
    except PQError as e:
        print(f"  [{name}] FAILED: {e}", file=sys.stderr)
        return {"error": str(e), "rows": [], "row_count": 0,
                "matchCount": 0, "columns": []}


# ---- preflight: is this source on this tenant? ----------------------------

def find_matching_source(client, requested: str
                         ) -> Tuple[Optional[str], List[str]]:
    """Return (exact_or_canonical_name, candidate_list).

    Exact match wins. Case-insensitive match is accepted. If nothing
    matches, we return (None, <shortlist of candidates>) so the caller
    can prompt the user with real names from this tenant.
    """
    try:
        sources = list_data_sources(client, hours=24, limit=200)
    except PQError as e:
        print(f"preflight FAILED: {e}", file=sys.stderr)
        return None, []
    names: List[str] = []
    for r in sources:
        n = r.get("dataSource.name")
        if n:
            names.append(n)
    # exact
    if requested in names:
        return requested, names
    # case-insensitive exact
    lc = requested.lower()
    ci = [n for n in names if n.lower() == lc]
    if len(ci) == 1:
        return ci[0], names
    # substring
    sub = [n for n in names if lc in n.lower()]
    if len(sub) == 1:
        return sub[0], names
    # alphanumeric-normalised comparison, e.g. "PromptSecurity" <-> "Prompt Security"
    norm = re.sub(r"[^a-z0-9]", "", lc)
    nm = [n for n in names if re.sub(r"[^a-z0-9]", "", n.lower()) == norm]
    if len(nm) == 1:
        return nm[0], names
    return None, sub or names[:30]


# ---- schema discovery (delegates to scripts/inspect_source.py) ------------
#
# Previous versions of this file ran a hardcoded list of probe queries
# (action, user, src.hostname, src.ip.address, event.type) via
# `| group n=count() by <field>`. That only works for sources that
# happen to emit those exact field names. We now delegate to
# inspect_source.discover_schema(), which projects a broad universal
# attribute list in one query and classifies whatever comes back.
# Downstream callers read `prim_key` / `action_key` off the returned
# schema rather than assuming names.


def _dims_from_schema(schema: Dict[str, Any]) -> Dict[str, bool]:
    """Legacy boolean-dims view, kept in data.json for renderers that
    gate sections on known classes without caring about exact names."""
    present_classes = {
        m["classified_as"] for m in schema.get("fields", {}).values()
    }
    return {
        "action":         "action" in present_classes,
        "principal_user": "principal_user" in present_classes,
        "principal_host": "principal_host" in present_classes,
        "principal_ip":   "principal_ip" in present_classes,
        "temporal":       "temporal" in present_classes,
        "network":        "network" in present_classes,
        "file":           "file" in present_classes,
        "process":        "process" in present_classes,
    }


# ---- client-side timeline slicing -----------------------------------------

def slice_timeline(client, base: str,
                   start: datetime, end: datetime,
                   slice_kind: str,
                   action_key: Optional[str]) -> List[Dict[str, Any]]:
    if slice_kind == "hour":
        step = timedelta(hours=1)
        fmt = "%Y-%m-%d %H:00"
    elif slice_kind == "day":
        step = timedelta(days=1)
        fmt = "%Y-%m-%d"
    else:
        step = timedelta(weeks=1)
        fmt = "%Y-%m-%d"

    ranges: List[Tuple[datetime, datetime]] = []
    t = start
    while t < end:
        ranges.append((t, min(t + step, end)))
        t += step

    def one(rng: Tuple[datetime, datetime]) -> Dict[str, Any]:
        s, e = rng
        label = s.strftime(fmt)
        if action_key:
            q = f"{base} | group n=count() by {action_key} | sort -n"
        else:
            q = f"{base} | group n=count()"
        r = _run(client, f"slice_{label}", q, start=s, end=e,
                 poll_deadline_s=90)
        by_action: Dict[str, int] = {}
        total = 0
        for row in r.get("rows") or []:
            if action_key:
                k = row.get(action_key)
                k = "None" if k in (None, "", "null") else str(k)
                n = int(row.get("n") or 0)
                by_action[k] = n
                total += n
            else:
                total = int(row.get("n") or 0)
        return {"date": label, "matchCount": total, "by_action": by_action}

    # 3-wide to respect the 3rps per-user cap
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        return list(ex.map(one, ranges))


# ---- summary computation --------------------------------------------------

def compute_summary(action_key: Optional[str],
                    by_action_rows: List[Dict[str, Any]],
                    mix_rows: List[Dict[str, Any]],
                    prim_key: Optional[str],
                    tenant_rows: List[Dict[str, Any]],
                    source: str) -> Dict[str, Any]:
    by_action: Dict[str, int] = {}
    total = 0
    for r in by_action_rows:
        if action_key:
            k = r.get(action_key)
            k = "None" if k in (None, "", "null") else str(k)
        else:
            k = "events"
        n = int(r.get("n") or 0)
        by_action[k] = n
        total += n

    block = int(by_action.get("block", 0))
    modify = int(by_action.get("modify", 0))
    bypass_ = int(by_action.get("bypass", 0))
    block_pct = 100 * block / total if total else 0.0
    bypass_pct = 100 * bypass_ / total if total else 0.0
    intervention_pct = 100 * (block + modify) / total if total else 0.0

    # Renderers (build_docx / build_pptx) expect top_user to be a
    # row-shaped dict: {<prim_key>: <value>, 'n': <count>}. That way
    # `tu.get(p_key)` and `tu['n']` both work without branching on
    # which prim_key the source uses.
    top_user: Optional[Dict[str, Any]] = None
    top_share = 0.0
    if prim_key and mix_rows:
        agg: Dict[Any, int] = defaultdict(int)
        for r in mix_rows:
            v = r.get(prim_key)
            if v in (None, "", "null"):
                continue
            agg[v] += int(r.get("n") or 0)
        ranked = sorted(agg.items(), key=lambda kv: -kv[1])
        if ranked:
            top_user = {prim_key: str(ranked[0][0]), "n": ranked[0][1]}
            top_share = 100 * ranked[0][1] / total if total else 0.0

    rank_24h: Optional[int] = None
    for i, r in enumerate(tenant_rows):
        if r.get("dataSource.name") == source:
            rank_24h = i + 1
            break

    return {
        "total": total,
        "by_action": by_action,
        "block": block,
        "modify": modify,
        "bypass": bypass_,
        "block_pct": round(block_pct, 2),
        "bypass_pct": round(bypass_pct, 2),
        "intervention_pct": round(intervention_pct, 2),
        "prim_key": prim_key,
        "top_principal_key": prim_key,
        "top_user": top_user,
        "top_share": round(top_share, 2),
        "rank_24h": rank_24h,
    }


# ---- main -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=(
        "Collect CTO-report data for any SDL data source. Writes "
        "reports/<slug>_<window>/data.json."))
    ap.add_argument("--source", required=True,
                    help="dataSource.name value, e.g. 'Prompt Security'")
    ap.add_argument("--window", default="7d",
                    help="1h, 24h, 7d, 30d, or <N>h / <N>d. Default: 7d.")
    ap.add_argument("--out-dir", default="reports",
                    help="Base directory for output. Default: reports/")
    ap.add_argument("--skip-preflight", action="store_true",
                    help=("Skip the 24h data-source existence check. "
                          "Only use when you know the source is correct "
                          "but inactive in the last 24h."))
    args = ap.parse_args()

    client = S1Client()
    try:
        hours, slice_kind = parse_window(args.window)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=hours)

    # ---- preflight --------------------------------------------------------
    source = args.source
    if not args.skip_preflight:
        print(f"Preflight: is '{args.source}' ingesting on this tenant?")
        matched, candidates = find_matching_source(client, args.source)
        if matched is None:
            print(f"\nERROR: '{args.source}' not found in last 24h.",
                  file=sys.stderr)
            if candidates:
                print("Closest candidates on this tenant:", file=sys.stderr)
                for c in candidates[:15]:
                    print(f"  - {c}", file=sys.stderr)
            else:
                print("No data sources returned. Check credentials or "
                      "pass --skip-preflight.", file=sys.stderr)
            print("\nRe-run with one of those names, or pass "
                  "--skip-preflight if you're sure the source is correct.",
                  file=sys.stderr)
            return 2
        if matched != args.source:
            print(f"  resolved '{args.source}' -> '{matched}'")
        source = matched

    slug = slugify(source)
    base = (f"dataSource.name = '{source}' "
            f"(tag != 'logVolume' OR !(tag = *))")
    out_dir = Path(args.out_dir) / f"{slug}_{args.window}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Tenant : {client.base_url}")
    print(f"Source : {source}")
    print(f"Window : {args.window}  ({start.isoformat()} to {end.isoformat()})")
    print(f"Slicing: {slice_kind}")
    print(f"Out    : {out_dir}/")
    print()

    # ---- schema discovery -------------------------------------------------
    # Pass the same tag-filter the core queries use, otherwise metric
    # events (tag='logVolume', emitted by many parsers) dominate the
    # sample and the classifier picks `severity` as action_key because
    # the real event attributes were crowded out.
    print("Discovering schema (LOG queryType, all emitted attributes)...")
    schema = discover_schema(
        client, source, hours=hours, sample=150,
        extra_filter="(tag != 'logVolume' OR !(tag = *))",
    )
    if schema.get("error") and schema.get("n_sampled", 0) == 0:
        print(f"\nERROR: schema discovery returned no events: "
              f"{schema['error']}. The source is on the tenant but the "
              f"window contains no data. Try a wider --window.",
              file=sys.stderr)
        return 3

    n_present = schema.get("n_present", 0)
    est = schema.get("estimated_match", 0)
    n_sampled = schema.get("n_sampled", 0)
    print(f"  sampled {n_sampled} events (of ~{est} in window), "
          f"{n_present} distinct attributes observed")
    prim_key, action_key = pick_keys(schema)
    print(f"  -> prim_key={prim_key}  action_key={action_key}")

    # Preview the top populated non-framework fields so the console
    # shows operators what the source actually carries.
    interesting = [
        (name, meta) for name, meta in schema["fields"].items()
        if meta["classified_as"] not in ("other", "temporal")
    ]
    interesting.sort(key=lambda kv: (-kv[1]["populated_frac"], kv[0]))
    for name, meta in interesting[:8]:
        pct = int(meta["populated_frac"] * 100)
        samp = ", ".join(meta["samples"][:1])[:60]
        print(f"  {meta['classified_as']:17s} {name:30s} "
              f"pop={pct:3d}%  e.g. {samp}")

    dims = _dims_from_schema(schema)

    # ---- core queries -----------------------------------------------------
    print("\nRunning core queries...")
    jobs: Dict[str, str] = {}
    if action_key:
        jobs["by_action"] = f"{base} | group n=count() by {action_key} | sort -n"
    else:
        jobs["by_action"] = f"{base} | group n=count()"

    if prim_key:
        group_cols = prim_key + (f", {action_key}" if action_key else "")
        jobs["per_user_mix_top10"] = (
            f"{base} | group n=count() by {group_cols} "
            f"| sort -n | limit 60")

    jobs["tenant_sources_24h"] = (
        "dataSource.name = * | group ct = count() by dataSource.name "
        "| sort -ct | limit 30")

    queries: Dict[str, Any] = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for name, q in jobs.items():
            h = 24 if name == "tenant_sources_24h" else hours
            futs[ex.submit(_run, client, name, q, h, None, None, 180)] = name
        for f in cf.as_completed(futs):
            name = futs[f]
            queries[name] = f.result()
            n = queries[name].get("row_count", "?")
            print(f"  {name}: {n} rows")

    # ---- timeline (client-side slicing, never timebucket) -----------------
    print(f"\nBuilding timeline ({slice_kind} slices)...")
    timeline_rows = slice_timeline(client, base, start, end, slice_kind,
                                   action_key)
    queries["daily_by_action"] = {
        "slice_kind": slice_kind,
        "rows": timeline_rows,
    }
    total_ts = sum(r["matchCount"] for r in timeline_rows)
    print(f"  {len(timeline_rows)} slices, {total_ts:,} total events")

    # ---- summary ----------------------------------------------------------
    summary = compute_summary(
        action_key=action_key,
        by_action_rows=queries["by_action"].get("rows", []),
        mix_rows=queries.get("per_user_mix_top10", {}).get("rows", []),
        prim_key=prim_key,
        tenant_rows=queries["tenant_sources_24h"].get("rows", []),
        source=source,
    )
    summary["action_key"] = action_key

    # ---- assemble ---------------------------------------------------------
    data = {
        "source": source,
        "slug": slug,
        "window_label": args.window,
        "days": round(hours / 24, 4),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "collected_at": end.isoformat(),
        "base_filter": base,
        "dims": dims,
        "discovered_schema": schema,
        "strategy": {
            "window_label": args.window,
            "slice_kind": slice_kind,
            "n_slices": len(timeline_rows),
        },
        "summary": summary,
        "queries": queries,
    }

    outfile = out_dir / "data.json"
    outfile.write_text(json.dumps(data, indent=2, default=str))
    print(f"\nwrote {outfile}  ({outfile.stat().st_size:,} bytes)")
    print(f"total events (by_action):   {summary['total']:,}")
    if summary.get("top_user"):
        print(f"top {prim_key}: {summary['top_user'].get(prim_key)} "
              f"({summary['top_share']:.1f}%)")
    if summary.get("rank_24h"):
        print(f"tenant rank (24h): #{summary['rank_24h']}")

    print()
    print("Next steps:")
    print(f"  python render_charts.py --data {outfile}")
    print(f"  python build_docx.py    --data {outfile}")
    print(f"  python build_pptx.py    --data {outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
