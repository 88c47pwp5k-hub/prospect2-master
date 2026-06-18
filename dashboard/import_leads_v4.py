import email, re, os, imaplib, openpyxl, json
from datetime import datetime, timedelta
from email.header import decode_header

CONFIG = json.load(open(os.path.expanduser("~/prospect2-master/config.json")))

FICHIER_XLSX = os.path.join(CONFIG["chemins"]["base"], CONFIG["chemins"]["dashboard"], "Leads_2026.xlsx")
FICHIER_JSON = os.path.join(CONFIG["chemins"]["base"], CONFIG["chemins"]["dashboard"], "leads_dashboard.json")

IMAP_SERVER = CONFIG["emails"]["imap_host"]
IMAP_PORT   = CONFIG["emails"]["imap_port"]

COMPTES = [
    {"user": CONFIG["emails"]["reception"], "password": CONFIG["emails"]["imap_password"], "source": "Site web"},
]

REGION_MAP = {
    "514": "Grand Montréal", "438": "Grand Montréal",
    "450": "Rive-Sud", "579": "Rive-Sud",
    "819": "Estrie/Mauricie", "873": "Estrie/Mauricie",
    "418": "Québec/Régions", "581": "Québec/Régions",
}

def get_region(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    return REGION_MAP.get(digits[:3], "Autre")

def decode_str(s):
    if s is None: return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes): result += part.decode(enc or "utf-8", errors="replace")
        else: result += part
    return result

def extraire_texte(msg):
    corps = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    corps = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            corps = payload.decode("utf-8", errors="replace")
    return corps

LABELS_INVALIDES = {
    "et nom de famille", "and last name", "de famille", "complet", "full name",
    "prénom", "prenom", "nom de famille", "first name", "last name",
    "votre nom", "your name", "nom complet", "enter name", "enter your name",
}

def is_nom_invalide(nom):
    n = nom.strip().lower()
    if len(n) < 2:
        return True
    if n in LABELS_INVALIDES:
        return True
    if any(label in n for label in LABELS_INVALIDES):
        return True
    if n.startswith("et ") or n.startswith("and "):
        return True
    return False


def strip_html(s):
    return re.sub(r'<[^>]+>', '', s).strip()

def parser_courriel(msg, source):
    corps = extraire_texte(msg)

    def ex(pattern):
        m = re.search(pattern, corps, re.IGNORECASE)
        return strip_html(m.group(1).strip()) if m else ""

    # Format texte: "Nom: Prénom Nom" (requiert ':' pour éviter les libellés)
    nom = ex(r"(?:pr[eé]nom\s+et\s+nom(?:\s+de\s+famille)?|nom\s+complet|full\s+name|nom|name)\s*:\s*([^\n\r<]+)")
    if is_nom_invalide(nom):
        nom = ""
    # Format HTML: <b>Prénom et nom de famille</b><br />Valeur
    if not nom:
        m = re.search(r'<b>(?:pr[eé]nom\s+et\s+nom(?:\s+de\s+famille)?|nom\s+complet|nom)[^<]*</b><br\s*/?>\s*([^<\n]+)', corps, re.IGNORECASE)
        if m:
            nom = strip_html(m.group(1).strip())
    tel     = ex(r"(?:num[eé]ro|t[eé]l[eé]phone?|tel|phone|cell)[:\s]*([(\d][0-9()\s\-\.]{8,})")
    if not tel:
        m = re.search(r"\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}", corps)
        if m: tel = m.group(0)
    if not tel:
        m = re.search(r'<b>(?:t[eé]l[eé]phone?|num[eé]ro)[^<]*</b><br\s*/?>\s*([^<\n]+)', corps, re.IGNORECASE)
        if m: tel = strip_html(m.group(1).strip())
    courriel_m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", corps)
    courriel = courriel_m.group(0) if courriel_m else ""
    ville   = ex(r"(?:ville|city)[:\s]+([^\n\r,<]+)")
    if not ville:
        m = re.search(r'<b>(?:votre\s+)?ville[^<]*</b><br\s*/?>\s*([^<\n]+)', corps, re.IGNORECASE)
        if m: ville = strip_html(m.group(1).strip())
    budget_raw = ex(r"(?:budget|besoin)[:/\s]+([^\n\r]+)")

    # Normaliser budget
    budget = "10k à 20k"
    bl = budget_raw.lower() + corps.lower()
    if "40 000" in bl or "40000" in bl or "60 000" in bl or "40k" in bl:
        budget = "40k à 60k+"
    elif "20 000" in bl or "20000" in bl or "30 000" in bl or "20k" in bl:
        budget = "20k à 40k"

    # Source courte
    source_court = "FB" if "facebook" in source.lower() or source == "Facebook" else "Web"

    if not nom or len(nom) < 2:
        return None

    return {
        "id":      int(datetime.now().timestamp() * 1000) + hash(nom) % 1000,
        "nom":     nom.strip(),
        "tel":     tel.strip(),
        "courriel": courriel.strip(),
        "ville":   ville.strip(),
        "budget":  budget,
        "source":  source_court,
        "statut":  "Nouveau",
        "date":    datetime.now().strftime("%Y-%m-%d"),
        "region":  get_region(tel),
    }

def lire_xlsx(chemin):
    if not os.path.exists(chemin):
        return [], []
    wb = openpyxl.load_workbook(chemin)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next((i for i, r in enumerate(rows) if r and r[0] == "Nom"), None)
    if header_idx is None:
        return [], []
    entete = rows[header_idx]
    data = rows[header_idx+1:]
    leads = []
    for r in data:
        if r and r[0] and str(r[0]).strip() and not is_nom_invalide(str(r[0])):
            leads.append({
                "id":       int(datetime.now().timestamp()*1000) + len(leads),
                "nom":      str(r[0] or "").strip(),
                "tel":      str(r[1] or "").strip(),
                "courriel": str(r[2] or "").strip(),
                "budget":   str(r[3] or "").strip(),
                "date":     str(r[4] or "")[:10],
                "ville":    str(r[5] or "").strip(),
                "source":   "FB" if str(r[6] or "").strip() in ("FB","Facebook") else "Web",
                "statut":   str(r[7] or "Nouveau").strip(),
                "region":   get_region(str(r[1] or "")),
            })
    return list(entete), leads

def sauvegarder_xlsx(chemin, entete, leads):
    wb = openpyxl.load_workbook(chemin)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next((i for i, r in enumerate(rows) if r and r[0] == "Nom"), None)
    if header_idx is None:
        return
    # Effacer les lignes de données
    for row in ws.iter_rows(min_row=header_idx+2):
        for cell in row:
            cell.value = None
    # Réécrire
    for i, lead in enumerate(leads):
        row_num = header_idx + 2 + i
        ws.cell(row_num, 1, lead["nom"])
        ws.cell(row_num, 2, lead["tel"])
        ws.cell(row_num, 3, lead["courriel"])
        ws.cell(row_num, 4, lead["budget"])
        ws.cell(row_num, 5, lead["date"])
        ws.cell(row_num, 6, lead["ville"])
        ws.cell(row_num, 7, lead["source"])
        ws.cell(row_num, 8, lead["statut"])
    wb.save(chemin)

def sauvegarder_json(chemin, leads):
    """Sauvegarde les leads en JSON pour le dashboard."""
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    print(f"   Dashboard JSON mis à jour : {len(leads)} leads")

def importer_depuis_imap(compte, noms_existants):
    nouveaux = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(compte["user"], compte["password"])
        mail.select("INBOX")
        depuis = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
        _, nums = mail.search(None, f'(SINCE {depuis} UNSEEN)')
        ids = nums[0].split() if nums[0] else []
        print(f"   {compte['user']} : {len(ids)} courriel(s) non lu(s)")
        for num in ids:
            _, data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            lead = parser_courriel(msg, compte["source"])
            if lead and lead["nom"].lower() not in noms_existants:
                nouveaux.append(lead)
        mail.logout()
    except Exception as e:
        print(f"   Erreur {compte['user']}: {e}")
    return nouveaux

def main():
    print(f"Import leads — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Lire Excel existant
    _, leads_existants = lire_xlsx(FICHIER_XLSX)
    noms_existants = {l["nom"].strip().lower() for l in leads_existants}

    ajouts = 0
    for compte in COMPTES:
        nouveaux = importer_depuis_imap(compte, noms_existants)
        for lead in nouveaux:
            nom_lower = lead["nom"].strip().lower()
            if nom_lower not in noms_existants:
                leads_existants.insert(0, lead)
                noms_existants.add(nom_lower)
                ajouts += 1
                print(f"   Ajoute : {lead['nom']} — {lead['ville']} ({lead['source']})")
            else:
                print(f"   Doublon ignore : {lead['nom']}")

    if ajouts > 0:
        sauvegarder_xlsx(FICHIER_XLSX, [], leads_existants)
        print(f"OK {ajouts} nouveau(x) lead(s) ajouté(s)!")
    else:
        print("Aucun nouveau lead aujourd'hui.")

    # Toujours mettre à jour le JSON pour le dashboard
    sauvegarder_json(FICHIER_JSON, leads_existants)

if __name__ == "__main__":
    main()
