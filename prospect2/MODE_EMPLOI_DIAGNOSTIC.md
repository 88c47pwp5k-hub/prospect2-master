# Mode d'emploi — Diagnostic Prospect 2.0

Pipeline complet : de l'invitation initiale jusqu'au suivi client.

---

## Vue d'ensemble

```
Étape 1 — Envoyer l'invitation
         ↓
Étape 2 — Notification de réponse reçue
         ↓
Étape 3 — Générer le rapport (generer_rapport_auto.py)
         ↓
Étape 4 — Réviser les scores calculés
         ↓
Étape 5 — Génération IA des actions recommandées (Claude API)
         ↓
Étape 6 — Vérifier le PDF final
         ↓
Étape 7 — Envoyer au client + suivi pipeline
```

---

## Étape 1 — Envoyer l'invitation au prospect

**App Dock :** `Envoyer Invitation` (pastille bleue — dossier Prospect 2,0)

**Ou en ligne de commande :**
```bash
python3 ~/Documents/prospect2/send_invitation_app.py
```

L'app ouvre automatiquement `http://127.0.0.1:5959` dans le navigateur.

**Formulaire :**
- Nom du prospect
- Adresse courriel

**Clic → Envoyer l'invitation**

L'email envoyé contient le lien vers le Google Forms de diagnostic.
Chaque envoi est loggué dans `~/Documents/prospect2/prospects.csv`.

---

## Étape 2 — Notification : réponse reçue

Quand le prospect remplit le formulaire, vous recevez une notification Google Forms par courriel.

**Vérifier la réponse :**
- Google Forms → onglet Réponses
- Ou directement à l'étape 3 — le script liste les répondants automatiquement

---

## Étape 3 — Générer le rapport

```bash
python3 ~/Documents/prospect2/generer_rapport_auto.py
```

Le script :
1. Se connecte au Google Forms (OAuth2 via `token_forms.pickle`)
2. Charge la structure du formulaire (6 sections, questions scorables)
3. Liste tous les répondants disponibles
4. Vous demande de choisir le client à traiter (ou sélection auto si un seul)

**Exemple de sortie :**
```
  3 réponse(s) :

    [1] Jean Tremblay  —  Paysagement Tremblay  (2026-07-20)
    [2] Marc Bergeron  —  Toitures Bergeron & Fils  (2026-07-22)
    [3] Marie Ouellet  —  Toitures Ouellet  (2026-07-22)

  Numéro du client à traiter : 2
```

---

## Étape 4 — Réviser les scores calculés

Après sélection, le script affiche les scores calculés automatiquement :

| Section       | Règle de calcul                                      |
|---------------|------------------------------------------------------|
| Échelle 1–5   | `(valeur − 1) / (5 − 1) × 20`  → 1=0/20, 5=20/20   |
| Choix multiple | `(1 − index / (n−1)) × 20`  → 1ère option = 20/20  |
| Texte libre   | Non scoré — extrait comme contexte qualitatif        |

**Exemple d'affichage :**
```
  ┌─────────────────────────────┬────────┐
  │ Section                     │ Score  │
  ├─────────────────────────────┼────────┤
  │ organisation                │  8/20  │
  │ outils                      │  8/20  │
  │ ventes                      │ 14/20  │
  │ finances                    │  8/20  │
  │ equipe                      │ 12/20  │
  │ vision                      │ 18/20  │
  └─────────────────────────────┴────────┘

  Score global : 57/100
```

Le script affiche aussi les extraits qualitatifs (réponses texte libre) par section.

---

## Étape 5 — Génération IA des actions recommandées

**Automatique — aucune action requise.**

Le script identifie les **3 sections les plus faibles** et appelle `claude-sonnet-4-6`
pour chacune, en lui fournissant :
- Le nom et secteur du client
- Le score obtenu
- Les réponses texte libre du client pour cette section

Claude génère **3 actions concrètes** à l'infinitif, spécifiques à ce que le client a dit.

**Exemple de sortie :**
```
  → Génération des actions personnalisées via Claude API…
     [Organisation] score=8/20 — 2 réponse(s) texte libre… ✓
     [Outils] score=8/20 — 1 réponse(s) texte libre… ✓
     [Finances] score=8/20 — 2 réponse(s) texte libre… ✓
```

Ces actions remplacent les textes fixes dans les pages 3 et 4 du rapport PDF.

**Clé API :** lue depuis `~/Documents/resume-matin/.env` (`ANTHROPIC_API_KEY`).

---

## Étape 6 — Vérifier le PDF final

Le PDF est généré automatiquement à la fin du script :

```
  PDF : ~/Documents/prospect2/rapport_diagnostic_TEST.pdf
```

Un backup daté est aussi créé dans `~/Documents/backup-production/`.

**Ouvrir pour vérification :**
```bash
open ~/Documents/prospect2/rapport_diagnostic_TEST.pdf
```

**Vérifier dans le PDF :**
- Page 1 — Couverture : nom, entreprise, secteur, date, score global
- Page 2 — Scores : barres et cercle SVG corrects
- Page 3 — Zones prioritaires : 3 sections + actions générées par IA (spécifiques au client)
- Page 4 — Plan 90 jours : actions des 3 zones prioritaires dans les phases Semaines 1–2 / 3–4 / 5–8
- Page 5 — Forfaits : prénom du client dans "RECOMMANDÉ POUR X"

**Si une action générée ne convient pas**, relancer le script — Claude génère des variantes différentes à chaque appel.

---

## Étape 7 — Envoyer au client + suivi pipeline

### Renommer le PDF avant envoi

```bash
cp ~/Documents/prospect2/rapport_diagnostic_TEST.pdf \
   ~/Documents/prospect2/rapport_diagnostic_NOM_CLIENT.pdf
```

### Envoyer par courriel

Joindre `rapport_diagnostic_NOM_CLIENT.pdf` à un courriel depuis `bdprospect2.0@gmail.com`.

### Suivi dans prospects.csv

Mettre à jour `~/Documents/prospect2/prospects.csv` avec la date d'envoi du rapport :

| nom | courriel | date_invitation | statut | date_rapport |
|-----|----------|-----------------|--------|--------------|
| Marc Bergeron | mbergeron@... | 2026-07-22 | rapport_envoyé | 2026-07-22 |

### Suivi pipeline (relances)

- **J+3** — Vérifier si le client a ouvert le rapport (accusé de réception email)
- **J+7** — Appel de suivi : "Avez-vous eu le temps de lire votre rapport ?"
- **J+14** — Si pas de réponse : dernier courriel de relance avec offre de démo

---

## Référence rapide — Commandes

```bash
# Envoyer une invitation
python3 ~/Documents/prospect2/send_invitation_app.py

# Générer un rapport (client réel depuis Google Forms)
python3 ~/Documents/prospect2/generer_rapport_auto.py

# Tester le pipeline complet (client fictif Marc Bergeron)
python3 ~/Documents/prospect2/test_simulation.py

# Ouvrir le dernier PDF généré
open ~/Documents/prospect2/rapport_diagnostic_TEST.pdf
```

---

## Dépannage

| Problème | Cause probable | Solution |
|----------|---------------|----------|
| `ModuleNotFoundError: anthropic` | Package non installé | `pip3 install anthropic` |
| `token_forms.pickle` expiré | OAuth2 expiré | Relancer `generer_rapport_auto.py` — le token se rafraîchit automatiquement |
| `FileNotFoundError: logo_prospect.jpg` | Logo manquant | `cp ~/Documents/prospect2/logo_prospect.png ~/Documents/prospect2/logo_prospect.jpg` |
| Actions Claude génériques | Aucune réponse texte libre | Normal si le client n'a pas répondu aux questions ouvertes |
| PDF vide / erreur WeasyPrint | Chemin logo incorrect | Vérifier `_LOGO_CANDIDATES` dans `rapport_diagnostic_2026-07-01.py` |

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `send_invitation_app.py` | Flask app — envoi invitation par courriel |
| `generer_rapport_auto.py` | Pipeline complet : Forms → scores → Claude → PDF |
| `test_simulation.py` | Simulation Marc Bergeron (test sans répondant réel) |
| `rapport_diagnostic_2026-07-01.py` | Générateur PDF WeasyPrint |
| `invitation_courriel.html` | Template HTML de l'email d'invitation |
| `prospects.csv` | Log de tous les prospects contactés |
| `credentials/token_forms.pickle` | Token OAuth2 Google Forms |
| `~/Documents/resume-matin/.env` | Clé API Anthropic (`ANTHROPIC_API_KEY`) |
