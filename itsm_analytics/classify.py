"""Classify a normalized ticket CSV into stream / category / work type.

    python -m itsm_analytics.classify tickets.csv --config config.json --out classified.csv [--unclassified]

Tier 1 (stream):  alert | process | voicemail | phish-report | user
Tier 2 (category): named machine-mail source, or a user-demand category from ordered subject rules,
                  falling back to description rules when the subject is generic or empty.
Tier 3 (work type): category rolled up to a handful of planning buckets.
"""
import argparse, csv, json, random, re, sys
from collections import Counter

from . import rules as RL

SCHEMA = ["system", "id", "created", "first_responded", "resolved", "status", "technician", "group",
          "requester", "requester_email", "subject", "description", "is_overdue", "is_fr_overdue"]


class Classifier:
    def __init__(self, config=None):
        cfg = config or {}
        self.process = {k.lower(): v for k, v in (cfg.get("process_senders") or {}).items()}
        extra = "|".join(re.escape(s) for s in cfg.get("extra_alert_senders") or [])
        self.alert_senders = RL.R("^(" + RL.ALERT_SENDERS + ("|" + extra if extra else "") + ")")
        self.alert_sources = [(s["label"], RL.R(s["sender"]) if s.get("sender") else None, RL.R(s["subject"]) if s.get("subject") else None)
                              for s in cfg.get("alert_sources") or []]
        self.aliases = cfg.get("technician_aliases") or {}
        lob = [(a["category"], RL.R(a["subject"]), RL.R(a["description"]) if a.get("description") else None)
               for a in cfg.get("line_of_business_apps") or []]
        cut = next(i for i, r in enumerate(RL.CATEGORY_RULES) if r[0] == "MFA / Authenticator") + 1
        self.rules = RL.CATEGORY_RULES[:cut] + lob + RL.CATEGORY_RULES[cut:]
        self.worktype = dict(RL.WORKTYPE, **{c: "Line-of-business apps" for c, _, _ in lob})
        sig = [re.escape(cfg["organization"])] if cfg.get("organization") else []
        self.sig_rx = RL.R(r"\|\s*(" + "|".join(sig) + r").*$") if sig else None

    # -- helpers -----------------------------------------------------------------------------
    def technician(self, name):
        name = (name or "").strip()
        return self.aliases.get(name, name) if name else "(unassigned)"

    @staticmethod
    def clean_subject(s):
        s = re.sub(r"^\[MIGRATION\]\[[^\]]*\]\s*[A-Z]+-\d+\s*:\s*", "", s or "")
        return re.sub(r"^\s*((re|fw|fwd|aw|automatic reply|external|\[ext\]|\[external\])\s*:?\s*)+", "", s, flags=re.I).strip()

    def clean_desc(self, d):
        d = (d or "")[:800]
        d = re.sub(r"(?is)(^|\n)\s*(thanks?|thank you|regards|sincerely|best regards|kind regards|sent from my|confidentiality notice|get outlook for).*$", "", d)
        if self.sig_rx:
            d = self.sig_rx.sub("", d)
        return d

    @staticmethod
    def language(subj, desc):
        return "es" if len(RL.SPANISH.findall(f"{subj} {(desc or '')[:400]}")) >= 2 or RL.SPANISH.search(subj or "") else "en"

    # -- tiers -------------------------------------------------------------------------------
    def stream(self, email, subj):
        e, s = (email or "").lower(), (subj or "").strip()
        if RL.VOICEMAIL.search(s):
            return "voicemail"
        if any(e.startswith(p) for p in self.process):
            return "process"
        if self.alert_senders.search(e) or RL.ALERT_SUBJECT.search(s) or any(
                (sx and sx.search(e)) or (jx and jx.search(s)) for _, sx, jx in self.alert_sources):
            return "alert"
        if RL.PHISH_REPORT.search(s):
            return "phish-report"
        return "user"

    def _match(self, text, use_desc):
        for cat, srx, drx in self.rules:
            rx = drx if use_desc else srx
            if rx is not None and rx.search(text):
                return cat
        return None

    def user_category(self, subj, desc):
        s, d = self.clean_subject(subj), self.clean_desc(desc)
        cat = self._match(s, False) if s else None
        name_only = bool(s) and cat is None and RL.NAME_ONLY.match(s)
        if cat is None or cat in RL.GENERIC:
            cat = (self._match(d, True) if d.strip() else None) or cat
        if cat is None:
            return "Unclassified (name-only/blank subject)" if (not s or name_only or len(s) < 4) else "Unclassified"
        if cat == "Laptop / PC hardware or performance" and RL.REQUEST_WORDS.search(f"{s} {d}"):
            cat = "Laptop request / replacement / swap"
        return cat

    def process_category(self, email):
        e = email.lower()
        return next((v for k, v in self.process.items() if e.startswith(k)), "Auto: other process mail")

    def classify(self, email, subj, desc):
        st = self.stream(email, subj)
        cat = {"alert": lambda: RL.alert_category(email or "", self.clean_subject(subj), self.alert_sources),
               "process": lambda: self.process_category(email or ""),
               "voicemail": lambda: "Voicemail callback",
               "phish-report": lambda: "User-reported phishing"}.get(st, lambda: self.user_category(subj, desc))()
        if cat.startswith(("Alert:", "Noise:")):
            st = "alert"
        wt = RL.STREAM_WORKTYPE.get(st) or self.worktype.get(cat, "Unclassified")
        return st, cat, wt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickets"); ap.add_argument("--config"); ap.add_argument("--out", default="classified.csv")
    ap.add_argument("--unclassified", action="store_true", help="print the top unclassified subjects to tune rules")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8")) if a.config else {}
    c = Classifier(cfg)
    with open(a.tickets, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    missing = [k for k in ("created", "subject", "requester_email") if rows and k not in rows[0]]
    if missing:
        sys.exit(f"input is missing required columns: {missing} (see SCHEMA.md)")
    for r in rows:
        r["stream"], r["category"], r["worktype"] = c.classify(r.get("requester_email", ""), r.get("subject", ""), r.get("description", ""))
        r["technician"] = c.technician(r.get("technician"))
        r["language"] = c.language(r.get("subject"), r.get("description")) if r["stream"] == "user" else ""
    with open(a.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} rows -> {a.out}")
    print("streams:", Counter(r["stream"] for r in rows).most_common())
    for k, n in Counter(r["worktype"] for r in rows).most_common():
        print(f"{n:7}  {k}")
    if a.unclassified:
        unc = [r for r in rows if r["stream"] == "user" and r["category"].startswith("Unclassified")]
        print(f"\nTop unclassified subjects ({len(unc)}):")
        for k, n in Counter(re.sub(r"\d+", "#", r["subject"].lower())[:60] for r in unc).most_common(40):
            print(f"{n:5}  {k}")
        random.seed(2)
        for r in random.sample(unc, min(15, len(unc))):
            print(" |", r["subject"][:45], "||", (r.get("description") or "")[:100].replace("\n", " "))


if __name__ == "__main__":
    main()
