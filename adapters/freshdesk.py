"""Freshdesk API export -> normalized tickets.csv.

Input folder: page_*.json (responses of GET /api/v2/tickets?include=requester,stats&per_page=100&page=N),
plus agents.json and groups.json (GET /api/v2/agents, /api/v2/groups). Freshdesk agents carry their name
under `contact`, unlike Freshservice.

    python adapters/freshdesk.py ./fd-export --out tickets.csv --tz America/New_York
"""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, flag, write

STATUS = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}


def parse(folder, tz="UTC"):
    load = lambda n: json.load(open(os.path.join(folder, n), encoding="utf-8")) if os.path.exists(os.path.join(folder, n)) else []
    agents = {x["id"]: (x.get("contact") or {}).get("name", "") for x in load("agents.json")}
    groups = {x["id"]: x.get("name", "") for x in load("groups.json")}
    rows = {}
    for f in sorted(glob.glob(os.path.join(folder, "page_*.json"))):
        page = json.load(open(f, encoding="utf-8"))
        for t in (page.get("tickets", []) if isinstance(page, dict) else page):
            st, rq = t.get("stats") or {}, t.get("requester") or {}
            rows[t["id"]] = {
                "system": "Freshdesk", "id": f'#{t["id"]}', "subject": (t.get("subject") or "").strip(),
                "created": from_iso(t.get("created_at"), tz), "first_responded": from_iso(st.get("first_responded_at"), tz),
                "resolved": from_iso(st.get("resolved_at") or st.get("closed_at"), tz),
                "status": STATUS.get(t.get("status"), str(t.get("status"))), "group": groups.get(t.get("group_id"), ""),
                "technician": agents.get(t.get("responder_id"), ""),
                "requester": rq.get("name", ""), "requester_email": (rq.get("email") or "").lower(),
                "description": strip_html(t.get("description_text") or t.get("description")),
                "is_overdue": flag(t.get("is_escalated")), "is_fr_overdue": flag(t.get("fr_escalated"))}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.folder, a.tz), a.out)


if __name__ == "__main__":
    main()
