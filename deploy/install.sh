#!/bin/bash
echo "=== Prospect 2.0 — Installation ==="
echo ""

if ! command -v git &> /dev/null; then
    echo "❌ Git n'est pas installé. Installe-le sur https://git-scm.com"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 n'est pas installé. Installe-le sur https://python.org"
    exit 1
fi

echo "✅ Prérequis OK"
echo ""

MASTER_DIR="$HOME/prospect2-master"

if [ -d "$MASTER_DIR" ]; then
    echo "--- Mise à jour du master ---"
    cd "$MASTER_DIR" && git pull
else
    echo "--- Téléchargement du master ---"
    git clone https://github.com/88c47pwp5k-hub/prospect2-master.git "$MASTER_DIR"
fi

echo "✅ Master téléchargé"
echo ""
echo "Lance maintenant :"
echo "  bash $HOME/prospect2-master/deploy/deployer.sh"
