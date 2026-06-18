#!/bin/bash
# Prospect 2.0 — Script de déploiement client
# Usage : bash deployer.sh

echo "=== Prospect 2.0 — Déploiement nouveau client ==="
echo ""

read -p "Nom du client : " NOM_CLIENT
read -p "Nom d'utilisateur Mac (ex: benoitdupuis) : " NOM_USER
read -p "Gmail du client : " GMAIL_CLIENT
read -p "Email de réception (ex: info@compagnie.ca) : " EMAIL_RECEPTION
read -p "Hôte IMAP (ex: mail.mailconfig.net) : " IMAP_HOST
read -p "Mot de passe IMAP : " IMAP_PASSWORD
read -p "Port dashboard (défaut 7373) : " DASHBOARD_PORT
DASHBOARD_PORT=${DASHBOARD_PORT:-7373}

echo ""
echo "--- Création de la structure ---"

BASE="/Users/$NOM_USER/prospect2-client"
mkdir -p "$BASE/dashboard"
mkdir -p "$BASE/resume-matin"
mkdir -p "$BASE/monitoring"
mkdir -p "$BASE/assets"
mkdir -p "$BASE/logs"

cp ../config.json "$BASE/config.json"

sed -i '' "s/NOM_CLIENT/$NOM_CLIENT/g" "$BASE/config.json"
sed -i '' "s/NOM_USER/$NOM_USER/g" "$BASE/config.json"
sed -i '' "s/GMAIL_CLIENT@gmail.com/$GMAIL_CLIENT/g" "$BASE/config.json"
sed -i '' "s/info@DOMAINE_CLIENT.ca/$EMAIL_RECEPTION/g" "$BASE/config.json"
sed -i '' "s/IMAP_HOST/$IMAP_HOST/g" "$BASE/config.json"
sed -i '' "s/MOT_DE_PASSE_IMAP/$IMAP_PASSWORD/g" "$BASE/config.json"
sed -i '' "s/7373/$DASHBOARD_PORT/g" "$BASE/config.json"

echo "✅ Structure créée dans $BASE"
echo "✅ config.json personnalisé pour $NOM_CLIENT"
echo "--- Copie des scripts ---"
cp ../dashboard/dashboard_server.py "$BASE/dashboard/"
cp ../dashboard/generer_dashboard.py "$BASE/dashboard/"
cp ../dashboard/import_leads_v4.py "$BASE/dashboard/"
cp ../dashboard/scanner_soumissions.py "$BASE/dashboard/"
cp ../resume-matin/resume_matin.py "$BASE/resume-matin/"
cp ../monitoring/test_sante_systeme.sh "$BASE/monitoring/"
cp -r ../deploy/launchagents "$BASE/deploy/"

# Remplacer les placeholders dans les plist
for plist in "$BASE/deploy/launchagents/"*.plist; do
    sed -i '' "s/NOM_CLIENT/$NOM_CLIENT/g" "$plist"
    sed -i '' "s|CHEMIN_BASE|/Users/$NOM_USER|g" "$plist"
done

echo "✅ Scripts copiés"
echo "✅ LaunchAgents configurés"
echo ""
echo "=== Déploiement terminé ==="
echo "Prochaines étapes manuelles :"
echo "1. Ajouter le logo dans $BASE/assets/logo.png"
echo "2. Configurer Gmail App Password dans config.json"
echo "3. Configurer la clé Anthropic dans config.json"
echo "4. Lancer : bash $BASE/monitoring/test_sante_systeme.sh"
