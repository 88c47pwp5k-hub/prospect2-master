"""
AIKA 6MM — Module de production Solarium Pro
À intégrer dans solarium_production.py

RÈGLE USINE (permanent) :
  - Zone de dessin : exploiter toute la page (géré par aika_dessin_v3)
  - Annotations/cotes sur les dessins : police ≥ 9 pt
  - Tableaux de données : FONTSIZE ≥ 10 pt (lisibilité atelier)
"""

from aika_dessin_v3 import dessiner_mur_aika_v3, MODELES, get_pan_largeurs

from fractions import Fraction
import math

# ─── CONSTANTES AIKA 6MM ──────────────────────────────────────────────────────
BARRES_AIKA = {
    "60-1001": {"desc": "Rail inférieur 4 trous",      "long_mm": 6600},
    "60-1002": {"desc": "Rail supérieur 4 trous",      "long_mm": 6600},
    "60-1003": {"desc": "Rail inférieur 3 trous",      "long_mm": 6600},
    "60-1004": {"desc": "Rail supérieur 3 trous",      "long_mm": 6600},
    "60-2001": {"desc": "Profil de verrouillage",      "long_mm": 6600},
    "60-2002": {"desc": "Profil vertical verre",       "long_mm": 5200},
    "60-2003": {"desc": "Profil horizontal verre",     "long_mm": 6600},
    "60-3001": {"desc": "Profil U",                    "long_mm": 6600},
    "60-3002": {"desc": "Profil de régulation",        "long_mm": 6600},
    "60-3003": {"desc": "Profil verrou clamp",         "long_mm": 6600},
}

QUINCAILLERIE_AIKA_BASE = [
    {"code": "60-6001",  "desc": "Capuchon de verrouillage",      "unite": "pcs", "par": "panneau", "qte": 2},
    {"code": "60-6002",  "desc": "Adaptateur cible",              "unite": "pcs", "par": "panneau", "qte": 2},
    {"code": "60-6003",  "desc": "Boîtier de roue",               "unite": "pcs", "par": "panneau", "qte": 1},
    {"code": "60-8001",  "desc": "Roue à billes",                 "unite": "pcs", "par": "panneau", "qte": 2},
    {"code": "60-8002",  "desc": "Vis de panneau",                "unite": "pcs", "par": "panneau", "qte": 2},
    {"code": "60-9006",  "desc": "Ensemble roues",                "unite": "pcs", "par": "panneau", "qte": 1},
    {"code": "10-8088",  "desc": "Vis de fixation",               "unite": "pcs", "par": "panneau", "qte": 3},
]

# Serrures — par mur selon sélection
SERRURES_AIKA = {
    "barrure_int":    {"code": "60-9005",    "desc": "Ensemble verrou — barrure intérieure",         "unite": "pcs", "qte": 1},
    "poignee_ext_L":  {"code": "60-9004_L",  "desc": "Poignée simple extérieure — gauche",           "unite": "pcs", "qte": 1},
    "poignee_ext_R":  {"code": "60-9004_R",  "desc": "Poignée simple extérieure — droite",           "unite": "pcs", "qte": 1},
    "barrure_centre": {"code": "60-9010_L",  "desc": "Mécanisme verrouillage sans clé unilatéral",   "unite": "pcs", "qte": 1},
    "barrure_cle":    {"code": "60-6006",    "desc": "Capuchon serrure latérale — barrure à clé",    "unite": "pcs", "qte": 1},
    "double_poignee": {"code": "60-9007",    "desc": "Double poignée",                               "unite": "pcs", "qte": 1},
}

# ─── UTILITAIRES (partagés avec cover) ────────────────────────────────────────
def _mm_to_po(mm): return mm / 25.4
def _po_to_mm(po): return round(po * 25.4)

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
    import re
    s = str(s).strip().replace('"','').replace("'","")
    if not s: return 0.0
    m = re.match(r'^(\d+)[-\s]+(\d+)/(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m2 = re.match(r'^(\d+)/(\d+)$', s)
    if m2: return int(m2.group(1))/int(m2.group(2))
    return float(s)

def _fmt(po):
    mm = _po_to_mm(po)
    return f'{_dvf(po)}  ({mm:,} mm)'.replace(',', ' ')

def _ffd(pieces_list, utile_po, kerf=0.25):
    toutes = []
    for p in pieces_list:
        for _ in range(p['qte']):
            # Copier tous les champs extra (mur, etc.) sauf 'qte'
            piece = {k: v for k, v in p.items() if k != 'qte'}
            toutes.append(piece)
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

# ─── CALCULS AIKA 6MM ─────────────────────────────────────────────────────────
def calculer_mur_aika(mur):
    """
    mur = {
      'nom': str,
      'largeur_po': float,
      'hauteur_po': float,
      'nb_rails': int,              (2, 3 = rail 3-trous / 4, 5 = rail 4-trous)
      'nb_panneaux': int,
      'modele': str,                ex: 'B/3'
      'ouvrant_chaque_cote': bool,  True = mode "ouvrant de chaque côté" (source Cielo 6005 Mur A)
      'serrures': list,             ex: ['barrure_int', 'poignee_ext_R']
      'couleur_alu': str,
      'couleur_verre': str,
      'encastre': bool,
    }
    """
    L_mm = _po_to_mm(mur['largeur_po'])
    H_mm = _po_to_mm(mur['hauteur_po'])
    nb   = mur['nb_panneaux']
    rails = mur.get('nb_rails', 3)

    # ── Mode ouverture et type de rail ──────────────────────────────────────────
    occ = mur.get('ouvrant_chaque_cote', False)   # "ouvrant de chaque côté"
    is_4slot = (rails >= 4)                        # rail 4-trous (60-1001/1002)

    # ── Profils rails selon nb_rails ──
    if is_4slot:
        code_inf, code_sup = "60-1001", "60-1002"
    else:
        code_inf, code_sup = "60-1003", "60-1004"

    L_po = mur['largeur_po']
    H_po = mur['hauteur_po']

    # Longueurs dérivées
    long_2001_mm = H_mm - 42   # profil verrouillage
    long_2002_mm = H_mm - 42   # profil vertical verre (même longueur)
    long_3001_mm = H_mm - 33   # profil U
    long_3002_mm = H_mm - 33   # profil régulation / clamp 4-trous
    long_3003_mm = H_mm - 42   # profil verrou clamp 3-trous

    # Séparateur : 52.4 mm en mode OCC, 46 mm standard (source Cielo 6208 / 6005)
    sep_mm = 52.4 if occ else 46.0
    mont_total = (nb + 1) * sep_mm

    # ── Largeurs de panneau ──────────────────────────────────────────────────────
    modele_l = mur.get('modele','A')[0].upper() if mur.get('modele') else 'A'
    if occ:
        # "Ouvrant de chaque côté" : tous les panneaux uniformes (source Cielo 6005 Mur A)
        larg_ext = larg_int = larg_pan_mm = round((L_mm - mont_total) / nb)
    elif modele_l in ('A','B','C','D') and nb > 2:
        # Panneau extérieur ≠ panneau intérieur — ratio confirmé Cielo 6208
        ratio_pan = 972 / 943
        larg_ext = round((L_mm - mont_total) / ((nb-2)*ratio_pan + 2))
        larg_int = round(larg_ext * ratio_pan)
        larg_pan_mm = larg_int  # valeur de référence pour usages génériques
    else:
        larg_ext = larg_int = larg_pan_mm = round((L_mm - mont_total) / nb)

    # ── Quantités profils ────────────────────────────────────────────────────────
    # Mode OCC : doublement de tous les profils (source Cielo 6005 Mur A — 0 écart)
    factor = 2 if occ else 1

    nb_2001 = rails * factor
    nb_2002 = rails * (nb - 1) * factor
    # 60-3001 : rails×2 pour rail 4-trous ET mode OCC (source Cielo 6005 Mur A et B)
    nb_3001 = rails * 2 if (occ or is_4slot) else rails

    # Verrou clamp : 60-3002 pour rail 4-trous, 60-3003 pour rail 3-trous
    if is_4slot:
        clamp_code = "60-3002"
        long_clamp_mm = long_3002_mm
        nb_clamp = 2                    # toujours 2 pour rail 4-trous (source Cielo 6005 Mur B)
    else:
        clamp_code = "60-3003"
        long_clamp_mm = long_3003_mm
        nb_clamp = 1 * factor           # 1 standard, 2 en mode OCC (source Cielo 6005 Mur A)

    profils = [
        {"code": code_inf,   "desc": BARRES_AIKA[code_inf]['desc'],   "long_mm": L_mm,          "long_po": L_po,                      "qte": 1},
        {"code": code_sup,   "desc": BARRES_AIKA[code_sup]['desc'],   "long_mm": L_mm,          "long_po": L_po,                      "qte": 1},
        {"code": "60-2001",  "desc": BARRES_AIKA['60-2001']['desc'],  "long_mm": long_2001_mm,  "long_po": _mm_to_po(long_2001_mm),   "qte": nb_2001},
        {"code": "60-2002",  "desc": BARRES_AIKA['60-2002']['desc'],  "long_mm": long_2002_mm,  "long_po": _mm_to_po(long_2002_mm),   "qte": nb_2002},
        {"code": "60-3001",  "desc": BARRES_AIKA['60-3001']['desc'],  "long_mm": long_3001_mm,  "long_po": _mm_to_po(long_3001_mm),   "qte": nb_3001},
        {"code": clamp_code, "desc": BARRES_AIKA[clamp_code]['desc'], "long_mm": long_clamp_mm, "long_po": _mm_to_po(long_clamp_mm),  "qte": nb_clamp},
    ]
    # 60-2003 : 2 par panneau (haut + bas)
    desc_2003 = BARRES_AIKA['60-2003']['desc']
    if occ:
        # Mode OCC : tous uniformes, nb×2 panneaux physiques × 2 profils = nb×4
        profils.append({"code": "60-2003", "desc": desc_2003,
                        "long_mm": larg_pan_mm, "long_po": _mm_to_po(larg_pan_mm), "qte": nb * 4})
    elif modele_l in ('A','B','C','D') and nb > 2:
        profils.append({"code": "60-2003", "desc": desc_2003,
                        "long_mm": larg_ext, "long_po": _mm_to_po(larg_ext), "qte": 2 * 2})    # 2 extrémités × 2
        profils.append({"code": "60-2003", "desc": desc_2003,
                        "long_mm": larg_int, "long_po": _mm_to_po(larg_int), "qte": (nb-2) * 2})  # intérieurs × 2
    else:
        profils.append({"code": "60-2003", "desc": desc_2003,
                        "long_mm": larg_pan_mm, "long_po": _mm_to_po(larg_pan_mm), "qte": nb * 2})

    # ── Verre 6mm ──
    # Hauteur verre = H - 132mm
    haut_verre_mm = H_mm - 132
    couleur_v = mur.get('couleur_verre','Clair')

    if occ:
        # Mode OCC : tous uniformes, nb×2 panneaux physiques
        verres = [{"larg_mm": larg_pan_mm+16, "haut_mm": haut_verre_mm, "qte": nb * 2, "couleur": couleur_v}]
    elif modele_l in ('A','B','C','D') and nb > 2:
        verres = [
            {"larg_mm": larg_ext+16, "haut_mm": haut_verre_mm, "qte": 2,    "couleur": couleur_v},
            {"larg_mm": larg_int+16, "haut_mm": haut_verre_mm, "qte": nb-2, "couleur": couleur_v},
        ]
    else:
        verres = [{"larg_mm": larg_pan_mm+16, "haut_mm": haut_verre_mm, "qte": nb, "couleur": couleur_v}]

    # ── Quincaillerie par panneau ──
    # Mode OCC : nb_glass = nb×2 panneaux physiques (chaque position visible = 2 panneaux empilés)
    nb_glass = nb * 2 if occ else nb
    quincaillerie = []
    for item in QUINCAILLERIE_AIKA_BASE:
        quincaillerie.append({
            "code": item['code'], "desc": item['desc'],
            "unite": item['unite'], "qte_calc": item['qte'] * nb_glass
        })

    # Joint de verre = périmètre de chaque vitre × nb (utiliser première largeur verre)
    larg_verre_ref = verres[0]['larg_mm']
    perim_verre_m = sum((v['larg_mm'] + haut_verre_mm) * 2 * v['qte'] for v in verres) / 1000
    quincaillerie.append({
        "code": "60-7001", "desc": "Joint de verre (périmètre vitres)",
        "unite": "m", "qte_calc": round(perim_verre_m, 2)
    })

    # Joint brosse = longueur 60-2002 × nb de 60-2002
    joint_brosse_m = long_2002_mm * nb_2002 / 1000
    quincaillerie.append({
        "code": "60-7004", "desc": "Joint brosse (profils 60-2002)",
        "unite": "m", "qte_calc": round(joint_brosse_m, 2)
    })

    # Serrures selon sélection (liste vide = pas de serrure)
    for s in mur.get('serrures', []):
        if s in SERRURES_AIKA:
            sx = SERRURES_AIKA[s]
            quincaillerie.append({
                "code": sx['code'], "desc": sx['desc'],
                "unite": sx['unite'], "qte_calc": sx['qte']
            })

    # ── Quincaillerie d'installation ──────────────────────────────────────────
    # Vis de blocage (couleur selon alu)
    couleur_lower = mur.get('couleur_alu', '').lower()
    if 'noir' in couleur_lower:
        quincaillerie.append({"code": "VA21,0807BZ", "desc": "Vis de blocage octogonale Noire",
                              "unite": "pcs", "qte_calc": rails * 2,
                              "installation": True, "note": "a valider"})
    else:
        quincaillerie.append({"code": "VA21,0807BL", "desc": "Vis de blocage octogonale Blanche",
                              "unite": "pcs", "qte_calc": rails * 2,
                              "installation": True, "note": "a valider"})
    # Caps hex colorés (1 Vert + 1 Rouge par serrure sélectionnée)
    nb_ser = len(mur.get('serrures', []))
    if nb_ser > 0:
        quincaillerie.append({"code": "60-8009", "desc": "Cap vis hex colore (selon serrure choisie)",
                              "unite": "pcs", "qte_calc": nb_ser * 2,
                              "installation": True, "note": "a valider"})
    # Vis de fixation selon substrat (choisir 1 ligne selon le type de mur)
    for code, desc, qte in [
        ("US21,0615CO",  "Vis rail alu autoperceuse",         rails * 6),
        ("VA04,0919SCO", "Vis rail pour bois",                rails * 6),
        ("VC02,1420RP",  "Vis a beton",                       rails * 4),
    ]:
        quincaillerie.append({"code": code, "desc": desc, "unite": "pcs", "qte_calc": qte,
                              "installation": True, "note": "choisir 1/substrat"})

    return {
        "nom": mur['nom'],
        "largeur_po": L_po, "hauteur_po": H_po,
        "largeur_mm": L_mm, "hauteur_mm": H_mm,
        "nb_panneaux": nb, "nb_rails": rails,
        "ouvrant_chaque_cote": occ,
        "modele": mur.get('modele',''),
        "encastre": mur.get('encastre', False),
        "couleur_alu": mur.get('couleur_alu',''),
        "couleur_verre": mur.get('couleur_verre','Clair'),
        "serrures": mur.get('serrures', []),
        "profils": profils,
        "verres": verres,
        "quincaillerie": quincaillerie,
        "nb_2002": nb_2002,
        "long_2002_mm": long_2002_mm,
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

# ─── GÉNÉRATION PDF AIKA 6MM ──────────────────────────────────────────────────
def generer_pdf_aika(params, fichier, mode='complet'):
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
    murs_calcules = []
    for m in params.get("murs", []):
        m['largeur_po'] = _fvd(m.get('largeur','0'))
        m['hauteur_po'] = _fvd(m.get('hauteur','0'))
        m['nb_panneaux'] = int(m.get('nb_panneaux', 1))
        m['nb_rails'] = int(m.get('nb_rails', 3))
        m['encastre'] = m.get('encastre', False)
        if m['largeur_po'] > 0 and m['hauteur_po'] > 0:
            murs_calcules.append(calculer_mur_aika(m))

    KERF = 0.25
    SEUIL = 6.0
    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    def entete(titre_doc):
        c.setFillColor(BLEU)
        c.rect(0, h-1.1*inch, w, 1.1*inch, fill=True, stroke=False)
        c.setFillColor(OR)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(0.4*inch, h-0.38*inch, "SOLARIUM PRO — AIKA 6mm")
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 8)
        c.drawString(0.4*inch, h-0.58*inch, titre_doc)
        c.drawString(0.4*inch, h-0.76*inch, f"No: {no_proj}  |  Client: {client}")
        c.drawRightString(w-0.4*inch, h-0.76*inch, str(date.today()))
        c.setFillColor(OR)
        c.rect(0, 0.3*inch, w, 0.25*inch, fill=True, stroke=False)
        c.setFillColor(BLEU)
        c.setFont("Helvetica", 7)
        c.drawCentredString(w/2, 0.4*inch,
            f"Solarium Pro  ·  {no_proj}  ·  {client}  ·  {date.today()}")

    def section(y, texte):
        c.setFillColor(BLEU)
        c.rect(0.45*inch, y-0.30*inch, w-0.9*inch, 0.30*inch, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.6*inch, y-0.20*inch, texte)
        return y - 0.48*inch

    def bandeau2(y, nom, L_po, H_po, nb, rails):
        haut = 0.34*inch
        c.setFillColor(GRIS2)
        c.rect(0.45*inch, y-haut, w-0.9*inch, haut, fill=True, stroke=False)
        c.setFillColor(BLEU)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.6*inch, y-0.19*inch, nom)
        c.setFont("Helvetica", 9)
        dim = (f"L = {_dvf(L_po)}  ({_po_to_mm(L_po)} mm)"
               f"    H = {_dvf(H_po)}  ({_po_to_mm(H_po)} mm)"
               f"    {nb} panneaux — {rails} rails")
        c.drawString(0.6*inch, y-0.31*inch, dim)
        return y - haut - 0.12*inch


    def tableau(y, data, cols):
        style = TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), BLEU),
            ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,GRIS]),
            ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",         (1,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ])
        header = [data[0]]
        rows   = data[1:]
        chunk  = list(header)
        for row in rows:
            candidate = chunk + [row]
            t_test = Table(candidate, colWidths=cols)
            t_test.setStyle(style)
            _, th = t_test.wrap(0, 0)
            if y - th < 0.9*inch:
                if len(chunk) > 1:
                    t_draw = Table(chunk, colWidths=cols)
                    t_draw.setStyle(style)
                    _, draw_h = t_draw.wrap(0, 0)
                    t_draw.drawOn(c, 0.4*inch, y - draw_h)
                    y -= draw_h
                c.showPage(); entete("(suite)"); y = h - 1.3*inch
                chunk = list(header) + [row]
            else:
                chunk = candidate
        if chunk:
            t_draw = Table(chunk, colWidths=cols)
            t_draw.setStyle(style)
            _, draw_h = t_draw.wrap(0, 0)
            if y - draw_h < 0.9*inch:
                c.showPage(); entete("(suite)"); y = h - 1.3*inch
            t_draw.drawOn(c, 0.4*inch, y - draw_h)
            y -= draw_h + 0.2*inch
        return y

    def dessin_mur_aika(y, mur_c):
        return dessiner_mur_aika_v3(c, y, mur_c, w, h, inch, colors, BLEU, OR)


    # ── Helpers : signature et tableau verres ────────────────────────────────
    def _verre_table(mur_c):
        data_v = [["Largeur verre", "Hauteur verre", "Couleur", "Qte"]]
        for v in mur_c['verres']:
            data_v.append([
                f"{v['larg_mm']} mm", f"{v['haut_mm']} mm",
                v['couleur'], str(v['qte'])
            ])
        return data_v

    def _bloc_appro(nom_mur):
        """Bloc de signature ancré en bas de page (au-dessus du pied de page)."""
        bw = 7.3*inch; bh = 1.42*inch
        bx = (w - bw) / 2; by = 0.65*inch
        c.setFillColor(colors.HexColor("#F0F4FB"))
        c.rect(bx, by, bw, bh, fill=True, stroke=False)
        c.setStrokeColor(BLEU); c.setLineWidth(1.0)
        c.rect(bx, by, bw, bh, fill=False, stroke=True)
        c.setFillColor(BLEU)
        c.rect(bx, by + bh - 0.32*inch, bw, 0.32*inch, fill=True, stroke=False)
        c.setFillColor(OR); c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(w/2, by + bh - 0.22*inch,
                            f"APPROBATION CLIENT — {nom_mur.upper()}")
        col_x = bx + 0.30*inch
        c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
        c.drawString(col_x, by + bh - 0.60*inch, "Signature du client :")
        c.setStrokeColor(colors.HexColor("#555555")); c.setLineWidth(0.7)
        c.line(col_x, by + bh - 0.95*inch, col_x + 3.0*inch, by + bh - 0.95*inch)
        c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor("#555555"))
        c.drawString(col_x, by + 0.12*inch,
                     "En signant, le client confirme avoir verifie et approuve les dimensions.")
        col2_x = bx + bw/2 + 0.20*inch
        c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
        c.drawString(col2_x, by + bh - 0.60*inch, "Date d'approbation :")
        c.setStrokeColor(colors.HexColor("#555555")); c.setLineWidth(0.7)
        c.line(col2_x, by + bh - 0.95*inch, col2_x + 2.0*inch, by + bh - 0.95*inch)
        c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
        c.drawString(col2_x, by + 0.44*inch, "Prepare par :")
        c.setFont("Helvetica-Bold", 9); c.setFillColor(BLEU)
        c.drawString(col2_x + 1.12*inch, by + 0.44*inch, "Cedric Rainville")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES APPROBATION — une page par mur, chacune avec sa propre signature
    # ══════════════════════════════════════════════════════════════════════════
    for idx, mur_c in enumerate(murs_calcules):
        entete(f"APPROBATION CLIENT — {mur_c['nom']}")
        y = h - 1.35*inch
        y = bandeau2(y, mur_c['nom'], mur_c['largeur_po'], mur_c['hauteur_po'],
                     mur_c['nb_panneaux'], mur_c['nb_rails'])
        y = dessin_mur_aika(y, mur_c)
        if notes.strip() and idx == len(murs_calcules) - 1:
            note_h = 0.60*inch
            if y - note_h > 2.4*inch:
                c.setFillColor(colors.HexColor("#FFF3CD"))
                c.rect(0.45*inch, y - note_h, w - 0.9*inch, note_h, fill=True, stroke=False)
                c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 9)
                c.drawString(0.60*inch, y - 0.18*inch, "NOTES :")
                c.setFont("Helvetica", 9)
                c.drawString(0.60*inch, y - 0.40*inch, notes[:130])
        _bloc_appro(mur_c['nom'])
        c.showPage()

    if mode == 'approbation':
        c.save()
        print(f"✓ Aika 6mm PDF approbation généré: {fichier}")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES SCHÉMA TECHNIQUE — une page par mur, sans signature (usage atelier)
    # ══════════════════════════════════════════════════════════════════════════
    for mur_c in murs_calcules:
        entete(f"SCHÉMA TECHNIQUE — {mur_c['nom']}")
        y = h - 1.35*inch
        y = bandeau2(y, mur_c['nom'], mur_c['largeur_po'], mur_c['hauteur_po'],
                     mur_c['nb_panneaux'], mur_c['nb_rails'])
        y = dessin_mur_aika(y, mur_c)
        y = tableau(y, _verre_table(mur_c), [1.9*inch, 1.9*inch, 1.2*inch, 0.6*inch])
        c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FEUILLE DE DÉBITAGE
    # ══════════════════════════════════════════════════════════════════════════
    entete("FEUILLE DE DÉBITAGE — Profils Aika 6mm")
    _draw_qr(c, no_proj, w, h, inch)
    y = h - 1.3*inch

    # ── Palette couleurs par mur ──────────────────────────────────────────────
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    _p_style = ParagraphStyle('dec', fontName='Helvetica', fontSize=9, leading=11)

    MUR_PALETTE = ["#C8640A","#1565C0","#2E7D32","#B71C1C","#6A1B9A","#00695C"]
    mur_noms_d = [mc['nom'] for mc in murs_calcules]
    mur_color_d = {nom: MUR_PALETTE[i % len(MUR_PALETTE)] for i, nom in enumerate(mur_noms_d)}
    multi_mur   = len(mur_noms_d) > 1

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
                    "nom": mur_c['nom'], "long": p['long_po'], "long_mm": p['long_mm']
                })

    # Légende couleurs → murs (une seule fois en haut de la page)
    if multi_mur:
        c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.HexColor("#333333"))
        c.drawString(0.45*inch, y, "Légende :")
        lx = 1.2*inch
        for nom in mur_noms_d:
            col = mur_color_d[nom]
            c.setFillColor(colors.HexColor(col))
            c.roundRect(lx, y - 0.02*inch, 0.11*inch, 0.13*inch, 2, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#222222")); c.setFont("Helvetica", 7.5)
            c.drawString(lx + 0.14*inch, y, nom)
            lx += c.stringWidth(nom, "Helvetica", 7.5) + 0.30*inch
        y -= 0.22*inch

    for (code, couleur), grp in profils_total.items():
        barre_mm = BARRES_AIKA.get(code, {}).get('long_mm', 6600)
        barre_po = barre_mm / 25.4
        utile_po = barre_po - 2.0

        # ── Tableau récap : longueur × mur × qté (avec couleur par mur) ──────
        from collections import defaultdict
        recap_by_wall = defaultdict(lambda: defaultdict(int))
        for g in grp['coupes']:
            recap_by_wall[round(g['long_mm'])][g['nom']] += 1

        if multi_mur:
            data_recap = [["Longueur (mm)", "Mur", "Qté"]]
            for long_mm in sorted(recap_by_wall.keys(), reverse=True):
                for mur_nom, qte in recap_by_wall[long_mm].items():
                    col = mur_color_d.get(mur_nom, '#333333')
                    mur_cell = Paragraph(
                        f'<font color="{col}"><b>■</b></font> {mur_nom}', _p_style)
                    data_recap.append([f"{long_mm} mm", mur_cell, str(qte)])
            col_recap = [2.0*inch, 2.3*inch, 0.5*inch]
        else:
            data_recap = [["Longueur de coupe (mm)", "Qté"]]
            for long_mm in sorted(recap_by_wall.keys(), reverse=True):
                qte_total = sum(recap_by_wall[long_mm].values())
                data_recap.append([f"{long_mm} mm", str(qte_total)])
            col_recap = [3.5*inch, 0.8*inch]

        # ── FFD : pièces individuelles avec info mur ──────────────────────────
        pieces_ffd = [{"nom": f"{round(g['long_mm'])} mm", "long": g['long'],
                        "qte": 1, "mur": g['nom']} for g in grp['coupes']]
        barres = _ffd(pieces_ffd, utile_po, KERF)
        nb_barres = len(barres)

        y = section(y, f"{code}  —  {grp['desc']}  —  {couleur}  —  Barres {barre_mm} mm  x{nb_barres}")
        y = tableau(y, data_recap, col_recap)

        # ── Tableau FFD avec couleurs par mur ─────────────────────────────────
        # Regrouper barres identiques (par contenu + reste)
        barres_groupees = {}
        for b in barres:
            pieces_sig = tuple(sorted(
                [(round(p['long']*25.4), p.get('mur','')) for p in b['pieces']],
                reverse=True
            ))
            reste_mm = round(b['reste']*25.4)
            cle = (pieces_sig, reste_mm)
            if cle not in barres_groupees:
                barres_groupees[cle] = {
                    'pieces': b['pieces'],
                    'util':   round(b['utilise']*25.4),
                    'reste':  reste_mm,
                    'qte':    0,
                }
            barres_groupees[cle]['qte'] += 1

        data_ffd = [["#", "Découpes (mm)", "Utilisé", "Reste"]]
        num = 1
        for bg in barres_groupees.values():
            pieces_html = []
            for p in sorted(bg['pieces'], key=lambda x: -x['long']):
                mm  = round(p['long'] * 25.4)
                col = mur_color_d.get(p.get('mur',''), '#333333')
                if multi_mur:
                    mur_abr = p.get('mur','')
                    pieces_html.append(
                        f'<font color="{col}"><b>{mm}</b></font>'
                        f'<font color="{col}" size="7"> [{mur_abr}]</font>'
                    )
                else:
                    pieces_html.append(f'<b>{mm}</b>')
            dec_cell = Paragraph('  +  '.join(pieces_html), _p_style)
            qte_label = f"x{bg['qte']}" if bg['qte'] > 1 else ""
            reste_str = f"{bg['reste']}" if bg['reste'] > round(SEUIL*25.4) else f"{bg['reste']} (!)"
            data_ffd.append([f"#{num}{qte_label}", dec_cell, str(bg['util']), reste_str])
            num += bg['qte']

        t_ffd = Table(data_ffd, colWidths=[0.5*inch, 4.2*inch, 1.1*inch, 0.8*inch])
        t_ffd.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0), BLEU),
            ("TEXTCOLOR",      (0,0),(-1,0), colors.white),
            ("FONTNAME",       (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, GRIS]),
            ("GRID",           (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",          (0,0),(0,-1), "CENTER"),
            ("ALIGN",          (2,0),(-1,-1), "CENTER"),
            ("TOPPADDING",     (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ]))
        _, th_ffd = t_ffd.wrap(0, 0)
        if y - th_ffd < 0.9*inch:
            c.showPage(); entete("(suite)"); y = h - 1.3*inch
        t_ffd.drawOn(c, 0.4*inch, y - th_ffd)
        y -= th_ffd + 0.2*inch

    # Légende (!)
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(0.4*inch, y + 0.12*inch,
                 f"(!) Reste < {round(SEUIL*25.4)} mm — ne pas ranger, mettre en dechet.")
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
                "long_po": p['long_po'], "long_mm": p['long_mm'], "qte": p['qte']
            })

    # ── Layout peinture : Photo | Code | Désignation | Grandeur+50mm | Qté | Coupé ✓ ──
    import os as _os
    _img_dir = _os.path.join(_os.path.dirname(__file__), "images_pieces")

    def _photo_profil(code):
        for ext in (".jpeg", ".jpg", ".png"):
            p = _os.path.join(_img_dir, f"{code}{ext}")
            if _os.path.exists(p):
                return p
        return None

    PH_W = 1.05*inch
    PH_H = 0.82*inch
    col_w_p = [PH_W, 0.72*inch, 1.90*inch, 1.55*inch, 0.48*inch, 0.65*inch]
    TOTAL_W_P = sum(col_w_p)
    HDR_P = [["Photo", "Code", "Désignation", "Grandeur (+50 mm)", "Qté", "Coupé ✓"]]

    def _draw_peinture_header(y_pos):
        t = Table(HDR_P, colWidths=col_w_p)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0), BLEU),
            ("TEXTCOLOR",      (0,0),(-1,0), colors.white),
            ("FONTNAME",       (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,0), 9),
            ("ALIGN",          (0,0),(-1,0), "CENTER"),
            ("TOPPADDING",     (0,0),(-1,0), 5),
            ("BOTTOMPADDING",  (0,0),(-1,0), 5),
        ]))
        _, th = t.wrap(0, 0)
        t.drawOn(c, 0.4*inch, y_pos - th)
        return y_pos - th

    # Regrouper par couleur pour n'avoir qu'un en-tête de couleur
    couleurs_p = list(dict.fromkeys(v['couleur'] for v in peinture.values()))
    premiere_couleur = True

    for couleur_p in couleurs_p:
        if not premiere_couleur:
            c.showPage(); entete("FEUILLE DE PEINTURE (suite)"); y = h - 1.3*inch
        premiere_couleur = False

        y = section(y, f"COULEUR : {couleur_p}")
        y = _draw_peinture_header(y)

        profils_couleur = [(k, v) for k, v in peinture.items() if v['couleur'] == couleur_p]
        bg_alt = [colors.white, GRIS]

        for row_i, ((code, _), grp) in enumerate(profils_couleur):
            barre_mm = BARRES_AIKA.get(code, {}).get('long_mm', 6600)
            UTILE_P  = barre_mm - 50
            KERF_P   = 6

            # Coupes regroupées
            coupes_p = {}
            for it in grp['items']:
                cle = it['long_mm']
                if cle not in coupes_p:
                    coupes_p[cle] = {'long_mm': it['long_mm'], 'qte': 0}
                coupes_p[cle]['qte'] += it['qte']
            coupes_sorted = sorted(coupes_p.values(), key=lambda x: -x['long_mm'])

            nb_lines = len(coupes_sorted)
            ROW_H = max(PH_H + 0.10*inch, nb_lines * 0.21*inch + 0.20*inch)

            if y - ROW_H < 1.85*inch:
                c.showPage(); entete("FEUILLE DE PEINTURE (suite)"); y = h - 1.3*inch
                y = _draw_peinture_header(y)

            rx = 0.4*inch
            # Fond de ligne
            c.setFillColor(bg_alt[row_i % 2])
            c.rect(rx, y - ROW_H, TOTAL_W_P, ROW_H, fill=True, stroke=False)
            c.setStrokeColor(colors.HexColor("#CCCCCC")); c.setLineWidth(0.4)
            c.rect(rx, y - ROW_H, TOTAL_W_P, ROW_H, fill=False, stroke=True)

            # — Photo —
            img_path = _photo_profil(code)
            ph_x = rx + 0.04*inch
            ph_y = y - ROW_H + 0.04*inch
            if img_path:
                try:
                    c.drawImage(img_path, ph_x, ph_y,
                                width=PH_W - 0.08*inch, height=ROW_H - 0.08*inch,
                                preserveAspectRatio=True, anchor='c', mask='auto')
                    img_path = img_path  # succès
                except Exception:
                    img_path = None
            if not img_path:
                c.setFillColor(colors.HexColor("#E0E8F0"))
                c.rect(ph_x, ph_y, PH_W - 0.08*inch, ROW_H - 0.08*inch, fill=True, stroke=False)
                c.setFillColor(colors.HexColor("#999")); c.setFont("Helvetica-Oblique", 7)
                c.drawCentredString(ph_x + (PH_W-0.08*inch)/2, ph_y + (ROW_H-0.08*inch)/2 - 3, "—")

            mid_y = y - ROW_H / 2 - 3

            # — Code —
            cx = rx + col_w_p[0]
            c.setFillColor(colors.HexColor("#222222")); c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(cx + col_w_p[1]/2, mid_y, code)

            # — Désignation —
            cx += col_w_p[1]
            c.setFont("Helvetica", 8)
            mots = grp['desc'].split()
            l1, l2 = [], []
            for mo in mots:
                if c.stringWidth(" ".join(l1+[mo]), "Helvetica", 8) < col_w_p[2]-6:
                    l1.append(mo)
                else:
                    l2.append(mo)
            c.drawString(cx+3, mid_y+(5 if l2 else 0), " ".join(l1))
            if l2:
                c.drawString(cx+3, mid_y-7, " ".join(l2))

            # — Grandeur(s) + Qté (une ligne par coupe) —
            cx_g = rx + sum(col_w_p[:3])
            cx_q = rx + sum(col_w_p[:4])
            line_h = 0.185*inch
            start_ly = y - (ROW_H - nb_lines * line_h) / 2 - line_h * 0.85
            for j, cp in enumerate(coupes_sorted):
                ly = start_ly - j * line_h
                lr = cp['long_mm'] + 50
                c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#222222"))
                c.drawCentredString(cx_g + col_w_p[3]/2, ly, f"{cp['long_mm']} mm  →  {lr} mm")
                c.drawCentredString(cx_q + col_w_p[4]/2, ly, str(cp['qte']))

            # — Case à cocher Coupé ✓ —
            cx_ck = rx + sum(col_w_p[:5])
            bx_s = 0.20*inch
            c.setStrokeColor(colors.HexColor("#666")); c.setLineWidth(0.5)
            c.rect(cx_ck + (col_w_p[5]-bx_s)/2, mid_y - bx_s/2 + 3, bx_s, bx_s,
                   fill=False, stroke=True)

            y -= ROW_H

    # ── Signatures peinture ──────────────────────────────────────────────────
    y -= 0.35*inch
    sig_y = max(y, 1.85*inch)
    c.setStrokeColor(BLEU); c.setLineWidth(0.6)
    c.line(0.45*inch, sig_y, 2.85*inch, sig_y)
    c.line(3.1*inch,  sig_y, 5.35*inch, sig_y)
    c.line(5.65*inch, sig_y, 7.75*inch, sig_y)
    c.setFillColor(colors.HexColor("#555555")); c.setFont("Helvetica", 7)
    c.drawString(0.45*inch, sig_y - 0.15*inch, "Reçu par le peintre — Nom + Signature")
    c.drawString(3.1*inch,  sig_y - 0.15*inch, "Date de réception")
    c.drawString(5.65*inch, sig_y - 0.15*inch, "Date de retour prévue")

    if mode == 'peinture':
        c.showPage()
        c.save()
        print(f"✓ Aika 6mm PDF peinture généré: {fichier}")
        return
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : LISTE DE VERRE
    # ══════════════════════════════════════════════════════════════════════════
    entete("LISTE DE VERRE — Aika 6mm")
    y = h - 1.3*inch

    verres_total = {}
    for mur_c in murs_calcules:
        for v in mur_c['verres']:
            cle = (v['larg_mm'], v['haut_mm'], v['couleur'])
            if cle not in verres_total:
                verres_total[cle] = {**v, "qte": 0, "murs": []}
            verres_total[cle]['qte'] += v['qte']
            verres_total[cle]['murs'].append(mur_c['nom'])

    data = [["Largeur", "Hauteur", "Couleur", "Qté", "Murs"]]
    for v in verres_total.values():
        data.append([
            f"{_dvf(v['larg_mm']/25.4)}  ({v['larg_mm']} mm)",
            f"{_dvf(v['haut_mm']/25.4)}  ({v['haut_mm']} mm)",
            v['couleur'], str(v['qte']),
            ", ".join(sorted(set(v['murs'])))
        ])
    y = tableau(y, data, [2.0*inch, 2.0*inch, 1.0*inch, 0.5*inch, 1.8*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : DÉCAISSE QUINCAILLERIE
    # ══════════════════════════════════════════════════════════════════════════
    entete("DÉCAISSE INVENTAIRE — Quincaillerie Aika 6mm")
    y = h - 1.3*inch

    qx_total = {}
    for mur_c in murs_calcules:
        for q in mur_c['quincaillerie']:
            cle = q['code']
            if cle not in qx_total:
                qx_total[cle] = {"code": q['code'], "desc": q['desc'],
                                  "unite": q['unite'], "qte": 0,
                                  "installation": q.get('installation', False),
                                  "note": q.get('note', '')}
            qx_total[cle]['qte'] += q['qte_calc']

    qx_std  = {k: v for k, v in qx_total.items() if not v.get('installation')}
    qx_inst = {k: v for k, v in qx_total.items() if v.get('installation')}

    # Section 1 — Quincaillerie & accessoires standard
    y = section(y, "QUINCAILLERIE & ACCESSOIRES")
    data = [["Code", "Description", "Unite", "Qte"]]
    for q in qx_std.values():
        qte_str = str(int(q['qte'])) if q['unite']=='pcs' else f"{q['qte']:.2f}".rstrip('0').rstrip('.')
        data.append([q['code'], q['desc'], q['unite'], qte_str])
    y = tableau(y, data, [1.0*inch, 4.0*inch, 0.6*inch, 0.8*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FICHE INSTALLATION
    # ══════════════════════════════════════════════════════════════════════════
    entete("FICHE INSTALLATION — Quincaillerie d'installation Aika 6mm")
    y = h - 1.3*inch
    y = section(y, "QUINCAILLERIE D'INSTALLATION")

    # Sous-titre note substrat
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(0.45*inch, y,
                 "Vis de fixation : choisir 1 type selon le substrat (alu / bois / béton)")
    y -= 0.25*inch

    # Tableau avec colonne photo
    PHOTO_W = 1.15*inch
    PHOTO_H = 0.90*inch

    def _photo_cell(code):
        """Retourne le chemin image si disponible, sinon None."""
        import os
        img_dir = os.path.join(os.path.dirname(__file__), "images_pieces")
        for ext in (".png", ".jpg", ".jpeg"):
            p = os.path.join(img_dir, f"{code}{ext}")
            if os.path.exists(p):
                return p
        return None

    col_widths_inst = [PHOTO_W, 1.05*inch, 2.60*inch, 0.55*inch, 0.55*inch, 1.15*inch]
    header_inst = [["Photo", "Code", "Description", "Unité", "Qté", "Note"]]

    # Dessiner en-tête
    t_hdr = Table(header_inst, colWidths=col_widths_inst)
    t_hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLEU),
        ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 10),
        ("ALIGN",         (0,0),(-1,0), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,0), 6),
        ("BOTTOMPADDING", (0,0),(-1,0), 6),
    ]))
    _, hdr_h = t_hdr.wrap(0, 0)
    t_hdr.drawOn(c, 0.4*inch, y - hdr_h)
    y -= hdr_h

    # Dessiner chaque ligne avec photo intégrée manuellement
    ROW_H = PHOTO_H + 0.10*inch
    bg_colors = [colors.white, GRIS]
    for i, q in enumerate(qx_inst.values()):
        if y - ROW_H < 1.85*inch:
            c.showPage(); entete("FICHE INSTALLATION (suite)"); y = h - 1.3*inch
        bg = bg_colors[i % 2]
        row_x = 0.4*inch
        # Fond de ligne
        c.setFillColor(bg)
        c.rect(row_x, y - ROW_H, sum(col_widths_inst), ROW_H, fill=True, stroke=False)
        c.setStrokeColor(colors.HexColor("#CCCCCC")); c.setLineWidth(0.4)
        c.rect(row_x, y - ROW_H, sum(col_widths_inst), ROW_H, fill=False, stroke=True)

        # Photo ou placeholder
        img_path = _photo_cell(q['code'])
        ph_x = row_x + 0.08*inch
        ph_y = y - ROW_H + 0.05*inch
        if img_path:
            try:
                c.drawImage(img_path, ph_x, ph_y, width=PHOTO_W - 0.16*inch, height=PHOTO_H - 0.10*inch,
                            preserveAspectRatio=True, anchor='c')
            except Exception:
                img_path = None
        if not img_path:
            c.setFillColor(colors.HexColor("#E0E8F0"))
            c.rect(ph_x, ph_y, PHOTO_W - 0.16*inch, PHOTO_H - 0.10*inch, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#888888")); c.setFont("Helvetica-Oblique", 7)
            c.drawCentredString(ph_x + (PHOTO_W - 0.16*inch)/2,
                                ph_y + (PHOTO_H - 0.10*inch)/2 - 4, "à valider")

        # Texte cellules
        col_offset = col_widths_inst[0]
        text_y = y - ROW_H/2 - 4
        qte_str = str(int(q['qte'])) if q['unite'] == 'pcs' else f"{q['qte']:.2f}".rstrip('0').rstrip('.')
        vals = [q['code'], q['desc'], q['unite'], qte_str, q.get('note', '')]
        aligns = ["CENTER", "LEFT", "CENTER", "CENTER", "LEFT"]
        for ci, (val, algn) in enumerate(zip(vals, aligns)):
            cw = col_widths_inst[ci + 1]
            cx = row_x + col_offset
            c.setFillColor(colors.HexColor("#222222")); c.setFont("Helvetica", 8.5)
            if algn == "CENTER":
                c.drawCentredString(cx + cw/2, text_y, str(val))
            else:
                # Wrap long text
                words = str(val).split()
                line1, line2 = [], []
                for w in words:
                    test = " ".join(line1 + [w])
                    if c.stringWidth(test, "Helvetica", 8.5) < cw - 6:
                        line1.append(w)
                    else:
                        line2.append(w)
                c.drawString(cx + 3, text_y + (5 if line2 else 0), " ".join(line1))
                if line2:
                    c.drawString(cx + 3, text_y - 9, " ".join(line2))
            col_offset += cw

        y -= ROW_H

    # ── Signatures installation ──────────────────────────────────────────────
    y -= 0.40*inch
    sig_y = max(y, 1.85*inch)
    c.setStrokeColor(BLEU); c.setLineWidth(0.6)
    c.line(0.45*inch, sig_y, 2.85*inch, sig_y)
    c.line(3.1*inch,  sig_y, 5.35*inch, sig_y)
    c.line(5.65*inch, sig_y, 7.75*inch, sig_y)
    c.setFillColor(colors.HexColor("#555555")); c.setFont("Helvetica", 7)
    c.drawString(0.45*inch, sig_y - 0.15*inch, "Installateur — Nom + Signature")
    c.drawString(3.1*inch,  sig_y - 0.15*inch, "Date d'installation")
    c.drawString(5.65*inch, sig_y - 0.15*inch, "Date de vérification")

    c.save()
    print(f"✓ Aika 6mm PDF généré: {fichier}")
