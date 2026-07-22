#!/usr/bin/env python3
"""
test_simulation.py — Prospect 2.0
Simule un répondant fictif complet, calcule les scores et génère le PDF
sans toucher au vrai Google Forms.

Profil simulé : Marc Bergeron — Toitures Bergeron & Fils
  Points forts   → Ventes (14/20), Vision (18/20)
  Points moyens  → Équipe (12/20)
  Points faibles → Organisation (9/20), Outils (8/20), Finances (8/20)
  Score global attendu : ~57/100 (En développement)
"""

import os, sys, warnings
warnings.filterwarnings("ignore")

# ─── Import des utilitaires du script principal ───────────────────────────────
sys.path.insert(0, os.path.expanduser("~/Documents/prospect2"))
from generer_rapport_auto import (
    _load_creds, _build_form_index, _compute_scores, _section_key,
    _patch_and_generate, RAPPORT_SCRIPT,
)
from googleapiclient.discovery import build

# ─── Réponse simulée — format identique à l'API Google Forms ─────────────────
# Chaque clé = questionId (récupéré du vrai formulaire).
# Règle de score rappel :
#   scale  : (valeur − 1) / (high − 1) × 20  → 1=0/20, 5=20/20
#   choice : première option = 20/20, score = (1 − idx/(n−1)) × 20

def _ans(value):
    return {"textAnswers": {"answers": [{"value": str(value)}]}}

SIMULATED_RESPONSE = {
    "responseId": "SIMULATION-2026-07-22",
    "createTime": "2026-07-22T10:00:00.000Z",
    "answers": {

        # ── Identification ────────────────────────────────────────────────────
        "5c3145d4": _ans("Marc Bergeron"),
        "14a89594": _ans("Toitures Bergeron & Fils"),
        "0ae830ee": _ans("Couverture et toiture"),
        "0b8d5213": _ans("8"),
        "4ebdf501": _ans("1 200 000"),
        "5fc86f92": _ans("Avril à novembre"),
        "00871591": _ans("2009"),
        "3bd5c7f1": _ans("mbergeron@toituresbergeron.ca"),

        # ── SECTION 01 — Organisation & Processus — cible ~9/20 ──────────────
        # Q1 scale 1-5 → 3 → (3-1)/4×20 = 10
        "74963087": _ans("3"),
        # Q1b texte libre
        "3d466c2c": _ans(
            "Les devis pis la procédure de fin de chantier. "
            "Le reste, c'est dans ma tête depuis 15 ans."
        ),
        # Q2 scale 1-5 → 2 → (2-1)/4×20 = 5
        "71da14e4": _ans("2"),
        # Q3 choice [1] "Partiel — verbal seulement" → (1-1/3)×20 = 13
        "5ce3c779": _ans("Partiel — verbal seulement"),
        # Q4 choice [2] "55–65h" → (1-2/4)×20 = 10
        "399a80de": _ans("55–65h"),
        # Q5 choice [4] "Gérer plusieurs chantiers simultanément" → (1-4/5)×20 = 4
        "664a2496": _ans("Gérer plusieurs chantiers simultanément"),
        # Q6 texte libre
        "1d60651c": _ans(
            "Je passerais plus de temps avec ma famille pis j'aurais enfin "
            "le temps de former mon contremaître comme il faut."
        ),
        # scores: 10+5+13+10+4 = 42/5 = 8.4 → arrondi 8

        # ── Outils & Automatisation — cible ~8/20 ────────────────────────────
        # texte libre
        "0bf44098": _ans(
            "Excel pour les soumissions, un carnet de notes pour les chantiers, "
            "pis QuickBooks que ma comptable utilise. C'est tout."
        ),
        # choice [1] "Je dois tout ressaisir" → (1-1/2)×20 = 10
        "04ce8888": _ans("Je dois tout ressaisir"),
        # scale 1-5 → 2 → (2-1)/4×20 = 5
        "11353cba": _ans("2"),
        # choice [2] "5 à 10h" → (1-2/4)×20 = 10
        "6709b614": _ans("5 à 10h"),
        # choice [2] "Jamais considéré" → (1-2/3)×20 = 6.7
        "182c83cf": _ans("Jamais considéré"),
        # scores: 10+5+10+6.7 = 31.7/4 = 7.9 → 8

        # ── SECTION 02 — Ventes & Soumissions — cible ~14/20 ─────────────────
        # Q7 choice [2] "50–65%" → (1-2/5)×20 = 12
        "4267c991": _ans("50–65%"),
        # Q8 choice [1] "Fichier Excel / Google Sheets" → (1-1/4)×20 = 15
        "29c50a69": _ans("Fichier Excel / Google Sheets"),
        # Q9 scale 1-5 → 4 → (4-1)/4×20 = 15
        "3cf5e59e": _ans("4"),
        # Q9b texte libre
        "2cc0b40f": _ans(
            "J'appelle à J+5 pis J+12. Des fois j'oublie si je suis pogné sur les toits."
        ),
        # Q10 choice [0] "Bouche-à-oreille" → 20/20
        "2b57d99c": _ans("Bouche-à-oreille"),
        # Q11 choice [2] "15–30" → (1-2/3)×20 = 6.7
        "7f8b0314": _ans("15–30"),
        # Q12a texte libre
        "4e62e680": _ans("18 000"),
        # Q12b texte libre
        "7ab3eeb1": _ans("Une douzaine par saison, surtout à cause du prix."),
        # scores: 12+15+15+20+6.7 = 68.7/5 = 13.7 → 14

        # ── SECTION 03 — Finances & Rentabilité — cible ~8/20 ────────────────
        # Q13 scale 1-5 → 2 → (2-1)/4×20 = 5
        "0a4e67ab": _ans("2"),
        # Q13b texte libre
        "20e183b6": _ans(
            "J'estime à l'œil en fin de chantier. "
            "Si c'est payé pis qu'il reste de l'argent dans le compte, c'est que c'était correct."
        ),
        # Q14 choice [2] "15–25%" → (1-2/5)×20 = 12
        "73e0e07f": _ans("15–25%"),
        # Q15 choice [3] "Non, aucun" → (1-3/3)×20 = 0
        "350949b3": _ans("Non, aucun"),
        # Q16 choice [2] "De mémoire" → (1-2/3)×20 = 6.7
        "28ffcc43": _ans("De mémoire"),
        # Q16b texte libre
        "3b00d297": _ans(
            "Des fois je rachète des vis ou de la corde parce que je savais pas "
            "qu'on en avait encore. C'est plate mais ça arrive."
        ),
        # Q17 scale 1-5 → 3 → (3-1)/4×20 = 10
        "55724bfb": _ans("3"),
        # Q18 choice [2] "Soumissions sous-évaluées" → (1-2/5)×20 = 12
        "49768852": _ans("Soumissions sous-évaluées"),
        # scores: 5+12+0+6.7+10+12 = 45.7/6 = 7.6 → 8

        # ── SECTION 04 — Équipe & Ressources humaines — cible ~12/20 ─────────
        # Q19a–c texte libre
        "2a9d55aa": _ans("3"),
        "7961bfb9": _ans("5"),
        "58b29aa8": _ans("2 à 3 selon la charge"),
        # Q20 choice [1] "Partiellement — certaines tâches" → (1-1/3)×20 = 13
        "51673a86": _ans("Partiellement — certaines tâches"),
        # Q21 scale 1-5 → 3 → (3-1)/4×20 = 10
        "33b3abec": _ans("3"),
        # Q22 choice [0] "Rétention des bons employés" → 20/20
        "6645c46a": _ans("Rétention des bons employés"),
        # Q23 scale 1-5 → 2 → (2-1)/4×20 = 5
        "44033e86": _ans("2"),
        # Q23b texte libre
        "62f90f5a": _ans("2 à 3 semaines avant d'être à l'aise sur le toit tout seul."),
        # Q24 texte libre
        "62eba3fe": _ans(
            "J'aimerais avoir un contremaître qui gère les chantiers pendant que "
            "moi je focus sur le développement d'affaires pis les gros contrats."
        ),
        # scores: 13+10+20+5 = 48/4 = 12

        # ── SECTION 05 — Vision & Ambitions — cible ~18/20 ───────────────────
        # Q25 choice [0] "Réduire mes heures de travail" → 20/20
        "2bc5e25c": _ans("Réduire mes heures de travail"),
        # Q26 choice [1] "Dans 3–5 ans" → (1-1/4)×20 = 15
        "7c009836": _ans("Dans 3–5 ans"),
        # Q27 texte libre
        "7713bfd4": _ans(
            "Une business qui roule sans moi au quotidien. 3 à 4 équipes sur le terrain, "
            "un bon contremaître, pis moi je m'occupe des gros contrats commerciaux "
            "pis de la croissance."
        ),
        # Q28 choice [0] "Manque de temps" → 20/20
        "7a6b2f10": _ans("Manque de temps"),
        # scores: 20+15+20 = 55/3 = 18.3 → 18
    },
}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  Prospect 2.0 — Simulation rapport diagnostic")
    print("  Client fictif : Marc Bergeron — Toitures Bergeron & Fils")
    print("=" * 62)

    # Charger la structure réelle du formulaire (IDs et types de questions)
    print("\n  → Chargement de la structure du formulaire…")
    creds   = _load_creds()
    service = build("forms", "v1", credentials=creds)
    sections, id_to_section, id_champs = _build_form_index(service)

    scorable_counts = {sk: sum(1 for q in qs if q["is_scorable"]) for sk, qs in sections.items()}
    print(f"     {len(sections)} sections | questions scorables : "
          + ", ".join(f"{sk}={n}" for sk, n in scorable_counts.items()))

    # Données d'identification depuis la réponse simulée
    def _get(qid):
        block = SIMULATED_RESPONSE["answers"].get(qid, {})
        raw   = block.get("textAnswers", {}).get("answers", [])
        return raw[0]["value"].strip() if raw else "?"

    nom        = _get(id_champs["nom"])
    entreprise = _get(id_champs["entreprise"])
    secteur    = _get(id_champs["secteur"])

    print(f"\n  Client     : {nom}")
    print(f"  Entreprise : {entreprise}")
    print(f"  Secteur    : {secteur}")

    # Calcul des scores
    print("\n  → Calcul des scores sur les données simulées…")
    scores, textes = _compute_scores(sections, id_to_section, SIMULATED_RESPONSE)

    print("\n  ┌─────────────────────────────┬────────┬──────────────────────┐")
    print("  │ Section                     │ Score  │                      │")
    print("  ├─────────────────────────────┼────────┼──────────────────────┤")
    for sk, score in scores.items():
        bar = "█" * score + "░" * (20 - score)
        print(f"  │ {sk:<27} │ {score:>2}/20  │ {bar} │")
    print("  └─────────────────────────────┴────────┴──────────────────────┘")

    score_global = round(sum(scores.values()) / (20 * len(scores)) * 100)
    print(f"\n  Score global : {score_global}/100")

    # Extraits qualitatifs
    print("\n  ── Extraits qualitatifs (réponses texte libre) ──────────────")
    for sk, items in textes.items():
        if not items:
            continue
        print(f"\n  [{sk}]")
        for item in items:
            q_short = item["question"][:70]
            r_short = item["reponse"].replace("\n", " ")[:150]
            print(f"    Q : {q_short}")
            print(f"    R : {r_short}")

    # Génération du PDF avec actions personnalisées via Claude API
    _patch_and_generate(nom, entreprise, secteur, scores, textes)


if __name__ == "__main__":
    main()
