"""
NÉOSCENICA — Module de production Solarium Pro v1
Structure identique à aika_6mm_module.py — 5 pages dans l'ordre.
Dépendance dessin : neoscenica_dessin_v1

RÈGLE USINE — Lisibilité et occupation de page :
  • Les dessins techniques occupent tout l'espace disponible de la page.
  • Toute étiquette, cote ou texte doit être lisible à 50 cm en conditions d'usine.
  • Taille minimum : 9 pt annotations, 10 pt tableaux.
  • Codes KIT Bettio apparaissent sur chaque liste de coupe (correspondance INVENTAIRE_MASTER.xlsx).
"""

import os, sys, re
from math import gcd
from datetime import date as _date
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import neoscenica_dessin_v1 as _dessin

# Codes KIT Bettio — Néoscenica
KITS_NEOSCENICA = {
    '3702': ('Guide coulisse sup',    6000),
    '3704': ('Profil compensateur',   6000),
    '1758': ('Profil coulissement',   6000),
    '3707': ('Coulissement incliné',  6000),
    '3699': ('Caisson/coffre',        4900),
    '3703': ('Barre poignée',         4700),
    '3214': ('Profil latéral',        4900),
    '3859': ('Tube/Toile',            4900),
}
# format: code → (nom_descriptif, barre_mm)

KERF              = 0.25
SEUIL_RESTE_PO    = 6.0
SEUIL_CENT_PO     = 98.0    # largeur max sans montant central

# ─── QUINCAILLERIE / ACCESSOIRES ─────────────────────────────────────────────
# Source : quincaillerie_neo_EzeSunDemo.xlsx — onglet FRA
# qte  : integer = pcs fixes par moustiquaire
#        'H'     = 1 mètre par mètre de HAUTEUR (linéaire)
#        'L'     = 1 mètre par mètre de LARGEUR  (linéaire)
QUINCAILLERIE_NEO = [
    # Brosses et adhésifs
    {'code': 'KIT3339', 'desc': 'Brosse 45° Noir (coffre)',              'qte': 'H', 'unite': 'ml'},
    {'code': 'KIT1819', 'desc': 'Brosse SPF 4.8×15 3P Gris',            'qte': 'H', 'unite': 'ml'},
    {'code': 'KIT3871', 'desc': 'Brosse anti-vent Anima21 Gris',        'qte': 'L', 'unite': 'ml'},
    {'code': 'KIT3069', 'desc': 'Double adhésif métal H.10mm×50m',      'qte': 'L', 'unite': 'ml'},
    # Profils coulissement (longueur fixe 2500mm)
    {'code': 'KIT4160', 'desc': 'Profil coulissement coffre L.2500mm',  'qte': 4,   'unite': 'pcs'},
    {'code': 'KIT3761', 'desc': 'Profil coulissement poignée L.2500mm', 'qte': 4,   'unite': 'pcs'},
    # Vis et rivets
    {'code': 'KIT3808', 'desc': 'Vis TORX 3×40',                        'qte': 4,   'unite': 'pcs'},
    {'code': 'KIT3340', 'desc': 'Vis TORX 4.5×12',                      'qte': 2,   'unite': 'pcs'},
    {'code': 'KIT3059', 'desc': 'Vis TORX 3.5×30',                      'qte': 8,   'unite': 'pcs'},
    {'code': 'KIT3793', 'desc': 'Vis TORX 3.5×50',                      'qte': 8,   'unite': 'pcs'},
    {'code': 'KIT3556', 'desc': 'Rivet manuel mâle',                    'qte': 4,   'unite': 'pcs'},
    {'code': 'KIT3557', 'desc': 'Rivet manuel femelle',                 'qte': 4,   'unite': 'pcs'},
    {'code': 'KIT160',  'desc': 'Boîte vis et chevilles',               'qte': 2,   'unite': 'pcs', 'note': 'Option'},
    # Ressorts et accessoires de glissement
    {'code': 'KIT3893', 'desc': 'Ressort 600mm',                        'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3888', 'desc': 'Tête supérieure',                      'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3744', 'desc': 'Paire de tulipes pour toile',          'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3892', 'desc': 'Glissière supérieure assemblée',       'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3740', 'desc': 'Glissière supérieure pour toile',      'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3894', 'desc': 'Bouchon pour tube',                    'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3741', 'desc': 'Glissière inférieure pour toile',      'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3736', 'desc': 'Glissière inférieure (A)',             'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3737', 'desc': 'Glissière inférieure (B)',             'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3735', 'desc': 'Embout inf. pour coulisse mobile',     'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3895', 'desc': 'Support coffre avec double adhésif',   'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3889', 'desc': 'Groupe de pression',                   'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3738', 'desc': 'Ressort de pression',                  'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3353', 'desc': 'Double adhésif pour pose L.1500mm',    'qte': 1,   'unite': 'pcs', 'note': 'Option'},
    {'code': 'KIT3758', 'desc': "Élément d'espacement lame finale",     'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3759', 'desc': 'Arrêt coulisse',                       'qte': 1,   'unite': 'pcs'},
    {'code': 'KIT3883', 'desc': 'Coulisse mobile 1500mm',               'qte': 1,   'unite': 'pcs', 'note': 'selon H'},
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
    s = str(s).strip().replace('"','').replace("'","")
    if not s: return 0.0
    m = re.match(r'^(\d+)[-\s]+(\d+)/(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m2 = re.match(r'^(\d+)/(\d+)$', s)
    if m2: return int(m2.group(1))/int(m2.group(2))
    return float(s)

def _ffd(pieces_list, utile_po, kerf=0.25):
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
                b['pieces'].append(piece); b['utilise'] += besoin; placee = True; break
        if not placee:
            barres.append({'num': len(barres)+1, 'pieces': [piece], 'utilise': besoin})
    for b in barres:
        b['reste'] = utile_po - b['utilise']
    return barres

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


# ─── CALCUL MUR ───────────────────────────────────────────────────────────────
def _kp(code, nom, long, qte):
    nom_kit, barre_mm = KITS_NEOSCENICA[code]
    return {'nom': nom, 'kit': code, 'kit_nom': nom_kit,
            'barre_mm': barre_mm, 'barre_po': barre_mm / 25.4, 'long': long, 'qte': qte}

def calculer_mur_neoscenica(mur):
    """
    mur = {nom, largeur_po, hauteur_po, type, sens, couleur_alu,
           partage (Double seulement: 'egal'|'sur_mesure'),
           largeur_pan_a, largeur_pan_b (Double sur_mesure seulement)}

    Mode Simple  : 1 panneau de largeur L_po.
    Mode Double  : 2 moustiquaires indépendants côte à côte (pas de montant central).
                   Chacun roule vers son propre poteau extérieur.
                   partage='egal'      → chaque panneau = L_po ÷ 2
                   partage='sur_mesure'→ largeurs saisies séparément (somme doit = L_po)
    """
    L_po     = mur['largeur_po']
    H_po     = mur['hauteur_po']
    type_mur = mur.get('type', 'Simple')
    mont_lat = H_po - 1.625
    H_mm     = round(H_po * 25.4)

    def _pieces_pan(suffix, L_pan):
        """Jeu complet de pièces pour un panneau de largeur L_pan."""
        L_pan_mm = round(L_pan * 25.4)
        ps = [
            _kp('3704', f'Profil compensateur/seuil{suffix}', (L_pan_mm - 12)  / 25.4, 1),
            _kp('3702', f'Guide coulisse sup{suffix}',        (L_pan_mm - 175) / 25.4, 1),
            _kp('1758', f'Profil coulissement{suffix}',       (L_pan_mm - 115) / 25.4, 2),
            _kp('3699', f'Caisson{suffix}',                   (H_mm - 85)  / 25.4,     1),
            _kp('3703', f'Barre poignée{suffix}',             (H_mm - 138) / 25.4,     1),
            _kp('3214', f'Profil latéral{suffix}',            mont_lat,                 2),
            _kp('3859', f'Tube/Toile{suffix}',                (H_mm - 48)  / 25.4,     1),
        ]
        if L_pan > SEUIL_CENT_PO:
            ps.append(_kp('3707', f'Coulissement central incliné{suffix}', mont_lat, 1))
        return ps

    if type_mur == 'Double':
        partage = mur.get('partage', 'egal')
        if partage == 'sur_mesure':
            L_a = _fvd(str(mur.get('largeur_pan_a', ''))) or L_po / 2
            L_b = _fvd(str(mur.get('largeur_pan_b', ''))) or L_po / 2
        else:
            L_a = L_b = L_po / 2
        panneaux = [
            {'label': 'Panneau A', 'largeur_po': L_a, 'largeur_mm': round(L_a * 25.4)},
            {'label': 'Panneau B', 'largeur_po': L_b, 'largeur_mm': round(L_b * 25.4)},
        ]
        pieces = _pieces_pan(' — Pan. A', L_a) + _pieces_pan(' — Pan. B', L_b)
    else:
        panneaux = [{'label': '', 'largeur_po': L_po, 'largeur_mm': round(L_po * 25.4)}]
        pieces   = _pieces_pan('', L_po)

    return {
        'nom':         mur.get('nom', ''),
        'largeur_po':  L_po,  'hauteur_po':  H_po,
        'largeur_mm':  round(L_po * 25.4), 'hauteur_mm': round(H_po * 25.4),
        'type':        type_mur,
        'partage':     mur.get('partage', 'egal') if type_mur == 'Double' else None,
        'sens':        mur.get('sens',        'Gauche'),
        'couleur_alu': mur.get('couleur_alu', ''),
        'nb_mont_cent': 0,   # toujours 0 — géré pièce par pièce dans _pieces_pan()
        'panneaux':    panneaux,
        'pieces':      pieces,
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

# ─── GÉNÉRATION PDF ───────────────────────────────────────────────────────────
def generer_pdf_neoscenica(params, fichier):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units    import inch
    from reportlab.pdfgen       import canvas
    from reportlab.lib          import colors
    from reportlab.platypus     import Table, TableStyle

    BLEU = colors.HexColor("#1F3864")
    OR   = colors.HexColor("#C68B00")
    GRIS = colors.HexColor("#F5F5F5")
    GRIS2= colors.HexColor("#D6E4F0")

    no_proj = params.get("no_projet", "")
    client  = params.get("client",    "")
    couleur = params.get("couleur",   "")
    notes   = params.get("notes",     "")

    # ── Construire murs calculés ──────────────────────────────────────────────
    murs_calc = []
    for m in params.get("murs", []):
        m['largeur_po'] = _fvd(m.get('largeur', '0'))
        m['hauteur_po'] = _fvd(m.get('hauteur', '0'))
        m['couleur_alu'] = m.get('couleur_alu', couleur)
        if m['largeur_po'] > 0 and m['hauteur_po'] > 0:
            murs_calc.append(calculer_mur_neoscenica(m))

    # ── Agréger toutes les pièces et FFD par kit ──────────────────────────────
    toutes_pieces = []
    for mc in murs_calc:
        toutes_pieces.extend(mc['pieces'])

    par_kit_agg = {}
    for p in toutes_pieces:
        kc = p['kit']
        if kc not in par_kit_agg:
            par_kit_agg[kc] = {'kit_nom': p['kit_nom'], 'barre_mm': p['barre_mm'],
                                'barre_po': p['barre_po'], 'acc': defaultdict(int)}
        par_kit_agg[kc]['acc'][(p['nom'], round(p['long'], 4))] += p['qte']

    kits_ffd = {}
    for kc, kd in par_kit_agg.items():
        pieces_kit = [{'nom': nom, 'long': long, 'qte': qte}
                      for (nom, long), qte in kd['acc'].items()]
        barres = _ffd(pieces_kit, kd['barre_po'])
        for i, b in enumerate(barres): b['num'] = i + 1
        kits_ffd[kc] = {**kd, 'barres': barres}

    # ── Restes à enregistrer ──────────────────────────────────────────────────
    restes = []
    for kc, kd in kits_ffd.items():
        for b in kd['barres']:
            if b['reste'] >= SEUIL_RESTE_PO:
                restes.append({'profil': f"KIT {kc} — {kd['kit_nom']}", 'longueur': b['reste']})

    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def entete(titre_doc):
        c.setFillColor(BLEU)
        c.rect(0, h-1.1*inch, w, 1.1*inch, fill=True, stroke=False)
        c.setFillColor(OR); c.setFont("Helvetica-Bold", 13)
        c.drawString(0.4*inch, h-0.38*inch, "SOLARIUM PRO — NÉOSCENICA")
        c.setFillColor(colors.white); c.setFont("Helvetica", 9)
        c.drawString(0.4*inch, h-0.58*inch, titre_doc)
        c.drawString(0.4*inch, h-0.76*inch,
                     f"No: {no_proj}  |  Client: {client}  |  Couleur: {couleur}")
        c.drawRightString(w-0.4*inch, h-0.76*inch, str(_date.today()))
        c.setFillColor(OR)
        c.rect(0, 0.3*inch, w, 0.25*inch, fill=True, stroke=False)
        c.setFillColor(BLEU); c.setFont("Helvetica", 7)
        c.drawCentredString(w/2, 0.4*inch,
                            f"Solarium Pro  ·  {no_proj}  ·  {client}  ·  {_date.today()}")

    def titre_section(y, texte):
        c.setFillColor(BLEU)
        c.rect(0.4*inch, y-0.26*inch, w-0.8*inch, 0.26*inch, fill=True, stroke=False)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 11)
        c.drawString(0.5*inch, y-0.17*inch, texte)
        return y - 0.44*inch

    def bandeau_mur(y, mc):
        haut = 0.32*inch
        c.setFillColor(GRIS2)
        c.rect(0.4*inch, y-haut, w-0.8*inch, haut, fill=True, stroke=False)
        c.setFillColor(BLEU); c.setFont("Helvetica", 10)
        dim_str = (f"{mc['nom']}  —  "
                   f"L = {_dvf(mc['largeur_po'])} ({mc['largeur_mm']} mm)  "
                   f"H = {_dvf(mc['hauteur_po'])} ({mc['hauteur_mm']} mm)  "
                   f"Type: {mc['type']}  Ouverture: {mc['sens']}")
        if mc['type'] == 'Double':
            pans = mc.get('panneaux', [])
            if pans:
                parts = '  +  '.join(
                    f"{p['label']}: {_dvf(p['largeur_po'])} ({p['largeur_mm']} mm)"
                    for p in pans)
                dim_str += f"  [{parts}]"
        c.drawString(0.5*inch, y-0.16*inch, dim_str)
        return y - haut - 0.14*inch

    def tableau(y, data, cols):
        style = TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  BLEU),
            ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
            ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, GRIS]),
            ("GRID",           (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",          (1,0),(-1,-1), "CENTER"),
            ("TOPPADDING",     (0,0),(-1,-1), 7),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 7),
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
                c.showPage(); entete("(suite)"); y = h - 1.4*inch
                chunk = list(header) + [row]
            else:
                chunk = candidate
        if chunk:
            t_draw = Table(chunk, colWidths=cols)
            t_draw.setStyle(style)
            _, draw_h = t_draw.wrap(0, 0)
            if y - draw_h < 0.9*inch:
                c.showPage(); entete("(suite)"); y = h - 1.4*inch
            t_draw.drawOn(c, 0.4*inch, y - draw_h)
            y -= draw_h + 0.25*inch
        return y

    def table_coupes(y, barres):
        data = [["#", "Découpes (pouces)", "Utilisé", "Reste"]]
        for b in barres:
            dec  = " + ".join(_dvf(p["long"]) for p in b["pieces"])
            rest = _dvf(b["reste"]) if b["reste"] >= SEUIL_RESTE_PO else f'{_dvf(b["reste"])} (!)'
            data.append([f"#{b['num']}", dec, _dvf(b["utilise"]), rest])
        return tableau(y, data, [0.4*inch, 4.9*inch, 1.2*inch, 1.2*inch])

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 : APPROBATION CLIENT
    # ══════════════════════════════════════════════════════════════════════════
    entete("APPROBATION CLIENT — Néoscenica (Moustiquaire)")
    y = h - 1.3*inch
    for mc in murs_calc:
        mcd = {
            'nom':          mc['nom'],
            'largeur_po':   mc['largeur_po'],   'hauteur_po':   mc['hauteur_po'],
            'largeur_mm':   mc['largeur_mm'],   'hauteur_mm':   mc['hauteur_mm'],
            'type':         mc['type'],          'sens':         mc['sens'],
            'couleur_alu':  mc['couleur_alu'],
            'nb_mont_cent': mc['nb_mont_cent'],
            'panneaux':     mc.get('panneaux', []),
        }
        y = bandeau_mur(y, mc)
        y = _dessin.dessiner_mur_neoscenica(c, y, mcd, w, h, inch, colors, BLEU, OR)
        y -= 0.10*inch
    _dessin.bloc_approbation(c, y, w, inch, colors, BLEU)
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 : SCHÉMA TECHNIQUE (dimensions mm + pouces)
    # ══════════════════════════════════════════════════════════════════════════
    entete("SCHÉMA TECHNIQUE — Néoscenica (dimensions mm + pouces)")
    y = h - 1.3*inch
    for mc in murs_calc:
        mcd = {
            'nom':          mc['nom'],
            'largeur_po':   mc['largeur_po'],   'hauteur_po':   mc['hauteur_po'],
            'largeur_mm':   mc['largeur_mm'],   'hauteur_mm':   mc['hauteur_mm'],
            'type':         mc['type'],          'sens':         mc['sens'],
            'couleur_alu':  mc['couleur_alu'],
            'nb_mont_cent': mc['nb_mont_cent'],
            'panneaux':     mc.get('panneaux', []),
        }
        y = bandeau_mur(y, mc)
        y = _dessin.dessiner_mur_neoscenica(c, y, mcd, w, h, inch, colors, BLEU, OR)
        y -= 0.15*inch
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 : RÉCAPITULATIF DES PIÈCES
    # ══════════════════════════════════════════════════════════════════════════
    entete("RÉCAPITULATIF DES PIÈCES — Néoscenica")
    y = h - 1.3*inch
    for mc in murs_calc:
        y = bandeau_mur(y, mc)
        y = titre_section(y, f"KIT BETTIO — {mc['nom']}")
        data = [["Kit", "Désignation", "Longueur (pouces)", "Longueur (mm)", "Qté"]]
        for p in mc['pieces']:
            data.append([
                p['kit'],
                p['nom'],
                _dvf(p['long']),
                str(round(p['long'] * 25.4)),
                str(p['qte']),
            ])
        y = tableau(y, data, [0.9*inch, 2.5*inch, 1.5*inch, 1.4*inch, 0.9*inch])
    if notes.strip():
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.rect(0.4*inch, y-0.55*inch, w-0.8*inch, 0.55*inch, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 9)
        c.drawString(0.5*inch, y-0.16*inch, "NOTES :")
        c.setFont("Helvetica", 9)
        c.drawString(0.5*inch, y-0.38*inch, notes[:130])
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES 4 : COUPES & QUINCAILLERIE — flux continu
    # ══════════════════════════════════════════════════════════════════════════
    entete("COUPES & QUINCAILLERIE — Néoscenica")
    _draw_qr(c, no_proj, w, h, inch)
    y = h - 1.4*inch

    # ── Tableau de coupe consolidé (un seul tableau, toutes kits) ─────────────
    y = titre_section(y, f"LISTES DE COUPE — {couleur}")
    data_c = [["Kit", "Désignation", "Barre", "#", "Découpes (pouces)", "Utilisé", "Reste"]]
    for kc, kd in kits_ffd.items():
        for b in kd['barres']:
            dec  = "  +  ".join(_dvf(p["long"]) for p in b["pieces"])
            rest = _dvf(b["reste"]) if b["reste"] >= SEUIL_RESTE_PO else f'{_dvf(b["reste"])} (!)'
            data_c.append([
                f"KIT {kc}", kd['kit_nom'], f"{kd['barre_mm']} mm",
                f"#{b['num']}", dec, _dvf(b["utilise"]), rest
            ])
    y = tableau(y, data_c, [0.65*inch, 1.6*inch, 0.75*inch, 0.3*inch, 2.8*inch, 0.75*inch, 0.75*inch])
    # Légende (!)
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(0.4*inch, y + 0.18*inch,
                 f"(!) Reste < {SEUIL_RESTE_PO:.0f}\" — ne pas ranger, mettre en dechet.")

    # ── Métrages projet ────────────────────────────────────────────────────────
    total_H_m = sum(mc['hauteur_mm'] / 1000 * len(mc['panneaux']) for mc in murs_calc)
    total_L_m = sum(pan['largeur_mm'] / 1000 for mc in murs_calc for pan in mc['panneaux'])
    total_panels = sum(len(mc['panneaux']) for mc in murs_calc)

    if y < 1.8*inch:
        c.showPage(); entete("QUINCAILLERIE — Néoscenica (suite)"); y = h - 1.4*inch
    y -= 0.15*inch

    # ── Quincaillerie principale ───────────────────────────────────────────────
    y = titre_section(y, f"QUINCAILLERIE & ACCESSOIRES — {total_panels} moustiquaire{'s' if total_panels > 1 else ''}")
    data_q = [["Code KIT", "Description", "Quantité", "Unité", "Note"]]
    for item in QUINCAILLERIE_NEO:
        qte = item['qte']
        if qte == 'H':
            qte_str = f"{total_H_m:.2f}"; unite_str = "ml"
        elif qte == 'L':
            qte_str = f"{total_L_m:.2f}"; unite_str = "ml"
        else:
            qte_str = str(qte * total_panels); unite_str = item['unite']
        data_q.append([item['code'], item['desc'], qte_str, unite_str, item.get('note', '')])
    y = tableau(y, data_q, [1.0*inch, 3.1*inch, 1.1*inch, 0.7*inch, 1.3*inch])

    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5 : FICHE PEINTURE
    # ══════════════════════════════════════════════════════════════════════════
    from solarium_utils import est_couleur_stock
    from reportlab.platypus import Image as RLImage

    # Profils exclus : aluminium brut ou non peints
    KITS_NON_PEINTS = {'1758', '3214', '3707'}

    _IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images_pieces')
    IMAGES_PROFILS = {
        '3699': os.path.join(_IMG_DIR, 'profil_3699.png'),
        '3703': os.path.join(_IMG_DIR, 'profil_3703.png'),
        '3702': os.path.join(_IMG_DIR, 'profil_3702.png'),
        '3704': os.path.join(_IMG_DIR, 'profil_3704.png'),
        '3859': os.path.join(_IMG_DIR, 'profil_tube_25x100.jpeg'),
    }

    def _img_cell(kit_code):
        path = IMAGES_PROFILS.get(kit_code)
        if path and os.path.exists(path):
            return RLImage(path, width=0.52*inch, height=0.38*inch)
        return ""

    # Agréger pièces à peindre par (kit, nom, long_mm)
    pieces_peinture = {}
    for p in toutes_pieces:
        if p['kit'] in KITS_NON_PEINTS:
            continue
        key = (p['kit'], p['kit_nom'], round(p['long'] * 25.4))
        pieces_peinture[key] = pieces_peinture.get(key, 0) + p['qte']

    entete("FICHE PEINTURE — Neoscenica")
    y = h - 1.4*inch
    stock = est_couleur_stock(couleur)
    cas_label = "STOCK — barres completes" if stock else "SUR MESURE — longueurs precisees"
    y = titre_section(y, f"Neoscenica.  Couleur : {couleur}  [{cas_label}]")

    if stock:
        # CAS 1 — Couleur stock : envoyer barres COMPLÈTES
        # FFD avec utile = barre_mm - 50mm pour compter le nombre de barres nécessaires
        par_code = {}
        for (kc, kit_nom, long_mm), qte in pieces_peinture.items():
            if kc not in par_code:
                _, barre_mm = KITS_NEOSCENICA[kc]
                par_code[kc] = {'kit_nom': kit_nom, 'barre_mm': barre_mm, 'pieces': []}
            par_code[kc]['pieces'].append({'nom': f'{long_mm}mm', 'long': long_mm / 25.4, 'qte': qte})

        data_p = [["Profil", "Code", "Designation", "Barre complete", "Nb barres", "Note"]]
        for kc in sorted(par_code):
            kd = par_code[kc]
            barre_mm = kd['barre_mm']
            utile_po = (barre_mm - 50) / 25.4
            barres = _ffd(kd['pieces'], utile_po)
            nb = len(barres)
            # Signaler si une pièce seule dépasse l'utile (impossible à loger)
            max_piece_mm = max(p['long'] * 25.4 for b in barres for p in b['pieces'])
            note = "(!) piece > barre-50mm" if max_piece_mm > (barre_mm - 50) else ""
            data_p.append([_img_cell(kc), kc, kd['kit_nom'],
                           f"{barre_mm} mm ({_dvf(barre_mm/25.4)})", str(nb), note])
        y = tableau(y, data_p, [0.62*inch, 0.65*inch, 1.65*inch, 1.85*inch, 0.7*inch, 1.15*inch])
    else:
        # CAS 2 — Couleur sur mesure : longueur précise + 50mm par pièce
        data_p = [["Profil", "Code", "Designation", "Grandeur (+50mm)", "Nombre", "Coupe"]]
        for (kc, kit_nom, long_mm), qte in sorted(pieces_peinture.items()):
            long_p = long_mm + 50
            grandeur = f"{_dvf(long_p / 25.4)}  ({long_p} mm)"
            data_p.append([_img_cell(kc), kc, kit_nom, grandeur, str(qte), ""])
        y = tableau(y, data_p, [0.62*inch, 0.65*inch, 1.7*inch, 2.05*inch, 0.65*inch, 0.95*inch])
    y -= 0.3*inch

    # Note Keven
    note_h = 0.40*inch
    c.setFillColor(colors.HexColor("#FFF3CD"))
    c.rect(0.4*inch, y - note_h, w - 0.8*inch, note_h, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 9)
    c.drawString(0.55*inch, y - 0.17*inch, "Note :")
    c.setFont("Helvetica", 9)
    c.drawString(1.1*inch, y - 0.17*inch,
                 "Keven — cocher chaque profil apres la coupe avant d'envoyer a la peinture")
    y -= note_h + 0.45*inch

    # Signatures — 3 champs
    sig_y = max(y, 1.8*inch)
    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.line(0.4*inch, sig_y, 2.8*inch, sig_y)
    c.line(3.1*inch, sig_y, 5.3*inch, sig_y)
    c.line(5.6*inch, sig_y, 7.7*inch, sig_y)
    c.setFillColor(BLEU); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch,  sig_y - 0.14*inch, "Recu par le peintre — Nom + Signature")
    c.drawString(3.1*inch,  sig_y - 0.14*inch, "Date de reception")
    c.drawString(5.6*inch,  sig_y - 0.14*inch, "Date de retour prevue")
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 6 : RESTES À ENREGISTRER
    # ══════════════════════════════════════════════════════════════════════════
    if restes:
        entete("RESTES À ENREGISTRER — Néoscenica")
        y = h - 1.3*inch
        y = titre_section(y, "NOUVEAUX RESTES GÉNÉRÉS PAR CETTE PRODUCTION")
        data = [["Profil", "Longueur (pouces)", "Longueur (mm)"]]
        for nr in restes:
            data.append([nr['profil'], _dvf(nr['longueur']), str(round(nr['longueur']*25.4))])
        y = tableau(y, data, [3.5*inch, 1.8*inch, 1.9*inch])
        c.showPage()

    c.save()
    print(f"✓ Néoscenica PDF généré : {fichier}")
