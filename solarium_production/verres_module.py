"""
Bon de commande verre IGP — Solarium Pro
Cover 10mm : dessins techniques avec trous (4R / 5R / TRIVEL) + cartouche coverglobal.com
Aika 6mm   : dessins sans trous, sans cartouche
"""
import os, re as _re, math
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo_Pro_Horizontal.png")

MAUVE  = colors.HexColor("#C299D4")
JAUNE  = colors.HexColor("#F5E642")
NOIR   = colors.HexColor("#000000")
BLEU_L = colors.HexColor("#0070C0")

CONTACT = {
    "tel":    "450-956-4330",
    "email":  "crainville@solariumpro.ca",
    "bureau": "Bureau : 433, rue Boivin Granby",
    "usine":  "Usine : 495, rue Edouard, Granby",
}

def _fvd(s):
    s = str(s).strip().replace('"','').replace("'","")
    if not s: return 0.0
    m = _re.match(r'^(\d+)[-\s]+(\d+)/(\d+)$', s)
    if m: return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m2 = _re.match(r'^(\d+)/(\d+)$', s)
    if m2: return int(m2.group(1))/int(m2.group(2))
    try: return float(s)
    except: return 0.0

def _crosshair(c, cx, cy, r=4.5):
    c.setLineWidth(0.6)
    c.circle(cx, cy, r, fill=False, stroke=True)
    c.line(cx - r*1.7, cy, cx + r*1.7, cy)
    c.line(cx, cy - r*1.7, cx, cy + r*1.7)

def _arrow_h(c, x1, x2, y, lbl, fs=6.5):
    sz = 4
    c.setLineWidth(0.45)
    c.line(x1, y, x2, y)
    for xp, d in [(x1, 1), (x2, -1)]:
        c.line(xp, y, xp + d*sz, y + sz*0.45)
        c.line(xp, y, xp + d*sz, y - sz*0.45)
    c.setFont("Helvetica", fs)
    c.drawCentredString((x1+x2)/2, y - fs - 2, lbl)

def _arrow_v(c, x, y1, y2, lbl, fs=6.5, offset=-14):
    sz = 4
    c.setLineWidth(0.45)
    c.line(x, y1, x, y2)
    for yp, d in [(y1, 1), (y2, -1)]:
        c.line(x, yp, x + sz*0.45, yp + d*sz)
        c.line(x, yp, x - sz*0.45, yp + d*sz)
    c.saveState()
    c.translate(x + offset, (y1+y2)/2)
    c.rotate(90)
    c.setFont("Helvetica", fs)
    c.drawCentredString(0, 0, lbl)
    c.restoreState()

def _tick(c, x, ya, yb):
    c.setLineWidth(0.3)
    c.line(x, ya, x, yb)


# ─── PAGE 1 : BON DE COMMANDE ────────────────────────────────────────────────
def _page_bon_commande(c, params, total_verres, epaisseur, produit):
    w, h = letter
    # Logo
    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, 0.5*inch, h - 1.4*inch, width=2.4*inch,
                    preserveAspectRatio=True, mask='auto')
    # Contact top-right
    c.setFont("Helvetica", 9); c.setFillColor(NOIR)
    c.drawRightString(w - 0.45*inch, h - 0.52*inch, CONTACT["tel"])
    c.setFillColor(BLEU_L)
    c.drawRightString(w - 0.45*inch, h - 0.70*inch, CONTACT["email"])
    c.setFillColor(NOIR)
    c.drawRightString(w - 0.45*inch, h - 0.88*inch, CONTACT["bureau"])
    c.drawRightString(w - 0.45*inch, h - 1.06*inch, CONTACT["usine"])
    # Title
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w/2, h - 1.65*inch, "Bon de commande")
    # Job / Date
    y = h - 2.10*inch
    no_proj = params.get("no_projet",""); client = params.get("client","")
    c.setFont("Helvetica", 10)
    c.drawString(0.5*inch, y, f"Job :  {no_proj}")
    c.drawRightString(w - 0.5*inch, y, f"Date :  {date.today().strftime('%d %B %Y')}")
    c.setLineWidth(0.5)
    c.line(0.5*inch, y - 3, w - 0.5*inch, y - 3)
    # Descriptif
    y -= 0.40*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.5*inch, y, "Descriptif :")
    c.line(0.5*inch, y - 3, w - 0.5*inch, y - 3)
    # Récupérer couleur verre du premier mur
    murs = params.get("murs",[])
    couleur_v = murs[0].get("couleur_verre","Clair") if murs else "Clair"
    couleur_txt = "clairs" if couleur_v == "Clair" else couleur_v.lower()
    y -= 0.40*inch
    if produit == 'cover':
        ligne1 = (f"Commande de {total_verres} verres {epaisseur}, {couleur_txt}, "
                  f"trempés, poli contour 4 faces. Perçage précis tel que croquis")
    else:
        ligne1 = (f"Commande de {total_verres} verres {epaisseur}, {couleur_txt}, "
                  f"trempés, poli contour 4 faces.")
    c.drawString(0.5*inch, y, ligne1)
    c.line(0.5*inch, y - 3, w - 0.5*inch, y - 3)
    y -= 0.40*inch
    c.drawString(0.5*inch, y, "Attention de bien Identifier les verres. Merci.")
    c.line(0.5*inch, y - 3, w - 0.5*inch, y - 3)
    for _ in range(5):
        y -= 0.35*inch
        c.line(0.5*inch, y, w - 0.5*inch, y)
    # Signatures bas de page
    yb = 1.35*inch
    c.setFont("Helvetica", 10)
    c.drawString(w*0.35, yb, "Date de livraison :  _______________________")
    c.drawString(w*0.35, yb - 0.35*inch, "Signature :  _______________________")


# ─── PAGE DESSIN TECHNIQUE ────────────────────────────────────────────────────
def _page_dessin(c, mur_nom, pan_num, larg_mm, haut_mm, type_verre, produit, total_pan):
    w, h = letter
    MAR    = 0.45*inch
    CART_H = 1.60*inch if produit == 'cover' else 0.0
    TOP    = 0.55*inch   # espace badges au-dessus du verre

    # Zone disponible pour le verre
    avail_w = w - 2*MAR - 0.90*inch   # laisser marge droite pour cote H
    avail_h = h - 2*MAR - CART_H - TOP - 0.50*inch  # laisser espace bas pour cote W

    # Échelle pour que le verre tienne dans la zone
    sx = avail_w / larg_mm
    sy = avail_h / haut_mm
    sc = min(sx, sy) * 0.88   # 12% de marge intérieure

    gw = larg_mm * sc   # largeur verre en pts
    gh = haut_mm * sc   # hauteur verre en pts

    # Position verre : centré horizontalement, calé en bas de la zone dessin
    gx0 = MAR + (avail_w - gw) / 2
    gy0 = MAR + CART_H + 0.35*inch   # bas du verre
    gx1 = gx0 + gw
    gy1 = gy0 + gh

    # Helpers mm → points depuis coin bas-gauche du verre
    def gx(mm): return gx0 + mm * sc
    def gy(mm): return gy0 + mm * sc

    # ── Fond blanc + bordure verre ──
    c.setFillColor(colors.white)
    c.setStrokeColor(NOIR)
    c.setLineWidth(1.2)
    c.rect(gx0, gy0, gw, gh, fill=True, stroke=True)

    # ── Cadre extérieur de la zone de dessin ──
    c.setLineWidth(0.7)
    frame_margin = 0.12*inch
    c.rect(MAR - frame_margin, MAR + CART_H - frame_margin,
           w - 2*MAR + 2*frame_margin, h - 2*MAR - CART_H + 2*frame_margin,
           fill=False, stroke=True)

    # ── Badges ──
    bw = max(1.0*inch, len(f"{mur_nom} #{pan_num}") * 0.07*inch)
    bh = 0.285*inch
    bx = gx0 + gw * 0.22
    by = gy0 + gh * 0.60
    c.setFillColor(MAUVE)
    c.roundRect(bx, by, bw, bh, 4, fill=True, stroke=False)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bx + bw/2, by + 8, f"{mur_nom} #{pan_num}")

    bw2 = 0.44*inch
    c.setFillColor(JAUNE)
    c.roundRect(bx, by - bh - 5, bw2, bh, 4, fill=True, stroke=False)
    c.setFillColor(NOIR); c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(bx + bw2/2, by - bh - 5 + 8, "1x")

    # ── Cote W (bas, horizontal) ──
    dim_y  = gy0 - 0.30*inch
    tick_y = gy0 - 0.06*inch
    c.setFillColor(NOIR); c.setStrokeColor(NOIR)
    _tick(c, gx0, tick_y, dim_y)
    _tick(c, gx1, tick_y, dim_y)
    _arrow_h(c, gx0, gx1, dim_y, f"W \u00b10.5    {larg_mm}mm", fs=7.5)

    # ── Cote H (droite, vertical) ──
    dim_x  = gx1 + 0.42*inch
    tick_x = gx1 + 0.07*inch
    c.setLineWidth(0.3)
    c.line(tick_x, gy0, dim_x + 0.06*inch, gy0)
    c.line(tick_x, gy1, dim_x + 0.06*inch, gy1)
    _arrow_v(c, dim_x, gy0, gy1, f"H \u00b10.5    {haut_mm}mm", fs=7.5, offset=14)

    # ── Trous de perçage (Cover seulement) ──
    if produit == 'cover':
        c.setStrokeColor(NOIR); c.setFillColor(NOIR)

        # 2 trous de fixation en haut
        top_y = gy(haut_mm - 108)
        top_y = min(top_y, gy1 - 8)   # ne pas dépasser le bord
        lx = gx(larg_mm * 0.28)
        rx = gx(larg_mm * 0.72)
        _crosshair(c, lx, top_y)
        _crosshair(c, rx, top_y)

        # Trou knob bas-gauche Ø9.54 à (65, 25)mm
        kx = gx(65); ky = gy(25)
        if kx > gx0 + 4 and kx < gx1 - 4 and ky > gy0 + 4:
            _crosshair(c, kx, ky)
            c.setFont("Helvetica", 6)
            c.drawString(kx + 5, ky + 3, "\u00d89.54")
            # 65 ±1 (horizontal)
            c.setLineWidth(0.3)
            ann_y = gy0 - 0.10*inch
            c.line(gx0, ann_y, kx, ann_y)
            c.line(gx0, gy0 - 3, gx0, ann_y); c.line(kx, gy0 - 3, kx, ann_y)
            c.setFont("Helvetica", 6)
            c.drawCentredString((gx0+kx)/2, ann_y - 7, "65 \u00b11")
            # 25 ±1 (vertical)
            ann_x2 = gx0 - 0.14*inch
            c.line(ann_x2, gy0, ann_x2, ky)
            c.line(gx0 - 3, gy0, ann_x2, gy0); c.line(gx0 - 3, ky, ann_x2, ky)
            c.saveState()
            c.translate(ann_x2 - 7, (gy0+ky)/2)
            c.rotate(90); c.setFont("Helvetica", 6)
            c.drawCentredString(0, 0, "25 \u00b11"); c.restoreState()

        # Trou bas-droite à (W-15, 36)mm
        brx = gx(larg_mm - 15); bry = gy(36)
        if brx < gx1 - 3 and bry > gy0 + 3:
            _crosshair(c, brx, bry)
            c.setFont("Helvetica", 6)
            c.drawString(brx + 4, bry + 4, "15")
            c.drawString(brx - 12, bry - 9, "36")

        if '5R' in type_verre:
            # Trou latéral (108, 920)mm
            shx = gx(108); shy = gy(920)
            if shy < gy1 - 4 and shy > gy0 + 4:
                _crosshair(c, shx, shy)
                c.setFont("Helvetica", 6)
                c.drawString(gx0 - 36, shy - 3, "X=108")
                c.saveState()
                c.translate(gx0 - 24, (gy0 + shy)/2)
                c.rotate(90); c.setFont("Helvetica", 6)
                c.drawCentredString(0, 0, "Y=920"); c.restoreState()

        elif 'TRIVEL' in type_verre:
            # Encoche TRIVEL haut-droite: 71mm from right, 130mm deep, R6
            nw = 71 * sc; nd = 130 * sc; r6 = max(6 * sc, 3)
            nx0 = gx1 - nw   # left edge of notch
            ny0 = gy1 - nd   # bottom of notch

            # Dessiner l'encoche (fond gris = fond blanc du verre + trait)
            c.setFillColor(colors.HexColor("#E8E8E8"))
            c.setStrokeColor(NOIR); c.setLineWidth(0.8)
            p = c.beginPath()
            p.moveTo(nx0, gy1)
            p.lineTo(gx1, gy1)
            p.lineTo(gx1, ny0 + r6)
            p.curveTo(gx1, ny0, gx1 - r6, ny0, nx0 + r6, ny0)
            p.lineTo(nx0, ny0)
            p.lineTo(nx0, gy1)
            p.close()
            c.drawPath(p, fill=True, stroke=True)

            # Cotes encoche
            c.setFillColor(NOIR); c.setFont("Helvetica", 6); c.setLineWidth(0.3)
            # 71 en haut
            c.line(nx0, gy1 + 6, gx1, gy1 + 6)
            c.drawCentredString((nx0+gx1)/2, gy1 + 8, "71")
            # 130 à droite
            c.saveState()
            c.translate(gx1 + 10, (gy1 + ny0)/2)
            c.rotate(90); c.setFont("Helvetica", 6)
            c.drawCentredString(0, 0, "130"); c.restoreState()
            # R6
            c.drawString(nx0 - 3, ny0 - 10, "R6")
            # Y 920
            y920 = gy(920)
            if y920 > gy0 and y920 < gy1:
                c.setLineWidth(0.3)
                c.line(gx1 + 3, y920, gx1 + 14, y920)
                c.setFont("Helvetica", 6)
                c.drawString(gx1 + 15, y920 - 3, "Y 920")

    # ── Cartouche (Cover seulement) ──
    if produit == 'cover':
        _cartouche(c, w, h, MAR, CART_H, type_verre, pan_num, total_pan)


def _cartouche(c, w, h, MAR, CART_H, type_verre, pan_num, total_pan):
    cx0 = MAR - 0.12*inch
    cx1 = w - MAR + 0.12*inch
    cy0 = MAR
    cy1 = cy0 + CART_H
    cw  = cx1 - cx0

    c.setStrokeColor(NOIR); c.setFillColor(colors.white)
    c.setLineWidth(0.7)
    c.rect(cx0, cy0, cw, CART_H, fill=True, stroke=True)

    # Séparateur horizontal au 2/5
    div_y = cy0 + CART_H * 0.42
    c.setLineWidth(0.35)
    c.line(cx0, div_y, cx1, div_y)

    # Colonnes verticales de la section basse (nom/signature/date/ref/rev/title)
    cols = [cx0 + cw*0.11, cx0 + cw*0.21, cx0 + cw*0.31, cx0 + cw*0.46, cx0 + cw*0.50]
    for x in cols:
        c.line(x, cy0, x, div_y)

    row_h = (div_y - cy0) / 4
    for i in range(1, 4):
        c.line(cx0, cy0 + i*row_h, cols[3], cy0 + i*row_h)

    labels = ["DRAWN","CHKD","APPV'D","MFG","Q.A."]
    row_ys = [cy0 + 3*row_h + 3, cy0 + 2*row_h + 3, cy0 + 1*row_h + 3, cy0 + 3, cy0 + 3]
    # only 4 rows — merge MFG and Q.A.
    row_ys = [cy0 + 3*row_h + 3, cy0 + 2*row_h + 3, cy0 + row_h + 3, cy0 + 3]
    for i, (lbl, ry) in enumerate(zip(["DRAWN","CHKD","APPV'D","Q.A."], row_ys)):
        c.setFont("Helvetica", 6); c.setFillColor(NOIR)
        c.drawString(cx0 + 2, ry, lbl)
    # Valeurs DRAWN
    c.drawString(cols[0] + 2, cy0 + 3*row_h + 3, "SCH")
    c.drawString(cols[1] + 2, cy0 + 3*row_h + 3, "15/11/2012")
    c.drawString(cols[2] + 2, cy0 + 3*row_h + 3, "C:40725a")
    c.drawString(cols[3] + 2, cy0 + 3*row_h + 3, "23.02.2009")

    # Séparateur colonnes section haute
    mid1 = cx0 + cw * 0.28
    mid2 = cx0 + cw * 0.50
    c.line(mid1, div_y, mid1, cy1)
    c.line(mid2, div_y, mid2, cy1)

    # FINISH / DEBUR / DO NOT SCALE / coverglobal.com
    c.setFont("Helvetica", 6.5); c.setFillColor(NOIR)
    spec = ["UNLESS OTHERWISE SPECIFIED:","DIMENSIONS ARE IN MILLIMETERS",
            "SURFACE FINISH:","TOLERANCES:  EN 12150-1-2000","LINEAR:","ANGULAR:"]
    for i, s in enumerate(spec):
        c.drawString(cx0 + 3, cy1 - 7 - i*8, s)

    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(mid1 + 3, cy1 - 10, "DEBUR AND")
    c.drawString(mid1 + 3, cy1 - 19, "BREAK SHARP")
    c.drawString(mid1 + 3, cy1 - 28, "EDGES")

    c.setFont("Helvetica", 7)
    c.drawCentredString((mid2+cx1)/2, cy1 - 10, "DO NOT SCALE DRAWING")
    c.setFont("Helvetica", 6)
    c.drawCentredString((mid2+cx1)/2, cy1 - 22, f"REVISION      0")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(BLEU_L)
    c.drawCentredString((mid2+cx1)/2, cy1 - 38, "www.coverglobal.com")
    c.setFillColor(NOIR)

    # Section droite: TITLE / DWG NO / Material / Scale / Sheet
    # Separators
    title_col  = cx0 + cw * 0.50
    dwgno_col  = cx0 + cw * 0.78
    c.line(title_col, cy0, title_col, div_y)
    c.line(dwgno_col, cy0, dwgno_col, cy0 + row_h*2)
    c.line(title_col, cy0 + row_h*2, cx1, cy0 + row_h*2)
    c.line(title_col, cy0 + row_h,   cx1, cy0 + row_h)

    if 'TRIVEL' in type_verre:
        title_main = "Fixation holes & Trivel lock notch"
        dwg_no     = f"10mm Trivel lock {'R' if 'R' in type_verre else 'L'}"
    elif '5R' in type_verre:
        title_main = "Fixation and knob holes"
        dwg_no     = f"10mm Glass 5 holes {'R' if 'R' in type_verre else 'L'}"
    else:
        title_main = "Fixation holes"
        dwg_no     = "10mm Glass"

    # TITLE
    c.setFont("Helvetica", 6); c.drawString(title_col + 4, cy0 + row_h*3.5, "TITLE:")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString((title_col + cx1)/2, cy0 + row_h*2.5, title_main)

    # DWG NO
    c.setFont("Helvetica", 6); c.drawString(title_col + 4, cy0 + row_h*2 + 2, "DWG NO.")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(title_col + 4, cy0 + row_h*1.4, dwg_no)
    # A4 box
    c.setFont("Helvetica-Bold", 9)
    c.drawString(dwgno_col + 4, cy0 + row_h*1.4, "A4")

    # Material
    c.setFont("Helvetica", 6); c.drawString(title_col + 4, cy0 + row_h + 2, "MATERIAL:")
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((title_col + dwgno_col)/2, cy0 + row_h*0.55, "Tempered glass")

    # Scale / Sheet
    c.setFont("Helvetica", 6)
    c.drawString(title_col + 4, cy0 + 3, f"WEIGHT: (W x H)/1000 x Thickness x 2.5 K gr")
    c.drawString(dwgno_col + 4, cy0 + row_h + 2, "SCALE:1:3")
    c.drawString(dwgno_col + 4, cy0 + 3, f"SHEET {pan_num} OF {total_pan}")

    # PERIMETER section (bas gauche de la zone title)
    c.drawCentredString((title_col + cols[3])/2 if cols[3] < title_col else (cx0 + title_col)/2,
                        cy0 + row_h + 2, "PERIMETER (OUT)")
    c.drawCentredString((cx0 + title_col)/2, cy0 + 3, "mm")

    # Mini-logo bas-gauche
    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, cx0 + 3, cy0 + 3, width=0.80*inch,
                    preserveAspectRatio=True, mask='auto')


# ─── FONCTION PRINCIPALE ──────────────────────────────────────────────────────
def generer_pdf_verres(params, fichier, produit='cover'):
    """
    Génère le bon de commande verre IGP.
    produit='cover' : avec trous (4R/5R/TRIVEL) + cartouche coverglobal.com
    produit='aika'  : sans trous, sans cartouche
    """
    murs_raw = params.get("murs", [])
    epaisseur = "10mm" if produit == 'cover' else "6mm"

    # Calculer tous les panneaux de verre
    panneaux = []   # list of (mur_nom, pan_num_in_mur, larg_mm, haut_mm, type_verre)
    for idx_m, mur_raw in enumerate(murs_raw):
        mur_letter = chr(65 + idx_m)
        mur_nom    = mur_raw.get("nom") or f"Mur {mur_letter}"
        pan_in_mur = 1

        if produit == 'cover':
            import cover_10mm_module as _cm
            mr = mur_raw.copy()
            mr['largeur_po']      = _fvd(mr.get('largeur','0'))
            mr['hauteur_po']      = _fvd(mr.get('hauteur','0'))
            mr['nb_panneaux']     = int(mr.get('nb_panneaux',1))
            mr['encastre']        = mr.get('encastre', False)
            mr['panneaux_egaux']  = mr.get('panneaux_egaux', True)
            lp = mr['largeur_po']; nb = mr['nb_panneaux']
            mr['largeur_porte_po'] = (_fvd(mr['largeur_porte']) if mr.get('largeur_porte')
                                      else lp / nb)
            mc = _cm.calculer_mur_cover(mr)
            for verre in mc['verres']:
                for _ in range(verre['qte']):
                    panneaux.append((mur_nom, pan_in_mur,
                                     verre['larg_mm'], verre['haut_mm'], verre['type']))
                    pan_in_mur += 1

        else:   # aika
            import aika_6mm_module as _am
            mr = mur_raw.copy()
            mr['largeur_po']  = _fvd(mr.get('largeur','0'))
            mr['hauteur_po']  = _fvd(mr.get('hauteur','0'))
            mr['nb_rails']    = int(mr.get('nb_rails', 3))
            mr['nb_panneaux'] = int(mr.get('nb_panneaux', 1))
            mr['serrures']    = mr.get('serrures', [])
            mc = _am.calculer_mur_aika(mr)
            for verre in mc['verres']:
                for _ in range(verre['qte']):
                    panneaux.append((mur_nom, pan_in_mur,
                                     verre['larg_mm'], verre['haut_mm'], 'plain'))
                    pan_in_mur += 1

    total = len(panneaux)
    c = canvas.Canvas(fichier, pagesize=letter)

    # Page 1: bon de commande
    _page_bon_commande(c, params, total, epaisseur, produit)
    c.showPage()

    # Pages techniques
    for idx_p, (mur_nom, pan_num, larg_mm, haut_mm, type_verre) in enumerate(panneaux):
        _page_dessin(c, mur_nom, pan_num, larg_mm, haut_mm, type_verre, produit, total)
        c.showPage()

    c.save()
    print(f"✓ Bon de commande verre ({produit}) — {total} panneaux — {fichier}")
