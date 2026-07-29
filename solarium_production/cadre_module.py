"""
CADRE / TRAPÈZE — Module de production Solarium Pro v1
Structure identique à aika_6mm_module.py — 5 pages dans l'ordre.
Dépendances : generateur_cadre_avec_restes, cadre_approbation_v2, cadre_montage_v1

RÈGLE USINE (permanent) :
  - Zone de dessin : exploiter toute la page (géré par cadre_approbation_v2 / cadre_montage_v1)
  - Annotations/cotes sur les dessins : police ≥ 9 pt
  - Tableaux de données : FONTSIZE ≥ 10 pt (lisibilité atelier)
"""

import os, sys, re
from math import gcd, sqrt, atan, cos, sin, ceil
from datetime import date as _date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generateur_cadre_avec_restes as _calc
import cadre_approbation_v2 as _appro
import cadre_montage_v1    as _montage

PROFILS_CADRE  = ['Tube alu 2-1/2"', 'Plaque pression', 'Couvercle']
SEUIL_RESTE_PO = 6.0

# Constantes trapèze
TUBE_EXT_PO = 2.5625   # 65 mm — dimension extérieure réelle (traverse bas)
TUBE_NOM_PO = 2.5      # 2-1/2" nominal — coupes angulaires G/D
KERF_TRAP   = 0.125    # trait de scie 1/8" — montant D uniquement


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


# ─── CALCUL MUR ───────────────────────────────────────────────────────────────
def calculer_mur_cadre(mur):
    """
    mur = {nom, largeur_po, vg_po, vd_po, nb_montants, couleur_alu}
    vg_po = hauteur gauche, vd_po = hauteur droite (identiques → rectangulaire).
    Retourne dict enrichi avec pieces de coupe.
    """
    L_po    = mur['largeur_po']
    VG      = mur.get('vg_po') or mur.get('hauteur_po', 0)
    VD      = mur.get('vd_po') or VG
    nb_mont = max(int(mur.get('nb_montants', 2)), 2)
    nb_sec  = nb_mont - 1
    est_trap = abs(VG - VD) > 0.01

    if est_trap:
        angle    = atan((VG - VD) / L_po) if L_po > 0 else 0.0
        cos_a    = cos(angle); sin_a = sin(angle)
        hyp      = sqrt(L_po**2 + (VG - VD)**2)
        # Côté le plus long de chaque coupe en biseau (face externe/haute de chaque montant)
        # mont_g : face gauche (x=0), la plus haute du montant gauche
        # mont_d : face interne (x=L-tw), la plus haute du montant droit
        #          = VD + TUBE_NOM*tan_a - TUBE_NOM/cos_a  (sans kerf — kerf géré par FFD)
        mont_g   = VG - TUBE_NOM_PO / cos_a
        mont_d   = VD - TUBE_NOM_PO * (1 - sin_a) / cos_a   # long side (pas de kerf ici)
        trav_bas = max((L_po - nb_mont * TUBE_EXT_PO) / nb_sec, 0) if nb_sec > 0 else 0

        pieces = [
            {'nom': 'Traverse du haut (hypoténuse)', 'longueur_dec': hyp,     'qte': 1},
            {'nom': 'Montant vertical gauche',        'longueur_dec': mont_g,  'qte': 1},
            {'nom': 'Montant vertical droit',         'longueur_dec': mont_d,  'qte': 1},
        ]
        if nb_mont > 2:
            # Montants internes : hauteur interpolée - TUBE_NOM/cos(angle)
            from collections import Counter
            int_cuts = []
            for i in range(1, nb_mont - 1):
                frac = i / (nb_mont - 1)
                H_i  = VG - frac * (VG - VD)
                int_cuts.append(round(H_i - TUBE_NOM_PO / cos_a, 4))
            for cut, qty in sorted(Counter(int_cuts).items(), reverse=True):
                pieces.append({'nom': f'Montant interne', 'longueur_dec': cut, 'qte': qty})
        pieces.append({'nom': 'Traverses du bas', 'longueur_dec': trav_bas, 'qte': nb_sec})
    else:
        H_po     = VG
        trav_bas = max((L_po - nb_mont * 2.5) / nb_sec, 0) if nb_sec > 0 else 0
        pieces = [
            {'nom': 'Traverse du haut',   'longueur_dec': L_po,       'qte': 1},
            {'nom': 'Montants verticaux', 'longueur_dec': H_po - 2.5, 'qte': nb_mont},
            {'nom': 'Traverses du bas',   'longueur_dec': trav_bas,   'qte': nb_sec},
        ]

    return {
        'nom':         mur.get('nom', ''),
        'largeur_po':  L_po,
        'vg_po':       VG,    'vd_po':       VD,
        'hauteur_po':  max(VG, VD),
        'largeur_mm':  round(L_po * 25.4),
        'vg_mm':       round(VG * 25.4),   'vd_mm':  round(VD * 25.4),
        'hauteur_mm':  round(max(VG, VD) * 25.4),
        'nb_montants': nb_mont, 'nb_sections': nb_sec,
        'est_trapeze': est_trap,
        'couleur_alu': mur.get('couleur_alu', ''),
        'pieces':      pieces,
    }


# ─── GÉNÉRATION PDF ───────────────────────────────────────────────────────────
def generer_pdf_cadre(params, fichier):
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
        m['largeur_po']  = _fvd(m.get('largeur', '0'))
        # Support VG/VD (trapèze) ou hauteur simple (rectangulaire)
        vg = _fvd(m.get('vg', '0')) or _fvd(m.get('hauteur', '0'))
        vd = _fvd(m.get('vd', '0')) or vg
        m['vg_po']       = vg
        m['vd_po']       = vd
        m['hauteur_po']  = max(vg, vd)
        m['nb_montants'] = int(m.get('nb_montants', 2))
        m['couleur_alu'] = couleur
        if m['largeur_po'] > 0 and m['vg_po'] > 0:
            murs_calc.append(calculer_mur_cadre(m))

    # ── Phase 1 : calculer les pièces par mur (sans FFD encore) ─────────────
    for mc in murs_calc:
        if mc.get('est_trapeze'):
            mc['pieces_calc'] = mc['pieces']
        else:
            mc['pieces_calc'] = _calc.calculer_pieces(
                str(mc['largeur_po']), str(mc['hauteur_po']), mc['nb_montants']
            )

    # ── Phase 2 : FFD combiné — TOUTES les pièces de TOUS les murs ensemble ──
    # Un seul appel optimiser_coupes par profil+couleur (pas un par mur)
    combined_contenants = {}   # {profil: contenants_list}
    tous_nr = []
    tous_rc = []
    for profil in PROFILS_CADRE:
        all_pieces_p = []
        for mc in murs_calc:
            for p in mc['pieces_calc']:
                all_pieces_p.append({
                    'nom':         f"{p['nom']} [{mc['nom']}]",
                    'longueur_dec': p['longueur_dec'],
                    'qte':         p['qte'],
                })
        cont, rc, nr = _calc.optimiser_coupes(all_pieces_p, profil, couleur, verbose=False)
        combined_contenants[profil] = cont
        tous_rc.extend(rc)
        tous_nr.extend(nr)

    if tous_rc:
        _calc.marquer_restes_utilises(tous_rc, no_proj)
    if tous_nr:
        _calc.ajouter_nouveaux_restes(tous_nr, no_proj, client, couleur)

    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def entete(titre_doc):
        c.setFillColor(BLEU)
        c.rect(0, h-1.1*inch, w, 1.1*inch, fill=True, stroke=False)
        c.setFillColor(OR); c.setFont("Helvetica-Bold", 13)
        c.drawString(0.4*inch, h-0.38*inch, "SOLARIUM PRO — CADRE / TRAPÈZE")
        c.setFillColor(colors.white); c.setFont("Helvetica", 8)
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
        c.rect(0.4*inch, y-0.22*inch, w-0.8*inch, 0.22*inch, fill=True, stroke=False)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 9)
        c.drawString(0.5*inch, y-0.14*inch, texte)
        return y - 0.36*inch

    def bandeau_mur(y, mc):
        haut = 0.26*inch
        c.setFillColor(GRIS2)
        c.rect(0.4*inch, y-haut, w-0.8*inch, haut, fill=True, stroke=False)
        c.setFillColor(BLEU); c.setFont("Helvetica", 9)
        if mc.get('est_trapeze'):
            dim_str = (f"L = {_dvf(mc['largeur_po'])} ({mc['largeur_mm']} mm)  "
                       f"VG = {_dvf(mc['vg_po'])} ({mc['vg_mm']} mm)  "
                       f"VD = {_dvf(mc['vd_po'])} ({mc['vd_mm']} mm)  "
                       f"TRAPÈZE  —  {mc['nb_montants']} montants")
        else:
            dim_str = (f"L = {_dvf(mc['largeur_po'])} ({mc['largeur_mm']} mm)  "
                       f"H = {_dvf(mc['hauteur_po'])} ({mc['hauteur_mm']} mm)  "
                       f"{mc['nb_montants']} montants — {mc['nb_sections']} sections")
        c.drawString(0.5*inch, y-0.16*inch, f"{mc['nom']}  —  {dim_str}")
        return y - haut - 0.08*inch

    def tableau(y, data, cols):
        t = Table(data, colWidths=cols)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  BLEU),
            ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
            ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, GRIS]),
            ("GRID",           (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",          (1,0),(-1,-1), "CENTER"),
            ("TOPPADDING",     (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
        ]))
        _, th = t.wrap(0, 0)
        if y - th < 0.9*inch:
            c.showPage(); entete("(suite)"); y = h-1.3*inch
        t.drawOn(c, 0.4*inch, y-th)
        return y - th - 0.2*inch

    def contenants_to_barres(contenants):
        barres = []
        for i, cont in enumerate(contenants):
            if not cont.get('pieces'): continue
            barres.append({
                'num':     i+1,
                'pieces':  [{'long': p['longueur']} for p in cont['pieces']],
                'utilise': cont.get('utilise_dec', 0),
                'reste':   cont.get('reste_final', 0),
            })
        return barres

    def table_coupes(y, barres):
        data = [["#", "Découpes (pouces)", "Utilisé", "Reste"]]
        for b in barres:
            dec  = " + ".join(_dvf(p["long"]) for p in b["pieces"])
            rest = _dvf(b["reste"]) if b["reste"] >= SEUIL_RESTE_PO else f'{_dvf(b["reste"])} (!)'
            data.append([f"#{b['num']}", dec, _dvf(b["utilise"]), rest])
        return tableau(y, data, [0.4*inch, 4.9*inch, 1.2*inch, 1.2*inch])

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1+ : APPROBATION CLIENT
    # ══════════════════════════════════════════════════════════════════════════
    for mc in murs_calc:
        mcd = {
            'nom':         mc['nom'],
            'largeur_po':  mc['largeur_po'],  'hauteur_po':  mc['hauteur_po'],
            'largeur_mm':  mc['largeur_mm'],  'hauteur_mm':  mc['hauteur_mm'],
            'nb_montants': mc['nb_montants'],
            'est_trapeze': mc.get('est_trapeze', False),
            'vg_po':       mc.get('vg_po', mc['hauteur_po']),
            'vd_po':       mc.get('vd_po', mc['hauteur_po']),
            'vg_mm':       mc.get('vg_mm', mc['hauteur_mm']),
            'vd_mm':       mc.get('vd_mm', mc['hauteur_mm']),
        }
        _appro.page_approbation_cadre(
            c, mcd, w, h, inch, colors,
            no_proj, client, couleur, str(_date.today())
        )
        c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : DESSIN DE MONTAGE
    # ══════════════════════════════════════════════════════════════════════════
    entete("DESSIN DE MONTAGE — Cadre / Trapèze")
    y = h - 1.3*inch
    for mc in murs_calc:
        mcd = {
            'nom':         mc['nom'],
            'largeur_po':  mc['largeur_po'],  'hauteur_po':  mc['hauteur_po'],
            'largeur_mm':  mc['largeur_mm'],  'hauteur_mm':  mc['hauteur_mm'],
            'nb_montants': mc['nb_montants'],
            'est_trapeze': mc.get('est_trapeze', False),
            'vg_po':       mc.get('vg_po', mc['hauteur_po']),
            'vd_po':       mc.get('vd_po', mc['hauteur_po']),
            'vg_mm':       mc.get('vg_mm', mc['hauteur_mm']),
            'vd_mm':       mc.get('vd_mm', mc['hauteur_mm']),
        }
        y = bandeau_mur(y, mc)
        y = _montage.dessiner_cadre_montage(c, y, mcd, w, h, inch, colors)
        y -= 0.15*inch
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : RÉCAPITULATIF DES PIÈCES
    # ══════════════════════════════════════════════════════════════════════════
    entete("RÉCAPITULATIF DES PIÈCES — Cadre / Trapèze")
    y = h - 1.3*inch
    for mc in murs_calc:
        y = bandeau_mur(y, mc)
        data = [["Pièce", "Longueur (pouces)", "Longueur (mm)", "Qté"]]
        for p in mc['pieces_calc']:
            data.append([p["nom"], _dvf(p["longueur_dec"]),
                         str(round(p["longueur_dec"]*25.4)), str(p["qte"])])
        y = tableau(y, data, [3.1*inch, 1.8*inch, 1.5*inch, 1.3*inch])
    if notes.strip():
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.rect(0.4*inch, y-0.55*inch, w-0.8*inch, 0.55*inch, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#856404")); c.setFont("Helvetica-Bold", 8)
        c.drawString(0.5*inch, y-0.16*inch, "NOTES :")
        c.setFont("Helvetica", 8)
        c.drawString(0.5*inch, y-0.38*inch, notes[:130])
    c.showPage()

    # ── Palette couleurs par mur ──────────────────────────────────────────────
    MUR_PALETTE = ["#C8640A","#1565C0","#2E7D32","#B71C1C","#6A1B9A","#00695C"]
    mur_noms = [mc['nom'] for mc in murs_calc]
    mur_color_map = {nom: MUR_PALETTE[i % len(MUR_PALETTE)] for i, nom in enumerate(mur_noms)}

    # ══════════════════════════════════════════════════════════════════════════
    # PAGES : LISTES DE COUPE
    # ══════════════════════════════════════════════════════════════════════════
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    p_style = ParagraphStyle('dec', fontName='Helvetica', fontSize=9, leading=11)

    import re as _re
    def _wall_from_nom(nom):
        """Extrait le nom du mur depuis 'Pièce [Nom Mur]'."""
        m = _re.search(r'\[(.+)\]$', nom)
        return m.group(1) if m else ''

    def contenants_to_barres_color(contenants):
        barres = []
        for i, cont in enumerate(contenants):
            if not cont.get('pieces'): continue
            barres.append({
                'num':     i + 1,
                'pieces':  [{'long': p['longueur'], 'nom': p['nom']} for p in cont['pieces']],
                'utilise': cont.get('utilise_dec', 0),
                'reste':   cont.get('reste_final', 0),
            })
        return barres

    def table_coupes_color(y, barres):
        from reportlab.platypus import Paragraph
        data = [["#", "Découpes (pouces)", "Utilisé", "Reste"]]
        for b in barres:
            pieces_html = []
            for p in b['pieces']:
                wall = _wall_from_nom(p['nom'])
                col  = mur_color_map.get(wall, '#333333')
                pieces_html.append(
                    f'<font color="{col}"><b>{_dvf(p["long"])}</b></font>'
                    + (f' <font color="{col}" size="7">[{wall}]</font>' if wall and len(mur_noms) > 1 else '')
                )
            dec_cell = Paragraph(' + '.join(pieces_html), p_style)
            rest = _dvf(b["reste"]) if b["reste"] >= SEUIL_RESTE_PO else f'{_dvf(b["reste"])} (!)'
            data.append([f"#{b['num']}", dec_cell, _dvf(b["utilise"]), rest])

        t = Table(data, colWidths=[0.4*inch, 4.9*inch, 1.2*inch, 1.2*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  BLEU),
            ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
            ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, GRIS]),
            ("GRID",           (0,0),(-1,-1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",          (0,0),(0,-1),  "CENTER"),
            ("ALIGN",          (2,0),(-1,-1), "CENTER"),
            ("TOPPADDING",     (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ]))
        _, th = t.wrap(0, 0)
        if y - th < 0.9*inch:
            c.showPage(); entete("(suite)"); y = h - 1.3*inch
        t.drawOn(c, 0.4*inch, y - th)
        return y - th - 0.2*inch

    for profil in PROFILS_CADRE:
        all_barres = contenants_to_barres_color(combined_contenants[profil])
        if not all_barres:
            continue
        for i, b in enumerate(all_barres):
            b['num'] = i + 1
        entete(f'LISTE DE COUPE — {profil}  (barres de 240")')
        y = h - 1.3*inch

        # Légende couleurs → murs (si multi-murs)
        if len(mur_noms) > 1:
            c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.HexColor("#333333"))
            c.drawString(0.45*inch, y, "Légende :")
            lx = 1.2*inch
            for nom in mur_noms:
                col = mur_color_map[nom]
                c.setFillColor(colors.HexColor(col))
                c.roundRect(lx, y - 0.02*inch, 0.11*inch, 0.13*inch, 2, fill=True, stroke=False)
                c.setFillColor(colors.HexColor("#222222")); c.setFont("Helvetica", 7.5)
                c.drawString(lx + 0.14*inch, y, nom)
                lx += c.stringWidth(nom, "Helvetica", 7.5) + 0.30*inch
            y -= 0.22*inch

        y = titre_section(y,
            f'{profil}  —  {couleur}  —  '
            f'{len(all_barres)} barre{"s" if len(all_barres) > 1 else ""}')
        y = table_coupes_color(y, all_barres)
        c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : QUINCAILLERIE — DÉCAISSAGE INVENTAIRE
    # ══════════════════════════════════════════════════════════════════════════
    entete("QUINCAILLERIE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, "DÉCAISSAGE INVENTAIRE — QUINCAILLERIE")

    # Spigots : 2 par montant extrémité, 3 par montant central
    total_spigots = 0
    for mc in murs_calc:
        nb = mc['nb_montants']
        total_spigots += 2 * 2 + 3 * max(0, nb - 2)

    # VA10 et joint caoutchouc : calculés par pièce de coupe (tous profils)
    # Chaque pièce est découpée dans les 3 profils (tube, plaque, couvercle)
    total_va10    = 0
    total_joint_m = 0.0
    for mc in murs_calc:
        for p in mc['pieces_calc']:
            l = p['longueur_dec']
            total_va10    += (ceil(l / 12) + 1) * p['qte'] * 3   # ×3 profils
            total_joint_m += (l * 2 + 2) * p['qte'] * 3 / 12     # pi → m (*0.0254*12 = *pi)

    # Nombre de barres utilisées par profil (depuis combined_contenants)
    def n_barres(profil_key):
        return sum(1 for cont in combined_contenants[profil_key] if cont.get('pieces'))

    data_q = [["Code", "Description", "Qté", "Unité"]]
    data_q.append(["SOLP-MEN350-L240", 'Tube aluminium 2-1/2"',  n_barres('Tube alu 2-1/2"'), "barres"])
    data_q.append(["SOLP-PPT250-L240", "Plaque pression 2-1/2\"", n_barres('Plaque pression'), "barres"])
    data_q.append(["SOLP-CAP87-L240",  "Couvercle 2-1/2\"",       n_barres('Couvercle'),      "barres"])
    data_q.append(["SOLP-PRF15-L240",  "Spigot",                   total_spigots,              "pcs"])
    data_q.append(["VA10",             "Vis VA10",                  total_va10,                 "pcs"])
    data_q.append(["VS30",             "Vis VS30",                  total_spigots * 2,          "pcs"])
    data_q.append(["PYF-FL2791-03",    "Joint caoutchouc",          f"{total_joint_m:.1f}",     "pi"])
    y = tableau(y, data_q, [2.2*inch, 2.6*inch, 1.0*inch, 1.0*inch])
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : VITRAGE
    # ══════════════════════════════════════════════════════════════════════════
    entete("VITRAGE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, "LISTE DE VERRE — 6mm Trempé")
    data_v = [["Mur", "Largeur verre (po)", "Hauteur (po)", "Largeur (mm)", "Hauteur (mm)", "Qté"]]
    for mc in murs_calc:
        if mc.get('est_trapeze'):
            # Trapèze : 1 panneau L × VG / VD
            data_v.append([
                mc['nom'],
                _dvf(mc['largeur_po']),
                f"G:{_dvf(mc['vg_po'])} / D:{_dvf(mc['vd_po'])}",
                str(mc['largeur_mm']),
                f"G:{mc['vg_mm']} / D:{mc['vd_mm']}",
                "1",
            ])
        else:
            # Cadre rectangulaire : nb_sections panneaux
            nb_sec = mc['nb_sections']
            trav_bas = next(
                (p['longueur_dec'] for p in mc['pieces_calc'] if 'bas' in p['nom'].lower()),
                mc['largeur_po'] / max(nb_sec, 1)
            )
            data_v.append([
                mc['nom'],
                _dvf(trav_bas),
                _dvf(mc['hauteur_po']),
                str(round(trav_bas * 25.4)),
                str(mc['hauteur_mm']),
                str(nb_sec),
            ])
    y = tableau(y, data_v, [1.0*inch, 1.3*inch, 1.5*inch, 1.2*inch, 1.5*inch, 0.7*inch])
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : FICHE PEINTURE
    # ══════════════════════════════════════════════════════════════════════════
    entete("FICHE PEINTURE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, f"BARRES À ENVOYER EN PEINTURE — {couleur}")

    # Regrouper toutes les pièces à peindre par profil + longueur (depuis combined_contenants)
    pieces_peinture = {}
    for profil in PROFILS_CADRE:
        for cont in combined_contenants[profil]:
            if not cont.get('pieces'):
                continue
            l_po = round(cont.get('longueur_dec', 240), 2)
            key = (profil, l_po)
            pieces_peinture[key] = pieces_peinture.get(key, 0) + 1

    data_p = [["Profil", "Longueur (pouces)", "Longueur (mm)", "Qté", "Couleur"]]
    for (profil, l_po), qte in sorted(pieces_peinture.items()):
        data_p.append([profil, _dvf(l_po), str(round(l_po * 25.4)), str(qte), couleur])
    y = tableau(y, data_p, [2.2*inch, 1.4*inch, 1.4*inch, 0.8*inch, 1.4*inch])

    y -= 0.25*inch
    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.line(0.4*inch, 1.8*inch, 3.5*inch, 1.8*inch)
    c.line(4.2*inch, 1.8*inch, 7.7*inch, 1.8*inch)
    c.setFillColor(BLEU); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch, 1.65*inch, "Approuvé peinture — Signature")
    c.drawString(4.2*inch, 1.65*inch, "Reçu par la peinture — Date")
    c.showPage()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : RESTES À ENREGISTRER
    # ══════════════════════════════════════════════════════════════════════════
    if tous_nr:
        entete("RESTES À ENREGISTRER — Cadre / Trapèze")
        y = h - 1.3*inch
        y = titre_section(y, "NOUVEAUX RESTES GÉNÉRÉS PAR CETTE PRODUCTION")
        data = [["Profil", "Longueur (pouces)", "Longueur (mm)", "Notes"]]
        for nr in tous_nr:
            data.append([
                nr['type_profil'],
                _dvf(nr['longueur']),
                str(round(nr['longueur'] * 25.4)),
                nr.get('notes', ''),
            ])
        y = tableau(y, data, [2.0*inch, 1.5*inch, 1.5*inch, 2.8*inch])
        c.showPage()

    c.save()
    print(f"✓ Cadre / Trapèze PDF généré : {fichier}")
