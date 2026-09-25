"""ServiceDesk Plus (Cloud, API v3) export -> normalized tickets.csv.

Input folder: JSON pages from GET /api/v3/requests with input_data list_info (row_count 100, start_index N,
optionally search_criteria on created_time windows so each window stays under the page cap). Duplicate
ids across pages are merged, preferring the record that carries a description.

    python adapters/servicedeskplus.py ./sdp-export --out tickets.csv --tz America/New_York
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_epoch_ms, json_pages, write

name = lambda o: (o or {}).get("name") or "" if isinstance(o, dict) else ""
epoch = lambda v: v.get("value") if isinstance(v, dict) else None


def parse(folder, tz="UTC"):
    rows = {}
    for _, data in json_pages(folder):
        for r in (data.get("data", data).get("requests") or []):
            rid = r.get("id")
            if not rid or (rid in rows and rows[rid]["_desc"] and "description" not in r):
                continue
            rq, tech = r.get("requester") or {}, r.get("technician") or {}
            rows[rid] = {
                "system": "ServiceDeskPlus", "id": r.get("display_id") or rid, "subject": (r.get("subject") or "").strip(),
                "created": from_epoch_ms(epoch(r.get("created_time")), tz), "first_responded": from_epoch_ms(epoch(r.get("responded_time")), tz),
                "resolved": from_epoch_ms(epoch(r.get("resolved_time")) or epoch(r.get("completed_time")), tz),
                "status": name(r.get("status")), "technician": name(tech), "group": name(r.get("group")),
                "requester": name(rq), "requester_email": (rq.get("email_id") or "").lower() if isinstance(rq, dict) else "",
                "description": strip_html(r.get("description")), "is_overdue": str(r.get("is_overdue", "")).lower(),
                "is_fr_overdue": str(r.get("is_first_response_overdue", "")).lower(), "_desc": "description" in r}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.folder, a.tz), a.out)


if __name__ == "__main__":
    main()
