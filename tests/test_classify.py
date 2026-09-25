import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from itsm_analytics.classify import Classifier

CFG = {"process_senders": {"disableduser@": "Auto: Disabled-user lifecycle task"},
       "line_of_business_apps": [{"category": "Time entry app", "subject": "time ?sheet|missed punch"}],
       "alert_sources": [{"label": "Alert: RMM", "sender": r"^rmm@example\.com"}],
       "technician_aliases": {"Sam": "Sam Rivera"}}


class TestClassifier(unittest.TestCase):
    c = Classifier(CFG)

    def check(self, email, subj, desc, stream, cat):
        st, ct, _ = self.c.classify(email, subj, desc)
        self.assertEqual((st, ct), (stream, cat), subj)

    def test_streams(self):
        self.check("defender-noreply@microsoft.com", "Incident 12 on a device", "", "alert", "Alert: Microsoft Defender / MDI")
        self.check("disableduser@example.com", "Equipment return", "", "process", "Auto: Disabled-user lifecycle task")
        self.check("", "V-Mail from +1 555 0100", "", "voicemail", "Voicemail callback")
        self.check("user@example.com", "[Phish Alert] invoice", "", "phish-report", "User-reported phishing")
        self.check("rmm@example.com", "Disk space low on WS-0142", "", "alert", "Alert: RMM")
        self.check("monitoring@example.com", "Problem: host unreachable", "", "alert", "Alert: infrastructure monitoring")

    def test_user_categories(self):
        self.check("a@example.com", "Password reset", "", "user", "Password reset / account lockout")
        self.check("a@example.com", "Timesheet", "", "user", "Time entry app")
        self.check("a@example.com", "help", "My laptop won't turn on", "user", "Laptop / PC hardware or performance")
        self.check("a@example.com", "Laptop", "Can I order a new laptop for our intern?", "user", "Laptop request / replacement / swap")
        self.check("a@example.com", "RE: FW: Printer", "", "user", "Printers / plotters / scanners")

    def test_language_and_alias(self):
        self.assertEqual(self.c.language("Necesito ayuda", "no puedo iniciar sesión"), "es")
        self.assertEqual(self.c.technician("Sam"), "Sam Rivera")
        self.assertEqual(self.c.technician(""), "(unassigned)")


if __name__ == "__main__":
    unittest.main()
