"""Generate a synthetic ticket export in the normalized schema. Every name, address and ticket is fake.

    python sample/generate_sample.py --n 6000 --out sample/tickets.csv
"""
import argparse, csv, random
from datetime import datetime, timedelta

TECHS = ["Sam Rivera", "Alex Chen", "Priya Patel", "Jordan Lee", "Morgan Blake", ""]
FIRST = ["Ana", "Ben", "Carla", "Dev", "Elena", "Frank", "Gia", "Hector", "Ivy", "Jon", "Kira", "Luis", "Mia", "Nate", "Omar", "Paula", "Rosa", "Tom"]
LAST = ["Garcia", "Smith", "Nguyen", "Lopez", "Brown", "Martinez", "Davis", "Hernandez", "Wilson", "Torres"]
USER = [  # (weight, subject, description)
    (14, "Password reset", "I am locked out of my account and can't sign in."),
    (5, "Necesito ayuda con mi contraseña", "No puedo iniciar sesión, mi cuenta está bloqueada. Gracias."),
    (6, "New laptop request", "Please order a new laptop for our new analyst."),
    (5, "Monitor and dock", "Need a second monitor and a docking station for my desk."),
    (6, "Printer not working", "The plotter on the 2nd floor shows a paper jam."),
    (5, "Outlook not receiving emails", "My outlook stopped receiving emails this morning."),
    (4, "New hire starting Monday", "New hire starting Monday needs an account and laptop."),
    (3, "Last day Friday", "Employee's last day is Friday, please remove all access."),
    (4, "Teams audio issue", "Microsoft Teams meeting audio cuts out."),
    (3, "Need Visio license", "Please assign a Visio license."),
    (3, "Install software", "Need admin rights to install the vendor software."),
    (3, "VPN not connecting", "The VPN will not connect from the hotel."),
    (2, "Is this legit?", "Got a suspicious email asking for my password. Is this legit?"),
    (2, "Laptop very slow", "My laptop keeps freezing and is running very slow."),
    (2, "Hotspot for offsite event", "Our offsite event needs a hotspot, the venue has no internet."),
    (2, "P drive access", "I need access to the shared drive folder for the new project."),
    (2, "Timesheet", "I missed punch yesterday and can't submit my timesheet."),
    (2, "help", ""),
    (1, "iPad replacement", "My iPad screen is cracked."),
]
MACHINE = [  # (weight, sender, subject)
    (10, "defender-noreply@microsoft.com", "Microsoft Defender: incident 4412 on a device"),
    (8, "monitoring@example.com", "Problem: host unreachable (ICMP ping)"),
    (4, "rmm@example.com", "Alert: [Disk space low] on WS-0142"),
    (3, "postmaster@example.com", "Undeliverable: Weekly report"),
    (3, "noreply@email.teams.microsoft.com", "You have 3 missed messages"),
    (5, "disableduser@example.com", "Disabled user: equipment return"),
    (3, "newhardwarerequest@example.com", "New Laptop Request - Analyst"),
    (2, "itreports@example.com", "Intune enrolled devices report"),
    (3, "", "V-Mail from +1 555 0100"),
]


def pick(items):
    return random.choices(items, weights=[w for w, *_ in items])[0][1:]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=6000); ap.add_argument("--out", default="sample/tickets.csv")
    ap.add_argument("--seed", type=int, default=7); a = ap.parse_args(); random.seed(a.seed)
    start = datetime(2025, 9, 1); rows = []
    people = [f"{f} {l}" for f in FIRST for l in LAST]
    for i in range(a.n):
        d = start + timedelta(days=random.random() * 365)
        if d.weekday() >= 5 and random.random() < 0.8:
            d -= timedelta(days=2)
        d = d.replace(hour=random.choices(range(24), weights=[1] * 6 + [6, 12, 11, 9, 8, 7, 6, 8, 7, 6, 4, 2] + [1] * 6)[0], minute=random.randrange(60))
        if random.random() < 0.55:
            subj, desc = pick(USER); who = random.choice(people)
            email = (who.lower().replace(" ", ".") + ("@gmail.com" if random.random() < 0.08 else "@example.com"))
            res = timedelta(hours=random.lognormvariate(1.6, 1.3))
        else:
            email, subj = pick(MACHINE); desc = ""; who = email.split("@")[0]
            res = timedelta(hours=random.lognormvariate(0.5, 1.0))
        resolved = d + res
        still_open = resolved > start + timedelta(days=365) or random.random() < 0.01
        rows.append({"system": "SAMPLE", "id": f"INC-{10000 + i}", "created": f"{d:%Y-%m-%d %H:%M:%S}",
                     "first_responded": f"{d + res * 0.2:%Y-%m-%d %H:%M:%S}", "resolved": "" if still_open else f"{resolved:%Y-%m-%d %H:%M:%S}",
                     "status": "Open" if still_open else "Closed", "technician": random.choice(TECHS), "group": random.choice(["Service Desk", "Assets", "Security"]),
                     "requester": who, "requester_email": email, "subject": subj, "description": desc,
                     "is_overdue": str(random.random() < 0.06).lower(), "is_fr_overdue": str(random.random() < 0.1).lower()})
    rows.sort(key=lambda r: r["created"])
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(len(rows), "synthetic tickets ->", a.out)


if __name__ == "__main__":
    main()
