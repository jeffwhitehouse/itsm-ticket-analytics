"""Zendesk Support export -> normalized tickets.csv.

Input folder: JSON pages from either
    GET /api/v2/incremental/tickets/cursor.json?start_time=0&include=users,groups,metric_sets
    GET /api/v2/tickets.json?include=users,groups,metric_sets
Sideloaded `users`, `groups` and `metric_sets` are collected across all pages. Pages from
GET /api/v2/ticket_metrics.json (a `ticket_metrics` array) can sit in the same folder instead of sideloading.

First response = created_at + reply_time_in_minutes.calendar; resolved = solved_at. Zendesk has no
per-ticket SLA breach flag outside the SLA policy objects, so the overdue columns are left empty.

    python adapters/zendesk.py ./zendesk-export --out tickets.csv --tz America/New_York
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, plus_minutes, json_pages, write


def parse(folder, tz="UTC"):
    tickets, users, groups, metrics = {}, {}, {}, {}
    for _, data in json_pages(folder):
        if not isinstance(data, dict):
            continue
        for t in data.get("tickets") or []:
            if t.get("id") is not None:
                tickets[t["id"]] = t
        users.update({u["id"]: u for u in data.get("users") or [] if "id" in u})
        groups.update({g["id"]: g.get("name", "") for g in data.get("groups") or [] if "id" in g})
        for m in (data.get("metric_sets") or []) + (data.get("ticket_metrics") or []):
            if m.get("ticket_id") is not None:
                metrics[m["ticket_id"]] = m
    rows = []
    for tid, t in tickets.items():
        m, rq = metrics.get(tid) or {}, users.get(t.get("requester_id")) or {}
        reply = (m.get("reply_time_in_minutes") or {}).get("calendar")
        rows.append({
            "system": "Zendesk", "id": f"#{tid}", "subject": (t.get("subject") or t.get("raw_subject") or "").strip(),
            "created": from_iso(t.get("created_at"), tz), "first_responded": plus_minutes(t.get("created_at"), reply, tz),
            "resolved": from_iso(m.get("solved_at"), tz),
            "status": (t.get("status") or "").capitalize(),
            "technician": (users.get(t.get("assignee_id")) or {}).get("name", ""), "group": groups.get(t.get("group_id"), ""),
            "requester": rq.get("name", ""), "requester_email": (rq.get("email") or "").lower(),
            "description": strip_html(t.get("description")), "is_overdue": "", "is_fr_overdue": ""})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.folder, a.tz), a.out)


if __name__ == "__main__":
    main()
