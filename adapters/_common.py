import csv, glob, html, json, os, re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = ["system", "id", "created", "first_responded", "resolved", "status", "technician", "group",
          "requester", "requester_email", "subject", "description", "is_overdue", "is_fr_overdue"]
TAG = re.compile(r"<[^>]+>")
# ISO-ish timestamps as APIs actually send them: "Z", "+0000", "+00:00", 0-9 fractional digits, space or T
ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)(?:\.(\d+))?\s*(Z|[+-]\d{2}:?\d{2})?$")


def strip_html(s, limit=1500):
    if not s:
        return ""
    s = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()[:limit]


def zone(name):
    """tzinfo for a zone name. UTC needs no database; named zones on Windows need `pip install tzdata`."""
    if name in (None, "", "UTC", "Etc/UTC", "Z"):
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        raise SystemExit(f"unknown time zone {name!r}. On Windows, Python has no zone database: pip install tzdata")


def local(dt_utc, tz):
    return dt_utc.astimezone(zone(tz)).strftime("%Y-%m-%d %H:%M:%S") if dt_utc else ""


def parse_dt(s, assume="UTC"):
    """Parse an API timestamp into an aware datetime. Naive values are taken to be in `assume`."""
    if not s or not isinstance(s, str):
        return None
    m = ISO.match(s.strip())
    if not m:
        return None
    day, hms, frac, off = m.groups()
    dt = datetime.fromisoformat(f"{day}T{hms if hms.count(':') == 2 else hms + ':00'}")
    if frac:
        dt = dt.replace(microsecond=int(frac[:6].ljust(6, "0")))
    if off in (None, ""):
        return dt.replace(tzinfo=zone(assume))
    if off == "Z":
        return dt.replace(tzinfo=timezone.utc)
    sign, hh, mm = (1 if off[0] == "+" else -1), int(off[1:3]), int(off[-2:])
    return dt.replace(tzinfo=timezone(sign * timedelta(hours=hh, minutes=mm)))


def from_iso(s, tz, assume="UTC"):
    return local(parse_dt(s, assume), tz)


def from_epoch_ms(v, tz):
    try:
        return local(datetime.fromtimestamp(int(v) / 1000, timezone.utc), tz) if v else ""
    except (TypeError, ValueError):
        return ""


def plus_minutes(s, minutes, tz):
    """created timestamp + N minutes (for systems that report reply time as a duration)."""
    dt = parse_dt(s)
    return local(dt + timedelta(minutes=minutes), tz) if dt and isinstance(minutes, (int, float)) else ""


def flag(v):
    """Normalize a true/false-ish value to 'true' / 'false' / '' (unknown)."""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower()
    return ""


def json_pages(folder, pattern="*.json"):
    """Yield (path, parsed JSON) for every export page in a folder, recursively; skip unreadable files."""
    for f in sorted(glob.glob(os.path.join(folder, "**", pattern), recursive=True)):
        try:
            yield f, json.load(open(f, encoding="utf-8"))
        except (ValueError, OSError):
            print(f"skipped unreadable file: {f}")


def write(rows, out):
    rows = sorted(rows, key=lambda r: r["created"])
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SCHEMA, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} tickets -> {out}")
