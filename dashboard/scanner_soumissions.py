#!/usr/bin/env python3
"""
Scanner IMAP — Dossiers Solarium Pro
Télécharge les PDF joints aux alertes "alerte nouveau dossier" et parse les champs.
Écrit dans {CONFIG["chemins"]["dashboard"]}/soumissions.json
"""
import email, re, os, imaplib, json, io, sys
from datetime import datetime, timedelta
from email.header import decode_header

CONFIG = json.load(open(os.path.expanduser("~/prospect2-master/config.json")))

IMAP_SERVER      = CONFIG["emails"]["imap_host"]
IMAP_PORT        = CONFIG["emails"]["imap_port"]
IMAP_USER        = CONFIG["emails"]["reception"]
IMAP_PASS        = CONFIG["emails"]["imap_password"]
DOSSIER          = os.path.join(CONFIG["chemins"]["base"], CONFIG["chemins"]["dashboard"])
SOUMISSIONS_JSON = os.path.join(DOSSIER, "soumissions.json")

def decode_str(s):
    if s is None: return ""
    parts = decode_header(s); result = ""
    for part, enc in parts:
        if isinstance(part, bytes): result += part.decode(enc or "utf-8", errors="replace")
        else: result += part
    return result

def load_soumissions():
    if not os.path.exists(SOUMISSIONS_JSON): return []
    with open(SOUMISSIONS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

SOUMISSIONS_JS = os.path.join(DOSSIER, "soumissions.js")

GENERER_SCRIPT = os.path.join(DOSSIER, "generer_dashboard.py")

def save_soumissions(data):
    with open(SOUMISSIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Écrire soumissions.js (utilisé par update_statut.py et le mode http)
    js_content = "var _SOUM_DATA = " + json.dumps(data, ensure_ascii=False) + ";"
    with open(SOUMISSIONS_JS, "w", encoding="utf-8") as f:
        f.write(js_content)
    # Regénérer le dashboard pour inliner les nouvelles données
    import subprocess, sys as _sys
    subprocess.Popen([_sys.executable, GENERER_SCRIPT],
                     stdout=open('/tmp/gen_dashboard.log', 'w'),
                     stderr=subprocess.STDOUT)

def champ(texte, *labels):
    for label in labels:
        m = re.search(r'(?:' + re.escape(label) + r')\s*[:\-]?\s*(.+?)(?=\n|$)',
                      texte, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val: return val
    return ""

def parser_pdf(pdf_bytes):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        return {"parse_error": str(e)}

    m_no = re.search(r'(SP-P\d+)', texte, re.IGNORECASE)
    no_projet = m_no.group(1).upper() if m_no else ""

    nom_projet   = champ(texte, "Nom du projet", "Nom projet", "Projet")
    client       = champ(texte, "Nom du client", "Client", "Nom client")
    adresse      = champ(texte, "Adresse du client", "Adresse client", "Adresse")
    telephone    = champ(texte, "Téléphone du client", "Telephone du client",
                         "Téléphone", "Telephone", "Tel", "Tél")
    type_travaux = champ(texte, "Type de travaux", "Type travaux", "Travaux")

    m_desc = re.search(r'[Dd]escription\s*[:\-]?\s*(.+)', texte, re.DOTALL)
    description = m_desc.group(1).strip()[:800] if m_desc else ""

    return {
        "no_projet":     no_projet,
        "nom_projet":    nom_projet,
        "client":        client,
        "adresse":       adresse,
        "telephone":     telephone,
        "type_travaux":  type_travaux,
        "description":   description,
    }

def scanner():
    existants    = load_soumissions()
    ids_existants = {s["msg_id"] for s in existants}
    # Clés de déduplication secondaire : nom_projet + telephone + date (YYYY-MM-DD)
    def cle_secondaire(s):
        date_brute = s.get("date_reception", "")
        date_courte = date_brute[:16] if date_brute else ""
        return (s.get("nom_projet", "").strip().lower(),
                s.get("telephone", "").strip(),
                date_courte)
    cles_secondaires = {cle_secondaire(s) for s in existants}
    nouveaux     = 0
    try:
        m = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        m.login(IMAP_USER, IMAP_PASS)
        m.select("INBOX")
        depuis = (datetime.now() - timedelta(days=14)).strftime("%d-%b-%Y")
        _, ids = m.search(None, f'(SINCE "{depuis}" SUBJECT "alerte nouveau dossier")')
        for uid in ids[0].split():
            _, data = m.fetch(uid, "(RFC822)")
            msg    = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", uid.decode())
            if msg_id in ids_existants: continue

            sujet    = decode_str(msg.get("Subject", ""))
            date_msg = msg.get("Date", "")

            # Chercher la pièce jointe PDF
            pdf_bytes = None
            pdf_nom   = ""
            for part in msg.walk():
                ct = part.get_content_type()
                cd = part.get("Content-Disposition", "")
                fn = decode_str(part.get_filename(""))
                if ct == "application/pdf" or (cd and "attachment" in cd and ".pdf" in fn.lower()):
                    pdf_bytes = part.get_payload(decode=True)
                    pdf_nom   = fn
                    break

            champs = parser_pdf(pdf_bytes) if pdf_bytes else {}

            # Fallback client depuis le sujet
            if not champs.get("client"):
                m2 = re.search(r"alerte nouveau dossier[^\-\—]*[\-\—]\s*(.+)", sujet, re.IGNORECASE)
                champs["client"] = m2.group(1).strip()[:80] if m2 else sujet[:80]

            # Déduplication secondaire : nom_projet + telephone + date
            entree = {
                "msg_id":         msg_id,
                "sujet":          sujet,
                "pdf_nom":        pdf_nom,
                "date_reception": date_msg,
                "statut":         "À faire",
                "date_statut":    datetime.now().isoformat(),
                **champs,
            }
            cle2 = cle_secondaire(entree)
            if cle2[0] and cle2 in cles_secondaires: continue

            existants.append(entree)
            ids_existants.add(msg_id)
            cles_secondaires.add(cle2)
            nouveaux += 1
        m.logout()
    except Exception as e:
        print(f"Erreur IMAP: {e}", file=sys.stderr)
        sys.exit(1)

    save_soumissions(existants)
    print(json.dumps({"ok": True, "nouveaux": nouveaux}))

if __name__ == "__main__":
    scanner()
