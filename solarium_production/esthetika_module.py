"""
ESTÉTIKA — Module de production Solarium Pro v2
Structure identique à aika_6mm_module.py — 5 pages dans l'ordre.
Estétika — produit aluminium sur mesure. Deux variantes : motorisée / manuelle.

RÈGLE USINE — Lisibilité et occupation de page :
  • Les dessins techniques occupent tout l'espace disponible de la page.
  • Toute étiquette, cote ou texte doit être lisible à 50 cm en conditions d'usine.
  • Taille minimum : 9 pt annotations, 10 pt tableaux.
  • Codes KIT Bettio apparaissent sur chaque liste de coupe (correspondance INVENTAIRE_MASTER.xlsx).
"""

import os, sys, re
from math import gcd, ceil
from datetime import date as _date
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KERF_PO        = 0.25   # Trait de scie
SEUIL_RESTE_PO = 6.0    # Reste minimum à conserver

KITS_ESTHETIKA = {
    'motorisee': {
        '3812': ('Caisson',             6000),
        '3813': ('Barre poignée',       6000),
        '3814': ('Profil compensateur', 5700),
        '3816': ('Profil adaptateur',   6000),
        '3818': ('Guide coulisse',      6000),
        '3931': ('Tube motorisé',       6000),
    },
    'manuelle': {
        '3812': ('Caisson',             6000),
        '3813': ('Barre poignée',       6000),
        '3814': ('Profil compensateur', 5700),
        '3817': ('Guide coulisse',      6000),
        '3928': ('Tube manuel',         6000),
    },
}
# format: code → (nom, barre_mm)

# ─── QUINCAILLERIE / ACCESSOIRES ─────────────────────────────────────────────
# Source : Estetika Gestion Projet.xlsx — onglet Ressort
QUINCAILLERIE_EST_MOT = [
    # Ressorts et supports pose encaissement
    {'code': 'KIT3935', 'desc': 'Ressort pose encaissement',             'qte': 2,        'unite': 'pcs'},
    {'code': 'KIT3936', 'desc': 'Support pour pose encaissement',        'qte': 2,        'unite': 'pcs'},
    {'code': 'KIT3937', 'desc': 'Ressort pour pose encaissement',        'qte': 2,        'unite': 'pcs'},
    {'code': 'KIT3938', 'desc': 'Compensateur pose encaissement',        'qte': 2,        'unite': 'pcs'},
    # Ballast — quantité dynamique : CEIL(largeur_mm / 400) par mur, additionné
    {'code': 'KIT3549', 'desc': 'Ballast 40cm (motorisé)',               'qte': 'BALLAST','unite': 'pcs', 'note': 'CEIL(L/400mm) par mur'},
    # Motorisation /77
    {'code': 'KIT3866', 'desc': 'Douille moteur /77',                    'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT3867', 'desc': 'Entraînement moteur /77',               'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT3969', 'desc': 'Douille point mort moteur /77',         'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT3869', 'desc': 'Bloc recharge /77',                     'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT3870', 'desc': 'Bouchon de trou /77',                   'qte': 1,        'unite': 'pcs'},
    # Moteur et électronique
    {'code': 'KIT4102', 'desc': 'Moteur bidirectionnel',                 'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT3842', 'desc': 'Bouton aimanté recharge',               'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT4114', 'desc': 'Câble interne 2m',                      'qte': 1,        'unite': 'pcs'},
    {'code': 'KIT4180', 'desc': 'Vis fixation moteur',                   'qte': 2,        'unite': 'pcs'},
    {'code': 'KIT4162', 'desc': 'Grain (motorisé)',                      'qte': 1,        'unite': 'pcs'},
]

QUINCAILLERIE_EST_MAN = [
    # Ressorts (sélection selon hauteur de toile)
    {'code': 'KIT3912', 'desc': 'Ressort 300mm',                    'qte': 1, 'unite': 'pcs', 'note': 'L 300–500 mm'},
    {'code': 'KIT3913', 'desc': 'Ressort 420mm',                    'qte': 1, 'unite': 'pcs', 'note': 'L 501–1151 mm'},
    {'code': 'KIT3914', 'desc': 'Ressort 800mm',                    'qte': 1, 'unite': 'pcs', 'note': 'L 1152–1800 mm'},
    {'code': 'KIT3915', 'desc': 'Ressort 1400mm',                   'qte': 1, 'unite': 'pcs', 'note': 'L 1801–2501 mm'},
    # Embouts, freins, tirettes
    {'code': 'KIT3916', 'desc': 'Bouchon assemblé diam.24',         'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3917', 'desc': 'Frein ralentisseur',               'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3918', 'desc': 'Tirette 60 cm',                    'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3906', 'desc': 'Embout gauche',                    'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3907', 'desc': 'Embout droite',                    'qte': 1, 'unite': 'pcs'},
    # Glissières et groupes de pression
    {'code': 'KIT3921', 'desc': 'Glissière gauche assemblée',       'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3922', 'desc': 'Glissière droite assemblée',       'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3923', 'desc': 'Groupe de pression gauche',        'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3924', 'desc': 'Groupe de pression droite',        'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3925', 'desc': 'Arrêt gauche',                     'qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3926', 'desc': 'Arrêt droite',                     'qte': 1, 'unite': 'pcs'},
    # Bouchons et profils
    {'code': 'KIT3939', 'desc': 'Bouchon pour profil compensateur', 'qte': 2, 'unite': 'pcs'},
    # Rivets et fixations
    {'code': 'KIT3556', 'desc': 'Rivet manuel mâle',                'qte': 2, 'unite': 'pcs'},
    {'code': 'KIT3557', 'desc': 'Rivet manuel femelle',             'qte': 2, 'unite': 'pcs'},
    # Brosses et adhésifs
    {'code': 'KIT2283', 'desc': 'Brosse grise pour poignée',        'qte': 'L',  'unite': 'ml'},
    {'code': 'KIT3871', 'desc': 'Brosse anti-vent pour coulisse',   'qte': 'H2', 'unite': 'ml'},
    {'code': 'KIT3339', 'desc': 'Brosse 45° noire pour coffre',     'qte': 'L',  'unite': 'ml'},
    # Coulissement et double adhésif
    {'code': 'KIT3481', 'desc': 'Goupille pour bouchon profil adaptateur','qte': 2, 'unite': 'pcs'},
    {'code': 'KIT3940', 'desc': 'Vis pour embout',                   'qte': 4, 'unite': 'pcs'},
    {'code': 'KIT3060', 'desc': 'Vis pour glissière',                'qte': 2, 'unite': 'pcs'},
    {'code': 'KIT3675', 'desc': 'Coulissement pour coffre L.2000mm','qte': 1, 'unite': 'pcs'},
    {'code': 'KIT3353', 'desc': 'Double adhésif pour pose L.1500mm','qte': 1, 'unite': 'pcs', 'note': 'Option'},
]


# ─── UTILITAIRES ──────────────────────────────────────────────────────────────
def _dvf(d):
    if d is None: return ""
    s = round(d * 16) / 16
    entier = int(s); reste = s - entier
    if reste < 0.001: return f'{entier}"'
    num = round(reste * 16); den = 16
    g = gcd(num, den); num //= g; den //= g
    return f'{entier}-{num}/{den}"' if entier else f'{num}/{den}"'

def _fvd(s):
    s = str(s).strip().replace('"', '').replace("'", "")
    if not s: return 0.0
    m = re.match(r'^(\d+)[-\s]+(\d+)/(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m2 = re.match(r'^(\d+)/(\d+)$', s)
    if m2: return int(m2.group(1)) / int(m2.group(2))
    return float(s)

def _fmt(po):
    mm = round(po * 25.4)
    return f'{_dvf(po)}  ({mm} mm)'


# ─── ALGORITHME FFD ───────────────────────────────────────────────────────────
def _ffd(pieces_list, barre_po, kerf=KERF_PO):
    """First-Fit Decreasing — retourne liste de barres."""
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
            if barre_po - b['utilise'] >= besoin:
                b['pieces'].append(piece)
                b['utilise'] += besoin
                placee = True
                break
        if not placee:
            barres.append({'num': len(barres) + 1, 'pieces': [piece], 'utilise': besoin})
    for b in barres:
        b['reste'] = barre_po - b['utilise']
    return barres


# ─── FFD PAR KIT ──────────────────────────────────────────────────────────────
def _ffd_kits(pieces, kerf=0.25):
    """FFD par kit — chaque kit avec sa longueur de barre propre."""
    par_kit = {}
    for p in pieces:
        if p.get('qte', 0) == 0:
            continue
        kc = p['kit']
        if kc not in par_kit:
            par_kit[kc] = {
                'kit_nom': p['kit_nom'],
                'barre_mm': p['barre_mm'],
                'barre_po': p['barre_po'],
                'pieces': []
            }
        par_kit[kc]['pieces'].append({'nom': p['nom'], 'long': p['long'], 'qte': p['qte']})
    for kc, kd in par_kit.items():
        kd['barres'] = _ffd(kd['pieces'], kd['barre_po'], kerf)
        for i, b in enumerate(kd['barres']):
            b['num'] = i + 1
    return par_kit


# ─── CALCUL MUR ESTÉTIKA ──────────────────────────────────────────────────────
def _kp(code, nom, long, qte, kits_dict):
    nom_kit, barre_mm = kits_dict[code]
    return {'nom': nom, 'kit': code, 'kit_nom': nom_kit,
            'barre_mm': barre_mm, 'barre_po': barre_mm / 25.4, 'long': long, 'qte': qte}


def calculer_mur_esthetika(mur):
    """
    mur = {
      'nom': str,
      'largeur_po': float,     largeur totale (façade)
      'hauteur_po': float,     hauteur totale
      'couleur_alu': str,      Blanc RAL 9016 / Noir RAL 9017 / Sur mesure
      'variante': str,         'motorisee' ou 'manuelle'
    }
    """
    L_po     = mur['largeur_po']
    H_po     = mur['hauteur_po']
    variante = mur.get('variante', 'motorisee')
    kits     = KITS_ESTHETIKA[variante]

    L_mm = round(L_po * 25.4)
    H_mm = round(H_po * 25.4)

    if variante == 'motorisee':
        pieces = [
            _kp('3812', 'Caisson',             (L_mm - 78) / 25.4, 1, kits),
            _kp('3813', 'Barre poignée',       (L_mm - 99) / 25.4, 1, kits),
            _kp('3816', 'Profil adaptateur',   (L_mm - 99) / 25.4, 1, kits),
            _kp('3814', 'Profil compensateur', (H_mm - 5)  / 25.4, 2, kits),
            _kp('3818', 'Guide coulisse',      (H_mm - 70) / 25.4, 2, kits),
            _kp('3931', 'Tube motorisé',       (L_mm - 40) / 25.4, 1, kits),
        ]
    else:
        pieces = [
            _kp('3812', 'Caisson',             (L_mm - 65) / 25.4, 1, kits),
            _kp('3813', 'Barre poignée',       (L_mm - 86) / 25.4, 1, kits),
            _kp('3814', 'Profil compensateur', (H_mm - 5)  / 25.4, 2, kits),
            _kp('3817', 'Guide coulisse',      (H_mm - 70) / 25.4, 2, kits),
            _kp('3928', 'Tube manuel',          (L_mm - 25) / 25.4, 1, kits),
        ]

    return {
        'nom':         mur.get('nom', ''),
        'largeur_po':  L_po,
        'hauteur_po':  H_po,
        'largeur_mm':  round(L_po * 25.4),
        'hauteur_mm':  round(H_po * 25.4),
        'couleur_alu': mur.get('couleur_alu', ''),
        'variante':    variante,
        'pieces':      pieces,
    }


# ─── DESSIN APPROBATION INLINE ────────────────────────────────────────────────
def _dessiner_esthetika(c, y, mc, w, h, inch, colors):
    """
    Dessin d'élévation frontale de l'Estétika.
    Retourne la nouvelle position y après le dessin.
    """
    BLEU   = colors.HexColor("#1F3864")
    OR     = colors.HexColor("#C68B00")
    GRIS   = colors.HexColor("#AAAAAA")
    POST_C = colors.HexColor("#333333")

    marge_g = 0.5 * inch
    marge_d = 0.5 * inch
    zone_w  = w - marge_g - marge_d
    zone_h  = min(4.5 * inch, y - 1.4 * inch)
    if zone_h < 1.5 * inch:
        return y  # pas assez de place

    # Espace réservé aux cotes
    cote_bas    = 0.35 * inch
    cote_gauche = 0.45 * inch
    dessin_x = marge_g + cote_gauche
    dessin_y = y - zone_h
    dessin_w = zone_w - cote_gauche - 0.1 * inch
    dessin_h = zone_h - cote_bas - 0.1 * inch

    L_po = mc['largeur_po']
    H_po = mc['hauteur_po']

    # Échelle selon la plus grande dimension
    scale_x = dessin_w / max(L_po, 1)
    scale_h = dessin_h / max(H_po + 8.0, 1)  # +8 pour les poteaux qui dépassent
    scale   = min(scale_x, scale_h)

    dw = L_po * scale
    dh = H_po * scale
    post_h   = (H_po + 6.0) * scale   # poteaux descendent de 6"
    post_w   = 2.5 * scale             # largeur visuelle poteau 2.5"
    poutre_h = 4.0 * scale             # hauteur visuelle traverse de tête

    ox = dessin_x + (dessin_w - dw) / 2
    oy = dessin_y + cote_bas + (dessin_h - dh) / 2

    # Sol (ligne)
    sol_y = oy - 6.0 * scale
    c.setStrokeColor(GRIS); c.setLineWidth(0.5)
    c.line(ox - 0.2 * inch, sol_y, ox + dw + 0.2 * inch, sol_y)

    # Poteaux (4 — dessin 2D élévation : on voit 2 poteaux)
    c.setFillColor(POST_C); c.setStrokeColor(POST_C); c.setLineWidth(0.3)
    c.rect(ox,               sol_y, post_w, post_h, fill=True, stroke=False)
    c.rect(ox + dw - post_w, sol_y, post_w, post_h, fill=True, stroke=False)

    # Traverse de tête (traverse supérieure)
    c.setFillColor(POST_C)
    c.rect(ox, oy + dh - poutre_h, dw, poutre_h, fill=True, stroke=False)

    # ── Cotes ──
    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.setFillColor(BLEU); c.setFont("Helvetica", 9)

    # Cote largeur (bas)
    y_cote = sol_y - 0.12 * inch
    c.line(ox, y_cote, ox + dw, y_cote)
    c.line(ox, y_cote - 0.04 * inch, ox, y_cote + 0.04 * inch)
    c.line(ox + dw, y_cote - 0.04 * inch, ox + dw, y_cote + 0.04 * inch)
    label_l = f"{_dvf(L_po)}  ({mc['largeur_mm']} mm)"
    c.drawCentredString(ox + dw / 2, y_cote - 0.13 * inch, label_l)

    # Cote hauteur (gauche)
    x_cote = ox - 0.12 * inch
    c.line(x_cote, oy, x_cote, oy + dh)
    c.line(x_cote - 0.04 * inch, oy, x_cote + 0.04 * inch, oy)
    c.line(x_cote - 0.04 * inch, oy + dh, x_cote + 0.04 * inch, oy + dh)
    c.saveState()
    c.translate(x_cote - 0.13 * inch, oy + dh / 2)
    c.rotate(90)
    label_h = f"{_dvf(H_po)}  ({mc['hauteur_mm']} mm)"
    c.drawCentredString(0, 0, label_h)
    c.restoreState()

    # Couleur
    c.setFillColor(BLEU); c.setFont("Helvetica", 9)
    c.drawCentredString(ox + dw / 2, oy + dh + 0.10 * inch, mc['couleur_alu'])

    return dessin_y - 0.1 * inch


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


# ─── GÉNÉRATION PDF ───────────────────────────────────────────────────────────
def generer_pdf_esthetika(params, fichier):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units    import inch
    from reportlab.pdfgen       import canvas
    from reportlab.lib          import colors
    from reportlab.platypus     import Table, TableStyle

    BLEU  = colors.HexColor("#1F3864")
    OR    = colors.HexColor("#C68B00")
    GRIS  = colors.HexColor("#F5F5F5")
    GRIS2 = colors.HexColor("#D6E4F0")

    no_proj        = params.get("no_projet", "")
    client         = params.get("client",    "")
    couleur        = params.get("couleur",   "")
    notes          = params.get("notes",     "")
    variante       = params.get("variante",  "motorisee")
    variante_label = "Motorisée" if variante == "motorisee" else "Manuelle"

    # ── Construire murs calculés ──────────────────────────────────────────────
    murs_calc = []
    for m in params.get("murs", []):
        m['largeur_po'] = _fvd(m.get('largeur', '0'))
        m['hauteur_po'] = _fvd(m.get('hauteur', '0'))
        m['couleur_alu'] = couleur
        m['variante']    = variante
        if m['largeur_po'] > 0 and m['hauteur_po'] > 0:
            murs_calc.append(calculer_mur_esthetika(m))

    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    titre_produit = f"SOLARIUM PRO — ESTÉTIKA {variante_label.upper()}"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def entete(titre_doc):
        c.setFillColor(BLEU)
        c.rect(0, h - 1.1 * inch, w, 1.1 * inch, fill=True, stroke=False)
        c.setFillColor(OR); c.setFont("Helvetica-Bold", 14)
        c.drawString(0.4 * inch, h - 0.38 * inch, titre_produit)
        c.setFillColor(colors.white); c.setFont("Helvetica", 9)
        c.drawString(0.4 * inch, h - 0.58 * inch, titre_doc)
        c.drawString(0.4 * inch, h - 0.76 * inch,
                     f"No: {no_proj}  |  Client: {client}  |  Couleur: {couleur}")
        c.drawRightString(w - 0.4 * inch, h - 0.76 * inch, str(_date.today()))
        c.setFillColor(OR)
        c.rect(0, 0.3 * inch, w, 0.25 * inch, fill=True, stroke=False)
        c.setFillColor(BLEU); c.setFont("Helvetica", 7)
        c.drawCentredString(w / 2, 0.4 * inch,
                            f"Solarium Pro  ·  {no_proj}  ·  {client}  ·  {_date.today()}")

    def titre_section(y, texte):
        c.setFillColor(BLEU)
        c.rect(0.4 * inch, y - 0.22 * inch, w - 0.8 * inch, 0.22 * inch, fill=True, stroke=False)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 11)
        c.drawString(0.5 * inch, y - 0.14 * inch, texte)
        return y - 0.36 * inch

    def bandeau_mur(y, mc):
        haut = 0.26 * inch
        c.setFillColor(GRIS2)
        c.rect(0.4 * inch, y - haut, w - 0.8 * inch, haut, fill=True, stroke=False)
        c.setFillColor(BLEU); c.setFont("Helvetica", 10)
        c.drawString(0.5 * inch, y - 0.16 * inch,
            f"{mc['nom']}  —  "
            f"L = {_dvf(mc['largeur_po'])} ({mc['largeur_mm']} mm)  "
            f"H = {_dvf(mc['hauteur_po'])} ({mc['hauteur_mm']} mm)")
        return y - haut - 0.08 * inch

    def tableau(y, data, cols):
        t = Table(data, colWidths=cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0),  BLEU),
            ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",          (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",     (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ]))
        _, th = t.wrap(0, 0)
        if y - th < 0.9 * inch:
            c.showPage(); entete("(suite)"); y = h - 1.3 * inch
        t.drawOn(c, 0.4 * inch, y - th)
        return y - th - 0.2 * inch

    def table_coupes(y, barres, barre_po):
        data = [["#", "Découpes (pouces)", "Utilisé", "Reste"]]
        for b in barres:
            dec  = " + ".join(_dvf(p["long"]) for p in b["pieces"])
            rest = _dvf(b["reste"]) if b["reste"] >= SEUIL_RESTE_PO else f'{_dvf(b["reste"])} (!)'
            data.append([f"#{b['num']}", dec, _dvf(b["utilise"]), rest])
        return tableau(y, data, [0.4 * inch, 4.9 * inch, 1.2 * inch, 1.2 * inch])

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES 1+ : APPROBATION CLIENT
    # ══════════════════════════════════════════════════════════════════════════
    for mc in murs_calc:
        entete(f"APPROBATION CLIENT — Estétika {variante_label}")
        y = h - 1.3 * inch
        y = bandeau_mur(y, mc)
        y -= 0.1 * inch
        y = _dessiner_esthetika(c, y, mc, w, h, inch, colors)

        # Notes
        if notes.strip():
            c.setFillColor(colors.HexColor("#FFF3CD"))
            c.rect(0.4 * inch, y - 0.55 * inch, w - 0.8 * inch, 0.55 * inch, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 8)
            c.drawString(0.5 * inch, y - 0.16 * inch, "NOTES :")
            c.setFont("Helvetica", 8)
            c.drawString(0.5 * inch, y - 0.38 * inch, notes[:130])

        # Bloc signature
        sig_y = 1.5 * inch
        c.setStrokeColor(BLEU); c.setLineWidth(0.5)
        c.line(0.4 * inch, sig_y, 3.5 * inch, sig_y)
        c.line(4.2 * inch, sig_y, 7.7 * inch, sig_y)
        c.setFillColor(BLEU); c.setFont("Helvetica", 7)
        c.drawString(0.4 * inch, sig_y - 0.15 * inch, "Signature client")
        c.drawString(4.2 * inch, sig_y - 0.15 * inch, "Date d'approbation")
        c.setFont("Helvetica-Bold", 7)
        c.drawString(0.4 * inch, sig_y - 0.30 * inch, "Préparé par : Céderic Rainville")

        c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : SCHÉMA TECHNIQUE / MONTAGE
    # ══════════════════════════════════════════════════════════════════════════
    entete(f"SCHÉMA TECHNIQUE — Estétika {variante_label}")
    y = h - 1.3 * inch
    for mc in murs_calc:
        y = bandeau_mur(y, mc)
        y -= 0.1 * inch
        y = _dessiner_esthetika(c, y, mc, w, h, inch, colors)
        y -= 0.15 * inch
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : RÉCAPITULATIF DES PIÈCES
    # ══════════════════════════════════════════════════════════════════════════
    entete(f"RÉCAPITULATIF DES PIÈCES — Estétika {variante_label}")
    y = h - 1.3 * inch
    for mc in murs_calc:
        y = bandeau_mur(y, mc)
        y = titre_section(y, f"{mc['nom']} — PIÈCES")
        data = [["Kit", "Désignation", "Longueur (pouces)", "Longueur (mm)", "Qté"]]
        for p in mc['pieces']:
            data.append([
                f"KIT {p['kit']}",
                p['nom'],
                _dvf(p['long']),
                str(round(p['long'] * 25.4)),
                str(p['qte']),
            ])
        y = tableau(y, data, [0.9 * inch, 2.5 * inch, 1.5 * inch, 1.4 * inch, 0.9 * inch])

    if notes.strip():
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.rect(0.4 * inch, y - 0.55 * inch, w - 0.8 * inch, 0.55 * inch, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 8)
        c.drawString(0.5 * inch, y - 0.16 * inch, "NOTES :")
        c.setFont("Helvetica", 8)
        c.drawString(0.5 * inch, y - 0.38 * inch, notes[:130])
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES 4 : COUPES & QUINCAILLERIE — flux continu
    # ══════════════════════════════════════════════════════════════════════════
    par_kit_agg = {}
    for mc in murs_calc:
        for p in mc['pieces']:
            kc = p['kit']
            if kc not in par_kit_agg:
                par_kit_agg[kc] = {
                    'kit_nom':  p['kit_nom'],
                    'barre_mm': p['barre_mm'],
                    'barre_po': p['barre_po'],
                    'acc': defaultdict(int),
                }
            par_kit_agg[kc]['acc'][(p['nom'], round(p['long'], 4))] += p['qte']

    kits_ffd = {}
    for kc, kd in par_kit_agg.items():
        pieces_kit = [
            {'nom': nom, 'long': long, 'qte': qte}
            for (nom, long), qte in kd['acc'].items()
        ]
        barres = _ffd(pieces_kit, kd['barre_po'])
        for i, b in enumerate(barres):
            b['num'] = i + 1
        kits_ffd[kc] = {**kd, 'barres': barres}
    del par_kit_agg

    entete(f"COUPES & QUINCAILLERIE — Estétika {variante_label}")
    _draw_qr(c, no_proj, w, h, inch)
    y = h - 1.3 * inch
    y = titre_section(y, f"LISTES DE COUPE — {couleur}")
    for kc, kd in kits_ffd.items():
        nb_b = len(kd['barres'])
        if y < 1.8 * inch:
            c.showPage(); entete(f"COUPES — Estétika {variante_label} (suite)"); y = h - 1.3 * inch
        y = titre_section(y, f"KIT {kc} — {kd['kit_nom']}  ·  barre {kd['barre_mm']} mm  ·  {nb_b} barre{'s' if nb_b>1 else ''}")
        y = table_coupes(y, kd['barres'], kd['barre_po'])
        y -= 0.06 * inch

    quincaillerie = (QUINCAILLERIE_EST_MAN + QUINCAILLERIE_EST_MOT) if variante == 'motorisee' else QUINCAILLERIE_EST_MAN
    if quincaillerie:
        if y < 1.8 * inch:
            c.showPage(); entete(f"QUINCAILLERIE — Estétika {variante_label} (suite)"); y = h - 1.3 * inch
        y -= 0.04 * inch
        y = titre_section(y, f"QUINCAILLERIE & ACCESSOIRES — Estétika {variante_label} — par projet")
        # Métriques projet pour formules linéaires
        total_L_m  = sum(mc['largeur_mm']  / 1000 for mc in murs_calc)
        total_H_m  = sum(mc['hauteur_mm']  / 1000 for mc in murs_calc)
        total_ballast = sum(ceil(mc['largeur_mm'] / 400) for mc in murs_calc)
        data_q = [["Code KIT", "Description", "Quantité", "Unité", "Note"]]
        for item in quincaillerie:
            q = item['qte']
            if q == 'L':
                qte_str = f"{total_L_m:.2f}"; unite_str = "ml"
            elif q == 'H':
                qte_str = f"{total_H_m:.2f}"; unite_str = "ml"
            elif q == 'H2':
                qte_str = f"{total_H_m * 2:.2f}"; unite_str = "ml"
            elif q == 'BALLAST':
                qte_str = str(total_ballast); unite_str = item['unite']
            else:
                qte_str = str(q); unite_str = item['unite']
            data_q.append([item['code'], item['desc'], qte_str, unite_str, item.get('note', '')])
        y = tableau(y, data_q, [1.0 * inch, 3.1 * inch, 1.1 * inch, 0.7 * inch, 1.3 * inch])

    # ── Kit installation FORO/LUCE CON VITI (Manuelle seulement) ─────────────
    if variante == 'manuelle':
        if y < 1.8 * inch:
            c.showPage(); entete(f"QUINCAILLERIE — Estetika {variante_label} (suite)"); y = h - 1.3 * inch
        y -= 0.15 * inch
        y = titre_section(y, "KIT INSTALLATION — FORO/LUCE CON VITI")
        total_murs = len(murs_calc)
        install_items = [
            ('KIT4126/40', 'Piece installation (a confirmer avec Cedric)', 2),
            ('KIT4144/40', 'Piece installation (a confirmer avec Cedric)', 2),
            ('KIT3923',    'Groupe de pression gauche',                     1),
            ('KIT3925',    'Arret gauche',                                  1),
            ('KIT3926',    'Arret droite',                                  1),
            ('KIT3924',    'Groupe de pression droite',                     1),
        ]
        data_inst = [["Code KIT", "Description", "Qte / mur", "Total projet"]]
        for code, desc, qte_par in install_items:
            data_inst.append([code, desc, str(qte_par), str(qte_par * total_murs)])
        y = tableau(y, data_inst, [1.1 * inch, 3.2 * inch, 1.4 * inch, 1.0 * inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5 : FICHE PEINTURE
    # ══════════════════════════════════════════════════════════════════════════
    entete(f"FICHE PEINTURE — Estétika {variante_label}")
    y = h - 1.4 * inch
    y = titre_section(y, f"Estetika {variante_label}.  Couleur : {couleur}")

    _IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images_pieces')
    IMAGES_PROFILS_EST = {
        '3812': os.path.join(_IMG_DIR, 'profil_3812.png'),
        '3813': os.path.join(_IMG_DIR, 'profil_3813.png'),
        '3814': os.path.join(_IMG_DIR, 'profil_3814.png'),
        '3816': os.path.join(_IMG_DIR, 'profil_3816.png'),
        '3817': os.path.join(_IMG_DIR, 'profil_3817.png'),
        '3818': os.path.join(_IMG_DIR, 'profil_3818.png'),
        '3928': os.path.join(_IMG_DIR, 'profil_tube_25x100.jpeg'),
        '3931': os.path.join(_IMG_DIR, 'profil_tube_25x100.jpeg'),
    }

    from reportlab.platypus import Image as RLImage

    def _img_cell_est(kit_code):
        path = IMAGES_PROFILS_EST.get(kit_code)
        if path and os.path.exists(path):
            return RLImage(path, width=0.52 * inch, height=0.38 * inch)
        return None

    pieces_peinture = {}
    for mc in murs_calc:
        for p in mc['pieces']:
            key = (p['kit'], p['kit_nom'], round(p['long'] * 25.4))
            pieces_peinture[key] = pieces_peinture.get(key, 0) + p['qte']

    data_p = [["Profil", "Code", "Designation", "Grandeur", "Nombre", "Coupe"]]
    for (kc, kit_nom, long_mm), qte in sorted(pieces_peinture.items()):
        img = _img_cell_est(kc) or ""
        grandeur = f"{_dvf(long_mm / 25.4)}  ({long_mm} mm)"
        data_p.append([img, kc, kit_nom, grandeur, str(qte), ""])

    y = tableau(y, data_p, [0.62 * inch, 0.65 * inch, 1.7 * inch, 2.05 * inch, 0.65 * inch, 0.95 * inch])
    y -= 0.3 * inch

    # Note Keven
    note_h = 0.40 * inch
    if y - note_h < 0.9 * inch:
        c.showPage(); entete(f"FICHE PEINTURE — Estetika {variante_label} (suite)"); y = h - 1.4 * inch
    c.setFillColor(colors.HexColor("#FFF3CD"))
    c.rect(0.4 * inch, y - note_h, w - 0.8 * inch, note_h, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 9)
    c.drawString(0.55 * inch, y - 0.17 * inch, "Note :")
    c.setFont("Helvetica", 9)
    c.drawString(1.1 * inch, y - 0.17 * inch,
                 "Keven — cocher chaque profil apres la coupe avant d'envoyer a la peinture")
    y -= note_h + 0.45 * inch

    # Signatures — 3 champs
    sig_y = max(y, 1.8 * inch)
    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.line(0.4 * inch, sig_y, 2.8 * inch, sig_y)
    c.line(3.1 * inch, sig_y, 5.3 * inch, sig_y)
    c.line(5.6 * inch, sig_y, 7.7 * inch, sig_y)
    c.setFillColor(BLEU); c.setFont("Helvetica", 7)
    c.drawString(0.4 * inch,  sig_y - 0.14 * inch, "Recu par le peintre — Nom + Signature")
    c.drawString(3.1 * inch,  sig_y - 0.14 * inch, "Date de reception")
    c.drawString(5.6 * inch,  sig_y - 0.14 * inch, "Date de retour prevue")
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 6 : RESTES À ENREGISTRER
    # ══════════════════════════════════════════════════════════════════════════
    restes = []
    for kc, kd in kits_ffd.items():
        for b in kd['barres']:
            if b['reste'] >= SEUIL_RESTE_PO:
                restes.append({'profil': f"KIT {kc} — {kd['kit_nom']}", 'reste': b['reste']})

    if restes:
        entete(f"RESTES À ENREGISTRER — Estétika {variante_label}")
        y = h - 1.3 * inch
        y = titre_section(y, "NOUVEAUX RESTES GÉNÉRÉS PAR CETTE PRODUCTION")
        data = [["Profil", "Longueur (pouces)", "Longueur (mm)", "Notes"]]
        for r in restes:
            data.append([r['profil'], _dvf(r['reste']), str(round(r['reste'] * 25.4)), ""])
        y = tableau(y, data, [2.0 * inch, 1.5 * inch, 1.5 * inch, 2.8 * inch])
        c.showPage()

    c.save()
    print(f"✓ Estétika {variante_label} PDF généré : {fichier}")
