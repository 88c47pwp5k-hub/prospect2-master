"""
Module de dessin de montage Cadre / Trapèze v1
===============================================

RECETTE STANDARD — RÈGLES DÉFINITIVES (ne jamais dévier)
=========================================================

1. TRAVERSE DU HAUT (rectangulaire) / HYPOTÉNUSE (trapèze)
   • Rectangulaire : tube pleine largeur x0→x1, dessiné EN DERNIER.
     Tous les montants s'arrêtent à y_top-th ; la traverse les recouvre proprement.
   • Trapèze : UNE SEULE ligne continue du coin extérieur haut gauche (x0, VG)
     au coin extérieur haut droit (x1, VD).
     Pas de tube parallélogramme — juste la ligne extérieure de bord à bord.

2. TRAVERSES DU BAS — SEGMENTÉES (une par baie)
   • Chaque segment : face interne montant gauche → face interne montant droit.
   • bx_l = mx_left(s) + tw,  bx_r = mx_left(s+1)
   • Aucun segment ne traverse ni ne chevauche un montant.

3. MONTANTS
   • Rectangulaire : tube_rect de y_bot à y_top-th.
   • Trapèze : parallélogramme avec sommet biseauté aligné sur l'hypoténuse.
     Face gauche top = y_at_x(mx),  face droite top = y_at_x(mx+tw).
     → Joint propre et fermé : le sommet rencontre exactement la ligne hyp.

4. SPIGOTS S — POSITIONS DÉFINITIVES
   • HAUT (nb_montants total, ex: 3) : un S centré sur chaque montant (x),
     à mi-hauteur de la traverse du haut (y = y_top - th/2 pour rectangulaire).
     → Jonction montant ↔ traverse du haut.
   • BAS (2 × nb_sections, ex: 4) : un S à chaque extrémité de chaque segment
     de traverse du bas — gauche = face droite du montant gauche (bx_l),
     droite = face gauche du montant droit (bx_r).
     → Les 2 spigots du montant central sont séparés par la largeur tw du montant.
   • PAS de spigots à mi-hauteur des montants.

5. COTATIONS — RÈGLE PERMANENTE : TOUJOURS MESURER LE POINT LE PLUS LONG
   Chaque cotation mesure TOUJOURS entre les deux points les plus longs de la pièce
   concernée. Jamais une mesure centrale ou une moyenne.

   • LARGEUR TOTALE (or) : au-DESSUS de la traverse du haut.
   • LARGEUR PAR SECTION (bleu) : en dessous de la traverse du bas.
   • HAUTEUR (bleu, gauche, rectangulaire) : longueur de coupe RÉELLE du montant
     = H_po - TUBE_W  (ex: 84" - 2.5" = 81-1/2").
     Flèche de y_bot à y_top-th (hauteur effective du montant).

   TRAPÈZE — cotations verticales et diagonale :
   • VG (bleu, gauche) : face extérieure du montant gauche = _yt(0) = VG.
     C'est la face gauche du montant, le point le plus long de cette pièce car
     la coupe en biseau est plus haute côté extérieur.
   • VD (bleu, droite) : face extérieure du cadre côté VD = _yt(1) = VD.
     Référence sur la face extérieure de la pièce. Le point le plus long du
     montant droit (face intérieure, ≈ VD + TUBE_W*(VG-VD)/L) est une valeur
     dérivée non spécifiée — la cotation VD affiche la valeur spécifiée VD.
   • HYPOTÉNUSE : mesurée coin extérieur à coin extérieur = sqrt(L²+(VG-VD)²).
     C'est la distance entre les deux points les plus longs du tube diagonal
     (coin (x0,VG) → coin (x1,VD)), comme pour toute pièce coupée en angle.
     AFFICHAGE : HYP et ANGLE sont dans l'en-tête (colonne HYP + colonne TRAPÈZE),
     pas sur le dessin. Format degré : f"{ang_phys:.1f}\u00b0" (ex: "28.7°").

6. SPIGOTS BAS — RÈGLE UNIFIÉE (rect ET trapèze identiques)
   Une seule boucle for s in range(nb_sec): draw_spigot(bx_l, sy_b) / draw_spigot(bx_r, sy_b)
   où bx_l = mx_left(s)+tw  (face droite du montant gauche du segment)
       bx_r = mx_left(s+1)   (face gauche du montant droit du segment)
   Position verticale : sy_b = y_bot + th + spigot_r + GAP_BAS (au-dessus de la traverse, pas dessus).
   Pour un trapèze 3 montants = 4 spigots aux extrémités des 2 segments.

7. ORDRE DE DESSIN
   1) Fond blanc global
   2) Panneaux de verre (bleu pâle)
   3) Traverses du bas (segmentées)
   4) Montants verticaux (jusqu'à y_top-th)
   5) Traverse du haut (pleine largeur, par-dessus tout)
   6) Contour extérieur
   7) Spigots S (haut : jonctions montants/haut, bas : extrémités segments)
   8) Cotations et légende

7. PRINCIPE GÉNÉRAL — MAXIMISER L'ESPACE DISPONIBLE (s'applique à TOUS les modules PDF)
   • Le dessin technique doit occuper toute la largeur/hauteur utilisable de la page.
     Aucun grand espace vide ne doit subsister autour du dessin si la page peut l'absorber.
   • Les polices (légendes, notes, étiquettes) doivent être proportionnelles à l'espace
     disponible : jamais écrasées ou illisibles s'il reste de la place.
     Taille minimale recommandée : 8pt pour les légendes secondaires, 10pt pour les titres.
   • Cette règle s'applique systématiquement à chaque génération future (Cadre, Trapèze,
     et tout autre module PDF). Ne pas patcher au cas par cas — intégrer dès la conception.
"""

from math import gcd as _gcd, sqrt as _sqrt, atan as _atan, cos as _cos, sin as _sin

TUBE_W = 2.5   # largeur profil aluminium en pouces (constante assemblage)


def _dvf(d):
    if d is None:
        return ""
    s = round(d * 16) / 16
    entier = int(s); reste = s - entier
    if reste < 0.001:
        return f'{entier}"'
    num = round(reste * 16); den = 16
    g = _gcd(num, den); num //= g; den //= g
    return f'{entier}-{num}/{den}"' if entier else f'{num}/{den}"'


def dessiner_cadre_montage(c, y, mur_calc, w, h, inch, colors):
    """
    Dessine la vue de montage d'un mur Cadre / Trapèze.
    Respecte impérativement la RECETTE STANDARD du module (voir docstring).

    mur_calc keys :
        nom, largeur_po, hauteur_po, largeur_mm, hauteur_mm,
        nb_montants, est_trapeze (opt), vg_po/vd_po/vg_mm/vd_mm (opt trapèze)
    """
    from reportlab.lib import colors as cl

    # ── Palette ───────────────────────────────────────────────────────────────
    NOIR    = cl.HexColor("#1A1A1A")
    BLEU_C  = cl.HexColor("#0055AA")
    BLEU_BG = cl.HexColor("#D6E4F7")
    OR_C    = cl.HexColor("#C68B00")
    OR_BG   = cl.HexColor("#FFF4DC")
    PROF_C  = cl.HexColor("#333333")
    VERRE_F = cl.HexColor("#E8F4FD")
    VERRE_B = cl.HexColor("#4A90D9")
    SPIG_C  = cl.HexColor("#FF6600")
    WHT     = cl.white
    TRAV_H_C = cl.HexColor("#1F3864")   # traverse du haut
    TRAV_B_C = cl.HexColor("#C68B00")   # traverses du bas
    MONT_C   = cl.HexColor("#2D6A3F")   # montants

    # ── Données mur ───────────────────────────────────────────────────────────
    L_mm    = mur_calc['largeur_mm']
    L_po    = mur_calc['largeur_po']
    VG      = mur_calc.get('vg_po') or mur_calc.get('hauteur_po', 0)
    VD      = mur_calc.get('vd_po') or VG
    VG_mm   = mur_calc.get('vg_mm', round(VG * 25.4))
    VD_mm   = mur_calc.get('vd_mm', round(VD * 25.4))
    H_po    = max(VG, VD)
    H_mm    = round(H_po * 25.4)
    est_trap = mur_calc.get('est_trapeze', False)
    nb_mont  = int(mur_calc.get('nb_montants', 2))
    nb_sec   = max(nb_mont - 1, 1)

    # Longueur réelle de coupe du montant (traverse du haut occupe le dessus)
    mont_po  = H_po - TUBE_W
    mont_mm  = round(mont_po * 25.4)

    # Hypoténuse (pré-calculé ici pour réutilisation dans étiquette + légende)
    if est_trap and L_po > 0:
        from math import sqrt as _sq, atan as _at, degrees as _deg
        hyp_po   = _sq(L_po**2 + (VG - VD)**2)
        hyp_mm   = round(hyp_po * 25.4)
        ang_phys = _deg(_at((VG - VD) / L_po))
    else:
        hyp_po = hyp_mm = ang_phys = None

    # Longueur traverse du bas par segment
    trav_bas_po = max((L_po - nb_mont * TUBE_W) / nb_sec, 0)
    trav_bas_mm = round(trav_bas_po * 25.4)

    # ── Mise en page ──────────────────────────────────────────────────────────
    mg_l      = 1.10*inch   # marge gauche (cotation V)
    mg_r      = 1.10*inch   # espace légende + VD
    TITLE_H   = 0.60*inch   # hauteur en-tête (2 lignes : nom + colonnes — lisibilité usine)
    TOP_COT   = 0.65*inch   # espace au-dessus dessin (cote largeur totale)
    BOT_COT   = 1.15*inch   # espace en dessous dessin (cotes sections)
    PAGE_BOT  = 0.90*inch   # marge bas de page

    zone_w = w - mg_l - mg_r
    avail_v = y - TITLE_H - TOP_COT - BOT_COT - PAGE_BOT

    ratio = H_po / L_po if L_po > 0 else 1
    vue_w = zone_w
    vue_h = vue_w * ratio
    if vue_h > avail_v:
        vue_h = avail_v
        vue_w = vue_h / ratio if ratio > 0 else zone_w
    if vue_w > zone_w:
        vue_w = zone_w
        vue_h = vue_w * ratio

    vue_w = max(vue_w, 1.5*inch)
    vue_h = max(vue_h, 1.5*inch)

    # Centrage horizontal dans la zone
    x0 = mg_l + (zone_w - vue_w) / 2
    x1 = x0 + vue_w

    # Vérification espace page
    espace_total = TITLE_H + TOP_COT + vue_h + BOT_COT
    if y - espace_total < PAGE_BOT:
        c.showPage()
        _entete_mini(c, w, h, inch, colors, mur_calc)
        y = h - 1.2*inch

    # Coordonnées verticales du dessin
    y_after_title = y - TITLE_H
    y_top = y_after_title - TOP_COT   # bord supérieur de la traverse du haut
    y_bot = y_top - vue_h             # bord inférieur

    # Échelle pixel/pouce
    px_h = vue_w / L_po if L_po > 0 else 1
    px_v = vue_h / H_po if H_po > 0 else 1
    tw   = TUBE_W * px_h   # épaisseur visuelle montant (horizontal)
    th   = TUBE_W * px_v   # épaisseur visuelle traverse (vertical)

    # ── Titre en colonnes (principe 7 — lisibilité) ───────────────────────────
    nb_int = nb_mont - 2
    # Ligne 1 : nom du mur + type de dessin
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w/2, y - 0.18*inch,
        f"{mur_calc['nom'].upper()}  —  DESSIN DE MONTAGE")
    # Séparateur horizontal
    c.setStrokeColor(cl.HexColor("#AAAAAA")); c.setLineWidth(0.4)
    c.line(0.3*inch, y - 0.27*inch, w - 0.3*inch, y - 0.27*inch)
    # Ligne 2 : colonnes de valeurs
    if est_trap:
        # 5 colonnes : L · VG · VD · HYP · TRAPÈZE+ANGLE
        # HYP = valeur dans l'en-tête, plus rien sur le dessin (règle point le plus long doc.)
        _hyp_hdr = f"{_dvf(hyp_po)}  ({hyp_mm} mm)" if hyp_po else "—"
        _ang_hdr = f"{ang_phys:.1f}\u00b0" if ang_phys is not None else "—"
        cols = [
            ("L",       f"{_dvf(L_po)}  ({L_mm} mm)",       w * 1/10),
            ("VG",      f"{_dvf(VG)}  ({VG_mm} mm)",        w * 3/10),
            ("VD",      f"{_dvf(VD)}  ({VD_mm} mm)",        w * 5/10),
            ("HYP",     _hyp_hdr,                            w * 7/10),
            ("TRAPÈZE", f"{nb_mont} MONT.  ·  {_ang_hdr}",  w * 9/10),
        ]
    else:
        cols = [
            ("L",     f"{_dvf(L_po)}  ({L_mm} mm)",                         w * 1/6),
            ("H",     f"{_dvf(H_po)}  ({H_mm} mm)",                         w * 3/6),
            ("TYPE",  f"{nb_mont} MONT. ({nb_int} INT.) · {nb_sec} BAIES",  w * 5/6),
        ]
    # Séparateurs verticaux
    c.setStrokeColor(cl.HexColor("#CCCCCC")); c.setLineWidth(0.3)
    sep_xs = [w/5, 2*w/5, 3*w/5, 4*w/5] if est_trap else [w/3, 2*w/3]
    for sx in sep_xs:
        c.line(sx, y - 0.31*inch, sx, y - 0.57*inch)
    for (lbl, val, cx) in cols:
        c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, y - 0.38*inch, lbl)
        c.setFillColor(NOIR); c.setFont("Helvetica", 10)
        c.drawCentredString(cx, y - 0.53*inch, val)

    # ── Hauteur au sommet pour fraction f ∈ [0,1] (trapèze) ─────────────────
    def _yt(frac):
        if est_trap:
            return y_bot + (VG + frac * (VD - VG)) * px_v
        return y_top

    # ── Position x (face gauche) du montant m ────────────────────────────────
    def mx_left(m):
        frac = m / (nb_mont - 1) if nb_mont > 1 else 0
        return x0 + frac * (vue_w - tw)

    # ── Hauteur de l'hypoténuse à la position x (trapèze) ────────────────────
    def y_at_x(x):
        frac = (x - x0) / vue_w if vue_w > 0 else 0
        return y_bot + (VG + frac * (VD - VG)) * px_v

    # ── HELPERS TUBES EN CONTOUR ──────────────────────────────────────────────
    def tube_rect(x, y_r, w_r, h_r, clr=None):
        fc = clr if clr is not None else TRAV_B_C
        c.setFillColor(fc)
        c.rect(x, y_r, w_r, h_r, fill=True, stroke=False)

    def tube_path(pts, clr=None):
        fc = clr if clr is not None else MONT_C
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]: p.lineTo(*pt)
        p.close()
        c.setFillColor(fc); c.drawPath(p, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════════════════════════
    # ORDRE DE DESSIN — voir RECETTE STANDARD
    # ══════════════════════════════════════════════════════════════════════════

    # 1. Fond blanc global
    c.setFillColor(WHT)
    if est_trap:
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=1, stroke=0)
    else:
        c.rect(x0, y_bot, vue_w, vue_h, fill=True, stroke=False)

    # 2. Panneaux de verre (entre traverses, entre montants)
    for s in range(nb_sec):
        vx_l = mx_left(s) + tw
        vx_r = mx_left(s + 1)
        vw_s = vx_r - vx_l
        vy_b = y_bot + th
        if est_trap:
            vy_tl = y_at_x(vx_l) - th   # top verre = face intérieure du tube hyp (côté gauche)
            vy_tr = y_at_x(vx_r) - th   # top verre = face intérieure du tube hyp (côté droit)
            p = c.beginPath()
            p.moveTo(vx_l, vy_b); p.lineTo(vx_r, vy_b)
            p.lineTo(vx_r, vy_tr); p.lineTo(vx_l, vy_tl); p.close()
            c.setFillColor(VERRE_F); c.drawPath(p, fill=1, stroke=0)
            c.setStrokeColor(VERRE_B); c.setLineWidth(0.6); c.drawPath(p, fill=0, stroke=1)
            cy_v = vy_b + ((vy_tl + vy_tr) / 2 - vy_b) / 2
        else:
            vy_t = y_top - th
            c.setFillColor(VERRE_F)
            c.rect(vx_l, vy_b, vw_s, vy_t - vy_b, fill=True, stroke=False)
            c.setStrokeColor(VERRE_B); c.setLineWidth(0.6)
            c.rect(vx_l, vy_b, vw_s, vy_t - vy_b, fill=False, stroke=True)
            cy_v = (vy_b + vy_t) / 2
        # Étiquette dimensions verre
        lh_lab = 0.38*inch; lw_lab = min(vw_s - 6, 1.20*inch)
        if lw_lab > 0.40*inch:
            cx_s = vx_l + vw_s / 2
            lx = cx_s - lw_lab/2; ly = cy_v - lh_lab/2
            c.setFillColor(BLEU_BG)
            c.roundRect(lx, ly, lw_lab, lh_lab, 0.025*inch, fill=True, stroke=False)
            c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
            c.roundRect(lx, ly, lw_lab, lh_lab, 0.025*inch, fill=False, stroke=True)
            c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(cx_s, ly + lh_lab - 0.115*inch,
                                f"L: {trav_bas_mm} mm  ({_dvf(trav_bas_po)})")
            if not est_trap:
                verre_h_po = H_po - 2 * TUBE_W
                c.setFont("Helvetica", 7)
                c.drawCentredString(cx_s, ly + 0.075*inch,
                                    f"H: {round(verre_h_po*25.4)} mm  ({_dvf(verre_h_po)})")

    # 3. Traverses du bas — UN SEGMENT PAR BAIE
    #    bx_l = face droite montant gauche, bx_r = face gauche montant droit
    for s in range(nb_sec):
        bx_l = mx_left(s) + tw
        bx_r = mx_left(s + 1)
        tube_rect(bx_l, y_bot, bx_r - bx_l, th, TRAV_B_C)

    # 4. Montants
    #    Rectangulaire : tube_rect jusqu'à y_top-th (sous traverse du haut).
    #    Trapèze : parallélogramme avec sommet en biseau, aligné exactement sur l'hypoténuse.
    #              Face gauche : y = y_at_x(mx),     face droite : y = y_at_x(mx+tw).
    #              Joint propre et fermé — pas de notch, pas de gap.
    for m in range(nb_mont):
        mx = mx_left(m)
        if est_trap:
            y_tl = y_at_x(mx)
            y_tr = y_at_x(mx + tw)
            tube_path([(mx, y_bot), (mx + tw, y_bot), (mx + tw, y_tr), (mx, y_tl)], MONT_C)
        else:
            tube_rect(mx, y_bot, tw, (y_top - th) - y_bot, MONT_C)

    # 5. Traverse du haut (rectangulaire) / Tube hypoténuse (trapèze)
    #    Rectangulaire : tube_rect pleine largeur, dessiné EN DERNIER.
    #    Trapèze : tube parallélogramme — face externe (x0,VG)→(x1,VD),
    #              face interne décalée de th vers le bas.
    #              Les montants biseautés s'arrêtent à y_at_x (face externe) :
    #              le tube hyp dessiné après recouvre proprement leurs sommets.
    if est_trap:
        tube_path([
            (x0, _yt(0)),
            (x1, _yt(1)),
            (x1, _yt(1) - th),
            (x0, _yt(0) - th),
        ], TRAV_H_C)
    else:
        tube_rect(x0, y_top - th, vue_w, th, TRAV_H_C)

    # 6. Contour extérieur
    c.setStrokeColor(PROF_C); c.setLineWidth(1.8)
    if est_trap:
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=0, stroke=1)
    else:
        c.rect(x0, y_bot, vue_w, vue_h, fill=False, stroke=True)

    # 7. Spigots S
    spigot_r = max(min(tw * 0.38, 0.088*inch), 5.0)

    def draw_spigot(sx, sy):
        c.setFillColor(SPIG_C)
        c.circle(sx, sy, spigot_r, fill=True, stroke=False)
        c.setStrokeColor(WHT); c.setLineWidth(0.4)
        c.circle(sx, sy, spigot_r, fill=False, stroke=True)
        c.setFillColor(WHT)
        c.setFont("Helvetica-Bold", max(6, int(spigot_r * 1.15)))
        c.drawCentredString(sx, sy - spigot_r * 0.38, "S")

    # HAUT — 1 S par montant à la jonction traverse du haut / hypoténuse
    # Rectangulaire : milieu de la traverse du haut au-dessus de chaque montant
    # Trapèze : milieu de la traverse hypoténuse au-dessus de chaque montant (même logique)
    for m in range(nb_mont):
        sx = mx_left(m) + tw / 2
        if est_trap:
            # Centre de l'hypoténuse à la position horizontale du montant
            sy = y_at_x(sx) - th / 2
        else:
            frac = m / (nb_mont - 1) if nb_mont > 1 else 0
            sy = _yt(frac) - th / 2
        draw_spigot(sx, sy)

    # BAS — extrémités de chaque segment de traverse du bas (rect ET trapèze identiques)
    # Position : légèrement au-dessus de la traverse du bas (pas dessus)
    # bx_l = face droite du montant gauche du segment, bx_r = face gauche du montant droit
    GAP_BAS = 3.0
    sy_b = y_bot + th + spigot_r + GAP_BAS
    for s in range(nb_sec):
        bx_l = mx_left(s) + tw
        bx_r = mx_left(s + 1)
        draw_spigot(bx_l, sy_b)
        draw_spigot(bx_r, sy_b)

    # ══ COTATIONS ════════════════════════════════════════════════════════════
    # HYP (longueur + angle) : affiché dans l'en-tête colonnes, pas sur le dessin.
    # Règle "point le plus long" — formules définitives :
    #   VG  = _yt(0) = y_bot + VG * px_v        → face extérieure montant gauche (biseau : côté ext. = le plus long)
    #   VD  = _yt(1) = y_bot + VD * px_v        → face extérieure montant droit (valeur nominale spécifiée)
    #   HYP = sqrt(L_po²+(VG-VD)²) en pouces    → coin ext. gauche (x0,VG) → coin ext. droit (x1,VD)

    def fleche_h(x_a, x_b, yf, col):
        c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(0.7)
        c.line(x_a, yf, x_b, yf)
        sz = 0.055
        for xp, sens in [(x_b, -1), (x_a, +1)]:
            p = c.beginPath()
            p.moveTo(xp, yf)
            p.lineTo(xp + sens*sz*72, yf + 0.4*sz*72)
            p.lineTo(xp + sens*sz*72, yf - 0.4*sz*72)
            p.close(); c.drawPath(p, fill=1, stroke=0)

    def fleche_v(xf, y_a, y_b, col):
        c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(0.7)
        c.line(xf, y_a, xf, y_b)
        sz = 0.055
        for yp, sens in [(y_b, -1), (y_a, +1)]:
            p = c.beginPath()
            p.moveTo(xf, yp)
            p.lineTo(xf + 0.4*sz*72, yp + sens*sz*72)
            p.lineTo(xf - 0.4*sz*72, yp + sens*sz*72)
            p.close(); c.drawPath(p, fill=1, stroke=0)

    def etiq_above(cx_e, y_base, mm, po, fg, bg):
        """Étiquette au-dessus de y_base — TAILLE USINE : min 8pt"""
        lw = max(min(1.10*inch, vue_w*0.22), 0.70*inch); lh = 0.34*inch
        lx = cx_e - lw/2; ly = y_base + 0.05*inch
        c.setFillColor(bg)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(fg); c.setLineWidth(0.4)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(fg); c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(cx_e, ly + lh - 0.105*inch, f"{mm} mm")
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(cx_e, ly + 0.065*inch, _dvf(po))

    def etiq_below(cx_e, y_base, mm, po, fg, bg):
        """Étiquette en dessous de y_base — TAILLE USINE : min 8pt"""
        lw = max(min(1.10*inch, vue_w*0.22), 0.70*inch); lh = 0.34*inch
        lx = cx_e - lw/2; ly = y_base - lh - 0.05*inch
        c.setFillColor(bg)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(fg); c.setLineWidth(0.4)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(fg); c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(cx_e, ly + lh - 0.105*inch, f"{mm} mm")
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(cx_e, ly + 0.065*inch, _dvf(po))

    def etiq_v_left(x_e, cy_e, mm, po, fg, bg, label=""):
        """Étiquette verticale gauche — TAILLE USINE : min 8pt"""
        lw = 0.95*inch; lh = 0.34*inch
        lx = x_e - lw - 0.10*inch; ly = cy_e - lh/2
        c.setFillColor(bg)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(fg); c.setLineWidth(0.4)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(fg); c.setFont("Helvetica-Bold", 8.5)
        top_txt = f"{label} {mm} mm".strip() if label else f"{mm} mm"
        c.drawCentredString(lx + lw/2, ly + lh - 0.105*inch, top_txt)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(lx + lw/2, ly + 0.065*inch, _dvf(po))

    def etiq_v_right(x_e, cy_e, mm, po, fg, bg, label=""):
        """Étiquette verticale droite — TAILLE USINE : min 8pt"""
        lw = 0.95*inch; lh = 0.34*inch
        lx = x_e + 0.10*inch; ly = cy_e - lh/2
        c.setFillColor(bg)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(fg); c.setLineWidth(0.4)
        c.roundRect(lx, ly, lw, lh, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(fg); c.setFont("Helvetica-Bold", 8.5)
        top_txt = f"{label} {mm} mm".strip() if label else f"{mm} mm"
        c.drawCentredString(lx + lw/2, ly + lh - 0.105*inch, top_txt)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(lx + lw/2, ly + 0.065*inch, _dvf(po))

    # ── Cotation verticale ────────────────────────────────────────────────────
    # Trapèze : VG et VD suffisent (pas de cote montant séparée — évite le chevauchement)
    # Rectangulaire : longueur de coupe du montant (y_bot → y_top-th)
    if not est_trap:
        cx_v   = x0 - 0.38*inch
        mont_top_y = y_top - th
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x0 - 0.04*inch, y_bot,      cx_v - 0.04*inch, y_bot)
        c.line(x0 - 0.04*inch, mont_top_y, cx_v - 0.04*inch, mont_top_y)
        fleche_v(cx_v, y_bot, mont_top_y, BLEU_C)
        etiq_v_left(cx_v, (y_bot + mont_top_y)/2, mont_mm, mont_po, BLEU_C, BLEU_BG)

    # ── Cotation trapèze (VG / VD) ────────────────────────────────────────────
    if est_trap:
        y_top_g = _yt(0)
        cx_vg   = x0 - 0.38*inch
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x0 - 0.04*inch, y_bot,   cx_vg-0.04*inch, y_bot)
        c.line(x0 - 0.04*inch, y_top_g, cx_vg-0.04*inch, y_top_g)
        fleche_v(cx_vg, y_bot, y_top_g, BLEU_C)
        etiq_v_left(cx_vg, (y_bot + y_top_g)/2, VG_mm, VG, BLEU_C, BLEU_BG, "VG")

        y_top_d = _yt(1)   # face extérieure du cadre côté VD = valeur de référence spécifiée
        cx_vd   = x1 + 0.38*inch
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x1 + 0.04*inch, y_bot,   cx_vd+0.04*inch, y_bot)
        c.line(x1 + 0.04*inch, y_top_d, cx_vd+0.04*inch, y_top_d)
        fleche_v(cx_vd, y_bot, y_top_d, BLEU_C)
        etiq_v_right(x1 + 0.26*inch, (y_bot + y_top_d)/2, VD_mm, VD, BLEU_C, BLEU_BG, "VD")

    # ── Cote largeur totale EN HAUT ───────────────────────────────────────────
    cy_top_arr = y_top + 0.28*inch    # position de la flèche largeur totale (espace uniforme)
    c.setStrokeColor(OR_C); c.setLineWidth(0.5)
    c.line(x0, y_top + 0.03*inch, x0, cy_top_arr - 0.03*inch)
    c.line(x1, y_top + 0.03*inch, x1, cy_top_arr - 0.03*inch)
    fleche_h(x0, x1, cy_top_arr, OR_C)
    etiq_above((x0 + x1)/2, cy_top_arr, L_mm, L_po, OR_C, OR_BG)

    # ── Cotes largeur par section EN BAS ─────────────────────────────────────
    cy_sec = y_bot - 0.28*inch
    c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
    for s in range(nb_sec):
        bx_l = mx_left(s) + tw
        bx_r = mx_left(s + 1)
        cx_s  = (bx_l + bx_r) / 2
        c.line(bx_l, y_bot - 0.03*inch, bx_l, cy_sec + 0.03*inch)
        c.line(bx_r, y_bot - 0.03*inch, bx_r, cy_sec + 0.03*inch)
        fleche_h(bx_l, bx_r, cy_sec, BLEU_C)
        etiq_below(cx_s, cy_sec - 0.03*inch, trav_bas_mm, trav_bas_po, BLEU_C, BLEU_BG)

    # ── Légende — taille proportionnelle à l'espace disponible (principe 7) ──
    # Trapèze : l'espace est en bas de page (sous les cotations) — centrer sous le dessin.
    # Rectangulaire : à droite du dessin (espace mg_r).
    if est_trap:
        leg_x = x0
        leg_y = cy_sec - 0.58*inch
    else:
        leg_x = x1 + 0.12*inch
        leg_y = y_top - 0.14*inch
    # Cercle spigot (plus grand, lisible)
    c.setFillColor(SPIG_C)
    c.circle(leg_x + 0.10*inch, leg_y, 0.08*inch, fill=True, stroke=False)
    c.setFillColor(WHT); c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(leg_x + 0.10*inch, leg_y - 4.0, "S")
    # Titre
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 11)
    c.drawString(leg_x + 0.25*inch, leg_y - 3.5, "Spigot S")
    leg_y -= 0.26*inch
    # Explication haut (2 lignes)
    c.setFont("Helvetica", 10)
    c.drawString(leg_x, leg_y, "Haut : jonction")
    leg_y -= 0.17*inch
    c.drawString(leg_x, leg_y, "  montant")
    leg_y -= 0.22*inch
    # Explication bas (2 lignes)
    c.drawString(leg_x, leg_y, "Bas : extrémité")
    leg_y -= 0.17*inch
    c.drawString(leg_x, leg_y, "  segment")

    # (Angle hypoténuse affiché dans l'en-tête colonne TRAPÈZE — pas d'encadré séparé)

    # Légende couleurs (après la légende spigot)
    leg2 = [("Trav. haut", TRAV_H_C), ("Trav. bas", TRAV_B_C), ("Montants", MONT_C)]
    for lbl2, col2 in leg2:
        c.setFillColor(col2)
        c.roundRect(leg_x, leg_y, 0.12*inch, 0.12*inch, 1, fill=True, stroke=False)
        c.setFillColor(NOIR); c.setFont("Helvetica", 9)
        c.drawString(leg_x + 0.15*inch, leg_y - 1, lbl2)
        leg_y -= 0.20*inch

    return cy_sec - 0.48*inch


def dessiner_2_trapezes_cote_a_cote(c, mc_g, mc_d, w, h, inch, colors):
    """Dessine 2 trapèzes côte à côte sur une page (Trapèze GAUCHE / Trapèze DROIT)."""
    from reportlab.lib import colors as cl
    from math import gcd as _gcd, sqrt as _sqrt, atan as _atan, degrees as _deg
    NOIR    = cl.HexColor("#1A1A1A")
    BLEU_C  = cl.HexColor("#0055AA")
    BLEU_BG = cl.HexColor("#D6E4F7")
    OR_C    = cl.HexColor("#C68B00")
    OR_BG   = cl.HexColor("#FFF4DC")
    WHT     = cl.white
    TRAV_H_C = cl.HexColor("#1F3864")
    TRAV_B_C = cl.HexColor("#C68B00")
    MONT_C   = cl.HexColor("#2D6A3F")
    VERRE_F  = cl.HexColor("#E8F4FD")
    VERRE_B  = cl.HexColor("#4A90D9")
    SPIG_C   = cl.HexColor("#FF6600")

    def _dvf_local(d):
        if d is None:
            return ""
        s = round(d * 16) / 16
        entier = int(s); reste = s - entier
        if reste < 0.001:
            return f'{entier}"'
        num = round(reste * 16); den = 16
        g = _gcd(num, den); num //= g; den //= g
        return f'{entier}-{num}/{den}"' if entier else f'{num}/{den}"'

    # Zone dessin sous le bandeau (pas de bandeau ici — la page a déjà entete())
    HDR_H = 1.30 * inch   # espace réservé en haut (titre de page)
    BOT_H = 0.90 * inch   # marge bas
    half_w = w / 2

    def _draw_one(mc, x_off, mirror=False):
        """Dessine un trapèze dans la zone x_off .. x_off+half_w.
        mirror=True → côté LONG vers le centre (pignon gauche)."""
        VG_orig = mc.get('vg_po') or mc.get('hauteur_po', 0)
        VD_orig = mc.get('vd_po') or VG_orig
        VG_mm_orig = mc.get('vg_mm', round(VG_orig * 25.4))
        VD_mm_orig = mc.get('vd_mm', round(VD_orig * 25.4))
        L_po  = mc['largeur_po']
        L_mm  = mc['largeur_mm']
        nb_mont = int(mc.get('nb_montants', 2))
        nb_sec  = max(nb_mont - 1, 1)

        # Swap VG/VD si mirror (côté long vers le centre)
        if mirror:
            VG, VD = VD_orig, VG_orig
            VG_mm, VD_mm = VD_mm_orig, VG_mm_orig
            lbl_l, lbl_r   = "VD", "VG"
            mm_l, po_l     = VD_mm_orig, VD_orig
            mm_r, po_r     = VG_mm_orig, VG_orig
        else:
            VG, VD = VG_orig, VD_orig
            VG_mm, VD_mm = VG_mm_orig, VD_mm_orig
            lbl_l, lbl_r   = "VG", "VD"
            mm_l, po_l     = VG_mm_orig, VG_orig
            mm_r, po_r     = VD_mm_orig, VD_orig

        H_po = max(VG, VD)

        mg_l = 0.75 * inch; mg_r = 0.75 * inch
        avail_w = half_w - mg_l - mg_r

        # Zone verticale disponible — centrage vertical (Fix 2)
        zone_top = h - HDR_H - 0.28*inch   # sous entete + label nom mur
        zone_bot = BOT_H + 0.68*inch        # au-dessus cotation largeur bas
        zone_h   = max(zone_top - zone_bot, 1.0*inch)

        ratio = H_po / L_po if L_po > 0 else 1
        vue_w = avail_w
        vue_h = vue_w * ratio
        if vue_h > zone_h:
            vue_h = zone_h
            vue_w = vue_h / ratio if ratio > 0 else avail_w
        if vue_w > avail_w:
            vue_w = avail_w; vue_h = vue_w * ratio
        vue_w = max(vue_w, 0.8*inch); vue_h = max(vue_h, 0.8*inch)

        x0 = x_off + mg_l + (avail_w - vue_w) / 2
        x1 = x0 + vue_w
        # Centrage vertical dans la zone disponible
        y_bot = zone_bot + (zone_h - vue_h) / 2
        y_top = y_bot + vue_h

        px_h = vue_w / L_po if L_po > 0 else 1
        px_v = vue_h / H_po if H_po > 0 else 1
        tw = TUBE_W * px_h
        th = TUBE_W * px_v

        def _yt(frac):
            return y_bot + (VG + frac * (VD - VG)) * px_v

        def mx_left(m):
            frac = m / (nb_mont - 1) if nb_mont > 1 else 0
            return x0 + frac * (vue_w - tw)

        # Fond blanc
        c.setFillColor(WHT)
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=1, stroke=0)

        # Verres
        for s in range(nb_sec):
            vx_l = mx_left(s) + tw; vx_r = mx_left(s + 1)
            vy_b = y_bot + th
            vy_tl = _yt(0) - th + ((_yt(0) - th) - (_yt(1) - th)) * (vx_l - x0) / vue_w if vue_w > 0 else _yt(0) - th
            vy_tr = _yt(0) - th + ((_yt(0) - th) - (_yt(1) - th)) * (vx_r - x0) / vue_w if vue_w > 0 else _yt(1) - th
            p = c.beginPath()
            p.moveTo(vx_l, vy_b); p.lineTo(vx_r, vy_b)
            p.lineTo(vx_r, vy_tr); p.lineTo(vx_l, vy_tl); p.close()
            c.setFillColor(VERRE_F); c.drawPath(p, fill=1, stroke=0)
            c.setStrokeColor(VERRE_B); c.setLineWidth(0.6); c.drawPath(p, fill=0, stroke=1)

        # Traverses du bas
        for s in range(nb_sec):
            bx_l = mx_left(s) + tw; bx_r = mx_left(s + 1)
            c.setFillColor(TRAV_B_C)
            c.rect(bx_l, y_bot, bx_r - bx_l, th, fill=True, stroke=False)

        # Montants
        for m in range(nb_mont):
            mx = mx_left(m)
            f_l = (mx - x0) / vue_w if vue_w > 0 else 0
            f_r = (mx + tw - x0) / vue_w if vue_w > 0 else 0
            y_tl2 = _yt(max(0.0, min(1.0, f_l)))
            y_tr2 = _yt(max(0.0, min(1.0, f_r)))
            c.setFillColor(MONT_C)
            p = c.beginPath()
            p.moveTo(mx, y_bot); p.lineTo(mx + tw, y_bot)
            p.lineTo(mx + tw, y_tr2); p.lineTo(mx, y_tl2)
            p.close(); c.drawPath(p, fill=1, stroke=0)

        # Traverse du haut (hyp)
        c.setFillColor(TRAV_H_C)
        p = c.beginPath()
        p.moveTo(x0, _yt(0) - th); p.lineTo(x1, _yt(1) - th)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=1, stroke=0)

        # Contour
        c.setStrokeColor(cl.HexColor("#1A1A1A")); c.setLineWidth(1.6)
        p = c.beginPath()
        p.moveTo(x0, y_bot); p.lineTo(x1, y_bot)
        p.lineTo(x1, _yt(1)); p.lineTo(x0, _yt(0))
        p.close(); c.drawPath(p, fill=0, stroke=1)

        # Spigots
        spigot_r = max(min(tw * 0.38, 0.088*inch), 5.0)
        def draw_spigot(sx, sy):
            c.setFillColor(SPIG_C)
            c.circle(sx, sy, spigot_r, fill=True, stroke=False)
            c.setFillColor(WHT); c.setFont("Helvetica-Bold", max(6, int(spigot_r * 1.15)))
            c.drawCentredString(sx, sy - spigot_r * 0.38, "S")
        GAP_BAS = 3.0; sy_b = y_bot + th + spigot_r + GAP_BAS
        for m in range(nb_mont):
            sx_s = mx_left(m) + tw / 2
            sy_s = _yt((mx_left(m) + tw/2 - x0) / vue_w if vue_w > 0 else 0) - th/2
            draw_spigot(sx_s, sy_s)
        for s in range(nb_sec):
            bx_l = mx_left(s) + tw; bx_r = mx_left(s + 1)
            draw_spigot(bx_l, sy_b); draw_spigot(bx_r, sy_b)

        # Cotations VG (gauche)
        cy_vg = x_off + mg_l * 0.45
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x0 - 0.03*inch, y_bot, cy_vg - 0.03*inch, y_bot)
        c.line(x0 - 0.03*inch, _yt(0), cy_vg - 0.03*inch, _yt(0))
        c.line(cy_vg, y_bot, cy_vg, _yt(0))
        lw2 = 0.80*inch; lh2 = 0.28*inch
        lx2 = max(x_off + 0.02*inch, cy_vg - lw2/2)
        ly2 = (y_bot + _yt(0))/2 - lh2/2
        c.setFillColor(BLEU_BG); c.roundRect(lx2, ly2, lw2, lh2, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
        c.roundRect(lx2, ly2, lw2, lh2, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(lx2 + lw2/2, ly2 + lh2 - 0.09*inch, f"{lbl_l} {mm_l} mm")
        c.setFont("Helvetica", 6)
        c.drawCentredString(lx2 + lw2/2, ly2 + 0.055*inch, _dvf_local(po_l))

        # Cotations droite (VD ou VG selon mirror)
        cy_vd = x1 + 0.36*inch
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
        c.line(x1 + 0.03*inch, y_bot, cy_vd + 0.03*inch, y_bot)
        c.line(x1 + 0.03*inch, _yt(1), cy_vd + 0.03*inch, _yt(1))
        c.line(cy_vd, y_bot, cy_vd, _yt(1))
        lx3 = min(x_off + half_w - 0.02*inch - lw2, cy_vd - lw2/2)
        ly3 = (y_bot + _yt(1))/2 - lh2/2
        c.setFillColor(BLEU_BG); c.roundRect(lx3, ly3, lw2, lh2, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
        c.roundRect(lx3, ly3, lw2, lh2, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(lx3 + lw2/2, ly3 + lh2 - 0.09*inch, f"{lbl_r} {mm_r} mm")
        c.setFont("Helvetica", 6)
        c.drawCentredString(lx3 + lw2/2, ly3 + 0.055*inch, _dvf_local(po_r))

        # Cotation largeur bas
        cy_l = y_bot - 0.26*inch
        c.setStrokeColor(OR_C); c.setLineWidth(0.5)
        c.line(x0, y_bot - 0.03*inch, x0, cy_l + 0.03*inch)
        c.line(x1, y_bot - 0.03*inch, x1, cy_l + 0.03*inch)
        c.line(x0, cy_l, x1, cy_l)
        lw4 = 0.85*inch; lh4 = 0.28*inch
        lx4 = (x0+x1)/2 - lw4/2; ly4 = cy_l - lh4 - 0.02*inch
        c.setFillColor(OR_BG); c.roundRect(lx4, ly4, lw4, lh4, 0.02*inch, fill=True, stroke=False)
        c.setStrokeColor(OR_C); c.setLineWidth(0.4)
        c.roundRect(lx4, ly4, lw4, lh4, 0.02*inch, fill=False, stroke=True)
        c.setFillColor(OR_C); c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString((x0+x1)/2, ly4 + lh4 - 0.09*inch, f"{L_mm} mm")
        c.setFont("Helvetica", 6)
        c.drawCentredString((x0+x1)/2, ly4 + 0.055*inch, _dvf_local(L_po))

        # Nom du mur
        c.setFillColor(cl.HexColor("#1F3864")); c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x_off + half_w/2, y_top + 0.15*inch, mc.get('nom','').upper())

    # Séparateur vertical central
    c.setStrokeColor(cl.HexColor("#CCCCCC")); c.setLineWidth(0.8)
    c.setDash(4, 4)
    c.line(w/2, BOT_H, w/2, h - HDR_H)
    c.setDash()

    # Gauche : mirror=True (côté LONG vers le centre)
    # Droite : mirror=False (côté LONG déjà vers le centre)
    _draw_one(mc_g, 0,       mirror=True)
    _draw_one(mc_d, half_w,  mirror=False)


def _entete_mini(c, w, h, inch, colors, mur_calc):
    from reportlab.lib import colors as cl
    BLEU = cl.HexColor("#1F3864")
    OR_C = cl.HexColor("#C68B00")
    c.setFillColor(BLEU)
    c.rect(0, h - 0.55*inch, w, 0.55*inch, fill=True, stroke=False)
    c.setFillColor(OR_C); c.setFont("Helvetica-Bold", 10)
    c.drawString(0.4*inch, h - 0.32*inch, "SOLARIUM PRO -- CADRE / TRAPEZE  --  MONTAGE")
    c.setFillColor(cl.white); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch, h - 0.48*inch, f"Dessin de montage -- {mur_calc['nom']}")


print("Module dessin montage Cadre / Trapeze v1 OK")
