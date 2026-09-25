"""Any ticket system with a CSV export -> normalized tickets.csv, driven by a small column map.

Most service desks (HaloPSA, SysAid, Zoho Desk, TOPdesk, osTicket, GLPI, Ivanti...) can export a report to
CSV. Point this at the export and a JSON map naming which column holds which field:

    python adapters/csv_mapped.py export.csv --map mappings/example.json --out tickets.csv --tz America/New_York

Map format (see mappings/example.json): "columns" maps schema fields to export column names ("created",
"subject" and "requester_email" are required); "datetime_format" is a strptime pattern, or omit it for
ISO-style timestamps; "source_timezone" is the zone the export's times are in (default UTC). "status_map"
optionally renames status values, and "true_values" lists what counts as yes in the overdue columns.
"""
import argparse, csv, json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from _common import SCHEMA, strip_html, local, parse_dt, zone, write

REQUIRED = ("created", "subject", "requester_email")


def convert(value, fmt, src_tz, tz):
    value = (value or "").strip()
    if not value:
        return ""
    if fmt:
        try:
            return local(datetime.strptime(value, fmt).replace(tzinfo=zone(src_tz)), tz)
        except ValueError:
            return ""
    return local(parse_dt(value, src_tz), tz)


def parse(path, mapping, tz="UTC"):
    cols = mapping.get("columns") or {}
    missing = [k for k in REQUIRED if k not in cols]
    if missing:
        sys.exit(f"map is missing required columns: {missing}")
    fmt, src = mapping.get("datetime_format"), mapping.get("source_timezone", "UTC")
    status_map = mapping.get("status_map") or {}
    yes = {v.lower() for v in mapping.get("true_values") or ["true", "yes", "y", "1"]}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        absent = [c for c in cols.values() if c not in (reader.fieldnames or [])]
        if absent:
            sys.exit(f"export has no column(s) {absent}; columns found: {reader.fieldnames}")
        rows = []
        for i, r in enumerate(reader, 1):
            get = lambda k: (r.get(cols[k]) or "").strip() if k in cols else ""
            row = {k: get(k) for k in SCHEMA}
            row["system"] = mapping.get("system", "CSV")
            row["id"] = row["id"] or str(i)
            for k in ("created", "first_responded", "resolved"):
                row[k] = convert(row[k], fmt, src, tz)
            row["status"] = status_map.get(row["status"], row["status"])
            row["requester_email"] = row["requester_email"].lower()
            row["description"] = strip_html(row["description"])
            for k in ("is_overdue", "is_fr_overdue"):
                row[k] = ("true" if row[k].lower() in yes else "false") if row[k] else ""
            if row["created"]:
                rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv"); ap.add_argument("--map", required=True); ap.add_argument("--out", default="tickets.csv")
    ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.csv, json.load(open(a.map, encoding="utf-8")), a.tz), a.out)


if __name__ == "__main__":
    main()
