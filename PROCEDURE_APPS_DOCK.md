# Procédure Apps Dock — Solarium Pro

## Légende des apps

| Pastille | Nom complet | Description |
|----------|-------------|-------------|
| SP | Solarium Production | Générateur de documents PDF — `localhost:5757` |
| SD | Solarium Dashboard | Tableau de bord leads |
| SU | Suivi Usine Kevin | Vue Kevin — Railway `/keven` |
| SV | Suivi Client | Suivi production Benoît/Cathy/Cédric — Railway principal |


## 1. Apps dans le Dock

| Pastille | Nom | URL | Chemin local |
|----------|-----|-----|--------------|
| SP | Suivi Production | `http://localhost:5757` | `~/Desktop/Solarium Pro /application SP/Suivi Production.app` |
| SD | SolariumDashboard | Leads dashboard | `~/Desktop/Solarium Pro /application SP/SolariumDashboard.app` |
| SU | SuiviUsineKevin | `https://energetic-elegance-production-2aa7.up.railway.app/keven` | `~/Desktop/SuiviUsineKevin.app` |
| SV | Suivi Client 2 | `https://energetic-elegance-production-2aa7.up.railway.app` | `~/Desktop/Suivi Client 2.app` |


## 2. Créer une nouvelle app Dock

```bash
# 1. Créer l'app — TOUJOURS sur ~/Desktop, pas dans ~/Applications (osacompile échoue là)
osacompile -o ~/Desktop/"NomApp.app" -e 'do shell script "open -a Safari \"URL\""'

# 2. Appliquer l'icône depuis ~/Documents/Pastilles/
mkdir -p /tmp/logo_XX.iconset
for size in 16 32 128 256 512; do
  sips -z $size $size ~/Documents/Pastilles/logo_XX.png --out /tmp/logo_XX.iconset/icon_${size}x${size}.png
  double=$((size*2))
  sips -z $double $double ~/Documents/Pastilles/logo_XX.png --out /tmp/logo_XX.iconset/icon_${size}x${size}@2x.png
done
iconutil -c icns /tmp/logo_XX.iconset -o /tmp/logo_XX.icns

swift - <<'EOF'
import AppKit
let icon = NSImage(contentsOfFile: "/tmp/logo_XX.icns")!
let ok   = NSWorkspace.shared.setIcon(icon, forFile: "/Users/benoitdupuis/Desktop/NomApp.app", options: [])
print(ok ? "OK" : "Échec")
EOF

# 3. Redémarrer le Dock si nécessaire
killall Dock
```


## 3. Modifier statuts/options dans Suivi Production

```bash
# 1. Modifier la config localement
nano ~/Documents/Suivi-Production/data/config.json

# 2. Tester en local
open http://localhost:5858

# 3. Déployer le code sur Railway
cd ~/Documents/Suivi-Production && railway up

# 4. Mettre à jour la config sur Railway (clé du workflow)
curl -s -X POST https://energetic-elegance-production-2aa7.up.railway.app/api/config \
  -H "Content-Type: application/json" \
  -d @~/Documents/Suivi-Production/data/config.json
```


## 4. Changer l'environnement de SV (local ↔ Railway)

L'URL affichée par `Suivi Client 2.app` est contrôlée par :

```
~/Documents/Suivi-Production/url_courante.txt
```

Pour basculer l'environnement, modifier ce fichier :

```bash
# Railway (production)
echo "https://energetic-elegance-production-2aa7.up.railway.app" > ~/Documents/Suivi-Production/url_courante.txt

# Local
echo "http://localhost:5858" > ~/Documents/Suivi-Production/url_courante.txt
```

> Ce mécanisme est duplicable pour tout client Prospect 2.0 — un seul fichier texte contrôle l'environnement sans toucher à l'app.


## 5. IMPORTANT — Règles de création d'apps Dock

- Les apps doivent être créées avec `osacompile` sur le bureau (`~/Desktop/`) — `osacompile` échoue dans `~/Applications/`
- Pour épingler dans le Dock : ouvrir l'app, puis clic droit sur l'icône dans le Dock pendant qu'elle tourne → **Options → Garder dans le Dock**
- iCloud Drive bloque `fileicon` — utiliser la méthode AppKit via Swift/Claude Code pour appliquer les icônes
- Ne jamais utiliser d'IP locale dans les scripts — toujours Railway URL ou `localhost` avec port fixe


## 6. SD — SolariumDashboard (détail)

- **Chemin** : `~/Desktop/Solarium Pro /application SP/SolariumDashboard.app`
- **Lancement** : exécute `python3 ~/Documents/import_leads_v4.py` puis ouvre `dashboard_leads.html` dans Chrome
- **Dashboard HTML** : `~/Desktop/dashboard_leads.html`


## 7. Modifier l'interface Suivi Production

- Les entêtes et colonnes sont dans le HTML, **pas dans config.json**
- Fichier à modifier : `~/Documents/Suivi-Production/templates/index.html`

```bash
# 1. Backup obligatoire avant toute modification
cp ~/Documents/Suivi-Production/templates/index.html \
   ~/Documents/Suivi-Production/templates/index.html.bak

# 2. Modifier le fichier
nano ~/Documents/Suivi-Production/templates/index.html

# 3. Déployer
cd ~/Documents/Suivi-Production && railway up
```


## 8. Backup automatique

- Tout fichier modifié doit être copié dans `~/Documents/backup-production/`
- Apps importantes aussi dans :
  - `~/Documents/Suivi-Production/`
  - `~/Documents/Prospect 2.0/CLIENTS ACTIFS/_TEMPLATE.../BASE/Suivi-Production/`


## 8. Logos master

Dossier : `~/Documents/Pastilles/`

| Fichier | App |
|---------|-----|
| `logo_SP.png` | Solarium Production |
| `logo_SD.png` | Solarium Dashboard |
| `logo_SU.png` | Suivi Usine Kevin |
| `logo_SV.png` | Suivi Client |


## 9. Sécurité et backups automatiques

### SP — Solarium Production
- Backup automatique à chaque `save_soumissions()` dans `solarium_production.py`
- Destination : `~/Documents/backup-production/soumissions_SP_YYYY-MM-DD_HHhMM.json`

### SD — SolariumDashboard
- Backup horaire automatique via **launchd**
- Script : `~/Documents/backup-production/backup_soumissions.sh`
- Plist : `~/Library/LaunchAgents/com.solariumpro.backup-soumissions.plist`
- Destination : `~/Documents/backup-production/soumissions_dashboard_YYYY-MM-DD_HH.json`
- Commandes utiles :
  ```bash
  # Recharger après modification du plist
  launchctl unload ~/Library/LaunchAgents/com.solariumpro.backup-soumissions.plist
  launchctl load   ~/Library/LaunchAgents/com.solariumpro.backup-soumissions.plist
  ```

### SV — Suivi Client (Railway)
- Backup automatique avant chaque écriture (POST/PUT/PATCH/DELETE/reset)
- Destination : `/app/data/backups/dossiers_YYYY-MM-DD_HHhMM.json` (48 max, les plus vieux supprimés)
- `GET /api/backups` — liste les backups disponibles
- `POST /api/restore/<filename>` — restaure un backup (fait un backup avant restauration)
  ```bash
  # Lister les backups
  curl -s https://energetic-elegance-production-2aa7.up.railway.app/api/backups

  # Restaurer un backup
  curl -s -X POST https://energetic-elegance-production-2aa7.up.railway.app/api/restore/dossiers_2026-07-01_20h38.json
  ```

### Backup manuel — toutes les apps
- Dossier : `~/Documents/backup-production/`
- Contient toutes les apps et scripts datés (`_YYYY-MM-DD`)
- À faire en fin de session si fichiers modifiés


## 10. Module Solarium SM (soumissions)

**URL production :** `https://solarium-pro-sm-production.up.railway.app`
**Repo :** `~/solarium-sm` → GitHub `88c47pwp5k-hub/solarium-sm` → Railway auto-deploy sur `main`

### Déployer les changements SM
```bash
cd ~/solarium-sm
git add <fichiers>
git commit -m "message"
git push origin main   # Railway redéploie automatiquement (~2 min)
```

### Scanner IMAP (`scanner_soumissions.py`)
- **Automatique :** launchd chaque jour à 7h05 via `~/Library/LaunchAgents/com.benoitdupuis.scansoumissions.plist`
- **Manuel (test) :**
  ```bash
  python ~/Library/SolariumDashboard/scanner_soumissions.py
  ```
- Scanne INBOX pour sujets contenant `alerte nouveau dossier`
- Résultat dans `~/Library/SolariumDashboard/soumissions.json`
- Log : `~/Library/SolariumDashboard/scan_soumissions.log`

### Comportements conditionnels (depuis 18 juillet 2026)
- **Clause délai** : `_build_termes(dossier)` dans `app.py` → si installation par tiers (`installateur_accredit` / `client`), clause délai ne mentionne pas Solarium Pro pour l'installation
- **QTÉ** : colonne non visible côté client dans le PDF soumission
- **Bloc coordonnées** : séparateur vertical uniquement si adresse des travaux ≠ adresse client

### Guide interne
- **URL :** `https://solarium-pro-sm-production.up.railway.app/guide`
- Accessible à Benoit, Cathy, Cédric, Kevin (login requis)
- Couvre : créer soumission, envoi client, signature, contrat, facture, photos, sondage, distributeurs, questionnaire interne


## 11. Prospect 2.0 — Scripts de diagnostic (2026-07-22)

### send_invitation_app.py — Envoyer Invitation
- **Converti de Tkinter vers Flask** (port 5959) — ouvre automatiquement dans le navigateur au lancement
- App Dock : `~/Desktop/"Prospect 2,0"/"SOLICITATION — Clients futurs"/"Envoyer Invitation.app"`
- Launcher : `python3 ~/Documents/prospect2/send_invitation_app.py`
- Logue chaque envoi dans `prospects.csv`

### generer_rapport_auto.py — Rapport automatique
- Lit les réponses du Google Forms ID `1cMJLbieugSF8QbpS9TU8Tl47kranoYoQarQBeR8w91Y`
- Calcule 6 scores /20 (Organisation, Outils, Ventes, Finances, Équipe, Vision)
- Règle de score : échelle → `(val−low)/(high−low)×20` ; choix multiple → première option = 20/20
- Appelle `rapport_diagnostic_2026-07-01.py` pour générer le PDF final
- Credentials : `~/Documents/prospect2/credentials/token_forms.pickle`
- Usage : `python3 ~/Documents/prospect2/generer_rapport_auto.py`

### test_simulation.py — Simulation sans répondant réel
- Simule Marc Bergeron / Toitures Bergeron & Fils (profil moyen-faible 57/100)
- Valide le pipeline complet sans toucher au vrai formulaire
- Usage : `python3 ~/Documents/prospect2/test_simulation.py`

### Section "Outils & Automatisation" ajoutée au Forms (2026-07-22)
- Insérée entre "Organisation & Processus" (index 8) et "Ventes & Soumissions" (index 22)
- 5 questions : texte libre, 3 choix multiples, 1 échelle 1–5


## 12. Checklist fin de session

- [ ] README.html mis à jour avec tous les changements
- [ ] Git push : `cd ~/prospect2-master && git push`
- [ ] Backup : `cp fichiers modifiés ~/Documents/backup-production/`
- [ ] Config Railway synchronisée si changements Suivi Production :
      ```bash
      curl -s -X POST https://energetic-elegance-production-2aa7.up.railway.app/api/config \
        -H "Content-Type: application/json" \
        -d @~/Documents/Suivi-Production/data/config.json
      ```
- [ ] PROCEDURE_APPS_DOCK.md à jour si nouveaux apps ou procédures
