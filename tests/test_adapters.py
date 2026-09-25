"""Adapter tests: a tiny synthetic export per system, shaped like that system's API response."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import _common, autotask, connectwise_psa, csv_mapped, freshdesk, freshservice, jira_service_management, servicedeskplus, servicenow, zendesk


try:
    from zoneinfo import ZoneInfo
    ZoneInfo("America/New_York"); HAVE_TZDB = True
except Exception:  # Windows without the tzdata package
    HAVE_TZDB = False
needs_tzdb = unittest.skipUnless(HAVE_TZDB, "no time zone database (on Windows: pip install tzdata)")


def folder(files):
    d = tempfile.mkdtemp()
    for name, data in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            fh.write(data if isinstance(data, str) else json.dumps(data))
    return d


def one(rows):
    assert len(rows) == 1, rows
    return rows[0]


class TestTimestamps(unittest.TestCase):
    def test_formats(self):
        for s in ("2026-03-02T14:05:09Z", "2026-03-02T14:05:09.123+0000", "2026-03-02T14:05:09.1234567+00:00",
                  "2026-03-02 14:05:09", "2026-03-02T09:05:09-05:00"):
            self.assertEqual(_common.from_iso(s, "UTC"), "2026-03-02 14:05:09", s)

    @needs_tzdb
    def test_timezone_and_duration(self):
        self.assertEqual(_common.from_iso("2026-07-01T12:00:00Z", "America/New_York"), "2026-07-01 08:00:00")
        self.assertEqual(_common.plus_minutes("2026-03-02T14:00:00Z", 90, "UTC"), "2026-03-02 15:30:00")
        self.assertEqual(_common.from_iso("not a date", "UTC"), "")


class TestAdapters(unittest.TestCase):
    def test_servicenow(self):
        f = lambda v, d=None: {"value": v, "display_value": d if d is not None else v}
        r = one(servicenow.parse(folder({"p1.json": {"result": [{
            "number": f("INC0010001"), "short_description": f("VPN not connecting"), "description": f("From the hotel"),
            "opened_at": f("2026-03-02 14:00:00", "03/02/2026 09:00:00"), "resolved_at": f("2026-03-02 16:00:00"),
            "state": f("6", "Resolved"), "assigned_to": f("abc123", "Sam Rivera"), "assignment_group": f("def456", "Service Desk"),
            "caller_id": f("ghi789", "Ana Garcia"), "caller_id.email": f("ana.garcia@example.com"), "made_sla": f("false")}]}})))
        self.assertEqual((r["id"], r["created"], r["resolved"], r["status"], r["technician"], r["group"], r["requester_email"], r["is_overdue"]),
                         ("INC0010001", "2026-03-02 14:00:00", "2026-03-02 16:00:00", "Resolved", "Sam Rivera", "Service Desk", "ana.garcia@example.com", "true"))

    def test_jira_service_management(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Laptop won't boot"}]}]}
        r = one(jira_service_management.parse(folder({"page1.json": {"issues": [{"key": "HELP-42", "fields": {
            "summary": "Laptop", "description": adf, "created": "2026-03-02T14:00:00.000+0000", "resolutiondate": None,
            "status": {"name": "Waiting for support"}, "assignee": {"displayName": "Alex Chen"}, "project": {"name": "IT Help"},
            "reporter": {"displayName": "Ben Smith", "emailAddress": "Ben.Smith@example.com"},
            "customfield_10030": {"completedCycles": [{"stopTime": {"iso8601": "2026-03-02T14:20:00+0000"}, "breached": False}]},
            "customfield_10031": {"ongoingCycle": {"breached": True}}}}]}}), first_response_field="customfield_10030", resolution_field="customfield_10031"))
        self.assertEqual((r["id"], r["created"], r["first_responded"], r["resolved"], r["group"], r["requester_email"], r["is_fr_overdue"], r["is_overdue"]),
                         ("HELP-42", "2026-03-02 14:00:00", "2026-03-02 14:20:00", "", "IT Help", "ben.smith@example.com", "false", "true"))
        self.assertIn("Laptop won't boot", r["description"])

    def test_zendesk(self):
        r = one(zendesk.parse(folder({"p1.json": {
            "tickets": [{"id": 101, "subject": "Printer jam", "description": "2nd floor", "created_at": "2026-03-02T14:00:00Z",
                         "status": "solved", "assignee_id": 7, "requester_id": 9, "group_id": 3}],
            "users": [{"id": 7, "name": "Priya Patel"}, {"id": 9, "name": "Carla Lopez", "email": "carla.lopez@example.com"}],
            "groups": [{"id": 3, "name": "Support"}],
            "metric_sets": [{"ticket_id": 101, "solved_at": "2026-03-02T18:00:00Z", "reply_time_in_minutes": {"calendar": 45, "business": 45}}]}})))
        self.assertEqual((r["id"], r["first_responded"], r["resolved"], r["status"], r["technician"], r["group"], r["requester"]),
                         ("#101", "2026-03-02 14:45:00", "2026-03-02 18:00:00", "Solved", "Priya Patel", "Support", "Carla Lopez"))

    def test_freshdesk(self):
        r = one(freshdesk.parse(folder({
            "page_1.json": [{"id": 5, "subject": "Password reset", "created_at": "2026-03-02T14:00:00Z", "status": 5, "responder_id": 1,
                             "group_id": 2, "requester": {"name": "Dev Nguyen", "email": "dev.nguyen@example.com"}, "is_escalated": False,
                             "fr_escalated": True, "stats": {"first_responded_at": "2026-03-02T14:10:00Z", "closed_at": "2026-03-02T15:00:00Z"}}],
            "agents.json": [{"id": 1, "contact": {"name": "Jordan Lee"}}], "groups.json": [{"id": 2, "name": "Tier 1"}]})))
        self.assertEqual((r["status"], r["technician"], r["group"], r["resolved"], r["is_overdue"], r["is_fr_overdue"]),
                         ("Closed", "Jordan Lee", "Tier 1", "2026-03-02 15:00:00", "false", "true"))

    def test_freshservice(self):
        r = one(freshservice.parse(folder({
            "page_1.json": {"tickets": [{"id": 9, "subject": "Monitor", "created_at": "2026-03-02T14:00:00Z", "status": 4, "responder_id": 1,
                                         "group_id": 2, "requester": {"name": "Elena Brown", "email": "elena.brown@example.com"}, "stats": {}}]},
            "agents.json": [{"id": 1, "first_name": "Morgan", "last_name": "Blake"}], "groups.json": [{"id": 2, "name": "Service Desk"}]})))
        self.assertEqual((r["id"], r["status"], r["technician"], r["group"]), ("INC-9", "Resolved", "Morgan Blake", "Service Desk"))

    def test_servicedeskplus(self):
        r = one(servicedeskplus.parse(folder({"p1.json": {"requests": [{
            "id": "1", "display_id": "REQ-1", "subject": "Teams audio", "created_time": {"value": "1772460000000"},
            "status": {"name": "Open"}, "technician": {"name": "Sam Rivera"}, "requester": {"name": "Frank Davis", "email_id": "Frank.Davis@example.com"},
            "is_overdue": False}]}})))
        self.assertEqual((r["id"], r["created"], r["technician"], r["requester_email"], r["is_overdue"]),
                         ("REQ-1", "2026-03-02 14:00:00", "Sam Rivera", "frank.davis@example.com", "false"))

    def test_connectwise_psa(self):
        rows = connectwise_psa.parse(folder({"p1.json": [
            {"id": 3001, "summary": "New hire laptop", "board": {"id": 1, "name": "Help Desk"}, "status": {"name": "New"},
             "owner": {"id": 4, "identifier": "srivera", "name": "Sam Rivera"}, "contactName": "Gia Wilson",
             "contactEmailAddress": "gia.wilson@example.com", "_info": {"dateEntered": "2026-03-02T14:00:00Z"},
             "dateResponded": "2026-03-02T14:30:00Z", "isInSla": True},
            {"id": 3002, "summary": "Project task", "board": {"name": "Projects"}, "_info": {"dateEntered": "2026-03-02T14:00:00Z"}}]}),
            boards="Help Desk")
        r = one(rows)
        self.assertEqual((r["id"], r["created"], r["first_responded"], r["technician"], r["group"], r["is_overdue"]),
                         ("#3001", "2026-03-02 14:00:00", "2026-03-02 14:30:00", "Sam Rivera", "Help Desk", "false"))

    def test_autotask(self):
        r = one(autotask.parse(folder({
            "tickets_1.json": {"items": [{"id": 77, "ticketNumber": "T20260302.0001", "title": "Outlook not syncing",
                                          "createDate": "2026-03-02T14:00:00.000Z", "firstResponseDateTime": "2026-03-02T14:05:00Z",
                                          "status": 5, "queueID": 8, "assignedResourceID": 11, "contactID": 21,
                                          "serviceLevelAgreementHasBeenMet": False}]},
            "resources.json": {"items": [{"id": 11, "firstName": "Alex", "lastName": "Chen"}]},
            "contacts.json": {"items": [{"id": 21, "firstName": "Hector", "lastName": "Martinez", "emailAddress": "hector.martinez@example.com"}]},
            "fields.json": {"fields": [{"name": "status", "isPickList": True, "picklistValues": [{"value": "5", "label": "Complete"}]},
                                       {"name": "queueID", "isPickList": True, "picklistValues": [{"value": "8", "label": "Service Desk"}]}]}})))
        self.assertEqual((r["id"], r["status"], r["group"], r["technician"], r["requester"], r["is_overdue"]),
                         ("T20260302.0001", "Complete", "Service Desk", "Alex Chen", "Hector Martinez", "true"))

    @needs_tzdb
    def test_csv_mapped(self):
        d = folder({"export.csv": "Ticket ID,Date Created,Summary,Requester Email,Status,SLA Breached\n"
                                  "H-1,03/02/2026 09:00 AM,Printer jam,Ivy.Torres@example.com,Closed - Resolved,Yes\n"})
        mapping = {"system": "ExampleDesk", "datetime_format": "%m/%d/%Y %I:%M %p", "source_timezone": "America/New_York",
                   "status_map": {"Closed - Resolved": "Closed"},
                   "columns": {"id": "Ticket ID", "created": "Date Created", "subject": "Summary", "requester_email": "Requester Email",
                               "status": "Status", "is_overdue": "SLA Breached"}}
        r = one(csv_mapped.parse(os.path.join(d, "export.csv"), mapping, tz="UTC"))
        self.assertEqual((r["system"], r["id"], r["created"], r["status"], r["requester_email"], r["is_overdue"]),
                         ("ExampleDesk", "H-1", "2026-03-02 14:00:00", "Closed", "ivy.torres@example.com", "true"))

    def test_example_mapping_is_valid(self):
        m = json.load(open(os.path.join(os.path.dirname(__file__), "..", "mappings", "example.json"), encoding="utf-8"))
        self.assertTrue(all(k in m["columns"] for k in csv_mapped.REQUIRED))


if __name__ == "__main__":
    unittest.main()
