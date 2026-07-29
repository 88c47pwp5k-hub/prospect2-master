"""
Module de dessin Cadre / Trapèze v1
Vue schématique de face — style cohérent avec aika_dessin_v3.py et neoscenica_dessin_v1.py

Structure visuelle :
  - Rails supérieur et inférieur (bandes grises haut/bas)
  - Montants latéraux gauche et droite
  - nb_montants montants verticaux internes régulièrement espacés
  - Baies entre montants avec fond clair
  - Dimensions brutes en mm + pouces (largeur totale, hauteur, largeur de baie)
"""


def dessiner_mur_cadre(c, y, mur_calc, w, h, inch, colors, BLEU, OR):
    """
    Dessine la vue de face schématique d'un mur Cadre / Trapèze.

    mur_calc keys:
        nom, largeur_po, hauteur_po, largeur_mm, hauteur_mm,
        nb_montants (nombre de montants internes),
        couleur_alu

    Retourne le nouveau y après le dessin.
    """

    def dvf(d):
        if d is None: return ""
        from math import gcd
        s = round(d * 16) / 16
        entier = int(s); reste = s - entier
        if reste < 0.001: return f'{entier}"'
        num = round(reste * 16); den = 16
        g = gcd(num, den); num //= g; den //= g
        return f'{entier}-{num}/{den}"' if entier else f'{num}/{den}"'

    BLEU_C  = colors.HexColor("#0000CC")
    GRIS_R  = colors.HexColor("#C8D3E8")   # profil alu
    BAIE_F  = colors.HexColor("#F2F5FA")   # fond de baie
    BLEU_V  = colors.HexColor("#D6E4F0")   # étiquette dimension
    GRIS_LN = colors.HexColor("#9AAAC6")   # lignes internes

    L_mm       = mur_calc['largeur_mm']
    H_mm       = mur_calc['hauteur_mm']
    L_po       = mur_calc['largeur_po']
    H_po       = mur_calc['hauteur_po']
    nb_mont    = mur_calc.get('nb_montants', 2)   # total montants (extrémités inclus)
    nb_baies   = max(nb_mont - 1, 1)              # nb_sections = nb_montants - 1
    nb_mont_int = nb_mont - 2                     # montants internes seulement
    couleur    = mur_calc.get('couleur_alu', '')

    # ── ZONE D'AFFICHAGE ──────────────────────────────────────────────────────
    mg_cote = 0.55*inch
    mg_ext  = 0.35*inch
    zone_w  = w - mg_cote - mg_ext - mg_ext
    ratio   = H_mm / L_mm
    vue_h   = min(zone_w * ratio, 3.5*inch)
    vue_h   = max(vue_h, 2.0*inch)
    vue_w   = vue_h / ratio
    if vue_w > zone_w: vue_w = zone_w; vue_h = vue_w * ratio
    x0 = (w - vue_w) / 2

    espace = 0.30*inch + vue_h + 0.50*inch
    if y - espace < 0.9*inch:
        c.showPage()
        entete_mini_cadre(c, w, h, inch, colors, BLEU, OR, mur_calc)
        y = h - 1.2*inch

    # ── TITRE centré au-dessus du dessin ──────────────────────────────────────
    titre_complet = (f"{mur_calc['nom'].upper()}   ·   "
                     f"{nb_baies} BAIE{'S' if nb_baies > 1 else ''}  —  "
                     f"{nb_mont} MONTANTS ({nb_mont_int} INTERNE{'S' if nb_mont_int > 1 else ''})   ·   "
                     f"{couleur}")
    c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(w/2, y, titre_complet)
    y -= 0.20*inch

    y_top = y
    y_bot = y_top - vue_h

    # Épaisseur des profils — tous les tubes font 2-1/2" visuellement
    prof_po = 2.5
    px_h = vue_w / L_po
    px_v = vue_h / H_po
    rail_h     = prof_po * px_v   # épaisseur rail haut/bas
    mont_w     = prof_po * px_h   # épaisseur montant lat et interne (tous identiques)
    mont_int_w = mont_w           # même section que les montants latéraux

    # Zone intérieure
    ix = x0 + mont_w
    iy = y_bot + rail_h
    iw = vue_w - 2*mont_w
    ih = vue_h - 2*rail_h

    # ── FOND BLANC ──
    c.setFillColor(colors.white)
    c.rect(x0, y_bot, vue_w, vue_h, fill=True, stroke=False)

    # ── BAIES (fond clair) ──
    baie_w = (iw - nb_mont * mont_int_w) / nb_baies
    for b in range(nb_baies):
        bx = ix + b * (baie_w + mont_int_w)
        c.setFillColor(BAIE_F)
        c.rect(bx, iy, baie_w, ih, fill=True, stroke=False)

    # ── RAILS SUPÉRIEUR / INFÉRIEUR ──
    c.setFillColor(GRIS_R)
    c.rect(x0, y_bot + vue_h - rail_h, vue_w, rail_h, fill=True, stroke=False)
    c.rect(x0, y_bot, vue_w, rail_h, fill=True, stroke=False)

    # ── MONTANTS LATÉRAUX ──
    c.rect(x0, y_bot, mont_w, vue_h, fill=True, stroke=False)
    c.rect(x0 + vue_w - mont_w, y_bot, mont_w, vue_h, fill=True, stroke=False)

    # ── MONTANTS INTERNES ──
    for m in range(nb_mont):
        mx = ix + (m + 1) * baie_w + m * mont_int_w
        c.rect(mx, y_bot, mont_int_w, vue_h, fill=True, stroke=False)

    # ── CADRE EXTÉRIEUR ──
    c.setStrokeColor(BLEU_C); c.setLineWidth(1.8)
    c.rect(x0, y_bot, vue_w, vue_h, fill=False, stroke=True)
    c.setLineWidth(0.5)

    # ── ÉTIQUETTES BAIES (largeur brute / nb_baies) ──
    baie_po  = L_po / nb_baies
    baie_mm  = round(baie_po * 25.4)
    lhh = 0.26*inch
    for b in range(nb_baies):
        bx = ix + b * (baie_w + mont_int_w)
        cx_b = bx + baie_w / 2
        lw = min(baie_w - 4, 1.0*inch)
        lx = cx_b - lw/2; ly = iy + ih - lhh - 0.05*inch
        if lw > 0.30*inch:
            c.setFillColor(BLEU_V)
            c.roundRect(lx, ly, lw, lhh, 0.025*inch, fill=True, stroke=False)
            c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
            c.roundRect(lx, ly, lw, lhh, 0.025*inch, fill=False, stroke=True)
            c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(cx_b, ly + lhh - 0.090*inch, f"{baie_mm} mm")
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(cx_b, ly + lhh - 0.175*inch, f"{dvf(baie_po)}")

    # ── COTES ─────────────────────────────────────────────────────────────────
    c.setStrokeColor(BLEU_C); c.setFillColor(BLEU_C); c.setLineWidth(0.6)

    # Hauteur — côte gauche verticale (mm + pouces bruts)
    cx_h = x0 - 0.24*inch
    c.line(cx_h, y_bot, x0 - 0.04*inch, y_bot)
    c.line(cx_h, y_bot + vue_h, x0 - 0.04*inch, y_bot + vue_h)
    c.line(cx_h, y_bot, cx_h, y_bot + vue_h)
    c.saveState()
    c.translate(cx_h - 0.10*inch, y_bot + vue_h/2); c.rotate(90)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(0, 0.06*inch, f"{H_mm} mm")
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(0, -0.04*inch, f"{dvf(H_po)}")
    c.restoreState()

    # Largeur — côte bas horizontale (mm + pouces bruts)
    cy_l = y_bot - 0.18*inch
    c.line(x0, cy_l, x0 + vue_w, cy_l)
    c.line(x0, y_bot - 0.03*inch, x0, cy_l)
    c.line(x0 + vue_w, y_bot - 0.03*inch, x0 + vue_w, cy_l)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x0 + vue_w/2, cy_l - 0.08*inch, f"{L_mm} mm")
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(x0 + vue_w/2, cy_l - 0.18*inch, f"{dvf(L_po)}")

    return cy_l - 0.22*inch


def bloc_approbation_cadre(c, y, w, inch, colors, BLEU, fait_par="Céderic Rainville"):
    """Bloc de signature d'approbation client — Cadre / Trapèze."""
    BLEU_C = colors.HexColor("#0000CC")
    bw = 7.3*inch; bh = 1.45*inch
    bx = (w - bw) / 2; by = y - bh

    c.setFillColor(colors.HexColor("#F0F4FB"))
    c.rect(bx, by, bw, bh, fill=True, stroke=False)
    c.setStrokeColor(BLEU_C); c.setLineWidth(1.0)
    c.rect(bx, by, bw, bh, fill=False, stroke=True)

    # Bandeau titre
    c.setFillColor(BLEU); c.rect(bx, by + bh - 0.32*inch, bw, 0.32*inch, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#C68B00")); c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w/2, by + bh - 0.22*inch, "APPROBATION CLIENT — CADRE / TRAPÈZE")

    # Colonne gauche : signature
    col_x = bx + 0.25*inch
    c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
    c.drawString(col_x, by + bh - 0.58*inch, "Signature du client :")
    c.setStrokeColor(colors.HexColor("#555555")); c.setLineWidth(0.7)
    c.line(col_x, by + bh - 0.92*inch, col_x + 3.0*inch, by + bh - 0.92*inch)
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor("#555555"))
    c.drawString(col_x, by + 0.12*inch, "En signant, le client confirme avoir vérifié et approuvé les dimensions.")

    # Colonne droite : date + préparé par
    col2_x = bx + bw/2 + 0.15*inch
    c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
    c.drawString(col2_x, by + bh - 0.58*inch, "Date d'approbation :")
    c.setStrokeColor(colors.HexColor("#555555")); c.setLineWidth(0.7)
    c.line(col2_x, by + bh - 0.92*inch, col2_x + 2.0*inch, by + bh - 0.92*inch)

    c.setFillColor(colors.HexColor("#333333")); c.setFont("Helvetica-Bold", 9)
    c.drawString(col2_x, by + 0.42*inch, "Préparé par :")
    c.setFont("Helvetica-Bold", 9); c.setFillColor(BLEU_C)
    c.drawString(col2_x + 1.05*inch, by + 0.42*inch, fait_par)

    return by - 0.15*inch


def entete_mini_cadre(c, w, h, inch, colors, BLEU, OR, mur_calc):
    from reportlab.lib import colors as cl
    c.setFillColor(BLEU)
    c.rect(0, h - 0.55*inch, w, 0.55*inch, fill=True, stroke=False)
    c.setFillColor(OR); c.setFont("Helvetica-Bold", 10)
    c.drawString(0.4*inch, h - 0.32*inch, "SOLARIUM PRO — CADRE / TRAPÈZE")
    c.setFillColor(cl.white); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch, h - 0.48*inch, f"Approbation — {mur_calc['nom']}")


print("Module dessin Cadre / Trapèze v1 OK")
