"""
Module d'approbation Cadre / Trapèze v2
Page complète style référence PDF :
  - Fond crème #FFFDE7
  - Bandeau or avec logo Solarium Pro + titre
  - Vue de face avec sections hachurées A/B/C/D
  - Tableau dimensions
  - Spécifications matériaux
  - Zone signature Céderic Rainville

Usage :
    page_approbation_cadre(c, mur_calc, w, h, inch, colors,
                           no_proj, client, couleur_alu, date_str)
"""

import os
from math import gcd as _gcd, atan as _atan, sqrt as _sqrt, degrees as _deg
from datetime import date as _date

LOGO_PNG = os.path.expanduser(
    "~/Documents/Solarium-Pro-PDFs/Logo_Pro_Horizontal.png"
)

# Couleurs des sections (fill, hachure, badge)
_SEC = [
    ("#DCE9F7", "#2B5FA5", "#2B5FA5"),   # A — bleu
    ("#FFF8CC", "#9A7200", "#B8860B"),    # B — jaune/or
    ("#D4EDDA", "#2D6A3F", "#2D6A3F"),   # C — vert
    ("#F8D7DA", "#A93226", "#C0392B"),   # D — rose/rouge
]
_LABELS = ["A", "B", "C", "D"]


def _dvf(d):
    """Pouces → fraction impériale lisible (ex: 27-1/2")."""
    if d is None:
        return ""
    s = round(d * 16) / 16
    entier = int(s); reste = s - entier
    if reste < 0.001:
        return f'{entier}"'
    num = round(reste * 16); den = 16
    g = _gcd(num, den); num //= g; den //= g
    return f'{entier}-{num}/{den}"' if entier else f'{num}/{den}"'


def _hachures(c, cl, x, y, w, h, fill_hex, hatch_hex, spacing=9):
    """Remplit un rectangle avec un fond coloré + hachures 45°."""
    c.setFillColor(cl.HexColor(fill_hex))
    c.rect(x, y, w, h, fill=True, stroke=False)
    c.saveState()
    p = c.beginPath(); p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    c.setStrokeColor(cl.HexColor(hatch_hex))
    c.setLineWidth(0.55)
    total = w + h
    n = int(total / spacing) + 2
    for i in range(n):
        xi = x - h + i * spacing
        c.line(xi, y, xi + h, y + h)
    c.restoreState()


def _fleche_h(c, cl, x1, x2, y, col_hex):
    col = cl.HexColor(col_hex)
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(0.75)
    c.line(x1, y, x2, y)
    sz = 0.052
    inch72 = 72
    for xp, d in [(x1, 1), (x2, -1)]:
        p = c.beginPath()
        p.moveTo(xp, y)
        p.lineTo(xp + d*sz*inch72, y + 0.38*sz*inch72)
        p.lineTo(xp + d*sz*inch72, y - 0.38*sz*inch72)
        p.close()
        c.drawPath(p, fill=1, stroke=0)


def _fleche_v(c, cl, x, y1, y2, col_hex):
    col = cl.HexColor(col_hex)
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(0.75)
    c.line(x, y1, x, y2)
    sz = 0.052; inch72 = 72
    for yp, d in [(y1, 1), (y2, -1)]:
        p = c.beginPath()
        p.moveTo(x, yp)
        p.lineTo(x + 0.38*sz*inch72, yp + d*sz*inch72)
        p.lineTo(x - 0.38*sz*inch72, yp + d*sz*inch72)
        p.close()
        c.drawPath(p, fill=1, stroke=0)


def page_approbation_cadre(c, mur_calc, w, h, inch,
                           colors, no_proj, client,
                           couleur_alu="", date_str=""):
    """
    Génère une page complète d'approbation pour un mur Cadre/Trapèze.
    Appeler c.showPage() après si nécessaire.
    """
    from reportlab.lib import colors as cl
    from reportlab.lib.utils import ImageReader

    # Palette
    OR_C    = cl.HexColor("#C68B00")
    OR_LT   = cl.HexColor("#FFF8E1")
    CREME   = cl.HexColor("#FFFDE7")
    BLEU_F  = cl.HexColor("#1F3864")
    BLEU_C  = cl.HexColor("#0055AA")
    GRIS_P  = cl.HexColor("#333333")
    GRIS_T  = cl.HexColor("#666666")
    GRIS_LN = cl.HexColor("#AAAAAA")
    WHT     = cl.white
    NOIR    = cl.HexColor("#1A1A1A")

    # Données mur
    nb_mont  = int(mur_calc.get('nb_montants', 2))
    nb_sec   = max(nb_mont - 1, 1)
    L_po     = mur_calc['largeur_po']
    H_po     = mur_calc['hauteur_po']
    L_mm     = mur_calc['largeur_mm']
    H_mm     = mur_calc['hauteur_mm']
    est_trap = mur_calc.get('est_trapeze', False)
    VG       = mur_calc.get('vg_po', H_po)
    VD       = mur_calc.get('vd_po', H_po)
    VG_mm    = mur_calc.get('vg_mm', H_mm)
    VD_mm    = mur_calc.get('vd_mm', H_mm)
    nom      = mur_calc.get('nom', '')
    date_s   = date_str or str(_date.today())

    # Dimensions de coupe (pour tableau — rectangulaire seulement)
    trav_bas_po = max((L_po - nb_mont * 2.5) / nb_sec, 0)
    trav_bas_mm = round(trav_bas_po * 25.4)
    mont_po     = H_po - 2.5
    mont_mm     = round(mont_po * 25.4)

    # ── BANDEAU EN-TÊTE OR ────────────────────────────────────────────────────
    HDR_H = 0.74 * inch
    c.setFillColor(OR_C)
    c.rect(0, h - HDR_H, w, HDR_H, fill=True, stroke=False)

    # Logo
    logo = os.path.expanduser(LOGO_PNG)
    if os.path.exists(logo):
        try:
            lw = 2.10 * inch; lh = 0.54 * inch
            c.drawImage(logo, 0.18*inch, h - HDR_H + (HDR_H - lh)/2,
                        width=lw, height=lh,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Titre
    nb_label   = f"{nb_sec} SECTION{'S' if nb_sec > 1 else ''}"
    titre_type = "CADRE TRAPEZE" if est_trap else "CADRE RECTANGULAIRE"
    c.setFillColor(WHT); c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2 + 0.8*inch, h - 0.29*inch,
                        f"{titre_type} — {nb_label}")
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(w/2 + 0.8*inch, h - 0.54*inch,
                        "APPROBATION CLIENT")

    # ── BANDE INFO ────────────────────────────────────────────────────────────
    INFO_H = 0.33 * inch
    iy = h - HDR_H - INFO_H
    c.setFillColor(OR_LT)
    c.rect(0, iy, w, INFO_H, fill=True, stroke=False)
    c.setStrokeColor(OR_C); c.setLineWidth(0.7)
    c.line(0, iy, w, iy)
    c.setFillColor(BLEU_F); c.setFont("Helvetica-Bold", 8)
    c.drawString(0.28*inch, iy + 0.11*inch,
        f"Projet : {no_proj}   |   Client : {client}"
        f"   |   Couleur alu : {couleur_alu}   |   Date : {date_s}")
    c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(GRIS_T)
    c.drawRightString(w - 0.28*inch, iy + 0.11*inch, nom.upper())

    # ── ZONE DESSIN ───────────────────────────────────────────────────────────
    # Réserver depuis le bas : pied + signature + table + dessin
    FOOT_H  = 0.45 * inch
    SIG_H   = 1.45 * inch
    TABLE_H = (nb_sec + 3) * 0.265*inch + 0.45*inch  # header + rows + matériaux
    SEP_H   = 0.20 * inch

    DRAW_BOT_ABS = FOOT_H + SIG_H + SEP_H + TABLE_H + SEP_H   # y absolu du bas du dessin + flèches
    ARROW_BELOW  = 0.52 * inch   # espace flèche largeur + étiquettes baies
    BADGE_ABOVE  = 0.30 * inch   # espace badges A/B/C/D au-dessus
    LABEL_ABOVE  = 0.30 * inch   # titre "LARGEUR TOTALE" au-dessus des badges

    draw_y_bot = DRAW_BOT_ABS + ARROW_BELOW
    draw_y_top_max = h - HDR_H - INFO_H - BADGE_ABOVE - LABEL_ABOVE - 0.20*inch

    DX_LEFT   = 0.90 * inch if est_trap else 0.70 * inch   # marge gauche cote VG
    DX_RIGHT  = 0.90 * inch if est_trap else 0.25 * inch   # marge droite cote VD
    avail_w   = w - DX_LEFT - DX_RIGHT
    avail_h   = draw_y_top_max - draw_y_bot

    ratio  = H_mm / L_mm
    draw_h = min(avail_h, avail_w * ratio)
    draw_h = max(draw_h, 1.10 * inch)
    draw_w = draw_h / ratio
    if draw_w > avail_w:
        draw_w = avail_w
        draw_h = draw_w * ratio

    x0    = DX_LEFT + (avail_w - draw_w) / 2
    x1    = x0 + draw_w
    y_bot = draw_y_bot
    y_top = y_bot + draw_h

    # Épaisseur tubes à l'échelle (2.5" visuellement)
    px_h = draw_w / L_po
    px_v = draw_h / H_po
    tw   = 2.5 * px_h
    th   = 2.5 * px_v

    # Helper: y sommet au dessin à la fraction horizontale f (0=gauche, 1=droite)
    def _yt(f):
        if est_trap:
            return y_bot + draw_h * (VG - f * (VG - VD)) / H_po
        return y_top

    # ── FOND BLANC ────────────────────────────────────────────────────────────
    c.setFillColor(WHT)
    if est_trap:
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=1, stroke=0)
    else:
        c.rect(x0, y_bot, draw_w, draw_h, fill=True, stroke=False)

    # ── TRAVERSE DU HAUT (dessinée en premier — les montants couvriront les coins)
    c.setFillColor(GRIS_P)
    if est_trap:
        p = c.beginPath()
        p.moveTo(x0, _yt(0) - th); p.lineTo(x1, _yt(1) - th)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=1, stroke=0)
    else:
        c.rect(x0, y_top - th, draw_w, th, fill=True, stroke=False)

    # ── TRAVERSES DU BAS ──────────────────────────────────────────────────────
    for s in range(nb_sec):
        fl   = s / (nb_mont - 1) if nb_mont > 1 else 0
        fr   = (s + 1) / (nb_mont - 1) if nb_mont > 1 else 1
        bx_l = x0 + fl * (draw_w - tw) + tw
        bx_r = x0 + fr * (draw_w - tw)
        c.setFillColor(GRIS_P)
        c.rect(bx_l, y_bot, bx_r - bx_l, th, fill=True, stroke=False)

    # ── MONTANTS VERTICAUX (dessinés en dernier pour jonctions nettes) ────────
    for m in range(nb_mont):
        frac = m / (nb_mont - 1) if nb_mont > 1 else 0
        mx   = x0 + frac * (draw_w - tw)
        mont_h = _yt(frac) - y_bot
        c.setFillColor(GRIS_P)
        c.rect(mx, y_bot, tw, mont_h, fill=True, stroke=False)

    # ── ÉTIQUETTE HYPOTÉNUSE (trapèze uniquement) ────────────────────────────
    if est_trap and L_po > 0:
        hyp_po    = _sqrt(L_po**2 + (VG - VD)**2)
        hyp_mm    = round(hyp_po * 25.4)
        ang_phys  = _deg(_atan((VG - VD) / L_po))           # angle physique (deg)
        vis_angle = _deg(_atan((_yt(1) - _yt(0)) / (x1 - x0))) if x1 > x0 else 0
        cx_d = (x0 + x1) / 2
        cy_d = (_yt(0) - th / 2 + _yt(1) - th / 2) / 2
        hyp_label = f"{hyp_mm} mm  {_dvf(hyp_po)}  {ang_phys:.1f}deg"
        c.saveState()
        c.translate(cx_d, cy_d)
        c.rotate(vis_angle)
        c.setFillColor(WHT)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(0, -2.5, hyp_label)
        c.restoreState()

    # ── CONTOUR EXTÉRIEUR ─────────────────────────────────────────────────────
    c.setStrokeColor(BLEU_F); c.setLineWidth(1.6)
    if est_trap:
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=0, stroke=1)
    else:
        c.rect(x0, y_bot, draw_w, draw_h, fill=False, stroke=True)

    # ── COTE HAUTEUR GAUCHE (VG) ──────────────────────────────────────────────
    cx_haut = x0 - 0.38 * inch
    y_top_left = _yt(0)
    c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
    c.line(x0 - 0.04*inch, y_bot, cx_haut - 0.04*inch, y_bot)
    c.line(x0 - 0.04*inch, y_top_left, cx_haut - 0.04*inch, y_top_left)
    _fleche_v(c, cl, cx_haut, y_bot, y_top_left, "#0055AA")
    lw = 0.80*inch; lh = 0.30*inch
    lx = max(0.05*inch, cx_haut - lw/2); ly = (y_bot+y_top_left)/2 - lh/2
    c.setFillColor(cl.HexColor("#D6E4F7"))
    c.roundRect(lx, ly, lw, lh, 0.025*inch, fill=True, stroke=False)
    c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
    c.roundRect(lx, ly, lw, lh, 0.025*inch, fill=False, stroke=True)
    c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(lx + lw/2, ly + lh - 0.095*inch,
                        f"V.G. {VG_mm} mm" if est_trap else f"{H_mm} mm")
    c.setFont("Helvetica", 6)
    c.drawCentredString(lx + lw/2, ly + 0.06*inch, _dvf(VG if est_trap else H_po))

    # ── COTE HAUTEUR DROITE (VD) — trapèze seulement ─────────────────────────
    if est_trap:
        y_top_right = _yt(1)
        cx_haut_r = x1 + 0.38 * inch
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x1 + 0.04*inch, y_bot, cx_haut_r + 0.04*inch, y_bot)
        c.line(x1 + 0.04*inch, y_top_right, cx_haut_r + 0.04*inch, y_top_right)
        _fleche_v(c, cl, cx_haut_r, y_bot, y_top_right, "#0055AA")
        lw2 = 0.80*inch; lh2 = 0.30*inch
        lx2 = min(w - 0.05*inch - lw2, cx_haut_r - lw2/2)
        ly2 = (y_bot + y_top_right)/2 - lh2/2
        c.setFillColor(cl.HexColor("#D6E4F7"))
        c.roundRect(lx2, ly2, lw2, lh2, 0.025*inch, fill=True, stroke=False)
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
        c.roundRect(lx2, ly2, lw2, lh2, 0.025*inch, fill=False, stroke=True)
        c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(lx2 + lw2/2, ly2 + lh2 - 0.095*inch, f"V.D. {VD_mm} mm")
        c.setFont("Helvetica", 6)
        c.drawCentredString(lx2 + lw2/2, ly2 + 0.06*inch, _dvf(VD))

    # ── COTE LARGEUR TOTALE (bas, or) ─────────────────────────────────────────
    cy_tot = y_bot - 0.26 * inch
    c.setStrokeColor(OR_C); c.setLineWidth(0.5)
    c.line(x0, y_bot - 0.04*inch, x0, cy_tot + 0.04*inch)
    c.line(x1, y_bot - 0.04*inch, x1, cy_tot + 0.04*inch)
    _fleche_h(c, cl, x0, x1, cy_tot, "#C68B00")
    lw = max(0.95*inch, 0.75*inch); lh = 0.30*inch
    lx = (x0+x1)/2 - lw/2; ly = cy_tot - lh - 0.04*inch
    c.setFillColor(cl.HexColor("#FFF4DC"))
    c.roundRect(lx, ly, lw, lh, 0.025*inch, fill=True, stroke=False)
    c.setStrokeColor(OR_C); c.setLineWidth(0.4)
    c.roundRect(lx, ly, lw, lh, 0.025*inch, fill=False, stroke=True)
    c.setFillColor(OR_C); c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString((x0+x1)/2, ly + lh - 0.095*inch, f"{L_mm} mm")
    c.setFont("Helvetica", 6)
    c.drawCentredString((x0+x1)/2, ly + 0.06*inch, _dvf(L_po))

    # ── TABLEAU DIMENSIONS ────────────────────────────────────────────────────
    # Ancrage : juste au-dessus du bloc signature
    TABLE_TOP_Y = FOOT_H + SIG_H + SEP_H + TABLE_H
    t_x   = 0.28 * inch
    t_w   = w - 0.56 * inch
    t_y   = TABLE_TOP_Y
    row_h = 0.265 * inch
    col1  = t_w * 0.18   # Section
    col2  = t_w * 0.36   # Largeur brute
    col3  = t_w * 0.46   # Largeur de coupe (traverse bas)

    # Fond tableau
    c.setFillColor(WHT)
    total_rows = nb_sec + 2  # sections + hauteur + total largeur
    c.rect(t_x, t_y - total_rows*row_h - row_h, t_w, total_rows*row_h + row_h,
           fill=True, stroke=False)

    # En-tête tableau
    c.setFillColor(OR_C)
    c.rect(t_x, t_y - row_h, t_w, row_h, fill=True, stroke=False)
    c.setFillColor(WHT); c.setFont("Helvetica-Bold", 8)
    headers = ["SECTION", "LARGEUR BRUTE PAR SECTION", "LARGEUR COUPE (TRAVERSE BAS)"]
    xs = [t_x + col1*0, t_x + col1, t_x + col1 + col2]
    ws = [col1, col2, col3]
    for i, (hdr, hx, hw) in enumerate(zip(headers, xs, ws)):
        c.drawCentredString(hx + hw/2, t_y - row_h + 0.09*inch, hdr)

    # Séparateurs verticaux en-tête
    c.setStrokeColor(cl.HexColor("#A07000")); c.setLineWidth(0.5)
    for vx in [t_x + col1, t_x + col1 + col2]:
        c.line(vx, t_y - row_h, vx, t_y - row_h - total_rows*row_h)

    # Rangées sections
    baie_brute_po = L_po / nb_sec
    baie_brute_mm = round(baie_brute_po * 25.4)
    for s in range(nb_sec):
        ry = t_y - row_h - (s + 1) * row_h
        fill_hex = _SEC[s % 4][0]
        badge_hex = _SEC[s % 4][2]
        # Badge lettre
        bw = 0.20*inch; bh = 0.17*inch
        bx = t_x + col1/2 - bw/2
        by = ry + (row_h - bh)/2
        c.setFillColor(cl.HexColor(badge_hex))
        c.roundRect(bx, by, bw, bh, 0.025*inch, fill=True, stroke=False)
        c.setFillColor(WHT); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(t_x + col1/2, by + bh - 0.13*inch, _LABELS[s % 4])
        # Valeurs
        c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(t_x + col1 + col2/2, ry + row_h - 0.115*inch,
                            f"{baie_brute_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawCentredString(t_x + col1 + col2/2, ry + 0.065*inch,
                            f"({_dvf(baie_brute_po)})")
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(t_x + col1 + col2 + col3/2, ry + row_h - 0.115*inch,
                            f"{trav_bas_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawCentredString(t_x + col1 + col2 + col3/2, ry + 0.065*inch,
                            f"({_dvf(trav_bas_po)})")

    # Rangée hauteur
    ry_h = t_y - row_h - (nb_sec + 1) * row_h
    c.setFillColor(BLEU_F); c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(t_x + col1/2, ry_h + row_h - 0.115*inch, "HAUTEUR")
    if est_trap:
        c.drawString(t_x + col1 + 0.10*inch, ry_h + row_h - 0.115*inch,
                     f"G: {VG_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawString(t_x + col1 + 0.10*inch, ry_h + 0.065*inch, f"({_dvf(VG)})")
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(t_x + col1 + col2 + 0.10*inch, ry_h + row_h - 0.115*inch,
                     f"D: {VD_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawString(t_x + col1 + col2 + 0.10*inch, ry_h + 0.065*inch,
                     f"({_dvf(VD)})")
    else:
        c.drawCentredString(t_x + col1 + col2/2, ry_h + row_h - 0.115*inch,
                            f"{H_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawCentredString(t_x + col1 + col2/2, ry_h + 0.065*inch,
                            f"({_dvf(H_po)})")
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(t_x + col1 + col2 + col3/2, ry_h + row_h - 0.115*inch,
                            f"{mont_mm} mm")
        c.setFont("Helvetica", 7)
        c.drawCentredString(t_x + col1 + col2 + col3/2, ry_h + 0.065*inch,
                            f"({_dvf(mont_po)})  coupe montant")

    # Rangée total largeur
    ry_t = t_y - row_h - (nb_sec + 2) * row_h
    c.setFillColor(OR_C); c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(t_x + col1/2, ry_t + row_h - 0.115*inch, "TOTAL")
    c.drawCentredString(t_x + col1 + col2/2, ry_t + row_h - 0.115*inch,
                        f"{L_mm} mm")
    c.setFont("Helvetica", 7)
    c.drawCentredString(t_x + col1 + col2/2, ry_t + 0.065*inch,
                        f"({_dvf(L_po)})  largeur totale brute")

    # Bordure tableau
    c.setStrokeColor(OR_C); c.setLineWidth(0.8)
    c.rect(t_x, ry_t, t_w, (total_rows + 1)*row_h, fill=False, stroke=True)
    c.setLineWidth(0.4)
    for row_i in range(total_rows):
        ly_line = ry_t + row_i * row_h
        c.line(t_x, ly_line, t_x + t_w, ly_line)

    # ── LIGNE MATÉRIAUX ───────────────────────────────────────────────────────
    mat_y = ry_t - 0.08*inch
    mat_h = 0.28*inch
    c.setStrokeColor(GRIS_LN); c.setLineWidth(0.4)
    c.rect(t_x, mat_y - mat_h, t_w, mat_h, fill=False, stroke=True)
    c.setFillColor(GRIS_P); c.setFont("Helvetica-Bold", 7)
    c.drawString(t_x + 0.15*inch, mat_y - mat_h + 0.09*inch,
        'Matériaux : Tube aluminium 2-1/2"  ·  Plaque de pression  ·  Couvercle de finition')

    # ── BLOC SIGNATURE ────────────────────────────────────────────────────────
    sig_top  = FOOT_H + SIG_H
    sig_bot  = FOOT_H
    sig_x    = 0.28 * inch
    sig_w    = w - 0.56 * inch

    c.setStrokeColor(BLEU_C); c.setLineWidth(0.9)
    c.rect(sig_x, sig_bot, sig_w, SIG_H, fill=False, stroke=True)

    # Bandeau titre signature
    c.setFillColor(BLEU_F)
    c.rect(sig_x, sig_top - 0.32*inch, sig_w, 0.32*inch, fill=True, stroke=False)
    c.setFillColor(OR_C); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w/2, sig_top - 0.22*inch,
                        "APPROBATION CLIENT — CADRE / TRAPÈZE")

    # Signature gauche
    col_sx = sig_x + 0.25*inch
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawString(col_sx, sig_top - 0.56*inch, "Signature du client :")
    c.setStrokeColor(cl.HexColor("#555555")); c.setLineWidth(0.7)
    c.line(col_sx, sig_top - 0.92*inch, col_sx + 3.0*inch, sig_top - 0.92*inch)
    c.setFont("Helvetica", 7.5); c.setFillColor(cl.HexColor("#555555"))
    c.drawString(col_sx, sig_bot + 0.14*inch,
                 "En signant, le client confirme avoir vérifié et approuvé les dimensions.")

    # Date + préparé par droite
    col2_x = sig_x + sig_w/2 + 0.15*inch
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawString(col2_x, sig_top - 0.56*inch, "Date d'approbation :")
    c.setStrokeColor(cl.HexColor("#555555")); c.setLineWidth(0.7)
    c.line(col2_x, sig_top - 0.92*inch, col2_x + 2.0*inch, sig_top - 0.92*inch)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawString(col2_x, sig_bot + 0.44*inch, "Préparé par :")
    c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 9)
    c.drawString(col2_x + 1.05*inch, sig_bot + 0.44*inch, "Céderic Rainville")

    # ── PIED DE PAGE ──────────────────────────────────────────────────────────
    c.setFillColor(BLEU_F)
    c.rect(0, 0, w, FOOT_H - 0.08*inch, fill=True, stroke=False)
    c.setFillColor(OR_C); c.setFont("Helvetica", 7.5)
    c.drawCentredString(w/2, 0.16*inch,
        f"Solarium Pro  ·  {no_proj}  ·  {client}  ·  {date_s}")


print("Module approbation Cadre v2 OK")
