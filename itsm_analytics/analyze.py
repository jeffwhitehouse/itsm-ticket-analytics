"""Turn classified tickets into the metrics behind the report (JSON).

    python -m itsm_analytics.analyze classified.csv --config config.json --out report.json [--start 2025-09-01 --end 2026-08-31]
"""
import argparse, json, statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

FMT = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")
STREAM_LABEL = {"user": "Real user tickets", "alert": "Monitoring & machine mail", "process": "Lifecycle automation",
                "voicemail": "Voicemail callbacks", "phish-report": "User phishing reports"}


def dt(s):
    s = (s or "").strip().replace("Z", "")[:19]
    for f in FMT:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def med(v):
    v = [x for x in v if x is not None]
    return round(statistics.median(v), 1) if v else None


def p90(v):
    v = sorted(x for x in v if x is not None)
    return round(v[min(len(v) - 1, int(0.9 * len(v)))], 1) if v else None


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def truthy(x):
    return str(x).strip().lower() in ("true", "1", "yes")


def business_days(a, b):
    d, n = a.date(), 0
    while d <= b.date():
        n += d.weekday() < 5
        d += timedelta(days=1)
    return max(n, 1)


def analyze(rows, cfg, start=None, end=None):
    for r in rows:
        r["_c"], r["_f"], r["_r"] = dt(r.get("created")), dt(r.get("first_responded")), dt(r.get("resolved"))
        r["res_h"] = round((r["_r"] - r["_c"]).total_seconds() / 3600, 2) if r["_c"] and r["_r"] and r["_r"] >= r["_c"] else None
        r["fr_h"] = round((r["_f"] - r["_c"]).total_seconds() / 3600, 2) if r["_c"] and r["_f"] and r["_f"] >= r["_c"] else None
    rows = [r for r in rows if r["_c"]]
    start = start or min(r["_c"] for r in rows)
    end = end or max(r["_c"] for r in rows)
    rows = [r for r in rows if start <= r["_c"] <= end]
    for r in rows:
        r["month"] = r["_c"].strftime("%Y-%m")
    months = sorted({r["month"] for r in rows})
    user = [r for r in rows if r["stream"] == "user"]
    bdays = business_days(start, end)

    monthly = [{"month": m, "total": sum(1 for r in rows if r["month"] == m),
                **{s: sum(1 for r in rows if r["month"] == m and r["stream"] == s) for s in STREAM_LABEL}} for m in months]

    cats = []
    for cat, n in Counter(r["category"] for r in user).most_common():
        cr = [r for r in user if r["category"] == cat]
        cats.append({"category": cat, "worktype": cr[0]["worktype"], "count": n, "pct_user": pct(n, len(user)),
                     "per_month": round(n / max(1, len(months)), 1), "median_res_h": med(r["res_h"] for r in cr),
                     "p90_res_h": p90(r["res_h"] for r in cr), "median_fr_h": med(r["fr_h"] for r in cr),
                     "es_pct": pct(sum(r.get("language") == "es" for r in cr), n),
                     "top_techs": [f"{t} ({c})" for t, c in Counter(r["technician"] for r in cr).most_common(3)]})

    wts = []
    for wt, n in Counter(r["worktype"] for r in rows).most_common():
        wr = [r for r in rows if r["worktype"] == wt]
        wts.append({"worktype": wt, "count": n, "pct_total": pct(n, len(rows)), "median_res_h": med(r["res_h"] for r in wr),
                    "by_month": [sum(1 for r in wr if r["month"] == m) for m in months]})

    machine = [{"category": c, "count": n, "per_month": round(n / max(1, len(months)), 1), "pct_total": pct(n, len(rows))}
               for c, n in Counter(r["category"] for r in rows if r["stream"] != "user").most_common()]

    team_of = {m: t for t, ms in (cfg.get("teams") or {}).items() for m in ms}
    techs = []
    for t, n in Counter(r["technician"] for r in rows).most_common():
        tr = [r for r in rows if r["technician"] == t]; tu = [r for r in tr if r["stream"] == "user"]
        active = sorted({r["month"] for r in tr})
        techs.append({"technician": t, "team": team_of.get(t, ""), "total": n, "user": len(tu),
                      "machine": n - len(tu), "pct_of_user": pct(len(tu), len(user)),
                      "user_per_active_month": round(len(tu) / max(1, len(active)), 1),
                      "median_res_h": med(r["res_h"] for r in tu), "median_fr_h": med(r["fr_h"] for r in tu),
                      "first_month": active[0] if active else "", "last_month": active[-1] if active else "",
                      "top_categories": [f"{c} ({k})" for c, k in Counter(r["category"] for r in tu).most_common(4)],
                      "user_by_month": [sum(1 for r in tu if r["month"] == m) for m in months]})

    personal = set(cfg.get("personal_domains") or [])
    req = Counter(r["requester_email"].lower() for r in user if r.get("requester_email"))
    dom = Counter(e.split("@")[-1] for e in (r["requester_email"].lower() for r in user if "@" in (r.get("requester_email") or "")))
    requesters = {"unique": len(req), "one_ticket_pct": pct(sum(c == 1 for c in req.values()), len(req)),
                  "five_plus": sum(c >= 5 for c in req.values()), "top_domains": dom.most_common(8),
                  "personal_email_pct": pct(sum(c for d, c in dom.items() if d in personal), len(user))}

    patterns = {"weekday": [sum(1 for r in user if r["_c"].weekday() == i) for i in range(7)],
                "hour": [sum(1 for r in user if r["_c"].hour == h) for h in range(24)]}

    sla = {"median_res_h": med(r["res_h"] for r in user), "p90_res_h": p90(r["res_h"] for r in user),
           "median_fr_h": med(r["fr_h"] for r in user), "same_day_pct": pct(sum(1 for r in user if r["res_h"] is not None and r["res_h"] <= 8), len(user)),
           "fr_overdue_pct": pct(sum(truthy(r.get("is_fr_overdue")) for r in user), len(user)),
           "overdue_pct": pct(sum(truthy(r.get("is_overdue")) for r in user), len(user))}

    open_rows = [r for r in rows if not r["_r"] and (r.get("status") or "").lower() not in ("closed", "resolved", "cancelled", "canceled")]
    def age(r):
        d = (end - r["_c"]).days
        return "<2d" if d < 2 else "2-5d" if d < 5 else "5-14d" if d < 14 else "14-30d" if d < 30 else ">30d"
    backlog = {"open": len(open_rows), "by_status": Counter(r.get("status", "") for r in open_rows).most_common(),
               "by_group": Counter(r.get("group", "") for r in open_rows).most_common(), "unassigned": sum(r["technician"] == "(unassigned)" for r in open_rows),
               "by_age": [(b, sum(age(r) == b for r in open_rows)) for b in ("<2d", "2-5d", "5-14d", "14-30d", ">30d")]}

    return {"organization": cfg.get("organization", ""), "window": f"{start:%b %d, %Y} - {end:%b %d, %Y}", "months": months,
            "business_days": bdays, "total": len(rows), "user": len(user), "per_bday": round(len(rows) / bdays, 1),
            "user_per_bday": round(len(user) / bdays, 1), "user_share_pct": pct(len(user), len(rows)),
            "streams": {STREAM_LABEL.get(k, k): v for k, v in Counter(r["stream"] for r in rows).most_common()},
            "es_pct": pct(sum(r.get("language") == "es" for r in user), len(user)),
            "monthly": monthly, "categories": cats, "worktypes": wts, "machine_mail": machine, "technicians": techs,
            "requesters": requesters, "patterns": patterns, "sla": sla, "backlog": backlog}


def main(argv=None):
    import csv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("classified"); ap.add_argument("--config"); ap.add_argument("--out", default="report.json")
    ap.add_argument("--start"); ap.add_argument("--end")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8")) if a.config else {}
    with open(a.classified, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    res = analyze(rows, cfg, dt(a.start) if a.start else None, (dt(a.end) + timedelta(days=1, seconds=-1)) if a.end else None)
    json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"{res['total']} tickets ({res['user_share_pct']}% real user demand) over {res['business_days']} business days -> {a.out}")


if __name__ == "__main__":
    main()
