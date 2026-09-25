"""Autotask PSA (REST) export -> normalized tickets.csv.

Input folder:
  tickets*.json    pages from POST /V1.0/Tickets/query (each has an `items` array)
  resources.json   optional, POST /V1.0/Resources/query  -> technician names
  contacts.json    optional, POST /V1.0/Contacts/query   -> requester names and emails
  fields.json      optional, GET  /V1.0/Tickets/entityInformation/fields -> labels for status and queue picklists
Without the optional files the ids are written as-is.

    python adapters/autotask.py ./autotask-export --out tickets.csv --tz America/New_York
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, flag, json_pages, write


def items(folder, name):
    p = os.path.join(folder, name)
    if not os.path.exists(p):
        return []
    d = json.load(open(p, encoding="utf-8"))
    return d.get("items", d) if isinstance(d, dict) else d


def picklists(folder):
    """{field name: {value: label}} from the entityInformation/fields response."""
    p = os.path.join(folder, "fields.json")
    if not os.path.exists(p):
        return {}
    out = {}
    for f in json.load(open(p, encoding="utf-8")).get("fields") or []:
        if f.get("isPickList"):
            out[f["name"]] = {str(v.get("value")): v.get("label", "") for v in f.get("picklistValues") or []}
    return out


def parse(folder, tz="UTC"):
    people = lambda x: f'{x.get("firstName") or ""} {x.get("lastName") or ""}'.strip()
    resources = {r["id"]: people(r) for r in items(folder, "resources.json") if "id" in r}
    contacts = {c["id"]: c for c in items(folder, "contacts.json") if "id" in c}
    pick = picklists(folder)
    label = lambda field, v: pick.get(field, {}).get(str(v), "" if v is None else str(v))
    rows = {}
    for _, data in json_pages(folder, "tickets*.json"):
        for t in (data.get("items") if isinstance(data, dict) else data) or []:
            if t.get("id") is None:
                continue
            c = contacts.get(t.get("contactID")) or {}
            met = flag(t.get("serviceLevelAgreementHasBeenMet"))
            rows[t["id"]] = {
                "system": "Autotask", "id": t.get("ticketNumber") or t["id"], "subject": (t.get("title") or "").strip(),
                "created": from_iso(t.get("createDate"), tz), "first_responded": from_iso(t.get("firstResponseDateTime"), tz),
                "resolved": from_iso(t.get("resolvedDateTime") or t.get("completedDate"), tz),
                "status": label("status", t.get("status")), "group": label("queueID", t.get("queueID")),
                "technician": resources.get(t.get("assignedResourceID"), str(t.get("assignedResourceID") or "")),
                "requester": people(c), "requester_email": (c.get("emailAddress") or "").lower(),
                "description": strip_html(t.get("description")),
                "is_overdue": {"true": "false", "false": "true"}.get(met, ""), "is_fr_overdue": ""}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.folder, a.tz), a.out)


if __name__ == "__main__":
    main()
