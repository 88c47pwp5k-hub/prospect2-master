# Prospect 2.0 — Master Template

## Structure
- config.json         → paramètres du client
- dashboard/          → serveur web leads et soumissions
- resume-matin/       → résumé email quotidien
- monitoring/         → alertes système
- tournee/            → optimisation de route (optionnel)
- deploy/             → scripts d'installation

---

## Quand tu signes un nouveau client

### Étape 1 — Informations à collecter
- Nom de la compagnie
- Nom d'utilisateur Mac du client
- Gmail dédié (créer un nouveau compte Gmail pour le client)
- Email de réception (ex: info@compagnie.ca)
- Hôte IMAP et mot de passe
- Couleurs de la compagnie (hex)
- Logo (format PNG)

### Étape 2 — Déploiement (sur le Mac du client)
```bash
cd ~/prospect2-master/deploy
bash deployer.sh
```
Entrer les informations demandées — le script crée tout automatiquement.

### Étape 3 — Credentials à configurer manuellement
1. Gmail App Password → https://myaccount.google.com/apppasswords
2. Google OAuth token → cd ~/prospect2-client && python3 resume-matin/resume_matin.py
3. Clé Anthropic → https://console.anthropic.com
4. Microsoft Client ID (si To Do utilisé) → https://portal.azure.com

### Étape 4 — Vérification
```bash
bash ~/prospect2-client/monitoring/test_sante_systeme.sh
```
Tout doit être vert avant de quitter le client.

### Étape 5 — Ton accès admin
- URL dashboard client : http://localhost:PORT
- Login admin : bdprospect2.0@gmail.com
- Tu peux accéder via tunnel SSH ou TeamViewer

---

## Solarium Pro = référence
Ne jamais modifier les fichiers dans ~/dashboard/, ~/Documents/resume-matin/, ~/Documents/test_sante_systeme.sh
Ces fichiers sont le laboratoire — le master s'en inspire seulement.
