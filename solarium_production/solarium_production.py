"""
SOLARIUM PRO — Générateur de documents de production
Serveur web local Flask → s'ouvre dans Safari
"""

import os, sys, threading, webbrowser, time, imaplib, email, json, re, shutil
from datetime import date, timedelta, datetime
from fractions import Fraction
from email.header import decode_header
from flask import Flask, render_template_string, request, jsonify, Response, send_file

DOSSIER_PDFS = os.path.expanduser("~/Documents/Solarium-Pro-PDFs")
os.makedirs(DOSSIER_PDFS, exist_ok=True)
BUREAU = os.path.expanduser("~/Desktop")
PORT = 5757

# ─── SOUMISSIONS CONFIG ───────────────────────────────────────────────────────
IMAP_SERVER     = "mail.mailconfig.net"
IMAP_PORT_IMAP  = 993
IMAP_USER       = "bdupuis@solariumpro.ca"
IMAP_PASS       = os.environ.get("IMAP_PASS", "")
SOUMISSIONS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soumissions.json")

sys.path.insert(0, DOSSIER_PDFS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generateur_cadre_avec_restes as cadre_mod
import cadre_module as cadre_new_mod
import aika_6mm_module as aika_mod
import cover_10mm_module as cover_mod
import cadre_approbation_v2 as cadre_appro_mod
import cadre_montage_v1 as cadre_montage_mod
import esthetika_module as esthetika_mod
import neoscenica_module as neo_mod
import verres_module as verres_mod

# ─── SOUMISSIONS HELPERS ─────────────────────────────────────────────────────
def _decode_str(s):
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

def save_soumissions(data):
    with open(SOUMISSIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _champ(texte, *labels):
    """Cherche le premier label trouvé et retourne la valeur qui suit."""
    for label in labels:
        m = re.search(
            r'(?:' + re.escape(label) + r')\s*[:\-]?\s*(.+?)(?=\n|$)',
            texte, re.IGNORECASE
        )
        if m:
            val = m.group(1).strip()
            if val: return val
    return ""

def _parser_pdf_soumission(pdf_bytes):
    """Extrait les champs structurés d'un PDF de soumission Solarium Pro."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        return {"parse_error": str(e)}

    # Numéro de projet format SP-PXXXXXXXXX
    m_no = re.search(r'(SP-P\d+)', texte, re.IGNORECASE)
    no_projet = m_no.group(1).upper() if m_no else ""

    nom_projet   = _champ(texte, "Nom du projet", "Nom projet", "Projet")
    client       = _champ(texte, "Nom du client", "Client", "Nom client")
    adresse      = _champ(texte, "Adresse du client", "Adresse client", "Adresse")
    telephone    = _champ(texte, "Téléphone du client", "Telephone du client",
                          "Téléphone", "Telephone", "Tel", "Tél")
    type_travaux = _champ(texte, "Type de travaux", "Type travaux", "Travaux")

    # Description : texte après le label "Description" jusqu'à la fin
    m_desc = re.search(
        r'[Dd]escription\s*[:\-]?\s*(.+)',
        texte, re.DOTALL
    )
    description = m_desc.group(1).strip()[:800] if m_desc else ""

    return {
        "no_projet":    no_projet,
        "nom_projet":   nom_projet,
        "client":       client,
        "adresse":      adresse,
        "telephone":    telephone,
        "type_travaux": type_travaux,
        "description":  description,
        "texte_complet": texte[:3000],
    }

def scanner_imap_soumissions():
    """Scanne la boîte IMAP, télécharge les PDF joints et parse les champs."""
    existants = load_soumissions()
    ids_existants  = {s["msg_id"] for s in existants}
    statuts_par_no = {s["no_projet"]: (s["statut"], s.get("date_statut")) for s in existants if s.get("no_projet")}
    nouveaux = 0
    try:
        m = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT_IMAP)
        m.login(IMAP_USER, IMAP_PASS)
        m.select("INBOX")
        depuis = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        _, ids = m.search(None, f'(SINCE "{depuis}" SUBJECT "alerte nouveau dossier")')
        for uid in ids[0].split():
            _, data = m.fetch(uid, "(RFC822)")
            msg    = email.message_from_bytes(data[0][1])
            msg_id = msg.get("Message-ID", uid.decode())
            if msg_id in ids_existants: continue

            sujet    = _decode_str(msg.get("Subject", ""))
            date_msg = msg.get("Date", "")

            # Chercher la pièce jointe PDF
            pdf_bytes = None
            pdf_nom   = ""
            for part in msg.walk():
                ct = part.get_content_type()
                cd = part.get("Content-Disposition", "")
                if ct == "application/pdf" or (cd and "attachment" in cd and ".pdf" in _decode_str(part.get_filename("")).lower()):
                    pdf_bytes = part.get_payload(decode=True)
                    pdf_nom   = _decode_str(part.get_filename(""))
                    break

            if pdf_bytes:
                champs = _parser_pdf_soumission(pdf_bytes)
            else:
                champs = {}

            # Fallback client depuis le sujet si le PDF n'a rien donné
            if not champs.get("client"):
                m2 = re.search(r"alerte nouveau dossier[^\-\—]*[\-\—]\s*(.+)", sujet, re.IGNORECASE)
                champs["client"] = m2.group(1).strip()[:80] if m2 else sujet[:80]

            no_projet = champs.get("no_projet", "")
            if no_projet and no_projet in statuts_par_no:
                statut_conserve, date_statut_conserve = statuts_par_no[no_projet]
            else:
                statut_conserve      = "À faire"
                date_statut_conserve = datetime.now().isoformat()

            existants.append({
                "msg_id":         msg_id,
                "sujet":          sujet,
                "pdf_nom":        pdf_nom,
                "date_reception": date_msg,
                "statut":         statut_conserve,
                "date_statut":    date_statut_conserve,
                **champs,
            })
            ids_existants.add(msg_id)
            nouveaux += 1
        m.logout()
    except Exception as e:
        return False, str(e)
    save_soumissions(existants)
    return True, nouveaux

# ─── UTILITAIRES ──────────────────────────────────────────────────────────────
def fvd(s): return cadre_mod.fraction_vers_decimal(s)
def dvf(d): return cadre_mod.decimal_vers_fraction(d)
def po_mm(d):
    mm = round(d * 25.4)
    return f'{dvf(d)}  ({mm:,} mm)'.replace(',', ' ')

def ffd(pieces_list, utile, kerf=0.25):
    toutes = []
    for p in pieces_list:
        for _ in range(p['qte']):
            toutes.append({'nom': p['nom'], 'long': p['long']})
    toutes.sort(key=lambda x: x['long'], reverse=True)
    barres = []
    for piece in toutes:
        besoin = piece['long'] + kerf
        placee = False
        for b in barres:
            if utile - b['utilise'] >= besoin:
                b['pieces'].append(piece)
                b['utilise'] += besoin
                placee = True
                break
        if not placee:
            barres.append({'num': len(barres)+1, 'pieces': [piece], 'utilise': besoin})
    for b in barres:
        b['reste'] = utile - b['utilise']
    return barres

# ─── HELPERS PDF ──────────────────────────────────────────────────────────────
def _entete(c, h, titre, no_proj, client, couleur):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    BLEU_R = colors.HexColor("#1F3864")
    OR_R   = colors.HexColor("#C68B00")
    c.setFillColor(BLEU_R)
    c.rect(0, h - 1.1*inch, 8.5*inch, 1.1*inch, fill=True, stroke=False)
    c.setFillColor(OR_R)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(0.4*inch, h - 0.44*inch, titre)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    from reportlab.pdfbase.pdfmetrics import stringWidth
    info = f"No: {no_proj}  |  Client: {client}  |  Couleur: {couleur}"
    max_info_w = 7.4*inch  # laisse de l'espace avant la date à 8.1"
    while len(info) > 20 and stringWidth(info, 'Helvetica', 9) > max_info_w:
        info = info[:-2] + '\u2026'
    c.drawString(0.4*inch, h - 0.72*inch, info)
    c.drawRightString(8.1*inch, h - 0.72*inch, str(date.today()))

def _pied(c, w, no_proj, client):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor("#1F3864"))
    c.rect(0, 0.3*inch, w, 0.3*inch, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#C68B00"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, 0.42*inch,
        f"Solarium Pro  \u00b7  {no_proj}  \u00b7  {client}  \u00b7  {date.today()}")

def _titre_section(c, y, w, texte):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor("#1F3864"))
    c.rect(0.4*inch, y - 0.22*inch, w - 0.8*inch, 0.22*inch, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.5*inch, y - 0.14*inch, texte)
    return y - 0.36*inch

def _table_coupes(c, y, w, h_page, barres, seuil=6.0):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    BLEU_R = colors.HexColor("#1F3864")
    GRIS_R = colors.HexColor("#F5F5F5")
    data = [["#", "Découpes (pouces)", "Utilisé", "Reste"]]
    for b in barres:
        dec_str  = " + ".join(dvf(p["long"]) for p in b["pieces"])
        rest_str = dvf(b["reste"]) if b["reste"] >= seuil else f'{dvf(b["reste"])} (!)'
        data.append([f"#{b['num']}", dec_str, dvf(b["utilise"]), rest_str])
    t = Table(data, colWidths=[0.4*inch, 4.9*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BLEU_R),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, GRIS_R]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN",         (0,0), (0,-1),  "CENTER"),
        ("ALIGN",         (2,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    t.wrapOn(c, w, h_page)
    _, t_h = t.wrap(0, 0)
    if y - t_h < 0.9*inch:
        c.showPage(); y = h_page - 0.5*inch
    t.drawOn(c, 0.4*inch, y - t_h)
    return y - t_h - 0.25*inch

def _table_recap(c, y, w, h_page, pieces):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    BLEU_R = colors.HexColor("#1F3864")
    GRIS_R = colors.HexColor("#F5F5F5")
    data = [["Pièce", "Longueur (pouces)", "Longueur (mm)", "Qté"]]
    for p in pieces:
        mm = str(round(p["long"] * 25.4))
        data.append([p["nom"], dvf(p["long"]), mm, str(p["qte"])])
    t = Table(data, colWidths=[3.1*inch, 1.8*inch, 1.5*inch, 1.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BLEU_R),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, GRIS_R]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN",         (1,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    t.wrapOn(c, w, h_page)
    _, t_h = t.wrap(0, 0)
    if y - t_h < 0.9*inch:
        c.showPage(); y = h_page - 0.5*inch
    t.drawOn(c, 0.4*inch, y - t_h)
    return y - t_h - 0.3*inch

def _notes(c, y, w, texte):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    if not texte.strip(): return y
    c.setFillColor(colors.HexColor("#FFF3CD"))
    c.rect(0.4*inch, y - 0.62*inch, w - 0.8*inch, 0.62*inch, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#856404"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.5*inch, y - 0.18*inch, "NOTES :")
    c.setFont("Helvetica", 9)
    c.drawString(0.5*inch, y - 0.44*inch, texte[:130])
    return y - 0.75*inch

def _bandeau_recap(c, y, w, texte):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor("#D6E4F0"))
    c.rect(0.4*inch, y - 0.3*inch, w - 0.8*inch, 0.3*inch, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#1F3864"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.5*inch, y - 0.18*inch, texte)
    return y - 0.52*inch

def _mur_header(c, y, w, nom_mur, idx, total):
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor("#E8F0FB"))
    c.rect(0.4*inch, y - 0.32*inch, w - 0.8*inch, 0.32*inch, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#1F3864"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.5*inch, y - 0.21*inch, f"MUR {idx}/{total}  \u2014  {nom_mur}")
    return y - 0.52*inch

def _contenants_to_barres(contenants):
    """Convertit les contenants de cadre_mod au format attendu par _table_coupes"""
    barres = []
    for i, cont in enumerate(contenants):
        if not cont.get('pieces'):
            continue
        pieces = [{'long': p['longueur']} for p in cont['pieces']]
        barres.append({
            'num': i + 1,
            'pieces': pieces,
            'utilise': cont.get('utilise_dec', 0),
            'reste': cont.get('reste_final', 0),
        })
    return barres

# ─── PDF CADRE / TRAPÈZE (mono-mur, rétrocompat) ─────────────────────────────
def generer_pdf_cadre(params, fichier):
    largeur_str = params["largeur"]
    hauteur_str = params["hauteur"]
    nb_montants = int(params["nb_montants"])
    no_projet   = params["no_projet"]
    client      = params["client"]
    couleur     = params["couleur"]
    pieces = cadre_mod.calculer_pieces(largeur_str, hauteur_str, nb_montants)
    profils = ['Tube alu 2-1/2"', 'Plaque pression', 'Couvercle']
    contenants_par_profil = {}
    tous_restes_consommes = []
    tous_nouveaux_restes  = []
    for profil in profils:
        contenants, rc, nr = cadre_mod.optimiser_coupes(pieces, profil, couleur, verbose=False)
        contenants_par_profil[profil] = contenants
        tous_restes_consommes.extend(rc)
        tous_nouveaux_restes.extend(nr)
    cadre_params = {
        "no_projet": no_projet, "client": client, "couleur": couleur,
        "largeur": largeur_str + '"', "hauteur": hauteur_str + '"',
        "nb_montants": nb_montants,
    }
    cadre_mod.generer_pdf_production(
        cadre_params, contenants_par_profil,
        tous_restes_consommes, tous_nouveaux_restes, fichier)
    if tous_restes_consommes:
        cadre_mod.marquer_restes_utilises(tous_restes_consommes, no_projet)
    if tous_nouveaux_restes:
        cadre_mod.ajouter_nouveaux_restes(tous_nouveaux_restes, no_projet, client, couleur)

# ─── PDF NÉOSCENICA MULTI-MURS ────────────────────────────────────────────────
def generer_pdf_neoscenica_multi(params, fichier):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    UTILE = 238.0; KERF = 0.25; SEUIL = 6.0; UTILE_PETIT = 143.0
    no_proj = params["no_projet"]; client = params["client"]
    couleur = params["couleur"]; notes = params.get("notes", "")
    murs = params.get("murs", [])
    c = canvas.Canvas(fichier, pagesize=letter)
    w, h = letter
    for idx, mur in enumerate(murs):
        if idx > 0:
            _pied(c, w, no_proj, client)
            c.showPage()
        largeur = fvd(mur["largeur"]); hauteur = fvd(mur["hauteur"])
        nom_mur = mur.get("nom", f"Mur {chr(65+idx)}")
        nb_mont_cent = 1 if largeur > 120 else 0
        mont_lat_long = hauteur - 1.625
        pieces_structure = [
            {"nom": "Rail supérieur",         "long": largeur,       "qte": 1},
            {"nom": "Rail inférieur / seuil", "long": largeur,       "qte": 1},
            {"nom": "Montants latéraux",      "long": mont_lat_long, "qte": 2},
        ]
        if nb_mont_cent:
            pieces_structure.append({"nom": "Montant central", "long": mont_lat_long, "qte": 1})
        pieces_moustiquaire = [
            {"nom": "Cadre moustiquaire — horizontal", "long": largeur - 1.625*2, "qte": 2},
            {"nom": "Cadre moustiquaire — vertical",   "long": hauteur - 1.625*2, "qte": 2},
        ]
        barres_struct = ffd(pieces_structure, UTILE, KERF)
        barres_moust  = ffd(pieces_moustiquaire, UTILE_PETIT, KERF)
        type_mur = mur.get("type", "Simple")
        sens_mur = mur.get("sens", "Gauche")
        y = h - 1.3*inch
        _entete(c, h, "DOCUMENT DE PRODUCTION — NÉOSCENICA (Moustiquaire)", no_proj, client, couleur)
        y = _mur_header(c, y, w, nom_mur, idx+1, len(murs))
        y = _bandeau_recap(c, y, w,
            f"Largeur: {dvf(largeur)}  ({round(largeur*25.4):,} mm)   |   "
            f"Hauteur: {dvf(hauteur)}  ({round(hauteur*25.4):,} mm)   |   "
            f"Type: {type_mur}   |   Ouverture: {sens_mur}   |   "
            f"Barres structure: {len(barres_struct)}   |   Barres cadre: {len(barres_moust)}"
            .replace(',', ' '))
        y = _titre_section(c, y, w, 'LISTE DE COUPE — Structure  Tube alu 1-5/8"  (barres de 240")')
        y = _table_coupes(c, y, w, h, barres_struct, SEUIL)
        y = _titre_section(c, y, w, "RÉCAPITULATIF — Structure")
        y = _table_recap(c, y, w, h, pieces_structure)
        y = _titre_section(c, y, w, 'LISTE DE COUPE — Cadre moustiquaire  Tube alu 3/4"  (barres de 144")')
        y = _table_coupes(c, y, w, h, barres_moust, 4.0)
        y = _titre_section(c, y, w, "RÉCAPITULATIF — Cadre moustiquaire")
        y = _table_recap(c, y, w, h, pieces_moustiquaire)
        if idx == len(murs) - 1:
            _notes(c, y, w, notes)
    _pied(c, w, no_proj, client)
    c.save()

# ─── PDF CADRE / TRAPÈZE MULTI-MURS ──────────────────────────────────────────
def generer_pdf_cadre_multi(params, fichier):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    SEUIL = 6.0
    no_proj = params["no_projet"]; client = params["client"]
    couleur = params["couleur"]; notes = params.get("notes", "")
    murs = params.get("murs", [])
    profils = ['Tube alu 2-1/2"', 'Plaque pression', 'Couvercle']
    c = canvas.Canvas(fichier, pagesize=letter)
    w, h = letter

    # ── PAGES APPROBATION — une page complète par mur ─────────────────────────
    for idx_a, mur_a in enumerate(murs):
        type_mur_a = mur_a.get("type", "cadre")
        est_trap_a = type_mur_a == "trapeze"
        largeur_a = fvd(mur_a["largeur"])
        nom_a = mur_a.get("nom", f"Mur {chr(65+idx_a)}")
        nb_mont_a = int(mur_a.get('nb_montants', 2))
        if est_trap_a:
            vg_a = fvd(mur_a.get("vg", "0"))
            vd_a = fvd(mur_a.get("vd", "0"))
            mur_calc = {
                'nom': nom_a,
                'largeur_po': largeur_a, 'vg_po': vg_a, 'vd_po': vd_a,
                'hauteur_po': max(vg_a, vd_a),
                'largeur_mm': round(largeur_a * 25.4),
                'vg_mm': round(vg_a * 25.4), 'vd_mm': round(vd_a * 25.4),
                'hauteur_mm': round(max(vg_a, vd_a) * 25.4),
                'nb_montants': nb_mont_a, 'est_trapeze': True,
            }
        else:
            hauteur_a = fvd(mur_a.get("hauteur", "0"))
            mur_calc = {
                'nom': nom_a,
                'largeur_po': largeur_a, 'hauteur_po': hauteur_a,
                'vg_po': hauteur_a, 'vd_po': hauteur_a,
                'largeur_mm': round(largeur_a * 25.4),
                'vg_mm': round(hauteur_a * 25.4), 'vd_mm': round(hauteur_a * 25.4),
                'hauteur_mm': round(hauteur_a * 25.4),
                'nb_montants': nb_mont_a, 'est_trapeze': False,
            }
        cadre_appro_mod.page_approbation_cadre(
            c, mur_calc, w, h, inch, colors,
            no_proj, client, couleur, str(date.today())
        )
        c.showPage()

    # ── PAGES PRODUCTION ──────────────────────────────────────────────────────
    for idx, mur in enumerate(murs):
        if idx > 0:
            _pied(c, w, no_proj, client)
            c.showPage()
        type_mur = mur.get("type", "cadre")
        est_trap = type_mur == "trapeze"
        largeur_str = mur["largeur"]
        nb_montants = int(mur["nb_montants"])
        nom_mur = mur.get("nom", f"Mur {chr(65+idx)}")
        mur_dict = {
            'largeur_po': fvd(largeur_str),
            'nb_montants': nb_montants,
            'couleur_alu': couleur,
            'nom': nom_mur,
        }
        if est_trap:
            mur_dict['vg_po'] = fvd(mur.get("vg", "0"))
            mur_dict['vd_po'] = fvd(mur.get("vd", "0"))
        else:
            mur_dict['hauteur_po'] = fvd(mur.get("hauteur", "0"))
        mur_result = cadre_new_mod.calculer_mur_cadre(mur_dict)
        pieces = mur_result['pieces']
        contenants_par_profil = {}
        tous_rc = []; tous_nr = []
        for profil in profils:
            contenants, rc, nr = cadre_mod.optimiser_coupes(pieces, profil, couleur, verbose=False)
            contenants_par_profil[profil] = contenants
            tous_rc.extend(rc); tous_nr.extend(nr)
        if tous_rc:
            cadre_mod.marquer_restes_utilises(tous_rc, no_proj)
        if tous_nr:
            cadre_mod.ajouter_nouveaux_restes(tous_nr, no_proj, client, couleur)
        y = h - 1.3*inch
        _entete(c, h, "DOCUMENT DE PRODUCTION — CADRE / TRAPÈZE", no_proj, client, couleur)
        y = _mur_header(c, y, w, nom_mur, idx+1, len(murs))
        if est_trap:
            recap_str = (
                f"Largeur: {dvf(mur_result['largeur_po'])}  ({mur_result['largeur_mm']:,} mm)   |   "
                f"H. gauche: {dvf(mur_result['vg_po'])}  ({mur_result['vg_mm']:,} mm)   |   "
                f"H. droite: {dvf(mur_result['vd_po'])}  ({mur_result['vd_mm']:,} mm)   |   "
                f"Montants: {nb_montants}"
            ).replace(',', ' ')
        else:
            recap_str = (
                f"Largeur: {dvf(mur_result['largeur_po'])}  ({mur_result['largeur_mm']:,} mm)   |   "
                f"Hauteur: {dvf(mur_result['hauteur_po'])}  ({mur_result['hauteur_mm']:,} mm)   |   "
                f"Montants: {nb_montants}"
            ).replace(',', ' ')
        y = _bandeau_recap(c, y, w, recap_str)
        pieces_recap = [{"nom": p["nom"], "long": p["longueur_dec"], "qte": p["qte"]} for p in pieces]
        y = _titre_section(c, y, w, "RÉCAPITULATIF DES PIÈCES")
        y = _table_recap(c, y, w, h, pieces_recap)
        for profil in profils:
            barres = _contenants_to_barres(contenants_par_profil[profil])
            if not barres:
                continue
            y = _titre_section(c, y, w, f'LISTE DE COUPE — {profil}  (barres de 240")')
            y = _table_coupes(c, y, w, h, barres, SEUIL)
        if idx == len(murs) - 1:
            _notes(c, y, w, notes)
    _pied(c, w, no_proj, client)
    c.save()

# ─── PDF ESTÉTIKA MULTI-MURS ──────────────────────────────────────────────────
def generer_pdf_esthetika_multi(params, fichier, motorisee=False):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    UTILE = 238.0; KERF = 0.25; SEUIL = 6.0
    no_proj = params["no_projet"]; client = params["client"]
    couleur = params["couleur"]; notes = params.get("notes", "")
    murs = params.get("murs", [])
    titre = "ESTÉTIKA MOTORISÉE" if motorisee else "ESTÉTIKA MANUELLE"
    c = canvas.Canvas(fichier, pagesize=letter)
    w, h = letter
    for idx, mur in enumerate(murs):
        if idx > 0:
            _pied(c, w, no_proj, client)
            c.showPage()
        largeur    = fvd(mur["largeur"]); profondeur = fvd(mur["profondeur"])
        haut_lames = fvd(mur["hauteur_lames"]); nb_lames = int(mur["nb_lames"])
        moteur     = mur.get("moteur", "").strip()
        nom_mur    = mur.get("nom", f"Mur {chr(65+idx)}")
        lame_long  = largeur - 1.0
        pieces_lames = [{"nom": "Lame orientable", "long": lame_long, "qte": nb_lames}]
        pieces_structure = [
            {"nom": "Poteaux",           "long": haut_lames + 6.0, "qte": 4},
            {"nom": "Poutres porteuses", "long": profondeur - 3.0, "qte": 2},
            {"nom": "Traverses de tête", "long": largeur,          "qte": 2},
        ]
        barres_lames  = ffd(pieces_lames,    UTILE, KERF)
        barres_struct = ffd(pieces_structure, UTILE, KERF)
        y = h - 1.3*inch
        _entete(c, h, f"DOCUMENT DE PRODUCTION — {titre} (Pergola à lames)", no_proj, client, couleur)
        y = _mur_header(c, y, w, nom_mur, idx+1, len(murs))
        y = _bandeau_recap(c, y, w,
            f"Largeur: {dvf(largeur)}  ({round(largeur*25.4):,} mm)   |   "
            f"Profondeur: {dvf(profondeur)}  ({round(profondeur*25.4):,} mm)   |   "
            f"H. lames: {dvf(haut_lames)}  ({round(haut_lames*25.4):,} mm)   |   {nb_lames} lames"
            .replace(',', ' '))
        if motorisee and moteur:
            c.setFillColor(colors.HexColor("#EEF2FA"))
            c.rect(0.4*inch, y - 0.28*inch, w - 0.8*inch, 0.28*inch, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#1F3864"))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(0.5*inch, y - 0.17*inch, f"Motorisation : {moteur}")
            y -= 0.42*inch
        y = _titre_section(c, y, w, f'LISTE DE COUPE — Lames  (barres de 240")  ×{nb_lames} lames')
        y = _table_coupes(c, y, w, h, barres_lames, SEUIL)
        y = _titre_section(c, y, w, "RÉCAPITULATIF — Lames")
        y = _table_recap(c, y, w, h, pieces_lames)
        y = _titre_section(c, y, w, 'LISTE DE COUPE — Structure  Tube alu 2-1/2"  (barres de 240")')
        y = _table_coupes(c, y, w, h, barres_struct, SEUIL)
        y = _titre_section(c, y, w, "RÉCAPITULATIF — Structure")
        y = _table_recap(c, y, w, h, pieces_structure)
        if idx == len(murs) - 1:
            _notes(c, y, w, notes)
    _pied(c, w, no_proj, client)
    c.save()

# ─── TEMPLATE HTML ────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Solarium Pro — Production</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    background: #F0F3F8; min-height: 100vh; }
  header { background: #1F3864; padding: 18px 32px; display: flex; align-items: baseline; gap: 20px; }
  header h1 { color: #fff; font-size: 24px; font-weight: 700; letter-spacing: 1px; }
  header p  { color: #C68B00; font-size: 14px; }
  .container { max-width: 720px; margin: 36px auto; padding: 0 16px 60px; }
  .card { background: #fff; border-radius: 10px; box-shadow: 0 2px 12px rgba(31,56,100,.10);
    padding: 28px 32px; margin-bottom: 20px; }
  .card h2 { color: #1F3864; font-size: 15px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .6px; border-bottom: 2px solid #C68B00; padding-bottom: 8px; margin-bottom: 20px; }
  label { display: block; font-size: 13px; font-weight: 600; color: #1F3864;
    margin-bottom: 5px; margin-top: 14px; }
  label:first-of-type { margin-top: 0; }
  input[type=text], select, textarea { width: 100%; padding: 10px 12px;
    border: 1.5px solid #C8D3E8; border-radius: 6px; font-size: 14px; color: #1a1a1a;
    background: #FAFBFE; transition: border-color .2s; outline: none; }
  input[type=text]:focus, select:focus { border-color: #1F3864; background: #fff; }
  input[type=checkbox] { width: auto; }
  textarea { resize: vertical; min-height: 64px; }
  .hint { font-size: 11px; color: #888; margin-top: 3px; }
  .modele-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .modele-btn { border: 2px solid #C8D3E8; background: #F8FAFF; border-radius: 8px;
    padding: 14px 10px; cursor: pointer; text-align: center; font-size: 13px;
    font-weight: 600; color: #1F3864; transition: all .18s; }
  .modele-btn:hover { border-color: #1F3864; background: #EEF2FA; }
  .modele-btn.active { border-color: #C68B00; background: #FFF8E6; color: #7A5200; }
  .btn-generer { display: block; width: 100%; padding: 15px; background: #C68B00;
    color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 700;
    cursor: pointer; margin-top: 8px; transition: background .2s; }
  .btn-generer:hover { background: #A57200; }
  .btn-generer:disabled { background: #ccc; cursor: default; }
  #statut { margin-top: 16px; padding: 12px 16px; border-radius: 7px; font-size: 14px;
    font-weight: 500; display: none; }
  #statut.ok    { background: #D4EDDA; color: #155724; }
  #statut.error { background: #F8D7DA; color: #721c24; }
  #statut.info  { background: #D1ECF1; color: #0c5460; }
  .badge { display: inline-block; background: #1F3864; color: #C68B00; font-size: 11px;
    font-weight: 700; padding: 2px 8px; border-radius: 12px; margin-left: 8px; }
  .nb-murs-sel { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
  .nb-btn { border:1.5px solid #C8D3E8; background:#F8FAFF; border-radius:6px;
    padding:6px 14px; font-size:13px; font-weight:600; color:#1F3864; cursor:pointer; }
  .nb-btn.active { border-color:#C68B00; background:#FFF8E6; color:#7A5200; }
  .mur-card { border:1px solid #C8D3E8; border-radius:8px; padding:14px; margin-bottom:10px; }
  .mur-header { background:#1F3864; color:#C68B00; font-size:12px; font-weight:600;
    padding:5px 12px; border-radius:5px; margin-bottom:12px; }
  .row3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }
  .row2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .sub-lbl { font-size:11px; font-weight:600; color:#555; text-transform:uppercase;
    letter-spacing:.4px; margin:8px 0 5px; }
  .serrure-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:6px; }
  .sbtn { border:1.5px solid #C8D3E8; background:#F8FAFF; border-radius:7px;
    padding:9px 10px; cursor:pointer; display:flex; align-items:flex-start; gap:8px; }
  .sbtn.on { border-color:#C68B00; background:#FFF8E6; }
  .sbtn .scheck { width:15px; height:15px; border:1.5px solid #C8D3E8; border-radius:3px;
    flex-shrink:0; margin-top:1px; display:flex; align-items:center; justify-content:center; }
  .sbtn.on .scheck { background:#C68B00; border-color:#C68B00; }
  .sbtn .st { font-size:12px; font-weight:600; color:#1F3864; display:block; }
  .sbtn.on .st { color:#7A5200; }
  .sbtn .sd { font-size:10px; color:#888; margin-top:2px; display:block; }
  .sep { height:1px; background:#eee; margin:10px 0; }
  /* ── Onglets ── */
  .tabs-nav { background:#162d56; display:flex; gap:4px; padding:0 24px; }
  .tab-btn { padding:12px 22px; color:#8a9fc0; font-size:14px; font-weight:600;
    border:none; background:transparent; cursor:pointer; border-bottom:3px solid transparent;
    transition:all .18s; }
  .tab-btn:hover { color:#fff; }
  .tab-btn.active { color:#C68B00; border-bottom-color:#C68B00; }
  .tab-pane { display:none; }
  .tab-pane.active { display:block; }
  /* ── Soumissions ── */
  .soum-toolbar { display:flex; justify-content:space-between; align-items:center;
    margin-bottom:16px; flex-wrap:wrap; gap:10px; }
  .btn-scan { background:#1F3864; color:#C68B00; border:none; border-radius:7px;
    padding:10px 20px; font-size:13px; font-weight:700; cursor:pointer; }
  .btn-scan:hover { background:#162d56; }
  .soum-card { background:#fff; border-radius:9px; box-shadow:0 2px 10px rgba(31,56,100,.09);
    padding:16px 20px 14px; margin-bottom:14px; border-left:5px solid #ccc;
    cursor:pointer; transition:box-shadow .15s; }
  .soum-card:hover { box-shadow:0 4px 18px rgba(31,56,100,.18); }
  .soum-card.statut-faire    { border-left-color:#dc3545; }
  .soum-card.statut-attente  { border-left-color:#ffc107; }
  .soum-card.statut-envoye   { border-left-color:#0d6efd; }
  .soum-card.statut-gagne    { border-left-color:#198754; }
  .soum-card.statut-perdu    { border-left-color:#6c757d; }
  .soum-card-top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:6px; }
  .soum-no    { font-size:11px; font-weight:700; color:#C68B00; letter-spacing:.5px; }
  .soum-type  { font-size:11px; color:#666; background:#f0f3f8; padding:2px 8px;
    border-radius:10px; white-space:nowrap; }
  .soum-client { font-size:15px; font-weight:700; color:#1F3864; margin-bottom:3px; }
  .soum-tel   { font-size:12px; color:#555; margin-bottom:4px; }
  .soum-desc  { font-size:12px; color:#777; margin-bottom:10px;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; }
  .soum-footer { display:flex; justify-content:space-between; align-items:center;
    flex-wrap:wrap; gap:6px; }
  .soum-date  { font-size:11px; color:#aaa; }
  .statut-btns { display:flex; flex-wrap:wrap; gap:5px; }
  .sbtn-statut { border:1.5px solid; border-radius:6px; padding:4px 10px;
    font-size:11px; font-weight:600; cursor:pointer; background:transparent; }
  .sbtn-statut.active { color:#fff!important; }
  .sbtn-faire   { border-color:#dc3545; color:#dc3545; }
  .sbtn-faire.active   { background:#dc3545; }
  .sbtn-attente { border-color:#cc8800; color:#cc8800; }
  .sbtn-attente.active { background:#cc8800; }
  .sbtn-envoye  { border-color:#0d6efd; color:#0d6efd; }
  .sbtn-envoye.active  { background:#0d6efd; }
  .sbtn-gagne   { border-color:#198754; color:#198754; }
  .sbtn-gagne.active   { background:#198754; }
  .sbtn-perdu   { border-color:#6c757d; color:#6c757d; }
  .sbtn-perdu.active   { background:#6c757d; }
  #soum-vide { color:#999; text-align:center; padding:40px 0; font-size:14px; }
  /* ── Modal ── */
  .modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.5);
    z-index:1000; align-items:center; justify-content:center; }
  .modal-overlay.open { display:flex; }
  .modal-box { background:#fff; border-radius:12px; width:min(600px,94vw);
    max-height:88vh; overflow-y:auto; box-shadow:0 8px 40px rgba(0,0,0,.3); }
  .modal-header { background:#1F3864; color:#fff; padding:18px 24px;
    border-radius:12px 12px 0 0; display:flex; justify-content:space-between; align-items:center; }
  .modal-header h3 { margin:0; font-size:16px; }
  .modal-close { background:none; border:none; color:#C68B00; font-size:22px;
    cursor:pointer; line-height:1; padding:0; }
  .modal-body { padding:24px; }
  .modal-field { margin-bottom:14px; }
  .modal-label { font-size:11px; font-weight:700; color:#888; text-transform:uppercase;
    letter-spacing:.5px; margin-bottom:3px; }
  .modal-value { font-size:14px; color:#1a1a1a; }
  .modal-desc  { font-size:13px; color:#444; white-space:pre-wrap; line-height:1.5;
    background:#f8f9fa; padding:10px 12px; border-radius:6px; border-left:3px solid #C68B00; }
  .modal-statuts { padding:16px 24px 24px; border-top:1px solid #eee; }
  .modal-statuts .statut-btns { gap:8px; }
  .modal-statuts .sbtn-statut { padding:7px 14px; font-size:13px; }
</style>
</head>
<body>
<header>
  <h1>SOLARIUM PRO</h1>
  <p>Générateur de documents de production</p>
</header>
<nav class="tabs-nav">
  <button class="tab-btn active" onclick="afficherOnglet('production',this)">Production</button>
  <button class="tab-btn" onclick="afficherOnglet('soumissions',this)">Soumissions</button>
</nav>

<div id="tab-production" class="tab-pane active">
<div class="container">
  <div class="card">
    <h2>1 — Choisir le modèle</h2>
    <div class="modele-grid">
      <button class="modele-btn active" onclick="choisirModele('Néoscenica', this)">Néoscenica</button>
      <button class="modele-btn" onclick="choisirModele('Cadre / Trapèze', this)">Cadre / Trapèze</button>
      <button class="modele-btn" onclick="choisirModele('Cover 10mm', this)">Cover 10mm</button>
      <button class="modele-btn" onclick="choisirModele('Aika 6mm', this)">Aika 6mm</button>
      <button class="modele-btn" onclick="choisirModele('Estétika Motorisée', this)">Estétika Motorisée</button>
      <button class="modele-btn" onclick="choisirModele('Estétika Manuelle', this)">Estétika Manuelle</button>
    </div>
  </div>
  <div class="card">
    <h2>2 — Informations du projet</h2>
    <label>Numéro de projet</label>
    <input type="text" id="no_projet" placeholder="ex: 2025-042">
    <label>Nom du client</label>
    <input type="text" id="client" placeholder="ex: Martin Gagnon">
    <label>Couleur</label>
    <select id="couleur" onchange="document.getElementById('couleur_autre_wrap').style.display=this.value==='Autre'?'block':'none'">
      <option>Noir RAL 9005</option>
      <option>Blanc RAL 9016</option>
      <option>Autre</option>
    </select>
    <div id="couleur_autre_wrap" style="display:none;margin-top:6px">
      <input type="text" id="couleur_autre" placeholder="ex: Champagne, Bronze anodisé…" style="width:100%">
    </div>
  </div>
  <div class="card" id="carte-dimensions">
    <h2>3 — Dimensions <span class="badge" id="badge-modele">Néoscenica</span></h2>
    <div id="champs-dimensions"></div>
  </div>
  <div class="card">
    <h2>4 — Notes / Instructions spéciales</h2>
    <textarea id="notes" placeholder="Options, précisions de pose, finitions particulières…"></textarea>
  </div>
  <button class="btn-generer" onclick="generer()" id="btn">☀ &nbsp;Générer le PDF</button>
  <button class="btn-generer" onclick="genererAikaAppro()" id="btn-appro" style="display:none;background:#1F3864;margin-top:8px">📋 &nbsp;Approbation client seulement</button>
  <button class="btn-generer" onclick="genererAikaPeinture()" id="btn-peinture" style="display:none;background:#5a3060;margin-top:8px">🎨 &nbsp;Fiche peinture seulement</button>
  <button class="btn-generer" onclick="genererVerresCommande()" id="btn-verres" style="display:none;background:#006B3C;margin-top:8px">🪟 &nbsp;Bon de commande verre</button>
  <div id="statut"></div>
</div>
</div><!-- /tab-production -->

<div id="tab-soumissions" class="tab-pane">
<div class="container">
  <div class="card">
    <h2>Soumissions</h2>
    <div class="soum-toolbar">
      <span id="soum-count" style="font-size:13px;color:#666"></span>
      <button class="btn-scan" id="btn-scan" onclick="scannerSoumissions()">↻ &nbsp;Scanner les courriels</button>
    </div>
    <div id="soum-liste"><p id="soum-vide">Chargement…</p></div>
  </div>
</div>
</div><!-- /tab-soumissions -->

<!-- Modal soumission -->
<div class="modal-overlay" id="soum-modal" onclick="fermerModalSi(event)">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-titre">Détails du dossier</h3>
      <button class="modal-close" onclick="fermerModal()">✕</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
    <div class="modal-statuts">
      <div class="modal-label" style="margin-bottom:8px">Statut</div>
      <div class="statut-btns" id="modal-statut-btns"></div>
    </div>
  </div>
</div>

<script>
let modeleActif = "Néoscenica";

function choisirModele(modele, btn) {
  modeleActif = modele;
  document.querySelectorAll('.modele-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('badge-modele').textContent = modele;
  cacherStatut();
  document.getElementById('btn-appro').style.display = 'none';
  document.getElementById('btn-peinture').style.display = 'none';
  document.getElementById('btn-verres').style.display = 'none';
  if (modele === 'Néoscenica')        { renderNeoForm();    document.getElementById('btn-appro').style.display='block'; document.getElementById('btn-peinture').style.display='block'; return; }
  if (modele === 'Cadre / Trapèze')   { renderCadreForm();  document.getElementById('btn-appro').style.display='block'; document.getElementById('btn-peinture').style.display='block'; document.getElementById('btn-verres').style.display='block'; return; }
  if (modele === 'Cover 10mm')        { renderCoverForm();  document.getElementById('btn-verres').style.display='block'; return; }
  if (modele === 'Aika 6mm')          { renderAikaForm();   document.getElementById('btn-appro').style.display='block'; document.getElementById('btn-peinture').style.display='block'; document.getElementById('btn-verres').style.display='block'; return; }
  if (modele === 'Estétika Motorisée'){ renderEstMotForm(); document.getElementById('btn-appro').style.display='block'; document.getElementById('btn-peinture').style.display='block'; return; }
  if (modele === 'Estétika Manuelle') { renderEstManForm(); document.getElementById('btn-appro').style.display='block'; document.getElementById('btn-peinture').style.display='block'; return; }
}

function poucesVersDecimal(s) {
  s = s.trim().replace(/['"]/g, '');
  if (!s) return null;
  const m = s.match(/^(\\d+)[-\\s]+(\\d+)\\/(\\d+)$/);
  if (m) return parseInt(m[1]) + parseInt(m[2]) / parseInt(m[3]);
  const f = s.match(/^(\\d+)\\/(\\d+)$/);
  if (f) return parseInt(f[1]) / parseInt(f[2]);
  const n = parseFloat(s);
  return isNaN(n) ? null : n;
}

function convMur(inId, convId) {
  const dec = poucesVersDecimal(document.getElementById(inId).value);
  const el  = document.getElementById(convId);
  if (dec && dec > 0) {
    el.textContent = Math.round(dec * 25.4).toLocaleString('fr-CA') + ' mm';
    el.style.color = '#1F3864';
  } else { el.textContent = ''; }
}

function nbMursSelector(prefix, nbActif, setFn) {
  return '<div style="margin-bottom:12px"><label>Nombre de murs</label>' +
    '<div class="nb-murs-sel" id="nb-murs-' + prefix + '">' +
    [1,2,3,4,5,6,7,8].map(n =>
      '<div class="nb-btn ' + (n===nbActif?'active':'') + '" onclick="' + setFn + '(' + n + ',this)">' + n + '</div>'
    ).join('') +
    '</div></div>';
}

function toggleCustomCouleur(selectId, inputId) {
  const sel = document.getElementById(selectId);
  const inp = document.getElementById(inputId);
  if (sel && inp) inp.style.display = sel.value === 'Gentek — sur mesure' ? 'block' : 'none';
}

function cacherStatut() { document.getElementById('statut').style.display = 'none'; }
function afficherStatut(msg, type) {
  const s = document.getElementById('statut');
  s.textContent = msg; s.className = type; s.style.display = 'block';
}
function valeur(id) { const el = document.getElementById(id); return el ? el.value.trim() : ''; }

async function genererAikaAppro() {
  cacherStatut();
  const btn = document.getElementById('btn-appro');
  const no_projet = valeur('no_projet');
  const client    = valeur('client');
  const _couleurSel = valeur('couleur');
  const couleur   = _couleurSel === 'Autre' ? (valeur('couleur_autre') || 'Autre') : _couleurSel;
  if (!no_projet || !client) {
    afficherStatut('⚠ Veuillez remplir le numéro de projet et le nom du client.', 'error'); return;
  }
  const APPRO_ROUTES = {
    'Aika 6mm':           ['/generer_aika_appro',          collectAikaParams,  'Aika 6mm'],
    'Cadre / Trapèze':    ['/generer_cadre_approbation',   collectCadreParams, 'Cadre / Trapèze'],
    'Néoscenica':         ['/generer_neo_approbation',     collectNeoParams,   'Néoscenica'],
    'Estétika Motorisée': ['/generer_est_mot_approbation', collectEstMotParams,'Estétika Motorisée'],
    'Estétika Manuelle':  ['/generer_est_man_approbation', collectEstManParams,'Estétika Manuelle'],
  };
  const info = APPRO_ROUTES[modeleActif];
  if (!info) { afficherStatut('⚠ Approbation non disponible pour ce modèle.', 'error'); return; }
  const [route, collectFn, label] = info;
  const params = { modele: modeleActif, no_projet, client, couleur, notes: valeur('notes') };
  params.murs = collectFn();
  if (!params.murs.length) { afficherStatut('⚠ Aucun mur configuré.', 'error'); return; }
  btn.disabled = true; afficherStatut(`Génération approbation ${label}…`, 'info');
  try {
    const resp = await fetch(route, { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(params) });
    const data = await resp.json();
    if (data.ok) {
      afficherStatut('✓ PDF : ' + data.fichier, 'ok');
      window.location.href = '/telecharger/' + encodeURIComponent(data.fichier);
    }
    else afficherStatut('✗ Erreur : ' + data.erreur, 'error');
  } catch(e) { afficherStatut('✗ Erreur réseau : ' + e, 'error'); }
  finally { btn.disabled = false; }
}

async function genererAikaPeinture() {
  cacherStatut();
  const btn = document.getElementById('btn-peinture');
  const no_projet = valeur('no_projet');
  const client    = valeur('client');
  const _couleurSel = valeur('couleur');
  const couleur   = _couleurSel === 'Autre' ? (valeur('couleur_autre') || 'Autre') : _couleurSel;
  if (!no_projet || !client) {
    afficherStatut('⚠ Veuillez remplir le numéro de projet et le nom du client.', 'error'); return;
  }
  const PEINTURE_ROUTES = {
    'Aika 6mm':           ['/generer_aika_peinture',   collectAikaParams,  'Aika 6mm'],
    'Cadre / Trapèze':    ['/generer_cadre_peinture',  collectCadreParams, 'Cadre / Trapèze'],
    'Néoscenica':         ['/generer_neo_peinture',    collectNeoParams,   'Néoscenica'],
    'Estétika Motorisée': ['/generer_est_mot_peinture',collectEstMotParams,'Estétika Motorisée'],
    'Estétika Manuelle':  ['/generer_est_man_peinture',collectEstManParams,'Estétika Manuelle'],
  };
  const info = PEINTURE_ROUTES[modeleActif];
  if (!info) { afficherStatut('⚠ Fiche peinture non disponible pour ce modèle.', 'error'); return; }
  const [route, collectFn, label] = info;
  const params = { modele: modeleActif, no_projet, client, couleur, notes: valeur('notes') };
  params.murs = collectFn();
  if (!params.murs.length) { afficherStatut('⚠ Aucun mur configuré.', 'error'); return; }
  btn.disabled = true; afficherStatut(`Génération fiche peinture ${label}…`, 'info');
  try {
    const resp = await fetch(route, { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(params) });
    const data = await resp.json();
    if (data.ok) {
      afficherStatut('✓ PDF : ' + data.fichier, 'ok');
      window.location.href = '/telecharger/' + encodeURIComponent(data.fichier);
    }
    else afficherStatut('✗ Erreur : ' + data.erreur, 'error');
  } catch(e) { afficherStatut('✗ Erreur réseau : ' + e, 'error'); }
  finally { btn.disabled = false; }
}

async function genererVerresCommande() {
  cacherStatut();
  const btn = document.getElementById('btn-verres');
  const no_projet = valeur('no_projet');
  const client    = valeur('client');
  if (!no_projet || !client) {
    afficherStatut('⚠ Veuillez remplir le numéro de projet et le nom du client.', 'error'); return;
  }
  const _couleurSel = valeur('couleur');
  const couleur = _couleurSel === 'Autre' ? (valeur('couleur_autre') || 'Autre') : _couleurSel;
  const VERRE_ROUTES = {
    'Cover 10mm':      ['/generer_verres_cover',   collectCoverParams,  'Cover'],
    'Aika 6mm':        ['/generer_verres_aika',    collectAikaParams,   'Aika'],
    'Cadre / Trapèze': ['/generer_cadre_verres',   collectCadreParams,  'Cadre / Trapèze'],
  };
  const info = VERRE_ROUTES[modeleActif];
  if (!info) { afficherStatut('⚠ Commande verre non disponible pour ce modèle.', 'error'); return; }
  const [route, collectFn, label] = info;
  const params = { modele: modeleActif, no_projet, client, couleur, notes: valeur('notes') };
  params.murs = collectFn();
  if (!params.murs.length) { afficherStatut('⚠ Aucun mur configuré.', 'error'); return; }
  btn.disabled = true; afficherStatut(`Génération bon de commande verre ${label}…`, 'info');
  try {
    const resp = await fetch(route, { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(params) });
    const data = await resp.json();
    if (data.ok) {
      afficherStatut('✓ PDF : ' + data.fichier, 'ok');
      window.location.href = '/telecharger/' + encodeURIComponent(data.fichier);
    }
    else afficherStatut('✗ Erreur : ' + data.erreur, 'error');
  } catch(e) { afficherStatut('✗ Erreur réseau : ' + e, 'error'); }
  finally { btn.disabled = false; }
}

async function generer() {
  cacherStatut();
  const btn = document.getElementById('btn');
  const no_projet = valeur('no_projet');
  const client    = valeur('client');
  const _couleurSel = valeur('couleur');
  const couleur   = _couleurSel === 'Autre' ? (valeur('couleur_autre') || 'Autre') : _couleurSel;
  if (!no_projet || !client) {
    afficherStatut('⚠ Veuillez remplir le numéro de projet et le nom du client.', 'error'); return;
  }
  const params = { modele: modeleActif, no_projet, client, couleur, notes: valeur('notes') };
  const ROUTES = {
    'Néoscenica':        ['/generer_neoscenica',   collectNeoParams,    'Néoscenica…'],
    'Cadre / Trapèze':   ['/generer_cadre',         collectCadreParams,  'Cadre / Trapèze…'],
    'Estétika Motorisée':['/generer_esthetika_mot', collectEstMotParams, 'Estétika Motorisée…'],
    'Estétika Manuelle': ['/generer_esthetika_man', collectEstManParams, 'Estétika Manuelle…'],
    'Cover 10mm':        ['/generer_cover',         collectCoverParams,  'Cover 10mm…'],
    'Aika 6mm':          ['/generer_aika',          collectAikaParams,   'Aika 6mm…'],
  };
  const info = ROUTES[modeleActif];
  if (!info) { afficherStatut('⚠ Modèle inconnu.', 'error'); return; }
  const [route, collectFn, label] = info;
  params.murs = collectFn();
  if (!params.murs.length) { afficherStatut('⚠ Aucun mur configuré.', 'error'); return; }
  btn.disabled = true; afficherStatut('Génération ' + label, 'info');
  try {
    const resp = await fetch(route, { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(params) });
    const data = await resp.json();
    if (data.ok) {
      afficherStatut('✓ PDF : ' + data.fichier, 'ok');
      window.location.href = '/telecharger/' + encodeURIComponent(data.fichier);
    }
    else afficherStatut('✗ Erreur : ' + data.erreur, 'error');
  } catch(e) { afficherStatut('✗ Erreur réseau : ' + e, 'error'); }
  finally { btn.disabled = false; }
}

// ══════════════════════════════════════════════════
// NÉOSCENICA
// ══════════════════════════════════════════════════
let nbMursNeo = 1;
function renderNeoForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('neo', nbMursNeo, 'setNbMursNeo') + '<div id="neo-murs"></div>';
  renderMursNeo();
}
function setNbMursNeo(n, btn) {
  document.querySelectorAll('#nb-murs-neo .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const container = document.getElementById('neo-murs');
  const current = container.querySelectorAll('.mur-card').length;
  if (n > current) {
    for (let i = current + 1; i <= n; i++) {
      container.insertAdjacentHTML('beforeend', neoMurBlock(i));
    }
  } else if (n < current) {
    const cards = container.querySelectorAll('.mur-card');
    for (let i = current; i > n; i--) cards[i-1].remove();
  }
  nbMursNeo = n;
}
function neoMurBlock(n) {
  return `<div class="mur-card"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="nm${n}_nom" placeholder="ex: Façade"></div>
      <div><label>Largeur (pouces)</label>
        <input type="text" id="nm${n}_largeur" placeholder="ex: 180" oninput="convMur('nm${n}_largeur','nm${n}_cl')">
        <span id="nm${n}_cl" class="hint"></span></div>
      <div><label>Hauteur (pouces)</label>
        <input type="text" id="nm${n}_hauteur" placeholder="ex: 96" oninput="convMur('nm${n}_hauteur','nm${n}_ch')">
        <span id="nm${n}_ch" class="hint"></span></div>
    </div>
    <div class="row3" style="margin-top:10px">
      <div><label>Type</label>
        <select id="nm${n}_type" onchange="toggleNeoType(${n})">
          <option value="Simple">Simple</option>
          <option value="Double">Double</option>
        </select></div>
      <div><label>Sens de l'ouverture</label>
        <select id="nm${n}_sens">
          <option value="Gauche">Gauche</option>
          <option value="Droite">Droite</option>
          <option value="Centre">Centre</option>
        </select></div>
      <div><label>Couleur extrusions</label>
        <select id="nm${n}_couleur_alu" onchange="toggleCustomCouleur('nm${n}_couleur_alu','nm${n}_couleur_custom')">
          <option value="Blanc (RAL 9016)">Blanc (RAL 9016)</option>
          <option value="Noir (RAL 9017)">Noir (RAL 9017)</option>
          <option value="Gentek — sur mesure">Gentek — sur mesure</option>
        </select>
        <input type="text" id="nm${n}_couleur_custom" placeholder="Préciser la couleur" style="margin-top:5px;display:none"></div>
    </div>
    <div id="nm${n}_double_opts" style="display:none;margin-top:10px;padding:10px;background:#f0f4ff;border-radius:6px">
      <div class="row3">
        <div><label>Partage des panneaux</label>
          <select id="nm${n}_partage" onchange="toggleNeoPartage(${n})">
            <option value="egal">Égal (L ÷ 2)</option>
            <option value="sur_mesure">Sur mesure</option>
          </select></div>
        <div id="nm${n}_pan_a_wrap" style="display:none"><label>Largeur Panneau A (pouces)</label>
          <input type="text" id="nm${n}_pan_a" placeholder="ex: 54"></div>
        <div id="nm${n}_pan_b_wrap" style="display:none"><label>Largeur Panneau B (pouces)</label>
          <input type="text" id="nm${n}_pan_b" placeholder="ex: 90"></div>
      </div>
    </div>
  </div>`;
}
function toggleNeoType(n) {
  const type = document.getElementById('nm' + n + '_type').value;
  document.getElementById('nm' + n + '_double_opts').style.display = type === 'Double' ? 'block' : 'none';
  if (type !== 'Double') {
    document.getElementById('nm' + n + '_pan_a_wrap').style.display = 'none';
    document.getElementById('nm' + n + '_pan_b_wrap').style.display = 'none';
  }
}
function toggleNeoPartage(n) {
  const show = document.getElementById('nm' + n + '_partage').value === 'sur_mesure';
  document.getElementById('nm' + n + '_pan_a_wrap').style.display = show ? 'block' : 'none';
  document.getElementById('nm' + n + '_pan_b_wrap').style.display = show ? 'block' : 'none';
}
function renderMursNeo() {
  let html = '';
  for (let i = 1; i <= nbMursNeo; i++) html += neoMurBlock(i);
  document.getElementById('neo-murs').innerHTML = html;
}
function collectNeoParams() {
  const murs = [];
  for (let i = 1; i <= nbMursNeo; i++) {
    const type    = document.getElementById('nm' + i + '_type')?.value || 'Simple';
    const partage = type === 'Double'
      ? (document.getElementById('nm' + i + '_partage')?.value || 'egal')
      : null;
    const mur = {
      nom:     document.getElementById('nm' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur: document.getElementById('nm' + i + '_largeur')?.value || '0',
      hauteur: document.getElementById('nm' + i + '_hauteur')?.value || '0',
      type,
      sens:        document.getElementById('nm' + i + '_sens')?.value || 'Gauche',
      couleur_alu:    document.getElementById('nm' + i + '_couleur_alu')?.value || 'Blanc (RAL 9016)',
      couleur_custom: document.getElementById('nm' + i + '_couleur_custom')?.value || '',
    };
    if (type === 'Double') {
      mur.partage = partage;
      if (partage === 'sur_mesure') {
        mur.largeur_pan_a = document.getElementById('nm' + i + '_pan_a')?.value || '';
        mur.largeur_pan_b = document.getElementById('nm' + i + '_pan_b')?.value || '';
      }
    }
    murs.push(mur);
  }
  return murs;
}

// ══════════════════════════════════════════════════
// CADRE / TRAPÈZE
// ══════════════════════════════════════════════════
let nbMursCadre = 1;
function renderCadreForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('cadre', nbMursCadre, 'setNbMursCadre') + '<div id="cadre-murs"></div>';
  renderMursCadre();
}
function setNbMursCadre(n, btn) {
  nbMursCadre = n;
  document.querySelectorAll('#nb-murs-cadre .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); renderMursCadre();
}
function cadreMurBlock(n) {
  return `<div class="mur-card"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="ca${n}_nom" placeholder="ex: Façade"></div>
      <div><label>Largeur totale (pouces)</label>
        <input type="text" id="ca${n}_largeur" placeholder="ex: 194-5/8" oninput="convMur('ca${n}_largeur','ca${n}_cl')">
        <span id="ca${n}_cl" class="hint"></span></div>
      <div><label>Type de mur</label>
        <select id="ca${n}_type" onchange="updateCadreType(${n})">
          <option value="cadre">Cadre rectangulaire</option>
          <option value="trapeze">Trap&#232;ze</option>
        </select></div>
    </div>
    <div class="row3" style="margin-top:8px">
      <div id="ca${n}_h_wrap"><label>Hauteur (pouces)</label>
        <input type="text" id="ca${n}_hauteur" placeholder="ex: 42" oninput="convMur('ca${n}_hauteur','ca${n}_ch')">
        <span id="ca${n}_ch" class="hint"></span></div>
      <div id="ca${n}_vg_wrap" style="display:none"><label>V.G. — Hauteur gauche (pouces)<br><small style="font-weight:normal;color:#888;">👁 vue depuis l'extérieur</small></label>
        <input type="text" id="ca${n}_vg" placeholder="ex: 47-1/4" oninput="convMur('ca${n}_vg','ca${n}_cvg')">
        <span id="ca${n}_cvg" class="hint"></span></div>
      <div id="ca${n}_vd_wrap" style="display:none"><label>V.D. — Hauteur droite (pouces)<br><small style="font-weight:normal;color:#888;">👁 vue depuis l'extérieur</small></label>
        <input type="text" id="ca${n}_vd" placeholder="ex: 6" oninput="convMur('ca${n}_vd','ca${n}_cvd')">
        <span id="ca${n}_cvd" class="hint"></span></div>
      <div><label>Nombre de montants verticaux</label>
        <input type="text" id="ca${n}_nb_montants" placeholder="ex: 5" style="max-width:180px"></div>
    </div>
  </div>`;
}
function updateCadreType(n) {
  const isTrap = document.getElementById('ca' + n + '_type').value === 'trapeze';
  document.getElementById('ca' + n + '_h_wrap').style.display = isTrap ? 'none' : '';
  document.getElementById('ca' + n + '_vg_wrap').style.display = isTrap ? '' : 'none';
  document.getElementById('ca' + n + '_vd_wrap').style.display = isTrap ? '' : 'none';
}
function renderMursCadre() {
  let html = '';
  for (let i = 1; i <= nbMursCadre; i++) html += cadreMurBlock(i);
  document.getElementById('cadre-murs').innerHTML = html;
}
function collectCadreParams() {
  const murs = [];
  for (let i = 1; i <= nbMursCadre; i++) {
    const type = document.getElementById('ca' + i + '_type')?.value || 'cadre';
    const isTrap = type === 'trapeze';
    const obj = {
      nom:         document.getElementById('ca' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur:     document.getElementById('ca' + i + '_largeur')?.value || '0',
      type:        type,
      nb_montants: document.getElementById('ca' + i + '_nb_montants')?.value || '2',
    };
    if (isTrap) {
      obj.vg = document.getElementById('ca' + i + '_vg')?.value || '0';
      obj.vd = document.getElementById('ca' + i + '_vd')?.value || '0';
    } else {
      obj.hauteur = document.getElementById('ca' + i + '_hauteur')?.value || '0';
    }
    murs.push(obj);
  }
  return murs;
}

// ══════════════════════════════════════════════════
// ESTÉTIKA MOTORISÉE
// ══════════════════════════════════════════════════
let nbMursEstMot = 1;
function renderEstMotForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('estmot', nbMursEstMot, 'setNbMursEstMot') + '<div id="estmot-murs"></div>';
  renderMursEstMot();
}
function setNbMursEstMot(n, btn) {
  nbMursEstMot = n;
  document.querySelectorAll('#nb-murs-estmot .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); renderMursEstMot();
}
function estMotMurBlock(n) {
  return `<div class="mur-card"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="em${n}_nom" placeholder="ex: Terrasse"></div>
      <div><label>Largeur (pouces)</label>
        <input type="text" id="em${n}_largeur" placeholder="ex: 144" oninput="convMur('em${n}_largeur','em${n}_cl')">
        <span id="em${n}_cl" class="hint"></span></div>
      <div><label>Hauteur (pouces)</label>
        <input type="text" id="em${n}_hauteur" placeholder="ex: 84" oninput="convMur('em${n}_hauteur','em${n}_ch')">
        <span id="em${n}_ch" class="hint"></span></div>
    </div></div>`;
}
function renderMursEstMot() {
  let html = '';
  for (let i = 1; i <= nbMursEstMot; i++) html += estMotMurBlock(i);
  document.getElementById('estmot-murs').innerHTML = html;
}
function collectEstMotParams() {
  const murs = [];
  for (let i = 1; i <= nbMursEstMot; i++) {
    murs.push({
      nom:     document.getElementById('em' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur: document.getElementById('em' + i + '_largeur')?.value || '0',
      hauteur: document.getElementById('em' + i + '_hauteur')?.value || '0',
    });
  }
  return murs;
}

// ══════════════════════════════════════════════════
// ESTÉTIKA MANUELLE
// ══════════════════════════════════════════════════
let nbMursEstMan = 1;
function renderEstManForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('estman', nbMursEstMan, 'setNbMursEstMan') + '<div id="estman-murs"></div>';
  renderMursEstMan();
}
function setNbMursEstMan(n, btn) {
  nbMursEstMan = n;
  document.querySelectorAll('#nb-murs-estman .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); renderMursEstMan();
}
function estManMurBlock(n) {
  return `<div class="mur-card"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="ema${n}_nom" placeholder="ex: Terrasse"></div>
      <div><label>Largeur (pouces)</label>
        <input type="text" id="ema${n}_largeur" placeholder="ex: 144" oninput="convMur('ema${n}_largeur','ema${n}_cl')">
        <span id="ema${n}_cl" class="hint"></span></div>
      <div><label>Hauteur (pouces)</label>
        <input type="text" id="ema${n}_hauteur" placeholder="ex: 84" oninput="convMur('ema${n}_hauteur','ema${n}_ch')">
        <span id="ema${n}_ch" class="hint"></span></div>
    </div></div>`;
}
function renderMursEstMan() {
  let html = '';
  for (let i = 1; i <= nbMursEstMan; i++) html += estManMurBlock(i);
  document.getElementById('estman-murs').innerHTML = html;
}
function collectEstManParams() {
  const murs = [];
  for (let i = 1; i <= nbMursEstMan; i++) {
    murs.push({
      nom:     document.getElementById('ema' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur: document.getElementById('ema' + i + '_largeur')?.value || '0',
      hauteur: document.getElementById('ema' + i + '_hauteur')?.value || '0',
    });
  }
  return murs;
}

// ══════════════════════════════════════════════════
// COVER 10MM
// ══════════════════════════════════════════════════
const COULEURS_ALU_C = ['Blanc (RAL 9016)','Noir (RAL 9017)','Bronze','Champagne','Autre'];
const COULEURS_VERRE_C = ['Clair','Teinté gris','Teinté bronze'];
const MODELES_OUV_C = ['A/i','B/i','C/i','D/i','E/i','A/e','B/e','C/e','D/e','E/e'];
let nbMursCover = 2;
function renderCoverForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('c', nbMursCover, 'setNbMursC') + '<div id="cover-murs"></div>';
  renderMursCover();
}
function setNbMursC(n, btn) {
  nbMursCover = n;
  document.querySelectorAll('#nb-murs-c .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); renderMursCover();
}
function coverMurBlock(n) {
  const s = (arr,sel='')=>arr.map(o=>`<option ${o===sel?'selected':''}>${o}</option>`).join('');
  return `<div class="mur-card"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="sub-lbl">Dimensions</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="cm${n}_nom" placeholder="ex: Façade"></div>
      <div><label>Largeur L (pouces)</label>
        <input type="text" id="cm${n}_largeur" placeholder="ex: 154-3/8" oninput="convMur('cm${n}_largeur','cm${n}_cl')">
        <span id="cm${n}_cl" class="hint"></span></div>
      <div><label>Hauteur H (pouces)</label>
        <input type="text" id="cm${n}_hauteur" placeholder="ex: 96" oninput="convMur('cm${n}_hauteur','cm${n}_ch')">
        <span id="cm${n}_ch" class="hint"></span></div>
    </div><div class="sep"></div>
    <div class="sub-lbl">Panneaux</div>
    <div class="row3">
      <div><label># de panneaux</label><input type="text" id="cm${n}_nb_panneaux" placeholder="ex: 5"></div>
      <div><label>Modèle ouverture</label><select id="cm${n}_modele">${s(MODELES_OUV_C,'B/i')}</select></div>
      <div><label>Largeur porte (pouces)</label>
        <input type="text" id="cm${n}_largeur_porte" placeholder="ex: 36" style="background:#fffbe6;border-color:#C68B00"></div>
    </div>
    <div style="display:flex;gap:16px;margin:8px 0">
      <label style="font-size:13px;display:flex;align-items:center;gap:5px">
        <input type="checkbox" id="cm${n}_encastre"> Encastré</label>
      <label style="font-size:13px;display:flex;align-items:center;gap:5px">
        <input type="checkbox" id="cm${n}_egaux" checked> Panneaux égaux</label>
    </div><div class="sep"></div>
    <div class="sub-lbl">Finition</div>
    <div class="row3">
      <div><label>Couleur extrusions</label><select id="cm${n}_couleur_alu">${s(COULEURS_ALU_C)}</select></div>
      <div><label>Couleur du verre</label><select id="cm${n}_couleur_verre">${s(COULEURS_VERRE_C)}</select></div>
      <div><label>Type de serrure</label><select id="cm${n}_serrure">
        <option value="simple">Bouton simple (10-9033-1)</option>
        <option value="double">Bouton double (10-9033-2)</option>
      </select></div>
    </div></div>`;
}
function renderMursCover() {
  let html = '';
  for (let i = 1; i <= nbMursCover; i++) html += coverMurBlock(i);
  document.getElementById('cover-murs').innerHTML = html;
}
function collectCoverParams() {
  const murs = [];
  for (let i = 1; i <= nbMursCover; i++) {
    murs.push({
      nom:           document.getElementById('cm' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur:       document.getElementById('cm' + i + '_largeur')?.value || '0',
      hauteur:       document.getElementById('cm' + i + '_hauteur')?.value || '0',
      nb_panneaux:   document.getElementById('cm' + i + '_nb_panneaux')?.value || '1',
      modele:        document.getElementById('cm' + i + '_modele')?.value || 'B/i',
      largeur_porte: document.getElementById('cm' + i + '_largeur_porte')?.value || '',
      encastre:      document.getElementById('cm' + i + '_encastre')?.checked || false,
      panneaux_egaux:document.getElementById('cm' + i + '_egaux')?.checked ?? true,
      couleur_alu:   document.getElementById('cm' + i + '_couleur_alu')?.value || 'Blanc (RAL 9016)',
      couleur_verre: document.getElementById('cm' + i + '_couleur_verre')?.value || 'Clair',
      serrure:       document.getElementById('cm' + i + '_serrure')?.value || 'simple',
    });
  }
  return murs;
}

// ══════════════════════════════════════════════════
// AIKA 6MM
// ══════════════════════════════════════════════════
const MODELES_AIKA = ['A','B','C','D','E','F','G'];
const RAILS_AIKA = [2,3,4,5,6,7,8];
const COULEURS_ALU_A = ['Blanc (RAL 9016)','Noir (RAL 9017)','Gentek — sur mesure'];
const COULEURS_VERRE_A = ['Clair','Teinté gris','Teinté bronze','Givré'];
const SERRURES_AIKA = [
  {id:'barrure_int',    label:'Barrure intérieure',  desc:'Verrou int. — 60-9004'},
  {id:'poignee_ext',    label:'Poignée ext. simple', desc:'Coulissante — 60-9010'},
  {id:'barrure_centre', label:'Barrure centre',      desc:'Double — 60-9007'},
  {id:'barrure_cle',    label:'Barrure à clé',       desc:'Abloy — 60-9002'},
];
let nbMursAika = 2;
function renderAikaForm() {
  document.getElementById('champs-dimensions').innerHTML =
    nbMursSelector('a', nbMursAika, 'setNbMursA') + '<div id="aika-murs"></div>';
  renderMursAika();
}
function setNbMursA(n, btn) {
  nbMursAika = n;
  document.querySelectorAll('#nb-murs-a .nb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); renderMursAika();
}
function modeleOptsAika(rails) {
  return MODELES_AIKA.map(l => `<option value="${l}${rails}">${l}${rails} — Vue intérieur</option>`).join('');
}
function aikaMurBlock(n) {
  const s = (arr,sel='')=>arr.map(o=>`<option ${o===sel?'selected':''}>${o}</option>`).join('');
  return `<div class="mur-card" id="am-${n}"><div class="mur-header">Mur ${String.fromCharCode(64 + n)}</div>
    <div class="sub-lbl">Dimensions</div>
    <div class="row3">
      <div><label>Nom du mur</label><input type="text" id="am${n}_nom" placeholder="ex: Façade"></div>
      <div><label>Largeur L (pouces)</label>
        <input type="text" id="am${n}_largeur" placeholder="ex: 124-1/2" oninput="convMur('am${n}_largeur','am${n}_cl')">
        <span id="am${n}_cl" class="hint"></span></div>
      <div><label>Hauteur H (pouces)</label>
        <input type="text" id="am${n}_hauteur" placeholder="ex: 82-11/16" oninput="convMur('am${n}_hauteur','am${n}_ch')">
        <span id="am${n}_ch" class="hint"></span></div>
    </div><div class="sep"></div>
    <div class="sub-lbl">Panneaux</div>
    <div class="row3">
      <div><label># de rails</label>
        <select id="am${n}_rails" onchange="updateModeleAika(${n})">
          ${RAILS_AIKA.map(r=>`<option value="${r}"${r===3?' selected':''}>${r} rails</option>`).join('')}
        </select></div>
      <div><label># de panneaux</label>
        <input type="text" id="am${n}_nb_panneaux" placeholder="ex: 6"></div>
      <div><label>Modèle ouverture</label>
        <select id="am${n}_modele">${modeleOptsAika(3)}</select></div>
    </div>
    <div style="display:flex;gap:16px;margin:8px 0">
      <label style="font-size:13px;display:flex;align-items:center;gap:5px">
        <input type="checkbox" id="am${n}_encastre"> Encastré</label>
    </div><div class="sep"></div>
    <div class="sub-lbl">Serrures(s) <span style="font-size:10px;font-weight:400;color:#888">— max 2</span></div>
    <div class="serrure-grid" id="am${n}_serrures">
      ${SERRURES_AIKA.map(sr=>`
      <div class="sbtn ${sr.id==='barrure_int'?'on':''}" onclick="toggleSerrureAika(this,'am${n}_serrures')">
        <div class="scheck"></div>
        <div><span class="st">${sr.label}</span><span class="sd">${sr.desc}</span></div>
        <input type="hidden" value="${sr.id}">
      </div>`).join('')}
    </div><div class="sep"></div>
    <div class="sub-lbl">Poignée</div>
    <div class="row3">
      <div><label>Type de poignée</label>
        <select id="am${n}_poignee">
          <option value="920_1">920 mm — 1 côté</option>
          <option value="920_2">920 mm — 2 côtés</option>
          <option value="250_1">250 mm — 1 côté</option>
          <option value="250_2">250 mm — 2 côtés</option>
        </select></div>
    </div>
    <div class="sep"></div>
    <div class="sub-lbl">Finition</div>
    <div class="row3">
      <div><label>Couleur extrusions</label><select id="am${n}_couleur_alu">${s(COULEURS_ALU_A)}</select></div>
      <div><label>Couleur du verre</label><select id="am${n}_couleur_verre">${s(COULEURS_VERRE_A)}</select></div>
    </div></div>`;
}
function renderMursAika() {
  let html = '';
  for (let i = 1; i <= nbMursAika; i++) html += aikaMurBlock(i);
  document.getElementById('aika-murs').innerHTML = html;
}
function updateModeleAika(n) {
  const r = document.getElementById('am' + n + '_rails').value;
  document.getElementById('am' + n + '_modele').innerHTML = modeleOptsAika(r);
}
function toggleSerrureAika(btn, gridId) {
  const grid = document.getElementById(gridId);
  const actifs = grid.querySelectorAll('.sbtn.on');
  if (btn.classList.contains('on')) btn.classList.remove('on');
  else if (actifs.length < 2) btn.classList.add('on');
}
function collectAikaParams() {
  const murs = [];
  for (let i = 1; i <= nbMursAika; i++) {
    const serrures = [];
    document.querySelectorAll('#am' + i + '_serrures .sbtn.on').forEach(btn => {
      serrures.push(btn.querySelector('input[type=hidden]').value);
    });
    const rails = parseInt(document.getElementById('am' + i + '_rails')?.value || '3');
    const modele_raw = document.getElementById('am' + i + '_modele')?.value || 'A3';
    const modele = modele_raw.replace(/[0-9]+/, '');
    murs.push({
      nom:           document.getElementById('am' + i + '_nom')?.value || 'Mur ' + String.fromCharCode(64 + i),
      largeur:       document.getElementById('am' + i + '_largeur')?.value || '0',
      hauteur:       document.getElementById('am' + i + '_hauteur')?.value || '0',
      nb_rails:      String(rails),
      nb_panneaux:   document.getElementById('am' + i + '_nb_panneaux')?.value || '1',
      modele,
      encastre:      document.getElementById('am' + i + '_encastre')?.checked || false,
      couleur_alu:   document.getElementById('am' + i + '_couleur_alu')?.value || 'Blanc (RAL 9016)',
      couleur_verre: document.getElementById('am' + i + '_couleur_verre')?.value || 'Clair',
      serrures,
      poignee:       document.getElementById('am' + i + '_poignee')?.value || '920_1',
    });
  }
  return murs;
}

// ══════════════════════════════════════════════════
// ONGLETS
// ══════════════════════════════════════════════════
function afficherOnglet(id, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  if (id === 'soumissions') chargerSoumissions();
}

// ══════════════════════════════════════════════════
// SOUMISSIONS
// ══════════════════════════════════════════════════
const STATUTS = [
  { key: 'À faire',            cls: 'faire',   label: 'À faire' },
  { key: 'En attente',         cls: 'attente', label: 'En attente' },
  { key: 'Soumission envoyée', cls: 'envoye',  label: 'Soumission envoyée' },
  { key: 'Gagné',              cls: 'gagne',   label: 'Gagné' },
  { key: 'Perdu',              cls: 'perdu',   label: 'Perdu' },
];
const STATUT_CLS = { 'À faire':'faire','En attente':'attente','Soumission envoyée':'envoye','Gagné':'gagne','Perdu':'perdu' };

let _soumissionsCache = [];

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function formatDate(s) {
  if (!s) return '';
  try { return new Date(s).toLocaleDateString('fr-CA', { year:'numeric', month:'short', day:'numeric' }); }
  catch { return s.slice(0,10); }
}
function cardId(msgId) { return 'card-' + btoa(unescape(encodeURIComponent(msgId))).replace(/[^a-zA-Z0-9]/g,''); }

function statutBtns(msgId, statutActif, context) {
  return STATUTS.map(st =>
    `<button class="sbtn-statut sbtn-${st.cls} ${statutActif===st.key?'active':''}"
      onclick="event.stopPropagation();majStatut('${esc(msgId)}','${st.key}','${context}')">${st.label}</button>`
  ).join('');
}

function renderSoumissionCard(s) {
  const cls   = STATUT_CLS[s.statut] || 'faire';
  const mid   = esc(s.msg_id);
  const desc  = (s.description || '').replace(/\\n/g,' ').trim();
  return `<div class="soum-card statut-${cls}" id="${cardId(s.msg_id)}" onclick="ouvrirModal('${mid}')">
    <div class="soum-card-top">
      <div>
        ${s.no_projet ? `<div class="soum-no">${esc(s.no_projet)}</div>` : ''}
        <div class="soum-client">${esc(s.client || s.nom_projet || '(sans nom)')}</div>
        ${s.telephone ? `<div class="soum-tel">📞 ${esc(s.telephone)}</div>` : ''}
      </div>
      ${s.type_travaux ? `<span class="soum-type">${esc(s.type_travaux)}</span>` : ''}
    </div>
    ${desc ? `<div class="soum-desc" title="${esc(desc)}">${esc(desc.length>110 ? desc.slice(0,110)+'…' : desc)}</div>` : ''}
    <div class="soum-footer">
      <span class="soum-date">${formatDate(s.date_reception)}</span>
      <div class="statut-btns">${statutBtns(s.msg_id, s.statut, 'card')}</div>
    </div>
  </div>`;
}

async function chargerSoumissions() {
  try {
    const resp = await fetch('/soumissions');
    _soumissionsCache = await resp.json();
    const liste = document.getElementById('soum-liste');
    const count = document.getElementById('soum-count');
    if (!_soumissionsCache.length) {
      liste.innerHTML = '<p id="soum-vide">Aucune soumission. Cliquez sur Scanner pour importer les courriels.</p>';
      count.textContent = '';
    } else {
      liste.innerHTML = _soumissionsCache.map(renderSoumissionCard).join('');
      count.textContent = _soumissionsCache.length + ' soumission' + (_soumissionsCache.length > 1 ? 's' : '');
    }
  } catch(e) { document.getElementById('soum-liste').innerHTML = '<p style="color:red">Erreur : ' + e + '</p>'; }
}

async function scannerSoumissions() {
  const btn = document.getElementById('btn-scan');
  btn.disabled = true; btn.textContent = 'Scan en cours…';
  try {
    const resp = await fetch('/soumissions/scan', { method: 'POST' });
    const data = await resp.json();
    if (data.ok) {
      await chargerSoumissions();
      btn.textContent = '✓ ' + data.nouveaux + ' nouveau(x)';
      setTimeout(() => { btn.textContent = '↻  Scanner les courriels'; btn.disabled = false; }, 2500);
    } else {
      btn.textContent = '✗ Erreur'; btn.disabled = false;
      alert('Erreur scan : ' + data.erreur);
    }
  } catch(e) { btn.textContent = '✗ Réseau'; btn.disabled = false; }
}

async function majStatut(msgId, statut, context) {
  await fetch('/soumissions/maj_statut', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ msg_id: msgId, statut }),
  });
  await chargerSoumissions();
  // Ré-ouvrir le modal si le changement vient du modal
  if (context === 'modal') ouvrirModal(msgId);
}

// ── Modal ──
function ouvrirModal(msgId) {
  const s = _soumissionsCache.find(x => x.msg_id === msgId);
  if (!s) return;
  const titre = s.no_projet || s.nom_projet || s.client || 'Dossier';
  document.getElementById('modal-titre').textContent = titre;
  function field(label, val) {
    if (!val) return '';
    return `<div class="modal-field"><div class="modal-label">${label}</div><div class="modal-value">${esc(val)}</div></div>`;
  }
  document.getElementById('modal-body').innerHTML =
    field('Numéro de projet', s.no_projet) +
    field('Nom du projet',    s.nom_projet) +
    field('Client',           s.client) +
    field('Adresse',          s.adresse) +
    field('Téléphone',        s.telephone) +
    field('Type de travaux',  s.type_travaux) +
    field('Date reçue',       formatDate(s.date_reception)) +
    (s.description ? `<div class="modal-field"><div class="modal-label">Description</div><div class="modal-desc">${esc(s.description)}</div></div>` : '') +
    (s.parse_error ? `<div class="modal-field"><div class="modal-label" style="color:#dc3545">Erreur parsing PDF</div><div class="modal-value" style="color:#dc3545">${esc(s.parse_error)}</div></div>` : '');
  document.getElementById('modal-statut-btns').innerHTML = statutBtns(msgId, s.statut, 'modal');
  document.getElementById('soum-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function fermerModal() {
  document.getElementById('soum-modal').classList.remove('open');
  document.body.style.overflow = '';
}
function fermerModalSi(e) { if (e.target === e.currentTarget) fermerModal(); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') fermerModal(); });

// Init
renderNeoForm();
</script>
</body>
</html>"""

# ─── FLASK APP ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

_SP_PASSWORD       = os.environ.get("SP_PASSWORD", "")        # Cédric (limité)
_SP_ADMIN_PASSWORD = os.environ.get("SP_ADMIN_PASSWORD", "")  # Benoît (admin)

@app.before_request
def basic_auth():
    if not _SP_PASSWORD:
        return
    auth = request.authorization
    if not auth or auth.password not in (_SP_PASSWORD, _SP_ADMIN_PASSWORD):
        return Response(
            "Accès Solarium Pro — Production\nMot de passe requis.",
            401,
            {"WWW-Authenticate": 'Basic realm="Solarium Pro Production"'},
        )
    from flask import g
    g.is_admin = bool(_SP_ADMIN_PASSWORD and auth.password == _SP_ADMIN_PASSWORD)

def _require_admin():
    from flask import g
    if not getattr(g, 'is_admin', False):
        return Response("Accès réservé à l'administrateur.", 403)

@app.route("/")
def index():
    return render_template_string(HTML)

def _nom_fichier(modele, no_proj, client):
    safe_proj   = no_proj.replace("/", "-").replace(" ", "_")
    safe_client = client.replace(" ", "_")
    safe_modele = modele.replace(" ", "_").replace("/", "-")
    return f"{safe_modele}_{safe_proj}_{safe_client}_{date.today()}.pdf"

@app.route("/generer_neoscenica", methods=["POST"])
def generer_neoscenica():
    try:
        params = request.get_json(force=True)
        nom    = _nom_fichier("Neoscenica", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        neo_mod.generer_pdf_neoscenica(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_cadre", methods=["POST"])
def generer_cadre_route():
    try:
        params = request.get_json(force=True)
        nom    = _nom_fichier("Cadre-Trapeze", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        cadre_new_mod.generer_pdf_cadre(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_cadre_approbation", methods=["POST"])
def generer_cadre_approbation():
    try:
        params = request.get_json(force=True)
        nom    = _nom_fichier("Cadre-Approbation", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        cadre_new_mod.generer_pdf_cadre(params, chemin, mode='approbation')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_cadre_peinture", methods=["POST"])
def generer_cadre_peinture():
    try:
        params = request.get_json(force=True)
        nom    = _nom_fichier("Cadre-Peinture", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        cadre_new_mod.generer_pdf_cadre(params, chemin, mode='peinture')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_cadre_verres", methods=["POST"])
def generer_cadre_verres():
    try:
        params = request.get_json(force=True)
        nom    = _nom_fichier("Cadre-Verres-IGP", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        cadre_new_mod.generer_pdf_cadre(params, chemin, mode='commande_verre')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_esthetika_mot", methods=["POST"])
def generer_esthetika_mot():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'motorisee'
        nom    = _nom_fichier("Esthetika-Motorisee", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_esthetika_man", methods=["POST"])
def generer_esthetika_man():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'manuelle'
        nom    = _nom_fichier("Esthetika-Manuelle", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_cover", methods=["POST"])
def generer_cover():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Cover10mm", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        cover_mod.generer_pdf_cover(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_aika", methods=["POST"])
def generer_aika():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Aika6mm", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        aika_mod.generer_pdf_aika(params, chemin)
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        os.system(f'open "{chemin}"')
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_aika_appro", methods=["POST"])
def generer_aika_appro():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Aika6mm-Appro", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        aika_mod.generer_pdf_aika(params, chemin, mode='approbation')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_aika_peinture", methods=["POST"])
def generer_aika_peinture():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Aika6mm-Peinture", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        aika_mod.generer_pdf_aika(params, chemin, mode='peinture')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_verres_cover", methods=["POST"])
def generer_verres_cover():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Verres-Cover", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        verres_mod.generer_pdf_verres(params, chemin, produit='cover')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_verres_aika", methods=["POST"])
def generer_verres_aika():
    try:
        params  = request.get_json(force=True)
        nom     = _nom_fichier("Verres-Aika", params.get("no_projet",""), params.get("client",""))
        chemin  = os.path.join(DOSSIER_PDFS, nom)
        verres_mod.generer_pdf_verres(params, chemin, produit='aika')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/telecharger/<nom>")
def telecharger_pdf(nom):
    import re
    if re.search(r'[/\\]', nom): return jsonify({"ok": False}), 400
    chemin = os.path.join(DOSSIER_PDFS, nom)
    return send_file(chemin, as_attachment=True, download_name=nom)

# ─── ROUTES FLASK NEO / ESTÉTIKA (appro + peinture) ─────────────────────────
@app.route("/generer_neo_approbation", methods=["POST"])
def generer_neo_approbation():
    try:
        params = request.get_json(force=True)
        nom = _nom_fichier("Neoscenica-Appro", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        neo_mod.generer_pdf_neoscenica(params, chemin, mode='approbation')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_neo_peinture", methods=["POST"])
def generer_neo_peinture():
    try:
        params = request.get_json(force=True)
        nom = _nom_fichier("Neoscenica-Peinture", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        neo_mod.generer_pdf_neoscenica(params, chemin, mode='peinture')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_est_mot_approbation", methods=["POST"])
def generer_est_mot_approbation():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'motorisee'
        nom = _nom_fichier("Esthetika-Mot-Appro", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin, mode='approbation')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_est_mot_peinture", methods=["POST"])
def generer_est_mot_peinture():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'motorisee'
        nom = _nom_fichier("Esthetika-Mot-Peinture", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin, mode='peinture')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_est_man_approbation", methods=["POST"])
def generer_est_man_approbation():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'manuelle'
        nom = _nom_fichier("Esthetika-Man-Appro", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin, mode='approbation')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/generer_est_man_peinture", methods=["POST"])
def generer_est_man_peinture():
    try:
        params = request.get_json(force=True)
        params['variante'] = 'manuelle'
        nom = _nom_fichier("Esthetika-Man-Peinture", params.get("no_projet",""), params.get("client",""))
        chemin = os.path.join(DOSSIER_PDFS, nom)
        esthetika_mod.generer_pdf_esthetika(params, chemin, mode='peinture')
        shutil.copy2(chemin, os.path.join(BUREAU, nom))
        return jsonify({"ok": True, "fichier": nom})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

# ─── ROUTES SOUMISSIONS ──────────────────────────────────────────────────────
@app.route("/soumissions")
def route_soumissions():
    return jsonify(load_soumissions())

@app.route("/soumissions/scan", methods=["POST"])
def route_scan():
    err = _require_admin()
    if err:
        return err
    try:
        ok, result = scanner_imap_soumissions()
        if ok:
            return jsonify({"ok": True, "nouveaux": result})
        return jsonify({"ok": False, "erreur": result})
    except Exception as ex:
        import traceback
        return jsonify({"ok": False, "erreur": str(ex), "trace": traceback.format_exc()})

@app.route("/soumissions/maj_statut", methods=["POST"])
def route_maj_statut():
    err = _require_admin()
    if err:
        return err
    data   = request.get_json(force=True)
    msg_id = data.get("msg_id", "")
    statut = data.get("statut", "")
    soumissions = load_soumissions()
    for s in soumissions:
        if s["msg_id"] == msg_id:
            s["statut"]      = statut
            s["date_statut"] = datetime.now().isoformat()
            break
    save_soumissions(soumissions)
    return jsonify({"ok": True})

# ─── LANCEMENT ────────────────────────────────────────────────────────────────
def ouvrir_navigateur():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")

if __name__ == "__main__":
    t = threading.Thread(target=ouvrir_navigateur, daemon=True)
    t.start()
    print(f"Module dessin Aika v3 OK")
    print(f"✓ Solarium Pro — http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
