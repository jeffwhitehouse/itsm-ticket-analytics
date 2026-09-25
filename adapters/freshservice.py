"""Freshservice API export -> normalized tickets.csv.

Input folder: page_*.json (responses of GET /api/v2/tickets?include=requester,stats&per_page=100&page=N),
plus agents.json and groups.json (GET /api/v2/agents, /api/v2/groups). How you fetch them is up to you;
never commit the exports.

    python adapters/freshservice.py ./fs-export --out tickets.csv --tz America/New_York [--groups "Service Desk,Assets"]
"""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, write

STATUS = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed", 6: "Cancelled", 7: "Rejected", 8: "Pending Approval", 9: "Pending Vendor",
          10: "Pending Change", 11: "Requester Responded", 12: "Re-Open", 13: "Pending Third Party", 14: "Work-in-Progress"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    ap.add_argument("--groups", help="comma-separated group names to keep (a shared instance often serves several divisions)")
    a = ap.parse_args()
    load = lambda n: json.load(open(os.path.join(a.folder, n), encoding="utf-8")) if os.path.exists(os.path.join(a.folder, n)) else []
    agents = {x["id"]: f'{x.get("first_name") or ""} {x.get("last_name") or ""}'.strip() for x in load("agents.json")}
    groups = {x["id"]: x["name"] for x in load("groups.json")}
    keep = {g.strip() for g in a.groups.split(",")} if a.groups else None
    rows = {}
    for f in sorted(glob.glob(os.path.join(a.folder, "page_*.json"))):
        for t in json.load(open(f, encoding="utf-8")).get("tickets", []):
            g = groups.get(t.get("group_id"), str(t.get("group_id") or ""))
            if keep and g not in keep:
                continue
            st, rq = t.get("stats") or {}, t.get("requester") or {}
            rows[t["id"]] = {
                "system": "Freshservice", "id": f'INC-{t["id"]}', "subject": (t.get("subject") or "").strip(),
                "created": from_iso(t.get("created_at"), a.tz), "first_responded": from_iso(st.get("first_responded_at"), a.tz),
                "resolved": from_iso(st.get("resolved_at") or st.get("closed_at"), a.tz),
                "status": STATUS.get(t.get("status"), str(t.get("status"))), "group": g,
                "technician": agents.get(t.get("responder_id"), str(t.get("responder_id") or "")),
                "requester": rq.get("name", ""), "requester_email": (rq.get("email") or "").lower(),
                "description": strip_html(t.get("description_text") or t.get("description")),
                "is_overdue": str(bool(t.get("is_escalated"))).lower(), "is_fr_overdue": str(bool(t.get("fr_escalated"))).lower()}
    write(rows.values(), a.out)


if __name__ == "__main__":
    main()
