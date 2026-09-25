"""ServiceNow (Table API) export -> normalized tickets.csv.

Input folder: JSON pages from
    GET /api/now/table/incident?sysparm_display_value=all&sysparm_limit=1000&sysparm_offset=N
        &sysparm_fields=number,short_description,description,opened_at,resolved_at,closed_at,state,
                        assigned_to,assignment_group,caller_id,caller_id.email,made_sla
(`sc_req_item` or any other task table works the same way). With sysparm_display_value=all every field is
{"display_value": ..., "value": ...}; `value` carries UTC timestamps and `display_value` carries names.
Plain sysparm_display_value=false/true exports are accepted too.

First response is not a field on the incident record (it lives in task_sla), so it is left empty.

    python adapters/servicenow.py ./snow-export --out tickets.csv --tz America/New_York
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, flag, json_pages, write


def val(rec, key):
    """Raw value of a field (UTC timestamps, sys_ids, booleans as strings)."""
    v = rec.get(key)
    return v.get("value", "") if isinstance(v, dict) else (v if v is not None else "")


def disp(rec, key):
    """Human-readable value of a field (names instead of sys_ids)."""
    v = rec.get(key)
    return (v.get("display_value") or "") if isinstance(v, dict) else (v if v is not None else "")


def parse(folder, tz="UTC"):
    rows = {}
    for _, data in json_pages(folder):
        for r in (data.get("result") if isinstance(data, dict) else data) or []:
            num = disp(r, "number") or val(r, "sys_id")
            if not num:
                continue
            made_sla = flag(val(r, "made_sla"))
            rows[num] = {
                "system": "ServiceNow", "id": num, "subject": str(disp(r, "short_description")).strip(),
                "created": from_iso(val(r, "opened_at") or val(r, "sys_created_on"), tz),
                "first_responded": "",
                "resolved": from_iso(val(r, "resolved_at") or val(r, "closed_at"), tz),
                "status": str(disp(r, "state")), "technician": str(disp(r, "assigned_to")), "group": str(disp(r, "assignment_group")),
                "requester": str(disp(r, "caller_id")), "requester_email": str(disp(r, "caller_id.email")).lower(),
                "description": strip_html(str(disp(r, "description"))),
                "is_overdue": {"true": "false", "false": "true"}.get(made_sla, ""), "is_fr_overdue": ""}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    a = ap.parse_args()
    write(parse(a.folder, a.tz), a.out)


if __name__ == "__main__":
    main()
