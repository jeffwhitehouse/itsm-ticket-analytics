"""Tier rules. Ordered; first match wins. Org-specific senders and apps come from config."""
import re

R = lambda p: re.compile(p, re.I)

# ---- Tier 1: stream --------------------------------------------------------------------------
# Generic machine senders only. Your own monitoring, RMM, EDR and backup tools go in the config
# (`alert_sources` names them; `extra_alert_senders` just marks them as machine mail).
ALERT_SENDERS = (
    r"defender-noreply@microsoft\.com|mssecurity-noreply@microsoft\.com|office365alerts@microsoft\.com|azure-noreply@microsoft\.com|"
    r"no-reply@teams\.mail\.microsoft|noreply@email\.teams\.microsoft\.com|maccount@microsoft\.com|no-reply@sharepointonline\.com|"
    r"postmaster@|mailer-daemon@|microsoftexchange[0-9a-f]*@|msonlineservicesteam@|[^@]+@microsoftonline\.com|"
    r"alerts?@|monitoring@|backup@|noreply@github|noreply@zoom|"
    r"[^@]+@ups\.com|[^@]+@fedex\.com|do-?not-?reply@|no-?reply@|noreply@"
)
VOICEMAIL = R(r"^\s*((re|fw|fwd):\s*)*(v-?mail from|voice ?mail\b|voice message from)")
PHISH_REPORT = R(r"^\s*((re|fw|fwd):\s*)*\[phish alert\]")
ALERT_SUBJECT = R(
    r"^\s*((re|fw|fwd):\s*)*(problem:|resolved:|azure vm:|"
    r"junk:|not junk:|phishing:[0-9a-f-]+\||delivery status notification|undeliverable|automatic reply|out of office|"
    r"alert:|security alert|incident \d+|new incident|\d+ new alerts|.*vulnerability scan|weekly digest|daily digest|"
    r".*license alert|.*backup (job|failed|report)|mailbox usage report|.*detections? found|"
    r".*threat detected|break glass|your case \d+ has been created|"
    r"microsoft 365 defender has detected|\[(urgent|escalation)\] security training)"
)

# ---- Language (EN/ES) -------------------------------------------------------------------------
SPANISH = R(
    r"\b(hola|buenas|buenos d[ií]as|contrase[ñn]a|cuenta|bloquead[ao]|bloqueo|desbloque|ayuda|necesito|gracias|por favor|"
    r"no puedo|tengo|problema[s]? con|ingresar|ponche|nuev[ao]|correo|impresora|computadora|orientaci[oó]n|certificados|urgente|"
    r"saludos|mi nombre es|restablecer|acceder|iniciar sesi[oó]n|usuario|trabajo|horas|foto perfil|clave)\b"
)

# ---- Tier 2: user-ticket categories (category, subject_rx, description_rx) ---------------------
CATEGORY_RULES = [
    ("Campaign: re-image deadline", R(r"re-?image deadline|device re-?image|action required: re-?image"), None),
    ("Campaign: profile photo", R(r"missing profile picture|profile (picture|photo|pic)|head ?shot|foto( de)? perfil|\bphoto\b|\bpicture\b"),
     R(r"profile picture|head ?shot|foto de perfil|use this (photo|picture)|upload (a |my )?(picture|photo)")),
    ("Campaign: password expiry notice", R(r"password expir(ed|ation) (notice|- immediate)"), None),
    ("Security training question", R(r"assigned training|security (awareness )?training|training (is )?overdue|phishing (training|simulation)"),
     R(r"security awareness training|assigned training|phishing simulation")),
    ("Asset inventory / transfer / disposal", R(r"return cart|disposal list|equipment transfer|reassign(ed)? equipment|asset (tag|transfer|returns?)|lost/stolen|stolen laptop"),
     R(r"mark(ed)? .* as disposed|disposal list|please assign the following")),
    ("Door / badge / cameras", R(r"\bbadge\b|door access|key ?card|building access|\bfob\b|alarm code|door code|security cameras?|access control system"),
     R(r"\bbadge\b|door access|alarm code|access control system")),
    ("New hire onboarding", R(r"new hires?\b|new employee|onboard|first day|nuevos? empleados?|orientaci[oó]n|start(s|ing)? (on )?(monday|tuesday|wednesday|thursday|friday|\d)|re-?enable"),
     R(r"new hire|new employee|onboard|nuevo empleado|start(s|ing)? (on )?(monday|next week|\d{1,2}/\d)|(needs?|needing) to be enabled")),
    ("Offboarding / leave / termination", R(r"terminat|offboard|leave of absence|\bloa\b|on leave|return from leave|last day|disable (account|user)|separation|resign|no longer with|\bfmla\b"),
     R(r"terminated|last day (is|was|will be)|no longer (with|employed)|leave of absence|remove all access|\bfmla\b")),
    ("Equipment return / shipping label", R(r"shipping label|return label|equipment return|laptop return|ship(ping)? back|send (it )?back|devoluci[oó]n"),
     R(r"shipping label|return label|ship (it|the laptop|the equipment) back")),
    ("Password reset / account lockout",
     R(r"password|passcode|locked ?out|lock ?out|unlock|account (is |has been )?(locked|disabled|blocked)|reset my|can'?t (log|sign) ?in|cannot (log|sign) ?in|"
       r"unable to (log|sign) ?in|credential|expired|trouble logging|contrase[ñn]a|bloque|desbloque|\bclave\b|no puedo (ingresar|entrar|acceder|iniciar)|iniciar sesi[oó]n|olvid[eé] mi"),
     R(r"password|locked out|unlock|account (is |has been |was )?(locked|blocked|disabled)|can'?t (log|sign|get) ?in|unable to (log|sign) ?in|contrase[ñn]a|desbloque|restablecer")),
    ("MFA / Authenticator", R(r"\bmfa\b|authenticator|two[- ]factor|2fa|verification code|\bduo\b"), R(r"authenticator|\bmfa\b|two[- ]factor|verification code")),
    # line-of-business apps from config are inserted here
    ("CAD / design software", R(r"\bcad\b|autocad|auto cad|solidworks|sketchup|\bdwg\b"), R(r"\bcad\b|autocad|solidworks|sketchup")),
    ("Power BI", R(r"power ?bi\b"), R(r"power ?bi\b")),
    ("Adobe Acrobat", R(r"adobe|acrobat|\bpdf\b"), R(r"adobe|acrobat")),
    ("Label printer software", R(r"dymo|p-?touch|label (printer|maker|software)"), R(r"dymo|label printer")),
    ("Misc SaaS / license", R(r"smartsheet|visio|ms project|\blicense\b|licence|subscription|dropbox|docusign|power automate"),
     R(r"smartsheet|visio|dropbox|docusign")),
    ("AI tools (Copilot / ChatGPT)", R(r"copilot|chat ?gpt|openai|\bclaude\b|\bai\b|gemini"), R(r"copilot|chat ?gpt|openai|\bclaude\b")),
    ("Training platform access", R(r"\blms\b|training|learning|certificados?|certification|course"), R(r"training (course|module|platform|site|portal|account)")),
    ("HR / payroll / non-IT misroute", R(r"\badp\b|payroll|paycheck|pay ?stub|w-?2\b|benefits|\bhr\b|401k|\bpto\b|direct deposit|expense report|business cards|per diem|reimburse|out sick|calling off"),
     R(r"\badp\b|payroll|paycheck|pay ?stub|w-?2\b|direct deposit|expense report|out sick|calling off|no me han pagado")),
    ("Email signature", R(r"signature"), R(r"email signature")),
    ("Distribution list / shared mailbox", R(r"distribution (list|group)|dist\.? list|\bdl\b|distro|shared (mailbox|inbox)|mailbox access|add .* to (the )?(dl|list|group)"),
     R(r"distribution (list|group)|\bdistro\b|shared (mailbox|inbox)|add (me|him|her|them) to the (dl|list|distribution)")),
    ("Microsoft Teams", R(r"\bteams\b|meeting room|conference room|transcription"), R(r"microsoft teams|ms teams|teams (meeting|call|room|app)|\bin teams\b")),
    ("SharePoint / OneDrive", R(r"share ?point|one ?drive|sync(ing)? (issue|problem|error)|file (link|sharing)"), R(r"share ?point|one ?drive|share (a|the) (file|folder|link)")),
    ("Windows / OS / device settings", R(r"windows update|bitlocker|recovery key|time ?zone|operating system|\bwindows 1[01]\b|display settings"), R(r"bitlocker|recovery key|windows update|time ?zone")),
    ("Outlook / email", R(r"outlook|not receiving|can'?t send|mailbox (is )?(full|almost)|inbox|calendar|bounce|quarantin|junk (mail|folder)|\bcorreo\b|^e-?mails?\W*$"),
     R(r"\boutlook\b|not receiving (any )?e-?mails?|can'?t send e-?mails?|mailbox (is )?full|emails? (are |is )?(not|bouncing|stuck|missing|going to junk)")),
    ("Excel / Office apps", R(r"excel|\bword\b|powerpoint|macro|office (365|apps?|install)|onenote"), R(r"\bexcel\b|macro|powerpoint|onenote")),
    ("Network drive / file share", R(r"\b[pst]:? ?-?drive\b|shared drive|network drive|mapped drive|file share|folder access|shared folder|restore (a )?deleted|deleted file|recover (a )?file"),
     R(r"network drive|mapped drive|shared drive|folder (access|permission)|file was deleted|restore (a |the )?(deleted )?file")),
    ("VPN / remote access / travel", R(r"\bvpn\b|zero trust|\bztna\b|out\.? ?of (the )?country|international travel|overseas|remote access"),
     R(r"\bvpn\b|zero trust|out of (the )?country|travel(ing|ling)? (to|abroad|internationally)")),
    ("Site network / internet / hotspot", R(r"hot ?spot|internet (at|for|on|is|down|access|connection|outage)|no internet|slow internet|wi-?fi|wireless|network (down|issue|outage|slow)|static ip|router|firewall|connectivity"),
     R(r"hot ?spot|internet (is )?(down|out|not working)|no internet|wi-?fi (is )?(down|not)|new office")),
    ("Phone / voicemail system", R(r"voice ?mail|phone system|extension|desk phone|call forward|caller id"), R(r"desk phone|voicemail box|call forward|extension \d")),
    ("iPad / tablet / mobile", R(r"i-? ?pad|tablet|i-?phone|cell ?phone|mobile (device|phone)|apple (id|pencil)|android|smartphone"), R(r"i-? ?pad|tablet|i-?phone|cell ?phone|apple id")),
    ("Printers / plotters / scanners", R(r"print|plotter|scan(ner|ning)?\b|toner|copier|designjet|\bink\b|impresora"), R(r"print(er|ing)|plotter|scanner|toner|impresora")),
    ("Laptop request / replacement / swap",
     R(r"(new|replacement|another|second|loaner|spare|upgraded?) (laptop|computer|pc|desktop)|laptop (request|swap|replacement|upgrade|order)|need a (laptop|computer)|request(ing)? (a |for )?(laptop|computer)|^new laptop$"),
     R(r"(new|replacement|another|loaner|upgraded?) (laptop|computer|pc)|laptop (request|swap|replacement|order)|need a (new )?(laptop|computer)|order(ing)? (a |an |new )?laptop")),
    ("Monitors / docks / peripherals", R(r"monitor|dock(ing)?|headset|head ?phones?|\bmouse\b|webcam|\bcable\b|adapter|dongle|hdmi|keyboard|charger|power (cord|adapter)"),
     R(r"monitor|dock(ing)? station|headset|webcam|keyboard and mouse|charger|power (cord|adapter)")),
    ("Laptop / PC hardware or performance",
     R(r"laptop|computer|\bpc\b|desktop|screen|touch ?pad|battery|blue ?screen|bsod|won'?t (turn|boot|power|start)|not (booting|charging)|\bslow\b|freez|crash|overheat|black screen|cracked|broken|microphone|audio|computadora|warranty"),
     R(r"laptop (is|won'?t|will not|keeps|has|screen|battery)|blue ?screen|won'?t (turn on|boot|power on)|black screen|cracked screen|running (very )?slow|keeps (freezing|crashing|restarting)|warranty")),
    ("Software install / admin rights", R(r"install|remote desk ?top|quick assist|admin(istrator)? (rights|access|privilege)|elevat|download|software|application|\bapps?\b|program|update|upgrade|uninstall|plugin|add-?in|driver|browser|java|zoom|activation"),
     R(r"install(ing|ed)?\b|admin(istrator)? (rights|access|privilege)|download(ing|ed)? (the )?(software|program|app)|need (the )?software|activation")),
    ("USB / removable media", R(r"\busb\b|flash drive|thumb drive|external (hard )?drive|removable|sd card"), R(r"\busb\b (drive|stick|port|is blocked)|flash drive|external (hard )?drive")),
    ("Re-image / rebuild", R(r"re-?imag|rebuild|factory reset|fresh install|\bwipe\b"), R(r"re-?imag|factory reset|wipe (the|my) (laptop|computer)")),
    ("Suspicious email / phishing question", R(r"phish|suspicious|\bscam\b|\bspam\b|is this (legit|real|safe)|fraud|hacked|compromise|\bvirus\b|malware|pop-?up"),
     R(r"phishing|suspicious (e-?mail|message|text)|is this (legit|legitimate|real|safe|a scam)|\bscam\b|hacked|malware")),
    ("Directory / name / contact updates", R(r"name change|last name|title (change|update)|update (my )?(name|title|phone|contact)|directory|display name|preferred name"),
     R(r"name change|update (my )?(title|phone number|contact)|display name|preferred name")),
    # generic fallbacks (subject only)
    ("Access request (generic)", R(r"\baccess\b|permission|log ?in|\baccount\b|credentials|enroll|invite|add me|remove me|user ?name|\bcuenta\b|\bacceso\b"), None),
    ("Equipment request (generic)", R(r"equipment|supplies|need (a|an|new|some)\b|request(ing)?\b|\border\b|purchase|\bbuy\b|quote"), None),
    ("Help / question (uninformative subject)", R(r"^\W*(help|question|issue|issues|problem|error|urgent|urgente|it help|it support|support|assistance|request|ticket|hello|hi|hola|ayuda|good morning|test|quick question|follow up)\W*\d*\W*$"), None),
]
GENERIC = {"Access request (generic)", "Equipment request (generic)", "Help / question (uninformative subject)"}
NAME_ONLY = R(r"^(fw:|re:)?\s*[A-Za-z][a-z'\-]+(,? [A-Za-z][a-z'\-\.]+){1,3}$")
REQUEST_WORDS = R(r"(new|replacement|another|loaner|upgraded?) (laptop|computer|pc)|laptop (request|swap|replacement|order)|need a (new )?(laptop|computer)|"
                  r"order(ing)? (a |an |new )?(laptop|monitor|dock|ipad|headset)|would like (a|to (order|request|get))|can i (get|order|have)|purchase|quote")

WORKTYPE = {
    "Password reset / account lockout": "Access & identity", "MFA / Authenticator": "Access & identity", "Access request (generic)": "Access & identity",
    "Distribution list / shared mailbox": "Access & identity", "Network drive / file share": "Access & identity", "Door / badge / cameras": "Access & identity",
    "New hire onboarding": "Joiner / mover / leaver", "Offboarding / leave / termination": "Joiner / mover / leaver",
    "Equipment return / shipping label": "Joiner / mover / leaver", "Directory / name / contact updates": "Joiner / mover / leaver",
    "Asset inventory / transfer / disposal": "Joiner / mover / leaver",
    "Laptop request / replacement / swap": "Equipment orders & fulfillment", "Monitors / docks / peripherals": "Equipment orders & fulfillment",
    "iPad / tablet / mobile": "Equipment orders & fulfillment", "Site network / internet / hotspot": "Equipment orders & fulfillment",
    "Equipment request (generic)": "Equipment orders & fulfillment",
    "Laptop / PC hardware or performance": "Break/fix support", "Printers / plotters / scanners": "Break/fix support", "Outlook / email": "Break/fix support",
    "Microsoft Teams": "Break/fix support", "SharePoint / OneDrive": "Break/fix support", "Windows / OS / device settings": "Break/fix support",
    "Re-image / rebuild": "Break/fix support", "Phone / voicemail system": "Break/fix support", "Excel / Office apps": "Break/fix support",
    "VPN / remote access / travel": "Break/fix support", "USB / removable media": "Break/fix support",
    "Training platform access": "Line-of-business apps", "HR / payroll / non-IT misroute": "Line-of-business apps",
    "CAD / design software": "Software & licensing", "Power BI": "Software & licensing", "Adobe Acrobat": "Software & licensing",
    "Label printer software": "Software & licensing", "Misc SaaS / license": "Software & licensing", "AI tools (Copilot / ChatGPT)": "Software & licensing",
    "Software install / admin rights": "Software & licensing", "Email signature": "Software & licensing",
    "Suspicious email / phishing question": "Security", "Security training question": "Security",
    "Campaign: re-image deadline": "IT campaign responses", "Campaign: profile photo": "IT campaign responses", "Campaign: password expiry notice": "IT campaign responses",
}
STREAM_WORKTYPE = {"alert": "Monitoring & machine mail", "process": "Lifecycle automation streams", "voicemail": "Voicemail callbacks", "phish-report": "Security"}


def alert_category(email, subj, sources=()):
    """Name the machine-mail source. Config `alert_sources` are tried first, then the generic
    built-ins below. Order matters: specific before generic."""
    e, s = email.lower(), subj
    for label, sender_rx, subject_rx in sources:
        if (sender_rx and sender_rx.search(e)) or (subject_rx and subject_rx.search(s)):
            return label
    checks = [
        (lambda: re.search(r"break glass", s, re.I), "Alert: break-glass account sign-in"),
        (lambda: re.search(r"security training", s, re.I), "Alert: security-training overdue blast"),
        (lambda: e.startswith(("defender-noreply", "mssecurity")) or re.search(r"\bmdi\b|incident \d+|defender", s, re.I), "Alert: Microsoft Defender / MDI"),
        (lambda: re.search(r"^(problem|resolved):|icmp ping|host (is )?(down|unreachable)", s, re.I), "Alert: infrastructure monitoring"),
        (lambda: e.startswith(("office365alerts", "azure-noreply", "no-reply@microsoft")) or e.endswith("microsoftonline.com") or re.search(r"mailbox usage report", s, re.I), "Alert: Microsoft 365 / Azure"),
        (lambda: re.search(r"threat detected|detections? found", s, re.I), "Alert: endpoint security"),
        (lambda: re.search(r"backup (job|failed|report)", s, re.I), "Alert: backup"),
        (lambda: re.search(r"vulnerability scan", s, re.I), "Alert: vulnerability scan"),
        (lambda: re.search(r"^phishing:[0-9a-f-]+\|", s, re.I), "Alert: Outlook phishing submission"),
        (lambda: re.search(r"^(junk|not junk):", s, re.I), "Alert: Outlook junk submission"),
        (lambda: e.startswith(("no-reply@teams", "noreply@email.teams")), "Noise: Teams missed-activity mail"),
        (lambda: re.search(r"delivery status notification|undeliverable|automatic reply|out of office", s, re.I) or e.startswith(("postmaster", "mailer-daemon", "microsoftexchange")), "Noise: bounces / auto-replies"),
        (lambda: e.endswith(("ups.com", "fedex.com")), "Noise: shipping carrier notifications"),
        (lambda: re.search(r"your case \d+ has been created", s, re.I), "Noise: vendor case auto-acks"),
    ]
    for test, label in checks:
        if test():
            return label
    return "Alert: other machine mail"
