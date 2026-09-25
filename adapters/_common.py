import csv, html, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCHEMA = ["system", "id", "created", "first_responded", "resolved", "status", "technician", "group",
          "requester", "requester_email", "subject", "description", "is_overdue", "is_fr_overdue"]
TAG = re.compile(r"<[^>]+>")


def strip_html(s, limit=1500):
    if not s:
        return ""
    s = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()[:limit]


def local(dt_utc, tz):
    return dt_utc.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S") if dt_utc else ""


def from_iso(s, tz):
    try:
        return local(datetime.fromisoformat(s.replace("Z", "+00:00")), tz) if s else ""
    except ValueError:
        return ""


def from_epoch_ms(v, tz):
    try:
        return local(datetime.fromtimestamp(int(v) / 1000, timezone.utc), tz) if v else ""
    except (TypeError, ValueError):
        return ""


def write(rows, out):
    rows = sorted(rows, key=lambda r: r["created"])
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SCHEMA, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} tickets -> {out}")
