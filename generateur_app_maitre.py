#!/usr/bin/env python3
"""
generateur_app_maitre.py — Générateur maître d'apps Prospect 2.0
=================================================================
Crée un bundle .app complet (structure + icône) en une seule commande.

Règles gravées dans ce script :
  - CFBundleExecutable = script bash (JAMAIS osacompile/applet)
  - Plist minimal (6 clés) — pas de NSUsageDescription, pas de CFBundleIconName
  - Icône : PIL + logo pieuvre + fond coloré arrondi (rayon 220px sur 1024px)
  - JAMAIS NSWorkspace.setIcon sur un .app (provoque kHasCustomIcon qui bloque AppIcon.icns)
  - macOS lit AppIcon.icns directement depuis Contents/Resources/ — c'est tout ce qu'il faut

Usage :
    python3 generateur_app_maitre.py \\
        --nom "Générer Rapport Diagnostic" \\
        --couleur "#502878" \\
        --script ~/Documents/prospect2/launchers/MonScript.sh

    python3 generateur_app_maitre.py \\
        --nom "Mon App" \\
        --couleur "#1B3A5C" \\
        --script-inline 'open -a "Google Chrome" ~/Documents/prospect2/README.html'

    # Tester sans toucher aux apps existantes (génère dans /tmp) :
    python3 generateur_app_maitre.py --nom "Documentation" --couleur "#9E931D" \\
        --script-inline 'open -a "Google Chrome" ~/Documents/prospect2/README.html' \\
        --dest /tmp/test_apps

Paramètres :
  --nom           Nom de l'app (ex: "Générer Rapport Diagnostic")
  --couleur       Couleur de fond en hex (ex: "#502878")
  --script        Chemin vers un fichier .sh à utiliser comme launcher
  --script-inline Contenu bash inline (alternative à --script)
  --dest          Dossier de destination (défaut: ~/Desktop/Prospect 2,0/Prospect 2,0 Apps)
  --no-backup     Ne pas créer de backup
"""

import argparse, os, sys, shutil, re, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw

# ── Chemins ──────────────────────────────────────────────────────────────────
LOGO_SOURCE  = os.path.expanduser("~/Documents/logo_prospect.png")
APPS_DIR     = os.path.expanduser("~/Desktop/Prospect 2,0/Prospect 2,0 Apps")
BACKUP_DIR   = os.path.expanduser("~/Documents/backup-production/Prospect 2,0 Apps")

# ── Paramètres icône (gelés — calibrés sur les apps validées) ─────────────────
CANVAS_SIZE   = 1024
CORNER_RADIUS = 220    # ~21.5% de 1024 — style macOS Big Sur
MARGIN_RATIO  = 0.08   # 8% de marge de chaque côté


# ── Fonctions icône ───────────────────────────────────────────────────────────

def hex_vers_rgb(hex_couleur):
    """Convertit '#502878' → (80, 40, 120)."""
    h = hex_couleur.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def retirer_fond_blanc(logo_img):
    """Rend transparent le fond blanc du logo pieuvre."""
    img  = logo_img.convert("RGBA")
    data = np.array(img, dtype=np.int32)
    r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
    lum   = (r + g + b) // 3
    alpha = np.where(lum >= 235, 0,
            np.where(lum <= 170, 255,
            ((235 - lum) * 255 // 65))).clip(0, 255).astype(np.uint8)
    out = img.copy()
    out.putalpha(Image.fromarray(alpha))
    return out


def creer_icone_png(bg_color_rgb):
    """Crée une image RGBA 1024×1024 : fond arrondi coloré + pieuvre centrée."""
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [0, 0, CANVAS_SIZE - 1, CANVAS_SIZE - 1],
        radius=CORNER_RADIUS,
        fill=(*bg_color_rgb, 255),
    )
    logo_clean  = retirer_fond_blanc(Image.open(LOGO_SOURCE))
    margin      = int(CANVAS_SIZE * MARGIN_RATIO)
    logo_dim    = CANVAS_SIZE - 2 * margin
    logo_scaled = logo_clean.resize((logo_dim, logo_dim), Image.LANCZOS)
    canvas.paste(logo_scaled, (margin, margin), logo_scaled)
    return canvas


def generer_iconset_pil(icon_img, iconset_dir):
    """Remplit un .iconset avec toutes les résolutions via PIL (pas sips)."""
    os.makedirs(iconset_dir, exist_ok=True)
    entries = [
        ("icon_16x16.png",      16),
        ("icon_16x16@2x.png",   32),
        ("icon_32x32.png",      32),
        ("icon_32x32@2x.png",   64),
        ("icon_128x128.png",   128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png",   256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png",   512),
        ("icon_512x512@2x.png", 1024),
    ]
    for fname, px in entries:
        icon_img.resize((px, px), Image.LANCZOS).save(
            os.path.join(iconset_dir, fname)
        )


def png_vers_icns(icon_img, dest_icns):
    """Convertit PNG → .icns via PIL + iconutil."""
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "AppIcon.iconset")
        generer_iconset_pil(icon_img, iconset)
        res = subprocess.run(
            ["iconutil", "-c", "icns", iconset, "-o", dest_icns],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"iconutil : {res.stderr.strip()}")


# ── Fonction principale ───────────────────────────────────────────────────────

def slugifier(nom):
    """Convertit 'Générer Rapport Diagnostic' → 'GenerRapportDiagnostic'."""
    # Retirer accents basiques
    remplacements = {'é':'e','è':'e','ê':'e','ë':'e','à':'a','â':'a',
                     'ù':'u','û':'u','ô':'o','î':'i','ï':'i','ç':'c',
                     'É':'E','È':'E','Ê':'E','À':'A','Â':'A','Î':'I'}
    s = nom
    for src, dst in remplacements.items():
        s = s.replace(src, dst)
    # Garder seulement lettres/chiffres, capitaliser chaque mot
    mots = re.split(r'\s+', s.strip())
    return ''.join(m.capitalize() for m in mots if m)


def creer_app(nom, hex_couleur, script_contenu, dest_dir, backup=True):
    """
    Crée un bundle .app complet.

    Paramètres :
      nom            : nom affiché de l'app
      hex_couleur    : couleur de fond ex '#502878'
      script_contenu : contenu bash du launcher
      dest_dir       : dossier parent où créer NomApp.app
      backup         : copier dans BACKUP_DIR avant écrasement
    """
    if not os.path.exists(LOGO_SOURCE):
        raise FileNotFoundError(f"Logo introuvable : {LOGO_SOURCE}")

    app_name  = f"{nom}.app"
    app_path  = os.path.join(dest_dir, app_name)
    exec_slug = slugifier(nom)
    bundle_id = "com.prospect2." + exec_slug.lower()

    print(f"\n── Création de {app_name} ──────────────────────────────")
    print(f"   Couleur : {hex_couleur}  |  Exécutable : {exec_slug}")
    print(f"   Destination : {app_path}")

    # Backup si l'app existait déjà
    if os.path.isdir(app_path) and backup:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_path = os.path.join(BACKUP_DIR, app_name)
        if os.path.isdir(backup_path):
            shutil.rmtree(backup_path)
        shutil.copytree(app_path, backup_path)
        print(f"   Backup : {backup_path}")

    # Supprimer l'ancien bundle
    if os.path.exists(app_path):
        shutil.rmtree(app_path) if os.path.isdir(app_path) else os.remove(app_path)

    # Créer la structure
    macos_dir     = os.path.join(app_path, "Contents", "MacOS")
    resources_dir = os.path.join(app_path, "Contents", "Resources")
    os.makedirs(macos_dir)
    os.makedirs(resources_dir)

    # Script launcher (bash, chmod +x)
    launcher_path = os.path.join(macos_dir, exec_slug)
    with open(launcher_path, "w") as f:
        if not script_contenu.startswith("#!"):
            f.write("#!/bin/bash\n")
        f.write(script_contenu)
        if not script_contenu.endswith("\n"):
            f.write("\n")
    os.chmod(launcher_path, 0o755)
    print(f"   ✓ Launcher : {exec_slug}")

    # Info.plist minimal (règle : 6 clés, jamais CFBundleIconName)
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>{exec_slug}</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundleIdentifier</key><string>{bundle_id}</string>
    <key>CFBundleName</key><string>{nom}</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>LSUIElement</key><false/>
</dict>
</plist>
"""
    with open(os.path.join(app_path, "Contents", "Info.plist"), "w") as f:
        f.write(plist_content)
    print("   ✓ Info.plist (7 clés, minimal)")

    # Icône : PIL + pieuvre + fond coloré (JAMAIS NSWorkspace.setIcon sur .app)
    print(f"   Génération icône fond {hex_couleur}…")
    bg_rgb   = hex_vers_rgb(hex_couleur)
    icon_img = creer_icone_png(bg_rgb)
    icns_path = os.path.join(resources_dir, "AppIcon.icns")
    png_vers_icns(icon_img, icns_path)
    taille_k = os.path.getsize(icns_path) // 1024
    print(f"   ✓ AppIcon.icns ({taille_k}K) — macOS lit directement, pas de NSWorkspace.setIcon")

    # Touch pour forcer Finder à relire
    subprocess.run(["touch", app_path], capture_output=True)

    print(f"   ✅ {app_name} créé avec succès")
    return app_path


# ── Entrée CLI ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Générateur maître d'apps Prospect 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--nom",           required=True,  help="Nom de l'app")
    parser.add_argument("--couleur",       required=True,  help="Couleur fond hex ex #502878")
    parser.add_argument("--script",        default=None,   help="Chemin fichier .sh launcher")
    parser.add_argument("--script-inline", default=None,   dest="script_inline",
                        help="Contenu bash inline")
    parser.add_argument("--dest",          default=APPS_DIR,
                        help=f"Dossier destination (défaut: {APPS_DIR})")
    parser.add_argument("--no-backup",     action="store_true", help="Ne pas créer de backup")

    args = parser.parse_args()

    # Valider couleur
    if not re.match(r'^#[0-9A-Fa-f]{6}$', args.couleur):
        print(f"Erreur : couleur invalide '{args.couleur}' — format attendu #RRGGBB")
        sys.exit(1)

    # Obtenir contenu script
    if args.script and args.script_inline:
        print("Erreur : utilisez --script OU --script-inline, pas les deux")
        sys.exit(1)
    if not args.script and not args.script_inline:
        print("Erreur : --script ou --script-inline requis")
        sys.exit(1)

    if args.script:
        chemin = os.path.expanduser(args.script)
        if not os.path.exists(chemin):
            print(f"Erreur : fichier script introuvable : {chemin}")
            sys.exit(1)
        with open(chemin) as f:
            script_contenu = f.read()
    else:
        script_contenu = args.script_inline

    dest = os.path.expanduser(args.dest)
    os.makedirs(dest, exist_ok=True)

    creer_app(
        nom=args.nom,
        hex_couleur=args.couleur,
        script_contenu=script_contenu,
        dest_dir=dest,
        backup=not args.no_backup,
    )

    print("\nRelance Dock et Finder…")
    subprocess.run(["killall", "Dock"],   capture_output=True)
    subprocess.run(["killall", "Finder"], capture_output=True)
    print("Terminé.")


if __name__ == "__main__":
    main()
