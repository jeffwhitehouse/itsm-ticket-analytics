# itsm-ticket-analytics

Answer "what is the helpdesk actually doing?" from a raw ticket export.

Most ticket systems report volume. Volume lies: in the export this was built against, only about
half of the tickets were real user requests; the rest was monitoring alerts, lifecycle
automation, bounces and voicemail notifications landing in the same queue. This tool separates
the two, then breaks real demand into categories and work types you can plan against
(self-service candidates, automation targets, staffing).

## Pipeline

```
export (Freshservice / ServiceDesk Plus / CSV)
  -> adapters/*.py            normalized tickets.csv (SCHEMA.md)
  -> itsm_analytics.classify  stream / category / work type / language per ticket
  -> itsm_analytics.analyze   report.json (all the numbers)
  -> itsm_analytics.report    report.html (single file, inline SVG, prints cleanly)
```

## Try it on synthetic data

```bash
python sample/generate_sample.py --n 6000 --out sample/tickets.csv     # fake people, fake tickets
python -m itsm_analytics.classify sample/tickets.csv --config config.example.json --out classified.csv --unclassified
python -m itsm_analytics.analyze  classified.csv --config config.example.json --out report.json
python -m itsm_analytics.report   report.json --out report.html
python -m unittest discover -s tests
```

No dependencies beyond the Python 3.10+ standard library.

## How classification works

1. **Stream**: `alert` (monitoring, security tools, bounces, Teams/M365 noise), `process` (your own
   lifecycle mailboxes, e.g. offboarding and new-hardware intake, from config), `voicemail`,
   `phish-report`, or `user`. Decided mostly by sender address, then subject patterns.
2. **Category**: machine mail is named by source: Microsoft Defender / 365, bounces and carrier mail
   are built in; your own monitoring, RMM and security tools are declared as `alert_sources` in config.
   User tickets go through ~40 ordered subject rules; when the subject is generic ("help", "question",
   a person's name) the description is tried instead. Hardware tickets that read like orders are moved
   to requests. Forward/reply prefixes, migration tags and signature blocks are stripped first.
3. **Work type**: categories roll up into Access & identity, Joiner/mover/leaver, Equipment orders,
   Break/fix, Line-of-business apps, Software & licensing, Security, IT campaign responses, plus
   the machine streams.
4. **Language**: English/Spanish detection, which surfaces where bilingual KB articles would pay off.

Tune with `--unclassified`: it prints the most common unclassified subjects and a random sample.

## Your organization's specifics live in config

`config.example.json` holds everything that is yours rather than generic: internal lifecycle mailboxes,
alert sources (sender/subject regex to a named machine-mail category), extra alert senders, line-of-business app patterns (ERP, time entry...), technician name aliases and
team membership. Copy it to `config.json` (gitignored) and edit.

## What the report shows

Headline tiles (volume per business day, real-demand share, median resolve, same-day rate, Spanish
share, open backlog), stream mix, month-by-month stacked volume, work types, a category table with
median and p90 resolve times and top technicians, machine-mail sources, per-technician load and active
months, intake by hour and weekday, requester patterns (one-and-done vs frequent, personal-email
share) and open backlog by age.

## Data handling

Real exports contain names, email addresses and ticket text. `*.csv`, `*.json` exports, `config.json` and
generated reports are gitignored; only the synthetic generator is committed. Keep it that way.

## License

MIT - see [LICENSE](LICENSE).
