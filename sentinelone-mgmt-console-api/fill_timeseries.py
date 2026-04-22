"""
Fill the daily-by-action timeseries client-side. The server-side
`timebucket` function didn't exist on this engine; instead, launch one
1-day slice per day (7 slices) and do the aggregation per slice. Runs
in parallel bound to ~3 rps.
"""
import sys, json, concurrent.futures as cf, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, "scripts")
from s1_client import S1Client
from pq import run_pq

BASE = "dataSource.name = 'Prompt Security' (tag != 'logVolume' OR !(tag = *))"


def slice_day(client, start, end):
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    label = start.strftime("%Y-%m-%d")
    t0 = time.time()
    res = run_pq(
        client,
        BASE + " | group n=count() by action | sort -n",
        start_time=start_iso, end_time=end_iso,
        poll_deadline_s=90, poll_interval_s=1.5,
    )
    print(f"  [{label}] {res['row_count']} rows "
          f"match={res['matchCount']} in {time.time()-t0:.1f}s")
    return {
        "date": label,
        "start": start_iso, "end": end_iso,
        "matchCount": res["matchCount"],
        "by_action": {str(r.get("action")): r.get("n")
                      for r in res["rows"]},
    }


def main():
    c = S1Client()
    end = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    days = [(end - timedelta(days=i+1), end - timedelta(days=i))
            for i in range(7)]
    days = list(reversed(days))
    print(f"Tenant: {c.base_url}")
    for s, e in days:
        print(f"  slice {s.isoformat()} -> {e.isoformat()}")

    results = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(slice_day, c, s, e) for s, e in days]
        for fut in cf.as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x: x["date"])

    data = json.loads(Path("ps_report_data.json").read_text())
    data["queries"]["daily_by_action"] = {
        "name": "daily_by_action",
        "method": "client-side-slicing",
        "rows": results,
    }
    Path("ps_report_data.json").write_text(json.dumps(data, indent=2,
                                                      default=str))
    print(f"\nwrote {len(results)} daily slices into ps_report_data.json")


if __name__ == "__main__":
    main()
