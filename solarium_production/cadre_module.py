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

_CADRE_IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images_pieces')
CADRE_IMAGES = {
    'Tube alu 2-1/2"': os.path.join(_CADRE_IMG_DIR, 'profil_tube_25x100.jpeg'),
}

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
def generer_pdf_cadre(params, fichier, mode=None):
    """
    mode=None ou 'all'         → dossier complet (approbation + production + peinture + verre)
    mode='approbation'         → seulement page(s) approbation client
    mode='peinture'            → seulement fiche peinture
    mode='commande_verre'      → seulement bon de commande verre IGP
    """
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

    # ── Phase 2 : FFD combiné — seulement si nécessaire pour le mode ─────────
    need_ffd = mode in (None, 'all', 'peinture') or mode is None
    combined_contenants = {}
    tous_nr = []; tous_rc = []
    if need_ffd:
        for profil in PROFILS_CADRE:
            all_pieces_p = []
            for mc in murs_calc:
                for p in mc['pieces_calc']:
                    all_pieces_p.append({
                        'nom':          f"{p['nom']} [{mc['nom']}]",
                        'longueur_dec': p['longueur_dec'],
                        'qte':          p['qte'],
                    })
            cont, rc, nr = _calc.optimiser_coupes(all_pieces_p, profil, couleur, verbose=False)
            combined_contenants[profil] = cont
            tous_rc.extend(rc); tous_nr.extend(nr)
        if tous_rc:
            _calc.marquer_restes_utilises(tous_rc, no_proj)
        if tous_nr:
            _calc.ajouter_nouveaux_restes(tous_nr, no_proj, client, couleur)

    w, h = letter
    c = canvas.Canvas(fichier, pagesize=letter)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def entete(titre_doc):
        NOIR_HDR = colors.HexColor("#111111")
        c.setFillColor(NOIR_HDR)
        c.rect(0, h - 1.10*inch, w, 1.10*inch, fill=True, stroke=False)
        # Titre produit centré, grand, or
        c.setFillColor(OR); c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(w/2, h - 0.38*inch, "SOLARIUM PRO")
        # Sous-titre produit en petit
        c.setFillColor(colors.white); c.setFont("Helvetica", 8)
        c.drawCentredString(w/2, h - 0.56*inch, "CADRE / TRAPÈZE  ·  CONCEPTION  ·  FABRICATION")
        # Titre document
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(w/2, h - 0.74*inch, titre_doc)
        # Info projet à gauche, date à droite
        c.setFont("Helvetica", 7.5)
        info = f"No: {no_proj}  |  Client: {client}  |  Couleur: {couleur}"
        c.drawString(0.35*inch, h - 0.90*inch, info)
        c.drawRightString(w - 0.35*inch, h - 0.90*inch, str(_date.today()))
        # Filet or en bas de l'en-tête
        c.setFillColor(OR)
        c.rect(0, h - 1.12*inch, w, 0.05*inch, fill=True, stroke=False)
        # Pied de page or
        c.setFillColor(OR)
        c.rect(0, 0.28*inch, w, 0.22*inch, fill=True, stroke=False)
        c.setFillColor(NOIR_HDR); c.setFont("Helvetica", 7)
        c.drawCentredString(w/2, 0.37*inch,
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

    def _img_cadre(profil):
        from reportlab.platypus import Image as RLImage
        p = CADRE_IMAGES.get(profil)
        if p and os.path.exists(p):
            return RLImage(p, width=0.52*inch, height=0.38*inch)
        return ""

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

    def _mcd(mc):
        """Construit le dict mur_calc enrichi pour les modules de dessin."""
        return {
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

    date_str = str(_date.today())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1+ : APPROBATION CLIENT
    # ══════════════════════════════════════════════════════════════════════════
    if mode in (None, 'all', 'approbation'):
        trap_list  = [mc for mc in murs_calc if mc.get('est_trapeze')]
        rect_list  = [mc for mc in murs_calc if not mc.get('est_trapeze')]

        # 2 trapèzes → page miroir côte à côte
        if len(trap_list) == 2:
            _appro.page_approbation_2_trapezes(
                c, _mcd(trap_list[0]), _mcd(trap_list[1]),
                w, h, inch, colors,
                no_proj, client, couleur, date_str
            )
            c.showPage()
        else:
            for mc in trap_list:
                _appro.page_approbation_cadre(
                    c, _mcd(mc), w, h, inch, colors,
                    no_proj, client, couleur, date_str
                )
                c.showPage()

        # Cadres rectangulaires — une page par mur
        for mc in rect_list:
            _appro.page_approbation_cadre(
                c, _mcd(mc), w, h, inch, colors,
                no_proj, client, couleur, date_str
            )
            c.showPage()

        if mode == 'approbation':
            c.save(); return

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE : DESSIN DE MONTAGE
    # ══════════════════════════════════════════════════════════════════════════
    if mode in (None, 'all'):
        trap_list_m = [mc for mc in murs_calc if mc.get('est_trapeze')]
        rect_list_m = [mc for mc in murs_calc if not mc.get('est_trapeze')]

        if len(trap_list_m) == 2:
            # 2 trapèzes → dessin côte à côte sur une seule page
            entete("DESSIN DE MONTAGE — Cadre Trapèze (2 pignons)")
            _montage.dessiner_2_trapezes_cote_a_cote(
                c, _mcd(trap_list_m[0]), _mcd(trap_list_m[1]), w, h, inch, colors
            )
            c.showPage()
        elif trap_list_m:
            entete("DESSIN DE MONTAGE — Cadre / Trapèze")
            y = h - 1.3*inch
            for mc in trap_list_m:
                y = bandeau_mur(y, mc)
                y = _montage.dessiner_cadre_montage(c, y, _mcd(mc), w, h, inch, colors)
                y -= 0.15*inch
            c.showPage()

        if rect_list_m:
            entete("DESSIN DE MONTAGE — Cadre / Trapèze")
            y = h - 1.3*inch
            for mc in rect_list_m:
                y = bandeau_mur(y, mc)
                y = _montage.dessiner_cadre_montage(c, y, _mcd(mc), w, h, inch, colors)
                y -= 0.15*inch
            c.showPage()

    # ── Palette couleurs par mur (utilisée dans listes de coupe) ────────────
    MUR_PALETTE = ["#C8640A","#1565C0","#2E7D32","#B71C1C","#6A1B9A","#00695C"]
    mur_noms = [mc['nom'] for mc in murs_calc]
    mur_color_map = {nom: MUR_PALETTE[i % len(MUR_PALETTE)] for i, nom in enumerate(mur_noms)}

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 'commande_verre' — Bon de commande verre IGP (Cadre / Trapèze)
    # Format : en-tête + grille de dessins sur UNE SEULE PAGE (max 3/rangée)
    # ══════════════════════════════════════════════════════════════════════════
    if mode == 'commande_verre':
        from reportlab.lib import colors as cl
        from math import sqrt as _sq_v
        NOIR   = cl.HexColor("#000000")
        BLEU_L = cl.HexColor("#0070C0")
        MAUVE  = cl.HexColor("#C299D4")
        JAUNE  = cl.HexColor("#F5E642")
        LOGO_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo_Pro_Horizontal.png")

        # ── Helpers flèches ───────────────────────────────────────────────────
        def _arh(x1v, x2v, ya, lbl, fs=7):
            sz = 3.5
            c.setLineWidth(0.4); c.setFillColor(NOIR); c.setStrokeColor(NOIR)
            c.line(x1v, ya, x2v, ya)
            for xp, d in [(x1v, 1), (x2v, -1)]:
                c.line(xp, ya, xp+d*sz, ya+sz*0.45)
                c.line(xp, ya, xp+d*sz, ya-sz*0.45)
            c.setFont("Helvetica", fs)
            c.drawCentredString((x1v+x2v)/2, ya - fs - 1.5, lbl)

        def _arv(xa, y1v, y2v, lbl, fs=7):
            sz = 3.5
            c.setLineWidth(0.4); c.setFillColor(NOIR); c.setStrokeColor(NOIR)
            c.line(xa, y1v, xa, y2v)
            for yp, d in [(y1v, 1), (y2v, -1)]:
                c.line(xa, yp, xa+sz*0.45, yp+d*sz)
                c.line(xa, yp, xa-sz*0.45, yp+d*sz)
            c.saveState(); c.translate(xa+13, (y1v+y2v)/2); c.rotate(90)
            c.setFont("Helvetica", fs); c.drawCentredString(0, 0, lbl); c.restoreState()

        # ── Construire liste de panneaux ──────────────────────────────────────
        panneaux = []
        for mc in murs_calc:
            nom_m = mc['nom']
            if mc.get('est_trapeze'):
                panneaux.append({
                    'nom': f"{nom_m} #1", 'type': 'trap',
                    'L_mm': mc['largeur_mm'],
                    'VG_mm': mc.get('vg_mm', mc['hauteur_mm']),
                    'VD_mm': mc.get('vd_mm', mc['hauteur_mm']),
                })
            else:
                nb_sec = mc['nb_sections']
                trav_bas_po = next(
                    (pp['longueur_dec'] for pp in mc['pieces_calc'] if 'bas' in pp['nom'].lower()),
                    mc['largeur_po'] / max(nb_sec, 1)
                )
                for s in range(nb_sec):
                    panneaux.append({
                        'nom': f"{nom_m} #{s+1}", 'type': 'rect',
                        'L_mm': round(trav_bas_po * 25.4),
                        'H_mm': mc['hauteur_mm'],
                    })

        total_pan = len(panneaux)

        # ── EN-TÊTE PAGE ─────────────────────────────────────────────────────
        HDR_Y = h - 1.20*inch
        if os.path.exists(LOGO_P):
            c.drawImage(LOGO_P, 0.45*inch, HDR_Y + 0.10*inch, width=2.20*inch,
                        preserveAspectRatio=True, mask='auto')
        c.setFont("Helvetica", 8.5); c.setFillColor(NOIR)
        c.drawRightString(w - 0.45*inch, HDR_Y + 0.66*inch, "450-956-4330")
        c.setFillColor(BLEU_L)
        c.drawRightString(w - 0.45*inch, HDR_Y + 0.46*inch, "crainville@solariumpro.ca")
        c.setFillColor(NOIR)
        c.drawRightString(w - 0.45*inch, HDR_Y + 0.26*inch, "Bureau : 433, rue Boivin Granby")
        c.drawRightString(w - 0.45*inch, HDR_Y + 0.06*inch, "Usine : 495, rue Edouard, Granby")

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w/2, h - 1.52*inch, "Bon de commande — Verre Cadre / Trapèze")

        y_hdr = h - 1.88*inch
        c.setFont("Helvetica", 9.5)
        c.drawString(0.45*inch, y_hdr, f"Job :  {no_proj}   |   Client :  {client}")
        c.drawRightString(w - 0.45*inch, y_hdr, f"Date :  {_date.today().strftime('%d %B %Y')}")
        c.setLineWidth(0.5); c.line(0.45*inch, y_hdr - 3, w - 0.45*inch, y_hdr - 3)

        y_hdr -= 0.32*inch
        # Descriptif surlignage jaune
        desc = f"Commande de {total_pan} verre(s) 6mm trempé, poli contour 4 faces — sans perçage"
        tw_d = c.stringWidth(desc, "Helvetica-Bold", 9)
        c.setFillColor(cl.HexColor("#FFF3CD"))
        c.rect(0.45*inch - 3, y_hdr - 3, tw_d + 6, 15, fill=True, stroke=False)
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
        c.drawString(0.45*inch, y_hdr, desc)
        c.setLineWidth(0.4); c.line(0.45*inch, y_hdr - 5, w - 0.45*inch, y_hdr - 5)

        # ── GRILLE DES DESSINS (sur la même page) ─────────────────────────────
        GRID_TOP  = y_hdr - 0.20*inch
        GRID_BOT  = 1.20*inch    # espace pour signatures en bas
        GRID_H    = GRID_TOP - GRID_BOT
        MAR_G     = 0.40*inch

        nb_cols = min(3, total_pan) if total_pan > 0 else 1
        nb_rows = (total_pan + nb_cols - 1) // nb_cols
        cell_w  = (w - 2*MAR_G) / nb_cols
        cell_h  = GRID_H / nb_rows

        for idx, pan in enumerate(panneaux):
            col = idx % nb_cols
            row = idx // nb_cols
            cx0 = MAR_G + col * cell_w
            cy0 = GRID_TOP - (row + 1) * cell_h   # bas de la cellule
            cy1 = cy0 + cell_h                      # haut de la cellule

            # Marges internes de la cellule
            PAD_T = 0.28*inch   # badge mur en haut
            PAD_B = 0.30*inch   # badge qty + flèche largeur en bas
            PAD_L = 0.55*inch   # flèche VG gauche
            PAD_R = 0.55*inch   # flèche VD droite
            draw_x0 = cx0 + PAD_L
            draw_x1 = cx0 + cell_w - PAD_R
            draw_y0 = cy0 + PAD_B
            draw_y1 = cy1 - PAD_T
            dw = draw_x1 - draw_x0
            dh = draw_y1 - draw_y0

            if pan['type'] == 'trap':
                L_mm  = pan['L_mm']
                VG_mm = pan['VG_mm']
                VD_mm = pan['VD_mm']
                H_mm  = max(VG_mm, VD_mm)
                if L_mm <= 0 or H_mm <= 0:
                    continue
                sc = min(dw / L_mm, dh / H_mm) * 0.88
                gw = L_mm * sc; gh_vg = VG_mm * sc; gh_vd = VD_mm * sc
                gx0 = draw_x0 + (dw - gw) / 2
                gx1 = gx0 + gw
                gy0 = draw_y0 + (dh - max(gh_vg, gh_vd)) / 2
                gy_vg = gy0 + gh_vg; gy_vd = gy0 + gh_vd
                c.setFillColor(colors.white); c.setStrokeColor(NOIR); c.setLineWidth(0.9)
                p = c.beginPath()
                p.moveTo(gx0, gy0); p.lineTo(gx1, gy0)
                p.lineTo(gx1, gy_vd); p.lineTo(gx0, gy_vg); p.close()
                c.drawPath(p, fill=True, stroke=True)
                # Cotes
                c.setFillColor(NOIR); c.setStrokeColor(NOIR)
                _arh(gx0, gx1, gy0 - 0.20*inch, f"L±0.5   {L_mm}mm")
                _arv(gx1 + 0.30*inch, gy0, gy_vg, f"VG±0.5  {VG_mm}mm")
                if VD_mm != VG_mm:
                    _arv(gx0 - 0.30*inch, gy0, gy_vd, f"VD±0.5  {VD_mm}mm")
            else:
                L_mm = pan['L_mm']; H_mm = pan['H_mm']
                if L_mm <= 0 or H_mm <= 0:
                    continue
                sc = min(dw / L_mm, dh / H_mm) * 0.88
                gw = L_mm * sc; gh = H_mm * sc
                gx0 = draw_x0 + (dw - gw) / 2
                gy0 = draw_y0 + (dh - gh) / 2
                gx1 = gx0 + gw; gy1 = gy0 + gh
                c.setFillColor(colors.white); c.setStrokeColor(NOIR); c.setLineWidth(0.9)
                c.rect(gx0, gy0, gw, gh, fill=True, stroke=True)
                c.setFillColor(NOIR); c.setStrokeColor(NOIR)
                _arh(gx0, gx1, gy0 - 0.20*inch, f"L±0.5   {L_mm}mm")
                _arv(gx1 + 0.30*inch, gy0, gy1, f"H±0.5   {H_mm}mm")

            # Badge mur (mauve, en haut de cellule)
            bw = max(0.95*inch, len(pan['nom']) * 0.072*inch); bh = 0.24*inch
            bx = cx0 + (cell_w - bw) / 2; by = cy1 - bh - 0.04*inch
            c.setFillColor(MAUVE); c.roundRect(bx, by, bw, bh, 3, fill=True, stroke=False)
            c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(bx + bw/2, by + 7, pan['nom'])

            # Badge quantité (jaune, en bas de cellule)
            qbw = 0.40*inch; qbh = 0.24*inch
            qbx = cx0 + (cell_w - qbw) / 2; qby = cy0 + 0.04*inch
            c.setFillColor(JAUNE); c.roundRect(qbx, qby, qbw, qbh, 3, fill=True, stroke=False)
            c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(qbx + qbw/2, qby + 7, "1x")

            # Séparateur cellule (trait léger)
            c.setStrokeColor(cl.HexColor("#DDDDDD")); c.setLineWidth(0.3)
            c.rect(cx0 + 0.02*inch, cy0, cell_w - 0.04*inch, cell_h, fill=False, stroke=True)

        # ── SIGNATURES EN BAS ─────────────────────────────────────────────────
        c.setFont("Helvetica", 9); c.setFillColor(NOIR)
        c.drawString(0.45*inch, 0.90*inch, "Date de livraison :  _______________________")
        c.drawString(0.45*inch, 0.55*inch, "Signature :  _______________________")
        c.setLineWidth(0.4); c.line(0.45*inch, GRID_BOT - 0.05*inch, w - 0.45*inch, GRID_BOT - 0.05*inch)

        c.save()
        print(f"✓ Cadre / Trapèze — Commande verre ({total_pan} panneaux) : {fichier}")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 'peinture' — Fiche peinture seule
    # ══════════════════════════════════════════════════════════════════════════
    if mode == 'peinture':
        entete(f"FICHE PEINTURE — Cadre / Trapèze")
        y = h - 1.3*inch
        y = titre_section(y, f"BARRES À ENVOYER EN PEINTURE — {couleur}")
        pieces_peinture = {}
        for profil in PROFILS_CADRE:
            for cont in combined_contenants.get(profil, []):
                if not cont.get('pieces'): continue
                l_po = round(cont.get('longueur_dec', 240), 2)
                key = (profil, l_po)
                pieces_peinture[key] = pieces_peinture.get(key, 0) + 1
        data_p = [["Profil", "Photo", "Longueur (pouces)", "Longueur (mm)", "Qté", "Couleur"]]
        for (profil, l_po), qte in sorted(pieces_peinture.items()):
            data_p.append([profil, _img_cadre(profil), _dvf(l_po), str(round(l_po*25.4)), str(qte), couleur])
        y = tableau(y, data_p, [1.8*inch, 0.62*inch, 1.3*inch, 1.1*inch, 0.7*inch, 1.1*inch])
        y -= 0.25*inch
        c.setStrokeColor(BLEU); c.setLineWidth(0.5)
        c.line(0.4*inch, 1.8*inch, 3.5*inch, 1.8*inch)
        c.line(4.2*inch, 1.8*inch, 7.7*inch, 1.8*inch)
        c.setFillColor(BLEU); c.setFont("Helvetica", 7)
        c.drawString(0.4*inch, 1.65*inch, "Approuvé peinture — Signature")
        c.drawString(4.2*inch, 1.65*inch, "Reçu par la peinture — Date")
        c.showPage()
        c.save()
        print(f"✓ Cadre / Trapèze — Fiche peinture : {fichier}")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # MODE all/None — Dossier complet
    # ══════════════════════════════════════════════════════════════════════════

    # PAGE : RÉCAPITULATIF DES PIÈCES
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

    # PAGES : LISTES DE COUPE
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    p_style = ParagraphStyle('dec', fontName='Helvetica', fontSize=9, leading=11)
    import re as _re

    def _wall_from_nom(nom):
        m2 = _re.search(r'\[(.+)\]$', nom)
        return m2.group(1) if m2 else ''

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
        all_barres = contenants_to_barres_color(combined_contenants.get(profil, []))
        if not all_barres: continue
        for i, b in enumerate(all_barres): b['num'] = i + 1
        entete(f'LISTE DE COUPE — {profil}  (barres de 240")')
        y = h - 1.3*inch
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
        y = titre_section(y, f'{profil}  —  {couleur}  —  {len(all_barres)} barre{"s" if len(all_barres) > 1 else ""}')
        y = table_coupes_color(y, all_barres)
        c.showPage()

    # PAGE : QUINCAILLERIE
    entete("QUINCAILLERIE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, "DÉCAISSAGE INVENTAIRE — QUINCAILLERIE")
    total_spigots = 0
    for mc in murs_calc:
        nb = mc['nb_montants']
        total_spigots += 2 * 2 + 3 * max(0, nb - 2)
    total_va10 = 0; total_joint_m = 0.0
    for mc in murs_calc:
        for p in mc['pieces_calc']:
            l = p['longueur_dec']
            total_va10    += (ceil(l / 12) + 1) * p['qte'] * 3
            total_joint_m += (l * 2 + 2) * p['qte'] * 3 / 12
    def n_barres(profil_key):
        return sum(1 for cont in combined_contenants.get(profil_key, []) if cont.get('pieces'))
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

    # PAGE : LISTE DE VERRE
    entete("VITRAGE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, "LISTE DE VERRE — 6mm Trempé")
    data_v = [["Mur", "Largeur (po)", "Hauteur (po)", "Largeur (mm)", "Hauteur (mm)", "Qté"]]
    for mc in murs_calc:
        if mc.get('est_trapeze'):
            data_v.append([mc['nom'], _dvf(mc['largeur_po']),
                           f"G:{_dvf(mc['vg_po'])} / D:{_dvf(mc['vd_po'])}",
                           str(mc['largeur_mm']),
                           f"G:{mc['vg_mm']} / D:{mc['vd_mm']}", "1"])
        else:
            nb_sec = mc['nb_sections']
            trav_bas = next((p['longueur_dec'] for p in mc['pieces_calc']
                             if 'bas' in p['nom'].lower()), mc['largeur_po'] / max(nb_sec, 1))
            data_v.append([mc['nom'], _dvf(trav_bas), _dvf(mc['hauteur_po']),
                           str(round(trav_bas*25.4)), str(mc['hauteur_mm']), str(nb_sec)])
    y = tableau(y, data_v, [1.0*inch, 1.3*inch, 1.5*inch, 1.2*inch, 1.5*inch, 0.7*inch])
    c.showPage()

    # PAGE : FICHE PEINTURE
    entete("FICHE PEINTURE — Cadre / Trapèze")
    y = h - 1.3*inch
    y = titre_section(y, f"BARRES À ENVOYER EN PEINTURE — {couleur}")
    pieces_peinture = {}
    for profil in PROFILS_CADRE:
        for cont in combined_contenants.get(profil, []):
            if not cont.get('pieces'): continue
            l_po = round(cont.get('longueur_dec', 240), 2)
            key = (profil, l_po)
            pieces_peinture[key] = pieces_peinture.get(key, 0) + 1
    data_p = [["Profil", "Photo", "Longueur (pouces)", "Longueur (mm)", "Qté", "Couleur"]]
    for (profil, l_po), qte in sorted(pieces_peinture.items()):
        data_p.append([profil, _img_cadre(profil), _dvf(l_po), str(round(l_po*25.4)), str(qte), couleur])
    y = tableau(y, data_p, [1.8*inch, 0.62*inch, 1.3*inch, 1.1*inch, 0.7*inch, 1.1*inch])
    y -= 0.25*inch
    c.setStrokeColor(BLEU); c.setLineWidth(0.5)
    c.line(0.4*inch, 1.8*inch, 3.5*inch, 1.8*inch)
    c.line(4.2*inch, 1.8*inch, 7.7*inch, 1.8*inch)
    c.setFillColor(BLEU); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch, 1.65*inch, "Approuvé peinture — Signature")
    c.drawString(4.2*inch, 1.65*inch, "Reçu par la peinture — Date")
    c.showPage()

    # PAGE : RESTES À ENREGISTRER
    if tous_nr:
        entete("RESTES À ENREGISTRER — Cadre / Trapèze")
        y = h - 1.3*inch
        y = titre_section(y, "NOUVEAUX RESTES GÉNÉRÉS PAR CETTE PRODUCTION")
        data = [["Profil", "Longueur (pouces)", "Longueur (mm)", "Notes"]]
        for nr in tous_nr:
            data.append([nr['type_profil'], _dvf(nr['longueur']),
                         str(round(nr['longueur']*25.4)), nr.get('notes', '')])
        y = tableau(y, data, [2.0*inch, 1.5*inch, 1.5*inch, 2.8*inch])
        c.showPage()

    c.save()
    print(f"✓ Cadre / Trapèze PDF généré : {fichier}")
