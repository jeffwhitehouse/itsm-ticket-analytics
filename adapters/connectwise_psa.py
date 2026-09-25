"""ConnectWise PSA (Manage) REST export -> normalized tickets.csv.

Input folder: JSON pages (each a JSON array) from
    GET /v4_6_release/apis/3.0/service/tickets?pageSize=1000&page=N
optionally with conditions=board/name="Help Desk" or a dateEntered window. Board is used as the group.
`initialDescription` is only returned by some versions/endpoints; when it is missing the description
stays empty and classification runs on the summary alone.

    python adapters/connectwise_psa.py ./cw-export --out tickets.csv --tz America/New_York [--boards "Help Desk,Projects"]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, flag, json_pages, write

ref = lambda o: (o.get("name") or o.get("identifier") or "") if isinstance(o, dict) else ""


def parse(folder, tz="UTC", boards=None):
    keep = {b.strip() for b in boards.split(",")} if boards else None
    rows = {}
    for _, data in json_pages(folder):
        for t in data if isinstance(data, list) else (data.get("tickets") or []):
            if t.get("id") is None or (keep and ref(t.get("board")) not in keep):
                continue
            entered = t.get("dateEntered") or (t.get("_info") or {}).get("dateEntered")
            in_sla = flag(t.get("isInSla"))
            rows[t["id"]] = {
                "system": "ConnectWisePSA", "id": f'#{t["id"]}', "subject": (t.get("summary") or "").strip(),
                "created": from_iso(entered, tz), "first_responded": from_iso(t.get("dateResponded"), tz),
                "resolved": from_iso(t.get("dateResolved") or t.get("closedDate"), tz),
                "status": ref(t.get("status")), "technician": ref(t.get("owner")), "group": ref(t.get("board")),
                "requester": t.get("contactName") or ref(t.get("contact")), "requester_email": (t.get("contactEmailAddress") or "").lower(),
                "description": strip_html(t.get("initialDescription")),
                "is_overdue": {"true": "false", "false": "true"}.get(in_sla, ""), "is_fr_overdue": ""}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    ap.add_argument("--boards", help="comma-separated board names to keep")
    a = ap.parse_args()
    write(parse(a.folder, a.tz, a.boards), a.out)


if __name__ == "__main__":
    main()
