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
echo ""
echo "Prochaine étape : copier les scripts génériques dans $BASE/"
