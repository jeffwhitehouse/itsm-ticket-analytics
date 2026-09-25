"""Jira Service Management (Jira Cloud REST) export -> normalized tickets.csv.

Input folder: JSON pages from GET /rest/api/3/search/jql?jql=project=HELP&fields=*all&nextPageToken=...
(the older /rest/api/3/search and /rest/api/2/search responses work too - all carry an `issues` array).
API v3 returns descriptions as Atlassian Document Format; they are flattened to plain text here.

SLA fields are custom fields whose ids differ per site. Look them up once
(GET /rest/servicedeskapi/servicedesk/{id}/queue or the field list) and pass them in:

    python adapters/jira_service_management.py ./jsm-export --out tickets.csv --tz America/New_York \\
        --first-response-field customfield_10030 --resolution-field customfield_10031 [--group-field customfield_10010]

Without --group-field the project name is used as the group.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from _common import strip_html, from_iso, json_pages, write


def adf_text(node):
    """Flatten Atlassian Document Format (or a plain string) to text."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        inner = "".join(adf_text(c) for c in node.get("content") or [])
        return inner + ("\n" if node.get("type") in ("paragraph", "heading", "listItem", "codeBlock") else "")
    if isinstance(node, list):
        return "".join(adf_text(c) for c in node)
    return ""


def name_of(v):
    """Display name of a Jira field value: user, option, request type or plain string."""
    if isinstance(v, dict):
        if isinstance(v.get("requestType"), dict):
            return v["requestType"].get("name", "")
        return v.get("displayName") or v.get("name") or v.get("value") or ""
    return v if isinstance(v, str) else ""


def sla(v):
    """(stop time of the first completed cycle, breached flag) from a JSM SLA field."""
    if not isinstance(v, dict):
        return "", ""
    done = v.get("completedCycles") or []
    if done:
        c = done[0]
        return (c.get("stopTime") or {}).get("iso8601", ""), str(bool(c.get("breached"))).lower()
    ongoing = v.get("ongoingCycle") or {}
    return "", (str(bool(ongoing.get("breached"))).lower() if ongoing else "")


def parse(folder, tz="UTC", first_response_field=None, resolution_field=None, group_field=None):
    rows = {}
    for _, data in json_pages(folder):
        for i in (data.get("issues") if isinstance(data, dict) else None) or []:
            f = i.get("fields") or {}
            key = i.get("key") or i.get("id")
            if not key:
                continue
            fr_at, fr_breached = sla(f.get(first_response_field)) if first_response_field else ("", "")
            _, res_breached = sla(f.get(resolution_field)) if resolution_field else ("", "")
            reporter = f.get("reporter") or {}
            rows[key] = {
                "system": "JiraServiceManagement", "id": key, "subject": (f.get("summary") or "").strip(),
                "created": from_iso(f.get("created"), tz), "first_responded": from_iso(fr_at, tz),
                "resolved": from_iso(f.get("resolutiondate"), tz),
                "status": name_of(f.get("status")), "technician": name_of(f.get("assignee")),
                "group": name_of(f.get(group_field)) if group_field else name_of(f.get("project")),
                "requester": reporter.get("displayName", ""), "requester_email": (reporter.get("emailAddress") or "").lower(),
                "description": strip_html(adf_text(f.get("description"))),
                "is_overdue": res_breached, "is_fr_overdue": fr_breached}
    return list(rows.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--out", default="tickets.csv"); ap.add_argument("--tz", default="UTC")
    ap.add_argument("--first-response-field", help="custom field id of the 'Time to first response' SLA")
    ap.add_argument("--resolution-field", help="custom field id of the 'Time to resolution' SLA")
    ap.add_argument("--group-field", help="field to use as the group (default: project name)")
    a = ap.parse_args()
    write(parse(a.folder, a.tz, a.first_response_field, a.resolution_field, a.group_field), a.out)


if __name__ == "__main__":
    main()
