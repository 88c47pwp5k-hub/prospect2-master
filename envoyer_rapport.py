#!/usr/bin/env python3
"""
Envoyer Rapport Diagnostic — Prospect 2.0
Envoie le rapport_diagnostic.pdf au client par courriel Gmail SMTP.
"""

import os, csv, smtplib, glob, re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# ── Configuration ────────────────────────────────────────────────────────────
load_dotenv(os.path.expanduser("~/Documents/prospect2/.env"))

EXPEDITEUR    = "bdprospect2.0@gmail.com"
APP_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "")
BASE          = os.path.expanduser("~/Documents/prospect2")
RAPPORTS_DIR  = os.path.join(BASE, "RAPPORTS_CLIENTS")
SUIVI_CSV     = os.path.join(RAPPORTS_DIR, "suivi_global.csv")
PROSPECTS_CSV = os.path.join(BASE, "prospects.csv")

SUJET_GABARIT = "Ton rapport diagnostic — Prospect 2.0"

CORPS_GABARIT = """\
Bonjour {prenom},

Merci d'avoir pris le temps de compléter le diagnostic — ça permet d'avoir un vrai portrait de {entreprise} plutôt que de deviner.

Tu trouveras ton rapport complet en pièce jointe : ton score global, tes zones prioritaires, et un plan d'action sur 90 jours.

Je vais te contacter dans les prochains jours pour qu'on discute ensemble de la stratégie et voir comment on peut avancer là-dessus.

Au plaisir d'en parler,
Benoit
Prospect 2.0"""


def lire_suivi():
    """Retourne la liste de toutes les lignes du suivi_global.csv."""
    if not os.path.exists(SUIVI_CSV):
        print(f"❌ Fichier introuvable : {SUIVI_CSV}")
        return []
    with open(SUIVI_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def choisir_client(lignes):
    """Affiche les clients 'À envoyer' et laisse l'utilisateur en choisir un."""
    a_envoyer = [r for r in lignes
                 if r.get("etape", "").strip() == "en_prospection"
                 and not r.get("sous_etape", "").strip()]
    if not a_envoyer:
        print("✅ Aucun client avec statut 'À envoyer' dans suivi_global.csv.")
        return None

    print("\n─── Clients prêts à recevoir leur rapport ───")
    for i, r in enumerate(a_envoyer, 1):
        print(f"  {i}. {r['nom_client']} — {r['entreprise']}  (score {r['score']}/100, généré le {r['date_dernier_envoi']})")

    choix = input("\nNuméro du client (ou Entrée pour annuler) : ").strip()
    if not choix:
        return None
    try:
        return a_envoyer[int(choix) - 1]
    except (ValueError, IndexError):
        print("Choix invalide.")
        return None


def trouver_dossier(nom_client, entreprise):
    """Cherche le dossier du client dans RAPPORTS_CLIENTS/."""
    # Cherche par pattern slug "Prenom_Nom_*"
    slug_base = nom_client.strip().replace(" ", "_")
    pattern = os.path.join(RAPPORTS_DIR, f"{slug_base}*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]

    # Fallback : cherche dossier contenant slug de l'entreprise
    slug_ent = entreprise.strip().replace(" ", "_")
    pattern2 = os.path.join(RAPPORTS_DIR, f"*{slug_ent}*")
    matches2 = glob.glob(pattern2)
    if matches2:
        return matches2[0]

    return None


def chercher_courriel(nom_client):
    """Cherche le courriel du client dans prospects.csv."""
    if not os.path.exists(PROSPECTS_CSV):
        return None
    nom_lower = nom_client.lower().strip()
    with open(PROSPECTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and nom_lower in row[0].lower():
                courriel = row[1].strip()
                if "@" in courriel:
                    return courriel
    return None


def mettre_a_jour_statut(dossier):
    """Met à jour statut.txt : À envoyer → Envoyé + date."""
    statut_path = os.path.join(dossier, "statut.txt")
    if not os.path.exists(statut_path):
        return
    with open(statut_path, "r", encoding="utf-8") as f:
        contenu = f.read()

    date_envoi = datetime.now().strftime("%Y-%m-%d")
    contenu = re.sub(r"(Statut\s*:).*", r"\1 Envoyé", contenu)
    contenu = re.sub(r"(Envoyé le\s*:).*", rf"\1 {date_envoi}", contenu)
    contenu = re.sub(r"(Méthode\s*:).*", r"\1 SMTP Gmail", contenu)

    with open(statut_path, "w", encoding="utf-8") as f:
        f.write(contenu)


def mettre_a_jour_suivi(lignes, nom_client):
    """Met à jour la ligne du client dans suivi_global.csv."""
    date_envoi = datetime.now().strftime("%Y-%m-%d")
    for r in lignes:
        if r["nom_client"].strip() == nom_client.strip():
            r["sous_etape"]         = "rapport_envoye"
            r["date_dernier_envoi"] = date_envoi

    fieldnames = ["nom_client", "entreprise", "score", "etape", "sous_etape",
                  "raison", "date_dernier_envoi", "chemin_rapport_pdf"]
    with open(SUIVI_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(lignes)


def envoyer_rapport(destinataire, nom_client, entreprise, pdf_path):
    """Construit et envoie le courriel avec la pièce jointe PDF."""
    prenom = nom_client.strip().split()[0]
    corps = CORPS_GABARIT.format(prenom=prenom, entreprise=entreprise.strip())

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"Benoit Dupuis — Prospect 2.0 <{EXPEDITEUR}>"
    msg["To"]      = destinataire
    msg["Subject"] = SUJET_GABARIT

    # Corps texte + version HTML simple
    html = corps.replace("\n", "<br>")
    html = f"<div style='font-family:sans-serif;font-size:15px;line-height:1.7;color:#222;max-width:560px'>{html}</div>"
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(corps, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    # Pièce jointe PDF
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "pdf")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="rapport_diagnostic_{prenom}.pdf"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(EXPEDITEUR, APP_PASSWORD)
        serveur.sendmail(EXPEDITEUR, destinataire, msg.as_bytes())


def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║   Envoyer Rapport Diagnostic — P 2.0    ║")
    print("╚══════════════════════════════════════════╝\n")

    lignes = lire_suivi()
    if not lignes:
        return

    client = choisir_client(lignes)
    if not client:
        print("Annulé.")
        return

    nom_client = client["nom_client"].strip()
    entreprise = client["entreprise"].strip()
    prenom     = nom_client.split()[0]

    # Trouver le dossier client
    dossier = trouver_dossier(nom_client, entreprise)
    if not dossier:
        print(f"❌ Dossier introuvable pour {nom_client} dans {RAPPORTS_DIR}")
        return

    pdf_path = os.path.join(dossier, "rapport_diagnostic.pdf")
    if not os.path.exists(pdf_path):
        print(f"❌ PDF introuvable : {pdf_path}")
        return

    # Chercher l'adresse courriel
    courriel = chercher_courriel(nom_client)
    if not courriel:
        print(f"\n⚠️  Courriel introuvable pour {nom_client} dans prospects.csv.")
        courriel = input("Adresse courriel du client : ").strip()
        if "@" not in courriel:
            print("Adresse invalide. Annulé.")
            return

    # ── APERÇU ───────────────────────────────────────────────────────────────
    corps_apercu = CORPS_GABARIT.format(prenom=prenom, entreprise=entreprise)

    print("\n" + "═" * 50)
    print("  APERÇU DU COURRIEL")
    print("═" * 50)
    print(f"  De       : Benoit Dupuis — Prospect 2.0 <{EXPEDITEUR}>")
    print(f"  À        : {courriel}")
    print(f"  Objet    : {SUJET_GABARIT}")
    print(f"  Pièce jointe : rapport_diagnostic_{prenom}.pdf ({os.path.getsize(pdf_path) // 1024} Ko)")
    print("─" * 50)
    print(corps_apercu)
    print("═" * 50)

    # ── CONFIRMATION ─────────────────────────────────────────────────────────
    confirm = input("\nEnvoyer ce courriel ? (oui / non) : ").strip().lower()
    if confirm not in ("oui", "o", "yes", "y"):
        print("Envoi annulé.")
        return

    # ── ENVOI ────────────────────────────────────────────────────────────────
    print(f"\n📤 Envoi en cours vers {courriel}…")
    try:
        envoyer_rapport(courriel, nom_client, entreprise, pdf_path)
        print(f"✅ Rapport envoyé à {courriel}")

        # Mise à jour des fichiers de suivi
        mettre_a_jour_statut(dossier)
        mettre_a_jour_suivi(lignes, nom_client)
        print(f"📋 Statut mis à jour : {nom_client} → Envoyé ({datetime.now().strftime('%Y-%m-%d')})")

    except Exception as e:
        print(f"❌ Erreur lors de l'envoi : {e}")

    input("\nAppuyez sur Entrée pour fermer…")


if __name__ == "__main__":
    main()
