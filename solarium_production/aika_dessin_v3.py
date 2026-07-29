"""
Logique de dessin Aika — tous modèles A à G
"""

# ── LOGIQUE DES MODÈLES ──────────────────────────────────────────────────────
# Chaque modèle définit:
#   - nb_operants: nombre de panneaux opérants
#   - operant_pos: position des opérants ('droite', 'gauche', 'centre')
#   - serrures: liste des serrures
#   - coupe_logique: comment répartir les panneaux dans les rails en coupe

MODELES = {
    'A': {
        'desc': '1 opérant — poignée droite, coulisse gauche',
        'operants': [('dernier', 'droite')],  # (position panneau, côté poignée)
        'serrures': ['poignee_droite'],
        'coupe': 'lateral_droite',  # opérant rail int à droite
    },
    'B': {
        'desc': '1 opérant — poignée gauche, coulisse droite',
        'operants': [('premier', 'gauche')],
        'serrures': ['poignee_gauche'],
        'coupe': 'lateral_gauche',
    },
    'C': {
        'desc': '1 opérant principal droite + serrures 2 extrémités',
        'operants': [('dernier', 'droite')],
        'serrures': ['poignee_droite', 'serrure_gauche'],
        'coupe': 'lateral_droite',
    },
    'D': {
        'desc': '1 opérant principal gauche + serrures 2 extrémités',
        'operants': [('premier', 'gauche')],
        'serrures': ['poignee_gauche', 'serrure_droite'],
        'coupe': 'lateral_gauche',
    },
    'E': {
        'desc': 'Ouverture centrale — 2 serrures centre',
        'operants': [('centre_gauche', 'gauche'), ('centre_droite', 'droite')],
        'serrures': ['poignee_centre_gauche', 'poignee_centre_droite'],
        'coupe': 'central',
    },
    'F': {
        'desc': 'Ouverture centrale — 2 serrures centre + 1 extrémité gauche',
        'operants': [('centre_gauche', 'gauche'), ('centre_droite', 'droite')],
        'serrures': ['poignee_centre_gauche', 'poignee_centre_droite', 'serrure_gauche'],
        'coupe': 'central',
    },
    'G': {
        'desc': 'Ouverture centrale — 2 serrures centre + 1 extrémité droite',
        'operants': [('centre_gauche', 'gauche'), ('centre_droite', 'droite')],
        'serrures': ['poignee_centre_gauche', 'poignee_centre_droite', 'serrure_droite'],
        'coupe': 'central',
    },
}


def get_pan_largeurs(mur):
    """
    Retourne la liste des largeurs de panneaux en mm.
    Pour modèles latéraux (A,B,C,D): extrémités différentes des intermédiaires
    Pour modèles centraux (E,F,G): tous égaux
    """
    verres = mur.get('verres', [])
    nb = mur['nb_panneaux']
    modele_lettre = mur.get('modele', 'A')[0].upper()

    # Reconstruire liste depuis les verres
    pan_larg = []
    for v in verres:
        for _ in range(v['qte']):
            pan_larg.append(v['larg_mm'])
    while len(pan_larg) < nb:
        pan_larg.append(pan_larg[-1] if pan_larg else mur['largeur_mm'] // nb)
    return pan_larg[:nb]


def get_coupe_rails(nb_panneaux, nb_rails, modele_lettre):
    """
    Retourne la répartition des panneaux dans les rails pour la vue en coupe.
    
    Règles:
    - Si nb_panneaux <= nb_rails: 1 panneau par rail (chacun dans son rail)
    - Si nb_panneaux > nb_rails: accordéon
      - Latéral (A,B,C,D): P1+Pn rail ext, P2+P(n-1) rail 2, etc.
      - Central (E,F,G): même logique accordéon
    """
    pan_par_rail = nb_panneaux / nb_rails

    if pan_par_rail <= 1.0:
        # 1 panneau par rail — chacun dans son rail
        rails = [[i] for i in range(nb_panneaux)]
        # Compléter avec rails vides si besoin
        while len(rails) < nb_rails:
            rails.append([])
        return rails

    # Accordéon: P1+Pn, P2+P(n-1), ...
    rails = []
    for r in range(nb_rails):
        gauche_idx = r
        droite_idx = nb_panneaux - 1 - r
        if gauche_idx < droite_idx:
            rails.append([gauche_idx, droite_idx])
        elif gauche_idx == droite_idx:
            rails.append([gauche_idx])
        else:
            rails.append([])
    return rails


def dessiner_mur_aika_v3(c, y, mur_calc, w, h, inch, colors, BLEU, OR):
    """
    Dessin complet style Cielo avec:
    - Montants uniformes
    - Étiquettes dans les panneaux
    - Vue en coupe selon modèle
    - Opérant fond bleuté
    """
    from fractions import Fraction

    def dvf(d):
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

    BLEU_C  = colors.HexColor("#0000CC")
    GRIS_R  = colors.HexColor("#C8D3E8")
    BLEU_V  = colors.HexColor("#D6E4F0")
    BLEU_OP = colors.HexColor("#EEF4FC")
    GRIS_H  = colors.HexColor("#4A6FA5")

    L_mm   = mur_calc['largeur_mm']
    H_mm   = mur_calc['hauteur_mm']
    L_po   = mur_calc['largeur_po']
    H_po   = mur_calc['hauteur_po']
    nb     = mur_calc['nb_panneaux']
    rails  = mur_calc['nb_rails']
    modele = mur_calc.get('modele', 'A/i')
    modele_lettre = modele[0].upper() if modele else 'A'
    sens   = "VUE DE L'INTÉRIEUR" if modele and modele[-1].lower() == 'i' else "VUE DE L'EXTÉRIEUR"
    modele_affiche = f"{modele_lettre}/{rails}"  # ex: F/4, A/4
    modele_info = MODELES.get(modele_lettre, MODELES['A'])
    coupe_type = modele_info['coupe']

    # Largeurs panneaux
    pan_larg = get_pan_largeurs(mur_calc)

    # Dimensions zones
    mg_l = 0.85*inch
    mg_r = 0.35*inch
    zone_w = w - mg_l - mg_r
    ratio = H_mm / L_mm
    vue_h = min(zone_w * ratio, 5.0*inch)
    vue_w = vue_h / ratio
    if vue_w > zone_w: vue_w = zone_w; vue_h = vue_w * ratio
    x0 = mg_l + (zone_w - vue_w) / 2

    rh_coupe = 0.17*inch
    gap_c    = 0.03*inch
    coupe_h  = 0.12*inch + (rails + 1) * (rh_coupe + gap_c) + 0.25*inch
    espace   = 0.22*inch + vue_h + 0.55*inch + coupe_h

    if y - espace < 0.9*inch:
        c.showPage(); entete_mini(c, w, h, inch, colors, BLEU, OR, mur_calc); y = h - 1.2*inch

    # ── TITRE style Cielo ──
    # Partie 1: nom mur / côté 1 /
    c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 7)
    partie1 = f"{mur_calc['nom'].upper()} / CÔTÉ 1 / "
    c.drawString(x0, y, partie1)
    w1 = c.stringWidth(partie1, "Helvetica-Bold", 7)
    # Partie 2: sens (INTÉRIEUR/EXTÉRIEUR) en gras rouge
    c.setFillColor(colors.HexColor("#CC0000"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x0 + w1, y, sens)
    w2 = c.stringWidth(sens, "Helvetica-Bold", 8)
    # Partie 3: couleur et modèle
    c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 7)
    partie3 = f" / {mur_calc['couleur_alu']} — Modèle {modele_affiche}"
    c.drawString(x0 + w1 + w2, y, partie3)
    y -= 0.20*inch

    y_vue_top = y
    y_bot = y_vue_top - vue_h

    # Épaisseur montant uniforme
    mont_mm = 8   # ~8mm comme Cielo
    px_mm = vue_w / L_mm
    mont_px = max(5, mont_mm * px_mm)

    # Calcul positions panneaux
    # Structure: [mont][P1][mont][P2][mont]...[Pn][mont]
    total_monts = (nb + 1) * mont_px
    total_verres_mm = sum(pan_larg)
    scale = (vue_w - total_monts) / total_verres_mm if total_verres_mm > 0 else 1

    pan_pos = []  # (x_debut, largeur_px) par panneau
    x_cur = x0 + mont_px
    for larg in pan_larg:
        pw = larg * scale
        pan_pos.append((x_cur, pw))
        x_cur += pw + mont_px

    # Identifier panneaux opérants selon modèle
    operants_idx = set()
    if modele_lettre in ('A', 'C'):
        operants_idx.add(nb - 1)
    elif modele_lettre in ('B', 'D'):
        operants_idx.add(0)
    elif modele_lettre in ('E', 'F', 'G'):
        operants_idx.add(nb // 2 - 1)
        operants_idx.add(nb // 2)

    # ── FOND: blanc pour fixes, bleu pour opérants ──
    c.setFillColor(colors.white)
    c.rect(x0, y_bot, vue_w, vue_h, fill=True, stroke=False)
    for i, (px, pw) in enumerate(pan_pos):
        if i in operants_idx:
            c.setFillColor(BLEU_OP)
        else:
            c.setFillColor(colors.white)
        c.rect(px, y_bot + 0.12*inch, pw, vue_h - 0.24*inch, fill=True, stroke=False)

    # ── RAILS haut/bas ──
    c.setFillColor(GRIS_R)
    c.rect(x0, y_bot + vue_h - 0.12*inch, vue_w, 0.12*inch, fill=True, stroke=False)
    c.rect(x0, y_bot, vue_w, 0.12*inch, fill=True, stroke=False)

    # ── MONTANTS UNIFORMES ──
    c.setFillColor(GRIS_R)
    x_cur = x0
    for i in range(nb + 1):
        c.rect(x_cur, y_bot, mont_px, vue_h, fill=True, stroke=False)
        if i < nb:
            x_cur += mont_px + pan_pos[i][1]

    # ── CADRE extérieur ──
    c.setStrokeColor(BLEU_C); c.setLineWidth(1.8)
    c.rect(x0, y_bot, vue_w, vue_h, fill=False, stroke=True)
    c.setLineWidth(0.5)

    # ── HACHURES + ÉTIQUETTES ──
    for i, (px, pw) in enumerate(pan_pos):
        cx = px + pw / 2
        cy = y_bot + vue_h / 2

        # Hachures
        c.setStrokeColor(GRIS_H); c.setLineWidth(0.7)
        gap = 0.09*inch
        for k in range(-2, 3):
            ox = k * gap
            c.line(cx+ox-0.08*inch, cy-0.13*inch, cx+ox+0.08*inch, cy+0.13*inch)

        # Étiquette dans le panneau
        lbl_w = min(pw - 4, 0.9*inch)
        lbl_h = 0.26*inch
        lbl_x = cx - lbl_w / 2
        lbl_y = y_bot + vue_h - 0.12*inch - lbl_h - 0.04*inch

        bg = colors.HexColor("#B8D0EC") if i in operants_idx else BLEU_V
        c.setFillColor(bg)
        c.roundRect(lbl_x, lbl_y, lbl_w, lbl_h, 0.03*inch, fill=True, stroke=False)
        c.setStrokeColor(BLEU_C); c.setLineWidth(0.4)
        c.roundRect(lbl_x, lbl_y, lbl_w, lbl_h, 0.03*inch, fill=False, stroke=True)

        if lbl_w > 0.45*inch:
            # Trouver largeur et hauteur verre pour ce panneau
            v_larg = pan_larg[i] + 16  # largeur verre = largeur panneau + 16mm
            cnt = 0
            for v in mur_calc.get('verres', []):
                cnt += v['qte']
                if i < cnt:
                    v_larg = v['larg_mm']
                    break
            v_haut = mur_calc['verres'][0]['haut_mm'] if mur_calc.get('verres') else H_mm - 132

            c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(cx, lbl_y + lbl_h - 0.10*inch, f"{v_larg} mm")
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(cx, lbl_y + 0.07*inch, f"{v_haut} mm")

        # Label opérant
        if i in operants_idx:
            c.setFillColor(BLEU_C); c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(cx, y_bot + 0.08*inch, "Opérant")

    # ── POIGNÉES ──
    c.setFillColor(BLEU_C)
    poig_h = 0.34*inch
    poig_w = 0.04*inch

    def poignee(xp, yp):
        c.roundRect(xp, yp - poig_h/2, poig_w, poig_h, 0.01*inch, fill=True, stroke=False)
        c.setFillColor(colors.white); c.setStrokeColor(BLEU_C); c.setLineWidth(0.8)
        c.rect(xp - 0.03*inch, yp - 0.05*inch, 0.10*inch, 0.06*inch, fill=True, stroke=True)
        c.setFillColor(BLEU_C)

    yp = y_bot + vue_h / 2

    if modele_lettre in ('A', 'C'):
        poignee(x0 + vue_w - poig_w/2, yp)
    elif modele_lettre in ('B', 'D'):
        poignee(x0 - poig_w/2, yp)
    elif modele_lettre in ('E', 'F', 'G'):
        # 2 poignées au centre
        xc = x0 + vue_w / 2
        c.rect(xc - mont_px/2 - poig_w, yp - poig_h/2, poig_w, poig_h, fill=True, stroke=False)
        c.rect(xc + mont_px/2, yp - poig_h/2, poig_w, poig_h, fill=True, stroke=False)
        # Serrure extrémité gauche pour F
        if modele_lettre == 'F':
            c.rect(x0, yp - 0.15*inch, 0.04*inch, 0.30*inch, fill=True, stroke=False)
        # Serrure extrémité droite pour G
        elif modele_lettre == 'G':
            c.rect(x0 + vue_w - 0.04*inch, yp - 0.15*inch, 0.04*inch, 0.30*inch, fill=True, stroke=False)

    # Serrure extrémités C et D
    if modele_lettre == 'C':
        c.rect(x0, yp - 0.15*inch, 0.04*inch, 0.30*inch, fill=True, stroke=False)
    elif modele_lettre == 'D':
        c.rect(x0 + vue_w - 0.04*inch, yp - 0.15*inch, 0.04*inch, 0.30*inch, fill=True, stroke=False)

    # ── FLÈCHES ouverture ──
    c.setStrokeColor(BLEU_C); c.setLineWidth(0.8)
    c.setDash([3, 2])
    yf = y_bot + vue_h * 0.6

    if modele_lettre in ('A', 'C'):
        px_op, pw_op = pan_pos[nb-1]
        c.line(px_op + pw_op * 0.7, yf, px_op + pw_op * 0.1, yf)
        _fleche(c, px_op + pw_op * 0.1, yf, BLEU_C)
    elif modele_lettre in ('B', 'D'):
        px_op, pw_op = pan_pos[0]
        c.line(px_op + pw_op * 0.3, yf, px_op + pw_op * 0.9, yf)
        _fleche(c, px_op + pw_op * 0.9, yf, BLEU_C)
    elif modele_lettre in ('E', 'F', 'G'):
        cg = nb // 2 - 1; cd = nb // 2
        if cg >= 0:
            px, pw = pan_pos[cg]
            c.line(px + pw * 0.7, yf, px + pw * 0.1, yf)
            _fleche(c, px + pw * 0.1, yf, BLEU_C)
        if cd < len(pan_pos):
            px, pw = pan_pos[cd]
            c.line(px + pw * 0.3, yf, px + pw * 0.9, yf)
            _fleche(c, px + pw * 0.9, yf, BLEU_C)
    c.setDash([])

    # ── COTES ──
    c.setStrokeColor(BLEU_C); c.setFillColor(BLEU_C); c.setLineWidth(0.6)
    # H gauche
    cx_h = x0 - 0.24*inch
    c.line(cx_h, y_bot, x0 - 0.04*inch, y_bot)
    c.line(cx_h, y_bot + vue_h, x0 - 0.04*inch, y_bot + vue_h)
    c.line(cx_h, y_bot, cx_h, y_bot + vue_h)
    c.saveState()
    c.translate(cx_h - 0.10*inch, y_bot + vue_h/2); c.rotate(90)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(0, 0, f"{H_mm} mm")
    c.restoreState()
    # L bas
    cy_l = y_bot - 0.18*inch
    c.line(x0, cy_l, x0 + vue_w, cy_l)
    c.line(x0, y_bot - 0.03*inch, x0, cy_l)
    c.line(x0 + vue_w, y_bot - 0.03*inch, x0 + vue_w, cy_l)
    c.line(x0, cy_l, x0 + 0.08*inch, cy_l)
    c.line(x0 + vue_w, cy_l, x0 + vue_w - 0.08*inch, cy_l)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x0 + vue_w/2, cy_l - 0.10*inch, f"{L_mm} mm")

    y_apres = y_bot - 0.42*inch

    # ── SÉPARATEUR ──
    c.setStrokeColor(colors.HexColor("#CCCCCC")); c.setLineWidth(0.3)
    c.setDash([3, 3]); c.line(x0, y_apres + 0.08*inch, x0 + vue_w, y_apres + 0.08*inch); c.setDash([])
    c.setFillColor(colors.HexColor("#666")); c.setFont("Helvetica", 6.5)
    c.drawString(x0, y_apres + 0.11*inch, "Vue en coupe (dessus)")

    # ── VUE EN COUPE ──
    y_c = y_apres - 0.04*inch
    lbl_x = x0 - 0.06*inch

    coupe_rails = get_coupe_rails(nb, rails, modele_lettre)

    # Mur arrière
    c.setFillColor(GRIS_R); c.setStrokeColor(BLEU_C); c.setLineWidth(0.7)
    c.rect(x0, y_c - 0.10*inch, vue_w, 0.10*inch, fill=True, stroke=True)
    c.setFillColor(colors.HexColor("#555")); c.setFont("Helvetica", 6)
    c.drawRightString(lbl_x, y_c - 0.06*inch, "Mur")

    rl_labels = {0: "Rail ext.", rails-1: "Rail int."}
    for r in range(1, rails-1):
        rl_labels[r] = f"Rail {r+1}"

    y_r = y_c - 0.10*inch - gap_c

    for ri, pan_list in enumerate(coupe_rails):
        c.setFillColor(colors.white); c.setStrokeColor(BLEU_C); c.setLineWidth(0.7)
        c.rect(x0, y_r - rh_coupe, vue_w, rh_coupe, fill=True, stroke=True)

        for pi in pan_list:
            if pi < len(pan_pos):
                px_v, pw_v = pan_pos[pi]
                est_op = pi in operants_idx
                mg = 0.01*inch
                c.setFillColor(BLEU_OP if est_op else BLEU_V)
                c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
                c.rect(px_v + mg, y_r - rh_coupe + 0.02*inch,
                       pw_v - 2*mg, rh_coupe - 0.04*inch, fill=True, stroke=True)
                # Label court
                lbl = f"P.{pi+1}" + (" Op." if est_op else "")
                c.setFillColor(BLEU_C); c.setFont("Helvetica", 5.5)
                if pw_v > 0.35*inch:
                    c.drawCentredString(px_v + pw_v/2, y_r - rh_coupe/2 - 0.02*inch, lbl)

                # Poignées dans coupe
                if est_op:
                    if modele_lettre in ('A', 'C') and pi == nb-1:
                        c.setFillColor(BLEU_C)
                        c.rect(px_v + pw_v - 0.025*inch, y_r - rh_coupe, 0.025*inch, rh_coupe, fill=True, stroke=False)
                    elif modele_lettre in ('B', 'D') and pi == 0:
                        c.setFillColor(BLEU_C)
                        c.rect(px_v, y_r - rh_coupe, 0.025*inch, rh_coupe, fill=True, stroke=False)

        # Poignées centrales dans coupe
        if modele_lettre in ('E', 'F', 'G') and ri == rails - 1:
            xc = x0 + vue_w / 2
            c.setFillColor(BLEU_C)
            c.rect(xc - mont_px/2 - 0.025*inch, y_r - rh_coupe, 0.025*inch, rh_coupe, fill=True, stroke=False)
            c.rect(xc + mont_px/2, y_r - rh_coupe, 0.025*inch, rh_coupe, fill=True, stroke=False)

        c.setFillColor(colors.HexColor("#555")); c.setFont("Helvetica", 6)
        c.drawRightString(lbl_x, y_r - rh_coupe/2 - 0.02*inch, rl_labels.get(ri, f"Rail {ri+1}"))
        y_r -= rh_coupe + gap_c

    # Façade
    c.setFillColor(colors.HexColor("#AAAAAA")); c.setStrokeColor(BLEU_C); c.setLineWidth(0.5)
    c.rect(x0, y_r - 0.05*inch, vue_w, 0.05*inch, fill=True, stroke=True)
    c.setFillColor(colors.HexColor("#555")); c.drawRightString(lbl_x, y_r - 0.03*inch, "Int.")

    return y_r - 0.22*inch


def _fleche(c, x, y, couleur):
    """Petite flèche manuelle"""
    from reportlab.lib import colors
    c.setFillColor(couleur); c.setStrokeColor(couleur); c.setLineWidth(0.8)
    # Tête de flèche simple
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x + 0.06*72, y + 0.03*72)
    p.lineTo(x + 0.06*72, y - 0.03*72)
    p.close()
    c.drawPath(p, fill=True, stroke=False)


def entete_mini(c, w, h, inch, colors, BLEU, OR, mur_calc):
    from reportlab.lib import colors as cl
    c.setFillColor(BLEU)
    c.rect(0, h - 0.55*inch, w, 0.55*inch, fill=True, stroke=False)
    c.setFillColor(OR); c.setFont("Helvetica-Bold", 10)
    c.drawString(0.4*inch, h - 0.32*inch, "SOLARIUM PRO — AIKA 6mm")
    c.setFillColor(cl.white); c.setFont("Helvetica", 7)
    c.drawString(0.4*inch, h - 0.48*inch, f"Approbation — {mur_calc['nom']}")

print("Module dessin Aika v3 OK")
