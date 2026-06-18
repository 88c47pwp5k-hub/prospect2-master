import os, pickle, smtplib, imaplib, email, msal, requests, json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG = json.load(open(os.path.expanduser("~/prospect2-master/config.json")))

DOSSIER      = os.path.dirname(os.path.abspath(__file__))
GOOGLE_CREDS = os.path.join(DOSSIER, "credentials.json")
TOKEN_FILE   = os.path.join(DOSSIER, "token.pickle")
TODO_TOKEN   = os.path.join(DOSSIER, "todo_token.json")
SOUMISSIONS  = os.path.join(CONFIG["chemins"]["base"], CONFIG["chemins"]["dashboard"], "soumissions.json")
EMAIL_FROM   = CONFIG["emails"]["envoi_gmail"]
EMAIL_TO     = CONFIG["emails"]["reception"]
SCOPES_GG    = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/contacts",
]
IMAP_SERVER  = CONFIG["emails"]["imap_host"]
IMAP_PORT    = CONFIG["emails"]["imap_port"]
IMAP_USER    = CONFIG["emails"]["reception"]
IMAP_PASS    = CONFIG["emails"]["imap_password"]
ANTHROPIC_KEY= CONFIG["emails"]["anthropic_key"]
MS_CLIENT_ID = CONFIG["microsoft"]["client_id"]
JOURS_FR     = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
MOIS_FR      = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

def date_fr():
    n = datetime.now()
    return f"{JOURS_FR[n.weekday()]} {n.day} {MOIS_FR[n.month-1]} {n.year}"

def get_gcreds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE,"rb") as f: creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDS, SCOPES_GG)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE,"wb") as f: pickle.dump(creds, f)
    return creds

def get_events():
    service = build("calendar","v3",credentials=get_gcreds())
    now = datetime.now(timezone.utc)
    debut = now.replace(hour=0,minute=0,second=0).isoformat()
    fin   = now.replace(hour=23,minute=59,second=59).isoformat()
    cals  = service.calendarList().list().execute().get("items",[])
    all_events = []
    seen = set()
    for cal in cals:
        try:
            res = service.events().list(calendarId=cal["id"],timeMin=debut,timeMax=fin,singleEvents=True,orderBy="startTime").execute()
            for e in res.get("items",[]):
                if e["id"] not in seen:
                    seen.add(e["id"])
                    e["_cal_name"] = cal.get("summary","")
                    all_events.append(e)
        except: pass
    all_events.sort(key=lambda e: e["start"].get("dateTime",e["start"].get("date","")))
    return all_events

def get_todo():
    cache = msal.SerializableTokenCache()
    with open(TODO_TOKEN,"r") as f: cache.deserialize(f.read())
    app = msal.PublicClientApplication(MS_CLIENT_ID, authority="https://login.microsoftonline.com/consumers", token_cache=cache)
    accounts = app.get_accounts()
    result = app.acquire_token_silent(["Tasks.Read"], account=accounts[0])
    token = result["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    listes = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=h).json()
    ignorer = ["Tâches","Liste sans titre","Liste sans titre 1","Liste sans titre 1 (1)","Flagged Emails"]
    groupes = {}
    total = 0
    for l in listes.get("value",[]):
        nom = l["displayName"]
        if nom in ignorer: continue
        taches = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{l['id']}/tasks", headers=h).json()
        items = [t for t in taches.get("value",[]) if t.get("status") != "completed"]
        if items:
            groupes[nom] = items
            total += len(items)
    with open(TODO_TOKEN,"w") as f: f.write(cache.serialize())
    return groupes, total

def get_soumissions():
    with open(SOUMISSIONS,"r",encoding="utf-8") as f: data = json.load(f)
    result = []
    for s in data:
        if s.get("statut") != "À faire": continue
        nom    = s.get("nom_projet","") or s.get("client","") or s.get("type_travaux","")
        no     = s.get("no_projet","")
        type_t = s.get("type_travaux","")
        date_r = s.get("date_reception","")
        delai_h = None
        if date_r:
            try:
                from email.utils import parsedate_to_datetime; d = parsedate_to_datetime(date_r)
                delai_h = int((datetime.now(timezone.utc)-d).total_seconds()/3600)
            except: pass
        result.append({"nom":nom,"no":no,"type":type_t,"delai_h":delai_h})
    return result

def decode_str(s):
    if s is None: return ""
    parts = decode_header(s)
    out = ""
    for part,enc in parts:
        if isinstance(part,bytes): out += part.decode(enc or "utf-8",errors="replace")
        else: out += part
    return out

def get_flagged_emails():
    courriels = []
    try:
        import socket
        socket.setdefaulttimeout(10)
        m = imaplib.IMAP4_SSL(IMAP_SERVER,IMAP_PORT,timeout=30)
        m.login(IMAP_USER,IMAP_PASS)
        m.select("INBOX")
        import time
        from imaplib import Time2Internaldate
        since=time.strftime("%d-%b-%Y",time.gmtime(time.time()-7*24*3600))
        _,ids = m.search(None,"FLAGGED","SINCE",since)
        for uid in ids[0].split()[-10:]:
            _,data = m.fetch(uid,"(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            sujet = decode_str(msg.get("Subject",""))
            exp   = decode_str(msg.get("From",""))
            date_msg = msg.get("Date","")
            corps = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type()=="text/plain":
                        corps = part.get_payload(decode=True).decode("utf-8",errors="replace")[:2000]
                        break
            else:
                corps = msg.get_payload(decode=True).decode("utf-8",errors="replace")[:2000]
            courriels.append({"sujet":sujet,"expediteur":exp,"date":date_msg,"corps":corps})
        m.logout()
    except Exception as e:
        print(f"⚠️ IMAP: {e}")
    return courriels

def extraire_contact(courriel):
    prompt = f"""Analyse ce courriel et extrait les informations du fournisseur/expéditeur s'il y en a une signature professionnelle.
Retourne UNIQUEMENT un JSON avec: nom, compagnie, telephone, email
Si pas de signature professionnelle claire, retourne: null

Courriel:
De: {courriel['expediteur']}
Contenu: {courriel['corps']}"""
    for tentative in range(2):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":200,"messages":[{"role":"user","content":prompt}]},
                timeout=30)
            texte = r.json()["content"][0]["text"].strip()
            if texte == "null": return None
            texte = texte.replace("```json","").replace("```","").strip()
            return json.loads(texte)
        except requests.exceptions.Timeout:
            print(f"⚠️ extraire_contact timeout (tentative {tentative+1}/2)")
        except Exception:
            return None
    return None

def gerer_contacts(courriels):
    nouveaux = []
    existants = []
    emails_traites = set()
    try:
        service = build("people","v1",credentials=get_gcreds())
        # Récupérer emails existants
        conn = service.people().connections().list(
            resourceName="people/me", pageSize=1000,
            personFields="names,emailAddresses,organizations,phoneNumbers"
        ).execute()
        emails_connus = {}
        for c in conn.get("connections",[]):
            for e in c.get("emailAddresses",[]):
                emails_connus[e.get("value","").lower()] = c
        for courriel in courriels:
            contact = extraire_contact(courriel)
            if not contact: continue
            nom=(contact.get("nom","") or "").strip()
            if not nom or nom.lower()=="none": continue
            email_c = (contact.get("email","") or "").lower().strip()
            if not email_c: continue
            if email_c in emails_traites: continue
            emails_traites.add(email_c)
            if email_c in emails_connus:
                existants.append(contact)
            else:
                # Créer le contact
                body = {"names":[{"givenName":contact.get("nom","")}]}
                if contact.get("email"):
                    body["emailAddresses"] = [{"value":contact["email"]}]
                if contact.get("telephone"):
                    body["phoneNumbers"] = [{"value":contact["telephone"]}]
                if contact.get("compagnie"):
                    body["organizations"] = [{"name":contact["compagnie"]}]
                try:
                    service.people().createContact(body=body).execute()
                    nouveaux.append(contact)
                except Exception as e:
                    print(f"⚠️ Création contact: {e}")
    except Exception as e:
        print(f"⚠️ Contacts: {e}")
    return nouveaux, existants

def analyser_courriel(c):
    prompt = f"""Assistant de Benoit Dupuis, Solarium Pro Granby QC (solariums alu: Aika, Cover, Néoscenica, Esthétika).
Courriel flaggé — De: {c['expediteur']} | Sujet: {c['sujet']}
Contenu: {c['corps'][:500]}
2-3 lignes: 1. Résumé 2. Action recommandée. Français québécois informel."""
    for tentative in range(2):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":200,"messages":[{"role":"user","content":prompt}]},
                timeout=30)
            return r.json()["content"][0]["text"]
        except requests.exceptions.Timeout:
            print(f"⚠️ analyser_courriel timeout (tentative {tentative+1}/2)")
        except Exception as e:
            return f"Analyse non disponible ({e})"
    return "Analyse non disponible (timeout)"

def envoyer_email(events, groupes_todo, total_todo, soumissions, courriels, nouveaux_contacts, existants_contacts):
    today = date_fr()

    # Rendez-vous
    rows_rdv = ""
    for e in events:
        debut = e["start"].get("dateTime",e["start"].get("date",""))
        heure = datetime.fromisoformat(debut.replace("Z","+00:00")).astimezone().strftime("%H:%M") if "T" in debut else "Toute la journée"
        cal = e.get("_cal_name","")
        rows_rdv += f"<tr><td style='padding:8px;color:#1F3864;font-weight:bold;width:70px'>{heure}</td><td style='padding:8px'>{e.get('summary','Sans titre')}</td><td style='padding:8px;color:#888;font-size:12px'>{cal}</td></tr>"
    if not rows_rdv:
        rows_rdv = "<tr><td colspan='3' style='padding:8px;color:#999'>Aucun rendez-vous aujourd'hui</td></tr>"

    # To Do
    html_todo = ""
    for nom,items in groupes_todo.items():
        html_todo += f"<div style='color:#C68B00;font-weight:bold;margin:10px 0 4px'>{nom}</div>"
        for t in items:
            html_todo += f"<div style='margin-bottom:4px'>💡 {t.get('title','')}</div>"
    if not html_todo:
        html_todo = "<p style='color:#999'>Aucune tâche</p>"

    # Soumissions
    html_soum = ""
    if soumissions:
        cards = ""
        for s in soumissions:
            delai = f" <span style='color:#e74c3c;font-weight:bold'>({s['delai_h']//24}j)</span>" if s.get("delai_h") and s["delai_h"]>0 else ""
            cards += f"<div style='border-left:3px solid #e74c3c;padding:8px 12px;margin-bottom:6px;background:#fff5f5'><b>{s['nom']}{delai}</b><div style='color:#888;font-size:12px'>{s['no']} · {s['type']}</div></div>"
        html_soum = f"<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px;margin-top:28px'>📋 Soumissions à faire ({len(soumissions)})</h2>{cards}"

    # Contacts fournisseurs
    html_contacts = ""
    if nouveaux_contacts or existants_contacts:
        cards = ""
        if nouveaux_contacts:
            cards += "<div style='color:#27ae60;font-weight:bold;margin:8px 0 4px'>Nouveaux</div>"
            for c in nouveaux_contacts:
                cards += f"<div style='background:#f0fff4;border-left:3px solid #27ae60;padding:8px 12px;margin-bottom:6px'><b>🖨 {c.get('nom','')}</b><div style='color:#555;font-size:12px'>{c.get('compagnie','')} · {c.get('telephone','')} · {c.get('email','')}</div></div>"
        if existants_contacts:
            cards += "<div style='color:#888;font-weight:bold;margin:8px 0 4px'>Déjà existants</div>"
            for c in existants_contacts:
                cards += f"<div style='background:#f8f9fa;border-left:3px solid #ccc;padding:8px 12px;margin-bottom:6px'><b style='color:#888'>🖨 {c.get('nom','')}</b><div style='color:#aaa;font-size:12px'>{c.get('compagnie','')} · {c.get('email','')}</div></div>"
        html_contacts = f"<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px;margin-top:28px'>🖨 Contacts fournisseurs ({len(nouveaux_contacts)+len(existants_contacts)})</h2>{cards}"

    # Courriels flaggés
    html_courriels = ""
    if courriels:
        cards = ""
        for c in courriels:
            analyse = analyser_courriel(c)
            cards += f"<div style='background:#f8f9fa;border-left:4px solid #C68B00;padding:12px;margin-bottom:10px;border-radius:4px'><b style='color:#1F3864'>📧 {c['sujet']}</b><div style='color:#666;font-size:12px;margin:4px 0'>De: {c['expediteur']}</div><div style='color:#333;font-size:13px;margin-top:6px'>{analyse}</div></div>"
        html_courriels = f"<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px;margin-top:28px'>🚩 Courriels flaggés ({len(courriels)})</h2>{cards}"
    else:
        html_courriels = "<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px;margin-top:28px'>🚩 Courriels flaggés</h2><p style='color:#999'>Aucun courriel flaggé</p>"

    html = f"""<div style='font-family:Arial,sans-serif;max-width:650px;margin:auto'>
<div style='background:#1F3864;padding:24px;text-align:center'>
<h1 style='color:white;margin:0;letter-spacing:2px'>SOLARIUM PRO</h1>
<p style='color:#C68B00;margin:6px 0 0'>Résumé du {today}</p>
</div>
<div style='padding:24px'>
<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px'>📅 Rendez-vous du jour</h2>
<table width='100%' style='border-collapse:collapse'>{rows_rdv}</table>
<h2 style='color:#1F3864;border-bottom:2px solid #C68B00;padding-bottom:8px;margin-top:28px'>💡 Idées & To Do ({total_todo})</h2>
{html_todo}
{html_soum}
{html_contacts}
{html_courriels}
</div>
<div style='background:#1F3864;padding:12px;text-align:center'>
<p style='color:#C68B00;margin:0;font-size:12px'>Solarium Pro · Bonne journée Benoit! 💪</p>
</div>
</div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ Résumé du {today}"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html,"html"))
    with smtplib.SMTP_SSL("smtp.gmail.com",465) as s:
        s.login(EMAIL_FROM, CONFIG["emails"]["gmail_app_password"])
        s.sendmail(EMAIL_FROM,EMAIL_TO,msg.as_string())
    print("✅ Courriel envoyé!")

if __name__ == "__main__":
    import time
    _t0 = time.time()
    def _chrono(label, fn, *args, **kwargs):
        t = time.time()
        result = fn(*args, **kwargs)
        print(f"   ⏱ {time.time()-t:.1f}s")
        return result

    print("📅 Calendriers...")
    events = _chrono("calendriers", get_events)
    print(f"   {len(events)} événement(s)")
    print("✅ Microsoft To Do...")
    groupes_todo, total_todo = _chrono("todo", get_todo)
    print(f"   {total_todo} tâche(s)")
    print("📋 Soumissions...")
    soumissions = _chrono("soumissions", get_soumissions)
    print(f"   {len(soumissions)} à faire")
    print("🚩 Courriels flaggés...")
    courriels = _chrono("imap", get_flagged_emails)
    print(f"   {len(courriels)} flaggé(s)")
    print("🖨 Contacts fournisseurs...")
    nouveaux, existants = _chrono("contacts", gerer_contacts, courriels)
    print(f"   {len(nouveaux)} nouveau(x), {len(existants)} existant(s)")
    print("📧 Envoi...")
    _chrono("envoi", envoyer_email, events, groupes_todo, total_todo, soumissions, courriels, nouveaux, existants)
    print(f"⏱ Total : {time.time()-_t0:.1f}s")
