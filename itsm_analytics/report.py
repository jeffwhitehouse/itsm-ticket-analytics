"""Render report.json as a single self-contained HTML page (inline SVG, no JS, prints cleanly).

    python -m itsm_analytics.report report.json --out report.html
"""
import argparse, html, json

CSS = """
:root{--bg:#fff;--fg:#1d2330;--muted:#5b6475;--line:#e3e6ec;--card:#f7f8fa;--a:#2a78d6;--b:#eb6834;--c:#1baf7a;--d:#eda100;--e:#8a63d2}
@media (prefers-color-scheme:dark){:root{--bg:#14161b;--fg:#e8eaef;--muted:#9aa3b2;--line:#2b2f38;--card:#1b1e25}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;max-width:1040px;margin:0 auto;padding:24px 16px}
h1{font-size:26px;margin:0}h2{font-size:19px;margin:36px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.sub{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.tile{background:var(--card);border-radius:10px;padding:12px 14px}.tile b{display:block;font-size:24px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}.wrap{overflow-x:auto}svg text{fill:var(--fg);font-size:11px}
.legend span{display:inline-block;margin-right:14px;font-size:12px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
"""
COLORS = ["var(--a)", "var(--b)", "var(--c)", "var(--d)", "var(--e)"]
E = html.escape


def fmt(v, suffix=""):
    return "&ndash;" if v is None else f"{v:,}{suffix}" if isinstance(v, int) else f"{v}{suffix}"


def hbars(items, width=640, bar=18):
    mx = max((v for _, v in items), default=1) or 1
    h = len(items) * (bar + 6) + 4; lab = 230
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" role="img">']
    for i, (k, v) in enumerate(items):
        y = i * (bar + 6); w = (width - lab - 70) * v / mx
        out.append(f'<text x="{lab - 8}" y="{y + bar - 5}" text-anchor="end">{E(str(k)[:38])}</text>'
                   f'<rect x="{lab}" y="{y}" width="{w:.1f}" height="{bar}" rx="3" fill="var(--a)"/>'
                   f'<text x="{lab + w + 6:.1f}" y="{y + bar - 5}">{v:,}</text>')
    return "".join(out) + "</svg>"


def stacked_months(monthly, keys, width=900, height=220):
    mx = max((sum(m[k] for k in keys) for m in monthly), default=1) or 1
    bw = (width - 40) / max(1, len(monthly))
    out = [f'<svg viewBox="0 0 {width} {height + 24}" width="100%" role="img">']
    for i, m in enumerate(monthly):
        y = height
        for j, k in enumerate(keys):
            hgt = height * m[k] / mx; y -= hgt
            out.append(f'<rect x="{30 + i * bw:.1f}" y="{y:.1f}" width="{bw * .78:.1f}" height="{hgt:.1f}" fill="{COLORS[j % 5]}"><title>{E(m["month"])} {E(k)}: {m[k]}</title></rect>')
        out.append(f'<text x="{30 + i * bw + bw * .39:.1f}" y="{height + 16}" text-anchor="middle">{E(m["month"][2:])}</text>')
    return "".join(out) + "</svg>"


def vbars(vals, labels, width=460, height=140):
    mx = max(vals) or 1; bw = width / len(vals)
    out = [f'<svg viewBox="0 0 {width} {height + 18}" width="100%" role="img">']
    for i, v in enumerate(vals):
        h = height * v / mx
        out.append(f'<rect x="{i * bw + 1:.1f}" y="{height - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" fill="var(--c)"><title>{labels[i]}: {v}</title></rect>')
        if len(vals) <= 7 or i % 3 == 0:
            out.append(f'<text x="{i * bw + bw / 2:.1f}" y="{height + 13}" text-anchor="middle">{labels[i]}</text>')
    return "".join(out) + "</svg>"


def render(r):
    s, sla = r["streams"], r["sla"]
    keys = ["user", "alert", "process", "voicemail", "phish-report"]
    o = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Helpdesk Review</title><style>{CSS}</style>",
         f"<h1>Helpdesk review{(' &middot; ' + E(r['organization'])) if r['organization'] else ''}</h1>",
         f"<div class=sub>{E(r['window'])} &middot; {r['business_days']} business days</div>",
         "<div class=tiles>",
         f"<div class=tile><b>{r['total']:,}</b>tickets ({r['per_bday']}/business day)</div>",
         f"<div class=tile><b>{r['user_share_pct']}%</b>are real user demand ({r['user_per_bday']}/day)</div>",
         f"<div class=tile><b>{fmt(sla['median_res_h'], ' h')}</b>median time to resolve (user)</div>",
         f"<div class=tile><b>{sla['same_day_pct']}%</b>resolved within 8 h</div>",
         f"<div class=tile><b>{r['es_pct']}%</b>of user tickets in Spanish</div>",
         f"<div class=tile><b>{r['backlog']['open']:,}</b>open at window end</div></div>",
         "<h2>Where the volume comes from</h2>", hbars(list(s.items())),
         "<h2>Month by month</h2><div class=legend>" + "".join(f"<span><i style='background:{COLORS[j]}'></i>{E(k)}</span>" for j, k in enumerate(keys)) + "</div>",
         stacked_months(r["monthly"], keys),
         "<h2>Work types</h2><div class=wrap><table><tr><th>Work type</th><th class=n>Tickets</th><th class=n>% of all</th><th class=n>Median resolve</th></tr>"]
    o += [f"<tr><td>{E(w['worktype'])}</td><td class=n>{w['count']:,}</td><td class=n>{w['pct_total']}%</td><td class=n>{fmt(w['median_res_h'], ' h')}</td></tr>" for w in r["worktypes"]]
    o.append("</table></div><h2>What users ask for</h2><div class=wrap><table><tr><th>Category</th><th>Work type</th><th class=n>Tickets</th><th class=n>% user</th>"
             "<th class=n>/month</th><th class=n>Median / p90 resolve</th><th class=n>ES</th><th>Top technicians</th></tr>")
    o += [f"<tr><td>{E(c['category'])}</td><td>{E(c['worktype'])}</td><td class=n>{c['count']:,}</td><td class=n>{c['pct_user']}%</td><td class=n>{c['per_month']}</td>"
          f"<td class=n>{fmt(c['median_res_h'])} / {fmt(c['p90_res_h'])} h</td><td class=n>{c['es_pct']}%</td><td>{E(', '.join(c['top_techs']))}</td></tr>" for c in r["categories"]]
    o.append("</table></div><h2>Machine mail and automation</h2>" + hbars([(m["category"], m["count"]) for m in r["machine_mail"][:15]]))
    o.append("<h2>Technicians</h2><div class=wrap><table><tr><th>Technician</th><th>Team</th><th class=n>User tickets</th><th class=n>Machine</th>"
             "<th class=n>User/active month</th><th class=n>Median resolve</th><th>Active</th><th>Top categories</th></tr>")
    o += [f"<tr><td>{E(t['technician'])}</td><td>{E(t['team'])}</td><td class=n>{t['user']:,}</td><td class=n>{t['machine']:,}</td><td class=n>{t['user_per_active_month']}</td>"
          f"<td class=n>{fmt(t['median_res_h'], ' h')}</td><td>{t['first_month']} &ndash; {t['last_month']}</td><td>{E('; '.join(t['top_categories']))}</td></tr>" for t in r["technicians"]]
    p, q = r["patterns"], r["requesters"]
    o.append("</table></div><h2>When tickets arrive</h2>" + vbars(p["hour"], [str(h) for h in range(24)]) + vbars(p["weekday"], ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]))
    o.append(f"<h2>Requesters</h2><p>{q['unique']:,} unique requesters; {q['one_ticket_pct']}% filed exactly one ticket, {q['five_plus']:,} filed five or more. "
             f"{q['personal_email_pct']}% of user tickets came from personal email domains.</p>")
    b = r["backlog"]
    o.append(f"<h2>Open backlog</h2><p>{b['open']:,} open, {b['unassigned']:,} unassigned.</p>" + hbars(b["by_age"]))
    o.append("<p class=sub>Generated by itsm-ticket-analytics.</p>")
    return "\n".join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("report"); ap.add_argument("--out", default="report.html")
    a = ap.parse_args(argv)
    open(a.out, "w", encoding="utf-8").write(render(json.load(open(a.report, encoding="utf-8"))))
    print("->", a.out)


if __name__ == "__main__":
    main()
