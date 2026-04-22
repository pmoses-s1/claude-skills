"""
Collect all aggregations for the Prompt Security 7-day CTO report.

Pulls every metric we need into a single JSON blob so the DOCX/PPTX
builders are pure rendering steps. Each query is an LRQ call via
scripts/pq.py. Runs in parallel where safe.

Writes: ps_report_data.json in the current directory.
"""
import sys
import json
import time
import concurrent.futures as cf
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")
from s1_client import S1Client
from pq import run_pq, PQError

BASE = "dataSource.name = 'Prompt Security' (tag != 'logVolume' OR !(tag = *))"
HOURS = 24 * 7  # 7 days


def q(client, name, pq_query, hours=HOURS, poll_deadline_s=180):
    t0 = time.time()
    try:
        res = run_pq(
            client, pq_query, hours=hours,
            poll_deadline_s=poll_deadline_s, poll_interval_s=1.5,
        )
        print(f"  [{name}] {res['row_count']} rows, "
              f"matchCount={res['matchCount']}, {time.time()-t0:.1f}s")
        return {
            "name": name, "query": pq_query,
            "matchCount": res["matchCount"],
            "row_count": res["row_count"],
            "columns": res["columns"],
            "rows": res["rows"],
            "elapsed_s": res["elapsed_s"],
        }
    except PQError as e:
        print(f"  [{name}] FAILED: {e}")
        return {"name": name, "query": pq_query, "error": str(e)}


def main():
    c = S1Client()
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=HOURS)
    print(f"Tenant:     {c.base_url}")
    print(f"Window:     {start.isoformat()} to {end.isoformat()}")
    print(f"Base filter: {BASE}")
    print()

    out = {
        "collected_at": end.isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "base_filter": BASE,
        "queries": {},
    }

    jobs = [
        # 1) Headline counts by action (log / block / modify / bypass / null)
        ("by_action",
         BASE + " | group n=count() by action | sort -n"),
        # 2) Top users overall
        ("by_user",
         BASE + " | group n=count() by user | sort -n | limit 25"),
        # 3) Users ranked by BLOCK volume (the interesting risk signal)
        ("by_user_blocks",
         BASE + " action = 'block' | group n=count() by user | sort -n | limit 20"),
        # 4) Users ranked by BYPASS count (the interesting "who's
        #    asserting override" signal)
        ("by_user_bypass",
         BASE + " action = 'bypass' | group n=count() by user | sort -n | limit 20"),
        # 5) Daily volume by action (stacked timeline source)
        ("daily_by_action",
         BASE + " | group n=count() by timebucket('1d'), action | sort timebucket"),
        # 6) Hourly volume overall (heatmap source)
        ("hourly_total",
         BASE + " | group n=count() by timebucket('1h') | sort timebucket"),
        # 7) Hourly volume by action
        ("hourly_by_action",
         BASE + " | group n=count() by timebucket('1h'), action | sort timebucket"),
        # 8) Block rate per user (top volume users only, ratio of block/total)
        ("per_user_mix_top10",
         BASE + " | group n=count() by user, action "
                " | sort -n | limit 60"),
    ]

    # Run the 7d queries in parallel (3-wide), one threadpool keeps us
    # under the per-user 3 rps cap while cutting total wall clock.
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        future_map = {
            ex.submit(q, c, name, query): name
            for name, query in jobs
        }
        for fut in cf.as_completed(future_map):
            name = future_map[fut]
            out["queries"][name] = fut.result()

    # enumerate data source presence alongside for context (shorter window)
    print("\nrunning enumerate_sources (24h context)...")
    out["queries"]["tenant_sources_24h"] = q(
        c, "tenant_sources_24h",
        "dataSource.name = * | group ct = count() by dataSource.name "
        "| sort -ct | limit 30",
        hours=24, poll_deadline_s=120,
    )

    outfile = Path("ps_report_data.json")
    outfile.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {outfile} ({outfile.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
