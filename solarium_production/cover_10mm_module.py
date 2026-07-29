"""
COVER 10MM — Module de production Solarium Pro
À intégrer dans solarium_production.py

RÈGLE USINE (permanent) :
  - Zone de dessin : exploiter toute la page, zone_h ≥ 3.5"
  - Annotations/cotes sur les dessins : police ≥ 9 pt
  - Tableaux de données : FONTSIZE ≥ 10 pt (lisibilité atelier)
"""

from fractions import Fraction
import math

# ─── CONSTANTES COVER 10MM ────────────────────────────────────────────────────
BARRES_COVER = {
    "10-1006": {"desc": "Profil guidage supérieur standard",     "long_mm": 6600, "long_po": 6600/25.4},
    "10-1013": {"desc": "Profil guidage supérieur avec ailes",   "long_mm": 6600, "long_po": 6600/25.4},
    "10-1010": {"desc": "Profil guidage inférieur",              "long_mm": 6600, "long_po": 6600/25.4},
    "10-2006": {"desc": "Profil de vitrage 10mm",                "long_mm": 6600, "long_po": 6600/25.4},
    "10-3005": {"desc": "Profil couvercle 10mm",                 "long_mm": 6600, "long_po": 6600/25.4},
}

QUINCAILLERIE_BASE = [
    {"code": "10-6029",   "desc": "Bague fixation verre 10mm",          "unite": "pcs", "qte_par_panneau": 4},
    {"code": "10-6055-1", "desc": "Support de passage",                  "unite": "pcs", "qte_fixe": 2},
    {"code": "10-6076-1", "desc": "Capuchon terminal paire noir (10-2006)", "unite": "pcs", "qte_par_mur": 2},
    {"code": "10-7016",   "desc": "Joint PVC h-seal 3200mm verre 10mm", "unite": "pcs", "qte_par_mur": 1},
    {"code": "10-7018",   "desc": "Joint PVC verre 10mm 3.2m",          "unite": "pcs", "qte_par_mur": 2},
    {"code": "10-7023",   "desc": "Joint terminal languette souple 30mm","unite": "m",   "qte_par_mur": 4},
    {"code": "10-7037",   "desc": "Joint brosse",                        "unite": "m",   "qte_par_mur": 8},
    {"code": "10-7044",   "desc": "Joint glissière profil 10-1010/1013", "unite": "m",   "qte_par_mur": 4},
    {"code": "10-8007",   "desc": "Goupille blocage 3x20",              "unite": "pcs", "qte_par_panneau": 4},
    {"code": "10-8033",   "desc": "Rivet 4.8x20",                       "unite": "pcs", "qte_par_panneau": 4},
    {"code": "10-8089",   "desc": "Vis d'arrêt 4.2x25 Torx",           "unite": "pcs", "qte_fixe": 2},
    {"code": "10-8091",   "desc": "Vis support passage 10-6055-1",      "unite": "pcs", "qte_fixe": 4},
    {"code": "10-9001-A", "desc": "Roue blocage sup. + sabot 10-5022",  "unite": "pcs", "qte_fixe": 2},
    {"code": "10-9003-A", "desc": "Roue ouverture sup. + sabot 10-5005","unite": "pcs", "qte_fixe": 2},
    {"code": "10-9016",   "desc": "Charnière avec 6 agrafes",           "unite": "pcs", "qte_par_mur": 2},
    {"code": "10-9021-A", "desc": "Roue blocage sup. à billes",         "unite": "pcs", "qte_par_panneau": 1},
    {"code": "10-9022-A", "desc": "Roue ouverture sup. à billes",       "unite": "pcs", "qte_par_panneau": 1},
    {"code": "10-9035-1-A","desc": "Roue blocage inf. 1009-10/13",      "unite": "pcs", "qte_fixe": 2},
    {"code": "10-9035-C", "desc": "Roue inférieure 10-1009/10 + sabot", "unite": "pcs", "qte_par_panneau": 1},
    {"code": "10-9045",   "desc": "Trivel avec poignée",                "unite": "pcs", "qte_par_trivel": 1},
    {"code": "10-9049",   "desc": "Stop clamp assemblé",                "unite": "pcs", "qte_par_mur": 1},
    {"code": "10-5004",   "desc": "Plaque d'extrémité profil sup.",     "unite": "pcs", "qte_par_mur": 2},
    {"code": "10-5036",   "desc": "Plaque d'extrémité profil inf.",     "unite": "pcs", "qte_par_mur": 2},
    # Codes présents dans la référence — quantités à confirmer avec Cédric / export Cielo
    {"code": "10-5032",   "desc": "Stop angle 40x25 + vis",             "unite": "pcs", "qte_fixe": 1, "note": "à confirmer"},
    {"code": "10-8088",   "desc": "Vis autoperceuse 4.2x16 Torx",       "unite": "pcs", "qte_fixe": 1, "note": "à confirmer"},
    {"code": "10-9012",   "desc": "Dispositif blocage panneau",          "unite": "pcs", "qte_par_panneau": 1},
    {"code": "10-A-8",    "desc": "Trous verre pour verrou Trivel",      "unite": "pcs", "qte_par_trivel": 1},
    {"code": "10-6004-1", "desc": "Clip trou ouverture (noir)",          "unite": "pcs", "qte_par_panneau": 1},
    {"code": "10-6005-1", "desc": "Guide de roue long (noir, terrasse)", "unite": "pcs", "qte_par_panneau": 1},
]

SERRURE_SIMPLE = {
    "code": "10-9033-1",
    "desc": "Serrure à bouton simple",
    "pieces": [
        {"code": "10-8043", "desc": "Verrou inox",              "qte": 1},
        {"code": "10-8048", "desc": "Vis M4x5 DIN 916",        "qte": 1},
        {"code": "10-8045", "desc": "Boîtier ressort",          "qte": 1},
        {"code": "10-8047", "desc": "Ressort 28x7x0.8",        "qte": 1},
        {"code": "10-8091", "desc": "Vis 4.2x9.5 T20",         "qte": 2},
        {"code": "10-8021", "desc": "Câble inox",               "qte": 1},
        {"code": "10-6025", "desc": "Embout câble",             "qte": 1},
        {"code": "10-6082", "desc": "Support ressort inox",     "qte": 1},
        {"code": "10-5027/1","desc": "Poignée simple",          "qte": 1},
    ]
}

SERRURE_DOUBLE = {
    "code": "10-9033-2",
    "desc": "Serrure à bouton double",
    "pieces": [
        {"code": "10-8043", "desc": "Verrou inox",              "qte": 1},
        {"code": "10-8048", "desc": "Vis M4x5 DIN 916",        "qte": 1},
        {"code": "10-8045", "desc": "Boîtier ressort",          "qte": 1},
        {"code": "10-8047", "desc": "Ressort 28x7x0.8",        "qte": 1},
        {"code": "10-8091", "desc": "Vis 4.2x9.5 T20",         "qte": 2},
        {"code": "10-8021", "desc": "Câble inox",               "qte": 1},
        {"code": "10-6025", "desc": "Embout câble",             "qte": 1},
        {"code": "10-6082", "desc": "Support ressort inox",     "qte": 1},
        {"code": "10-5027/2","desc": "Poignée double",          "qte": 1},
    ]
}

# ─── UTILITAIRES ──────────────────────────────────────────────────────────────
def _mm_to_po(mm):
    return mm / 25.4

def _po_to_mm(po):
    return round(po * 25.4)

def _dvf(d):
    """Decimal vers fraction pouces — arrondit au 1/16 le plus proche"""
    if d is None: return ""
    from math import gcd
    seizieme = round(d * 16) / 16
    entier = int(seizieme)
    reste = seizieme - entier
    if reste < 0.001:
        return f'{entier}"'
    num = round(reste * 16)
    den = 16
    g = gcd(num, den)
    num //= g; den //= g
    if entier == 0:
        return f'{num}/{den}"'
    return f'{entier}-{num}/{den}"'

def _fvd(s):
    """fraction string vers decimal ex: '72-1/4' → 72.25"""
    s = str(s).strip().replace('"','').replace("'","")
    if not s: return 0.0
    m = __import__('re').match(r'^(\d+)[-\s]+(\d+)/(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m2 = __import__('re').match(r'^(\d+)/(\d+)$', s)
    if m2: return int(m2.group(1))/int(m2.group(2))
    return float(s)

def _fmt_dim(po):
    mm = _po_to_mm(po)
    return f'{_dvf(po)}  ({mm:,} mm)'.replace(',', ' ')

def _ffd_cover(pieces_list, utile_po, kerf=0.25):
    """FFD pour profils Cover — barres en pouces"""
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
            if utile_po - b['utilise'] >= besoin:
                b['pieces'].append(piece)
                b['utilise'] += besoin
                placee = True
                break
        if not placee:
            barres.append({'num': len(barres)+1, 'pieces': [piece], 'utilise': besoin})
    for b in barres:
        b['reste'] = utile_po - b['utilise']
    return barres

# ─── CALCULS COVER 10MM ───────────────────────────────────────────────────────
def calculer_mur_cover(mur):
    """
    mur = {
      'nom': str,
      'largeur_po': float,   (dimension 4 trous)
      'hauteur_po': float,
      'nb_panneaux': int,
      'encastre': bool,
      'serrure': 'simple' | 'double',
      'largeur_porte_po': float,  (optionnel, si panneaux inégaux)
      'panneaux_egaux': bool,
      'modele': str,  ex: 'B/i'
      'couleur_alu': str,
      'couleur_verre': str,
    }
    Retourne dict avec profils, verres, quincaillerie calculés
    """
    L = mur['largeur_po']
    H = mur['hauteur_po']
    nb = mur['nb_panneaux']
    egaux = mur.get('panneaux_egaux', True)

    # ── Ajustement hauteur pour encastré ──
    # Encastré = 10-1013 (rail sol avec ailes) qui ajoute 1-1/4" à la hauteur de calcul.
    DELTA_ENCASTRE = 1.25  # pouces
    H_calcul = H + (DELTA_ENCASTRE if mur.get('encastre') else 0)

    # ── Largeurs panneau (calculées avant profils) ────────────────────────────
    if egaux:
        larg_panneau_po = L / nb
        panneaux_po = [(larg_panneau_po, nb, "porte+fixes")]
    else:
        larg_porte_po = mur.get('largeur_porte_po', L/nb)
        larg_fixes_po = (L - larg_porte_po) / (nb - 1) if nb > 1 else L
        panneaux_po = [(larg_porte_po, 1, "porte"), (larg_fixes_po, nb-1, "fixe")]

    # ── Profils ──
    # 10-1006 = rail supérieur TOUJOURS (guidage plafond, non encastré)
    # 10-1013 = rail inférieur encastré (remplace 10-1010 quand encastré)
    # 10-1010 = rail inférieur standard (non encastré)
    profil_inf = "10-1013" if mur.get('encastre') else "10-1010"
    profils = [
        {"code": "10-1006", "desc": BARRES_COVER['10-1006']['desc'], "long_po": L, "qte": 1},
        {"code": profil_inf, "desc": BARRES_COVER[profil_inf]['desc'], "long_po": L, "qte": 1},
    ]
    # 10-2006_10-3005 : 1 profil vitrage+couvercle par panneau × 2 faces
    # Longueur = largeur panneau mm - 11mm (source Cielo 6020/6210)
    for larg_po, qte_pan, _ in panneaux_po:
        long_vitr_mm = _po_to_mm(larg_po) - 11
        profils.append({
            "code": "10-2006_10-3005",
            "desc": "Profil vitrage + couvercle 10mm",
            "long_po": long_vitr_mm / 25.4,
            "qte": 2 * qte_pan,
        })

    # ── Panneaux et verres ──
    H_verre_mm = _po_to_mm(H_calcul) - 6

    if egaux:
        larg_verre_mm = _po_to_mm(larg_panneau_po) - 6
        serrure = mur.get('serrure', 'simple')
        type_verre = "5R R" if mur.get('modele','').endswith('/i') else "5R L"
        verres = [{"type": type_verre, "larg_mm": larg_verre_mm, "haut_mm": H_verre_mm, "qte": nb}]
        panneaux = [{"larg_po": larg_panneau_po, "qte": nb, "type": "porte+fixes"}]
    else:
        larg_porte_verre_mm = _po_to_mm(larg_porte_po) - 6
        larg_fixe_verre_mm  = _po_to_mm(larg_fixes_po) - 6
        verres = [
            {"type": "TRIVEL R", "larg_mm": larg_porte_verre_mm, "haut_mm": H_verre_mm, "qte": 1},
            {"type": "4R",       "larg_mm": larg_fixe_verre_mm,  "haut_mm": H_verre_mm, "qte": nb-1},
        ]
        panneaux = [
            {"larg_po": larg_porte_po, "qte": 1,    "type": "porte"},
            {"larg_po": larg_fixes_po, "qte": nb-1, "type": "fixe"},
        ]

    # ── Quincaillerie ──
    nb_trivel = sum(1 for v in verres if 'TRIVEL' in v['type'])
    quincaillerie = []
    for item in QUINCAILLERIE_BASE:
        q = item.copy()
        if 'qte_par_panneau' in item:
            q['qte_calc'] = item['qte_par_panneau'] * nb
        elif 'qte_fixe' in item:
            q['qte_calc'] = item['qte_fixe']
        elif 'qte_par_mur' in item:
            q['qte_calc'] = item['qte_par_mur']
        elif 'qte_par_trivel' in item:
            q['qte_calc'] = item['qte_par_trivel'] * nb_trivel
        else:
            q['qte_calc'] = 0
        if q['qte_calc'] > 0:
            quincaillerie.append(q)

    # Ajouter serrure
    serrure_data = SERRURE_SIMPLE if mur.get('serrure','simple') == 'simple' else SERRURE_DOUBLE
    for p in serrure_data['pieces']:
        quincaillerie.append({
            "code": p['code'], "desc": p['desc'],
            "unite": "pcs", "qte_calc": p['qte'],
            "groupe": "serrure"
        })

    # Câble 10-1081: hauteur verre porte en mm (basé sur H_calcul aussi)
    larg_porte_po_cable = mur.get('largeur_porte_po', L/nb) if not egaux else L/nb
    cable_mm = H_verre_mm  # hauteur verre porte (déjà calculée avec H_calcul)
    quincaillerie.append({
        "code": "10-1081", "desc": f"Câble acier inox (hauteur verre porte)",
        "unite": "mm", "qte_calc": cable_mm, "groupe": "serrure"
    })

    return {
        "nom": mur['nom'],
        "largeur_po": L,
        "hauteur_po": H,
        "nb_panneaux": nb,
        "modele": mur.get('modele',''),
        "encastre": mur.get('encastre', False),
        "couleur_alu": mur.get('couleur_alu',''),
        "couleur_verre": mur.get('couleur_verre','Clair'),
        "serrure": mur.get('serrure','simple'),
        "profils": profils,
        "verres": verres,
        "panneaux": panneaux,
        "quincaillerie": quincaillerie,
    }

# ─── QR CODE ──────────────────────────────────────────────────────────────────
def _draw_qr(c, no_proj, w, h, inch):
    try:
        import qrcode, tempfile, os
        from reportlab.lib import colors as _colors
        url = f"https://www.appsheet.com/start/c7fc9ce5-7fc0-4eac-966f-7e36732e8116#view=PROJETS_Detail&row={no_proj}"
        img = qrcode.make(url)
        tmp = tempfile.mktemp(suffix=".png")
        img.save(tmp)
        qr_size = 0.85 * inch
        pad = 0.05 * inch
        qr_x = w - qr_size - 0.25 * inch
        qr_y = h - qr_size - 0.12 * inch
        c.setFillColor(_colors.white)
        c.rect(qr_x - pad, qr_y - pad, qr_size + 2*pad, qr_size + 2*pad, fill=True, stroke=False)
        c.drawImage(tmp, qr_x, qr_y, width=qr_size, height=qr_size)
        os.remove(tmp)
    except Exception:
        pass

# ─── GÉNÉRATION PDF COVER 10MM ────────────────────────────────────────────────
def generer_pdf_cover(params, fichier):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from datetime import date

    BLEU  = colors.HexColor("#1F3864")
    OR    = colors.HexColor("#C68B00")
    GRIS  = colors.HexColor("#F5F5F5")
    GRIS2 = colors.HexColor("#D6E4F0")

    no_proj = params.get("no_projet","")
    client  = params.get("client","")
    notes   = params.get("notes","")

    # Construire liste des murs
    murs_raw = params.get("murs", [])
    murs_calcules = []
    for m in murs_raw:
        m['largeur_po'] = _fvd(m.get('largeur','0'))
        m['hauteur_po'] = _fvd(m.get('hauteur','0'))
        m['nb_panneaux'] = int(m.get('nb_panneaux', 1))
        m['encastre'] = m.get('encastre', False)
        m['panneaux_egaux'] = m.get('panneaux_egaux', True)
        m['largeur_porte_po'] = _fvd(m.get('largeur_porte','0')) if m.get('largeur_porte') else m['largeur_po']/m['nb_panneaux']
        murs_calcules.append(calculer_mur_cover(m))

    BARRE_PO = 6600 / 25.4  # 259.84"
    UTILE_PO = BARRE_PO - 2.0
    KERF = 0.25
    SEUIL = 6.0
    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    def entete(titre_doc):
        c.setFillColor(BLEU)
        c.rect(0, h-1.1*inch, w, 1.1*inch, fill=True, stroke=False)
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(0.4*inch, h-0.38*inch, "SOLARIUM PRO — COVER 10mm")
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 8)
        c.drawString(0.4*inch, h-0.58*inch, titre_doc)
        c.drawString(0.4*inch, h-0.76*inch, f"No: {no_proj}  |  Client: {client}")
        c.drawRightString(w-0.4*inch, h-0.76*inch, str(date.today()))
        c.setFillColor(OR)
        c.rect(0, 0.3*inch, w, 0.25*inch, fill=True, stroke=False)
        c.setFillColor(BLEU)
        c.setFont("Helvetica", 7)
        c.drawCentredString(w/2, 0.4*inch, f"Solarium Pro  ·  {no_proj}  ·  {client}  ·  {date.today()}")

    def section(y, texte):
        c.setFillColor(BLEU)
        c.rect(0.4*inch, y-0.22*inch, w-0.8*inch, 0.22*inch, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(0.5*inch, y-0.14*inch, texte)
        return y - 0.36*inch

    def bandeau(y, texte):
        c.setFillColor(GRIS2)
        c.rect(0.4*inch, y-0.26*inch, w-0.8*inch, 0.26*inch, fill=True, stroke=False)
        c.setFillColor(BLEU)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(0.5*inch, y-0.16*inch, texte)
        return y - 0.38*inch

    def bandeau2(y, nom, L_po, H_po, nb):
        """Bandeau mur avec nom gros + dimensions sur 2e ligne"""
        haut = 0.52*inch
        c.setFillColor(GRIS2)
        c.rect(0.4*inch, y-haut, w-0.8*inch, haut, fill=True, stroke=False)
        c.setFillColor(BLEU)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.5*inch, y-0.20*inch, f"Mur : {nom}")
        c.setFont("Helvetica", 9)
        dim_txt = (f"L = {_dvf(L_po)}  ({_po_to_mm(L_po):,} mm)"
                   f"      H = {_dvf(H_po)}  ({_po_to_mm(H_po):,} mm)"
                   f"      {nb} panneaux").replace(",", " ")
        c.drawString(0.5*inch, y-0.38*inch, dim_txt)
        return y - haut - 0.12*inch

    def tableau(y, data, cols):
        t = Table(data, colWidths=cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), BLEU),
            ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,GRIS]),
            ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",         (1,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ]))
        _, th = t.wrap(0,0)
        if y - th < 0.9*inch:
            c.showPage(); entete("(suite)"); y = h-1.3*inch
        t.drawOn(c, 0.4*inch, y-th)
        return y - th - 0.2*inch

    def dessin_mur(y, mur_calc):
        """Dessin schématique simplifié du mur"""
        nb = mur_calc['nb_panneaux']
        L_po = mur_calc['largeur_po']
        H_po = mur_calc['hauteur_po']
        modele = mur_calc['modele']

        # Zone dessin — RÈGLE USINE : exploiter toute la page
        zone_w = w - 1.0*inch
        zone_h = 3.5*inch
        x0 = 0.5*inch
        y0 = y - zone_h

        if y0 < 1.0*inch:
            c.showPage(); entete(f"Mur — {mur_calc['nom']}"); y = h-1.3*inch
            y0 = y - zone_h

        # Fond
        c.setFillColor(colors.HexColor("#F8FAFF"))
        c.rect(x0, y0, zone_w, zone_h, fill=True, stroke=False)
        c.setStrokeColor(BLEU)
        c.setLineWidth(0.5)
        c.rect(x0, y0, zone_w, zone_h, fill=False, stroke=True)

        # Rails haut et bas
        rail_h = 0.18*inch
        c.setFillColor(OR)
        c.rect(x0, y0+zone_h-rail_h, zone_w, rail_h, fill=True, stroke=False)
        c.rect(x0, y0, zone_w, rail_h, fill=True, stroke=False)

        # Panneaux verticaux
        pan_w = zone_w / nb
        for i in range(nb+1):
            xp = x0 + i*pan_w
            c.setStrokeColor(BLEU)
            c.setLineWidth(1.0 if i==0 or i==nb else 0.5)
            c.line(xp, y0+rail_h, xp, y0+zone_h-rail_h)

        # Flèche ouverture au centre du dernier panneau (ou 1er selon modèle)
        sens = modele[-1] if modele else 'i'
        pan_idx = nb-1
        xf = x0 + pan_idx*pan_w + pan_w/2
        yf = y0 + zone_h/2
        c.setStrokeColor(BLEU)
        c.setLineWidth(0.8)
        if sens == 'i':
            c.line(xf+0.15*inch, yf, xf-0.15*inch, yf)
            c.line(xf-0.15*inch, yf, xf-0.08*inch, yf+0.06*inch)
            c.line(xf-0.15*inch, yf, xf-0.08*inch, yf-0.06*inch)
        else:
            c.line(xf-0.15*inch, yf, xf+0.15*inch, yf)
            c.line(xf+0.15*inch, yf, xf+0.08*inch, yf+0.06*inch)
            c.line(xf+0.15*inch, yf, xf+0.08*inch, yf-0.06*inch)

        # Cotes — L sous le dessin, H à droite (vertical) — RÈGLE USINE ≥9pt
        c.setFillColor(BLEU)
        c.setFont("Helvetica-Bold", 9)
        # Largeur sous le dessin
        c.drawCentredString(x0+zone_w/2, y0-0.18*inch,
            f'{_dvf(L_po)}  ({_po_to_mm(L_po):,} mm)'.replace(',',' '))
        # Hauteur à droite, vertical
        c.saveState()
        c.translate(x0 + zone_w + 0.25*inch, y0 + zone_h/2)
        c.rotate(90)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(0, 0,
            f'{_dvf(H_po)}  ({_po_to_mm(H_po):,} mm)'.replace(',',' '))
        c.restoreState()

        # Infos mur — RÈGLE USINE ≥9pt
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(x0+0.05*inch, y0+0.07*inch,
            f"{nb} panneaux  |  Modèle: {modele}  |  {'Encastré' if mur_calc['encastre'] else 'Non encastré'}  |  "
            f"Verre: {mur_calc['couleur_verre']}  |  Alu: {mur_calc['couleur_alu']}")


        return y - zone_h - 0.38*inch

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE(S) 1+ : DESSIN SCHÉMATIQUE PAR MUR
    # ══════════════════════════════════════════════════════════════════════════
    entete("APPROBATION CLIENT — Dessins schématiques des murs")
    y = h - 1.3*inch

    for mur_c in murs_calcules:
        y = bandeau2(y, mur_c['nom'], mur_c['largeur_po'], mur_c['hauteur_po'], mur_c['nb_panneaux'])
        y = dessin_mur(y, mur_c)

        # Tableau panneaux
        data = [["#", "Largeur verre", "Hauteur verre", "Type"]]
        pan_num = 1
        for v in mur_c['verres']:
            for i in range(v['qte']):
                larg_po = v['larg_mm'] / 25.4
                haut_po = v['haut_mm'] / 25.4
                data.append([
                    f"#{pan_num}",
                    f"{_dvf(larg_po)}  ({v['larg_mm']} mm)",
                    f"{_dvf(haut_po)}  ({v['haut_mm']} mm)",
                    v['type']
                ])
                pan_num += 1
        y = tableau(y, data, [0.4*inch, 2.3*inch, 2.3*inch, 0.8*inch])
        y -= 0.1*inch

    if notes.strip():
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.rect(0.4*inch, y-0.55*inch, w-0.8*inch, 0.55*inch, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#856404"))
        c.setFont("Helvetica-Bold", 8); c.drawString(0.5*inch, y-0.16*inch, "NOTES :")
        c.setFont("Helvetica", 8); c.drawString(0.5*inch, y-0.38*inch, notes[:130])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FEUILLE DE DÉBITAGE — PROFILS
    # ══════════════════════════════════════════════════════════════════════════
    entete("FEUILLE DE DÉBITAGE — Profils Cover 10mm")
    _draw_qr(c, no_proj, w, h, inch)
    y = h - 1.3*inch

    # Regrouper tous les profils par code × couleur
    profils_total = {}
    for mur_c in murs_calcules:
        couleur = mur_c['couleur_alu']
        for p in mur_c['profils']:
            cle = (p['code'], couleur)
            if cle not in profils_total:
                profils_total[cle] = {"code": p['code'], "desc": p['desc'],
                                       "couleur": couleur, "coupes": []}
            for _ in range(p['qte']):
                profils_total[cle]['coupes'].append({
                    "nom": f"{p['desc']} — {mur_c['nom']}",
                    "long": p['long_po']
                })

    for (code, couleur), grp in profils_total.items():
        pieces_ffd = [{"nom": g['nom'], "long": g['long'], "qte": 1} for g in grp['coupes']]
        barres = _ffd_cover(pieces_ffd, UTILE_PO, KERF)
        nb_barres = len(barres)

        y = section(y, f"{code}  —  {grp['desc']}  —  {couleur}  —  Barres 6 600 mm (259-27/32\")  ×{nb_barres} barre(s)")

        data = [["#", "Découpes (pouces + mm)", "Utilisé", "Reste"]]
        for b in barres:
            dec = "  +  ".join(_dvf(p["long"]) for p in b['pieces'])
            util = f'{_dvf(b["utilise"])}  ({_po_to_mm(b["utilise"])} mm)'
            reste_str = f'{_dvf(b["reste"])}  ({_po_to_mm(b["reste"])} mm)' if b['reste'] >= SEUIL else f'{_dvf(b["reste"])} (!)'
            data.append([f"#{b['num']}", dec, util, reste_str])
        y = tableau(y, data, [0.35*inch, 4.6*inch, 1.5*inch, 1.2*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FEUILLE DE PEINTURE
    # ══════════════════════════════════════════════════════════════════════════
    entete("FEUILLE DE PEINTURE — Barres à peinturer")
    y = h - 1.3*inch

    peinture = {}
    for mur_c in murs_calcules:
        couleur = mur_c['couleur_alu']
        for p in mur_c['profils']:
            cle = (p['code'], couleur)
            if cle not in peinture:
                peinture[cle] = {"code": p['code'], "desc": p['desc'],
                                  "couleur": couleur, "items": []}
            peinture[cle]['items'].append({
                "mur": mur_c['nom'],
                "long_po": p['long_po'],
                "long_mm": _po_to_mm(p['long_po']),
                "qte": p['qte']
            })

    for (code, couleur), grp in peinture.items():
        y = section(y, f"{code}  —  {grp['desc']}  —  Couleur: {couleur}")
        data = [["Mur", "Longueur", "Qté"]]
        total_qte = 0
        for it in grp['items']:
            data.append([it['mur'], f"{_dvf(it['long_po'])}  ({it['long_mm']} mm)", str(it['qte'])])
            total_qte += it['qte']
        data.append(["TOTAL", "", str(total_qte)])
        y = tableau(y, data, [2.0*inch, 3.5*inch, 1.0*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : LISTE DE VERRE — BON IGP
    # ══════════════════════════════════════════════════════════════════════════
    entete("BON DE COMMANDE VERRE — IGP")
    y = h - 1.3*inch

    # Regrouper verres identiques
    verres_igp = {}
    for mur_c in murs_calcules:
        couleur_v = mur_c['couleur_verre']
        for v in mur_c['verres']:
            cle = (v['larg_mm'], v['haut_mm'], v['type'], couleur_v)
            if cle not in verres_igp:
                verres_igp[cle] = {"larg": v['larg_mm'], "haut": v['haut_mm'],
                                    "type": v['type'], "couleur": couleur_v,
                                    "qte": 0, "murs": []}
            verres_igp[cle]['qte'] += v['qte']
            verres_igp[cle]['murs'].append(mur_c['nom'])

    y = bandeau(y, f"Vitrage 10mm trempé  —  Projet: {no_proj}  —  Client: {client}")

    data = [["Type", "Largeur", "Hauteur", "Couleur", "Qté", "Murs"]]
    for v in verres_igp.values():
        data.append([
            v['type'],
            f"{_dvf(v['larg']/25.4)}  ({v['larg']} mm)",
            f"{_dvf(v['haut']/25.4)}  ({v['haut']} mm)",
            v['couleur'], str(v['qte']),
            ", ".join(sorted(set(v['murs'])))
        ])
    y = tableau(y, data, [0.65*inch, 2.0*inch, 2.0*inch, 1.0*inch, 0.4*inch, 1.2*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FEUILLE DE QUINCAILLERIE (décaisse inventaire)
    # ══════════════════════════════════════════════════════════════════════════
    entete("DÉCAISSE INVENTAIRE — Quincaillerie Cover 10mm")
    y = h - 1.3*inch

    # Agréger quincaillerie tous murs
    qx_total = {}
    for mur_c in murs_calcules:
        for q in mur_c['quincaillerie']:
            cle = q['code']
            if cle not in qx_total:
                qx_total[cle] = {"code": q['code'], "desc": q['desc'],
                                  "unite": q['unite'], "qte": 0}
            qx_total[cle]['qte'] += q['qte_calc']

    data = [["Code", "Description", "Unité", "Qté"]]
    for q in qx_total.values():
        qte_str = str(q['qte']) if q['unite'] == 'pcs' else f"{q['qte']:.3f}".rstrip('0').rstrip('.')
        data.append([q['code'], q['desc'], q['unite'], qte_str])
    y = tableau(y, data, [1.0*inch, 4.0*inch, 0.6*inch, 0.8*inch])

    c.save()
    print(f"✓ Cover 10mm PDF généré: {fichier}")
