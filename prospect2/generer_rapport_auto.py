#!/usr/bin/env python3
"""
generer_rapport_auto.py — Prospect 2.0
Lit les réponses Google Forms, calcule les scores par section, génère le PDF diagnostic.

Usage :
  python3 generer_rapport_auto.py
"""

import os, sys, pickle, warnings, subprocess
warnings.filterwarnings("ignore")

FORM_ID      = "1cMJLbieugSF8QbpS9TU8Tl47kranoYoQarQBeR8w91Y"
CREDS_PATH   = os.path.expanduser("~/Documents/prospect2/credentials/token_forms.pickle")
RAPPORT_SCRIPT = os.path.expanduser(
    "~/Documents/backup-production/rapport_diagnostic_2026-07-01.py"
)

# Mots-clés pour identifier chaque section → clé CLI du rapport
SECTION_MAP = [
    (["Organisation", "Processus"],          "organisation"),
    (["Outils", "Automatisation"],           "outils"),
    (["Ventes", "Soumissions"],              "ventes"),
    (["Finance", "Rentabilit"],              "finances"),   # Rentabilité / Rentabilite
    (["quipe", "Ressources humaines"],       "equipe"),     # Équipe / Equipe
    (["Vision", "Ambitions"],                "vision"),
]

def _section_key(title):
    for keywords, key in SECTION_MAP:
        if any(kw in title for kw in keywords):
            return key
    return None


# ─── Authentification ────────────────────────────────────────────────────────

def _load_creds():
    with open(CREDS_PATH, "rb") as f:
        creds = pickle.load(f)
    if not creds.valid or creds.expired:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(CREDS_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds


# ─── Structure du formulaire ─────────────────────────────────────────────────

def _build_form_index(service):
    """
    Parcourt les items du formulaire et retourne :
      sections       : {section_key: [question_info, ...]}
      id_to_section  : {question_id: section_key}
      id_champs      : {"nom": qid, "entreprise": qid, "secteur": qid}

    question_info = {
      "qid", "title", "type",          # type: choice | scale | text | other
      "options"   (list str, choice),
      "scale_low", "scale_high" (int, scale),
      "is_scorable" (bool)
    }

    Règle de score :
      - scale  : (valeur − low) / (high − low) × 20   → 1/5 = 0/20, 5/5 = 20/20
      - choice : première option = meilleure réponse = 20/20
                 (index 0 → 20, index N−1 → 0)
      - text   : non scoré, extrait comme contexte qualitatif
    """
    form = service.forms().get(formId=FORM_ID).execute()
    items = form.get("items", [])

    sections       = {}
    id_to_section  = {}
    current_key    = None
    id_champs      = {"nom": None, "entreprise": None, "secteur": None}

    for item in items:

        if "pageBreakItem" in item:
            key = _section_key(item.get("title", ""))
            current_key = key
            if key and key not in sections:
                sections[key] = []
            continue

        if "questionItem" not in item:
            continue

        q   = item["questionItem"]["question"]
        qid = q["questionId"]
        title_raw = item.get("title", "")

        # ── Champs d'identification (avant la 1ère section) ──────────────────
        if current_key is None:
            t = title_raw.lower()
            if "nom du dirigeant" in t or "nom du client" in t:
                id_champs["nom"] = qid
            elif "nom de l" in t and "entreprise" in t:
                id_champs["entreprise"] = qid
            elif "secteur" in t:
                id_champs["secteur"] = qid
            continue

        # ── Questions dans une section ────────────────────────────────────────
        q_info = {"qid": qid, "title": title_raw}

        if "choiceQuestion" in q:
            opts = [o["value"] for o in q["choiceQuestion"].get("options", [])]
            q_info.update({"type": "choice", "options": opts, "is_scorable": bool(opts)})

        elif "scaleQuestion" in q:
            sq = q["scaleQuestion"]
            q_info.update({
                "type":        "scale",
                "scale_low":   sq.get("low", 1),
                "scale_high":  sq.get("high", 5),
                "is_scorable": True,
            })

        elif "textQuestion" in q:
            paragraph = q["textQuestion"].get("paragraph", False)
            q_info.update({
                "type":        "text_long" if paragraph else "text_short",
                "is_scorable": False,
            })

        else:
            q_info.update({"type": "other", "is_scorable": False})

        sections[current_key].append(q_info)
        id_to_section[qid] = current_key

    return sections, id_to_section, id_champs


# ─── Calcul du score d'une réponse ───────────────────────────────────────────

def _score_one(q_info, answer_value):
    """Retourne un score float 0–20, ou None si inapplicable."""
    if q_info["type"] == "scale":
        low, high = q_info["scale_low"], q_info["scale_high"]
        try:
            v = float(answer_value)
        except (ValueError, TypeError):
            return None
        if high == low:
            return 10.0
        return round(max(0.0, min(20.0, (v - low) / (high - low) * 20)), 2)

    elif q_info["type"] == "choice":
        opts = q_info.get("options", [])
        if answer_value not in opts:
            return None
        n   = len(opts)
        idx = opts.index(answer_value)
        return round((1 - idx / (n - 1)) * 20, 2) if n > 1 else 20.0

    return None


def _compute_scores(sections, id_to_section, response):
    """
    Retourne :
      scores  : {section_key: int 0–20}  (moyenne des questions scorables)
      textes  : {section_key: [{"question": ..., "reponse": ...}]}
    """
    answers       = response.get("answers", {})
    section_pts   = {sk: [] for sk in sections}
    section_texts = {sk: [] for sk in sections}

    for qid, ans_block in answers.items():
        sk = id_to_section.get(qid)
        if not sk:
            continue

        q_info = next((q for q in sections[sk] if q["qid"] == qid), None)
        if not q_info:
            continue

        raw_list = ans_block.get("textAnswers", {}).get("answers", [])
        answer   = raw_list[0]["value"].strip() if raw_list else None
        if not answer:
            continue

        if q_info["is_scorable"]:
            s = _score_one(q_info, answer)
            if s is not None:
                section_pts[sk].append(s)
        else:
            section_texts[sk].append({
                "question": q_info["title"],
                "reponse":  answer,
            })

    scores = {}
    for sk in sections:
        pts = section_pts[sk]
        scores[sk] = min(20, max(0, round(sum(pts) / len(pts)))) if pts else 10

    return scores, section_texts


# ─── Affichage helper ─────────────────────────────────────────────────────────

def _get_field(response, qid):
    if not qid:
        return "?"
    block = response.get("answers", {}).get(qid, {})
    raw   = block.get("textAnswers", {}).get("answers", [])
    return raw[0]["value"].strip() if raw else "?"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    from googleapiclient.discovery import build

    print("=" * 62)
    print("  Prospect 2.0 — Génération automatique du rapport diagnostic")
    print("=" * 62)

    # Authentification
    creds   = _load_creds()
    service = build("forms", "v1", credentials=creds)

    # Structure
    print("\n  → Chargement de la structure du formulaire…")
    sections, id_to_section, id_champs = _build_form_index(service)
    scorable_counts = {sk: sum(1 for q in qs if q["is_scorable"]) for sk, qs in sections.items()}
    print(f"     {len(sections)} sections | questions scorables : "
          + ", ".join(f"{sk}={n}" for sk, n in scorable_counts.items()))

    # Réponses
    print("  → Récupération des réponses…")
    resp_data  = service.forms().responses().list(formId=FORM_ID).execute()
    responses  = resp_data.get("responses", [])

    if not responses:
        print("\n  Aucune réponse trouvée.")
        sys.exit(0)

    # Liste des répondants
    print(f"\n  {len(responses)} réponse(s) :\n")
    for i, r in enumerate(responses):
        nom       = _get_field(r, id_champs["nom"])
        entreprise = _get_field(r, id_champs["entreprise"])
        date      = r.get("createTime", "")[:10]
        print(f"    [{i + 1}] {nom}  —  {entreprise}  ({date})")

    # Sélection
    print()
    if len(responses) == 1:
        idx = 0
        print(f"  → Client unique sélectionné automatiquement.")
    else:
        raw = input("  Numéro du client à traiter : ").strip()
        try:
            idx = int(raw) - 1
            assert 0 <= idx < len(responses)
        except (ValueError, AssertionError):
            print("  Numéro invalide.")
            sys.exit(1)

    response   = responses[idx]
    nom        = _get_field(response, id_champs["nom"])
    entreprise = _get_field(response, id_champs["entreprise"])
    secteur    = _get_field(response, id_champs["secteur"])

    print(f"\n  Client     : {nom}")
    print(f"  Entreprise : {entreprise}")
    print(f"  Secteur    : {secteur}")

    # Calcul des scores
    print("\n  → Calcul des scores…")
    scores, textes = _compute_scores(sections, id_to_section, response)

    print("\n  ┌─────────────────────────────┬────────┐")
    print("  │ Section                     │ Score  │")
    print("  ├─────────────────────────────┼────────┤")
    for sk, score in scores.items():
        bar = "█" * score + "░" * (20 - score)
        print(f"  │ {sk:<27} │ {score:>2}/20  │  {bar}")
    print("  └─────────────────────────────┴────────┘")

    score_global = round(sum(scores.values()) / (20 * len(scores)) * 100)
    print(f"\n  Score global : {score_global}/100")

    # Extraits qualitatifs
    has_texts = any(textes.values())
    if has_texts:
        print("\n  ── Contexte qualitatif (réponses texte libres) ─────────────")
        for sk, items in textes.items():
            if not items:
                continue
            print(f"\n  [{sk}]")
            for item in items:
                q_short = item["question"][:72]
                r_lines = item["reponse"].replace("\n", " ")[:200]
                print(f"    Q : {q_short}")
                print(f"    R : {r_lines}")

    # Appel du script rapport
    cmd = [
        sys.executable, RAPPORT_SCRIPT,
        "--client",       nom,
        "--entreprise",   entreprise,
        "--secteur",      secteur,
        "--organisation", str(scores.get("organisation", 10)),
        "--ventes",       str(scores.get("ventes",       10)),
        "--equipe",       str(scores.get("equipe",       10)),
        "--finances",     str(scores.get("finances",     10)),
        "--outils",       str(scores.get("outils",       10)),
        "--vision",       str(scores.get("vision",       10)),
    ]

    print("\n" + "=" * 62)
    print("  → Génération du PDF…")
    print("=" * 62 + "\n")
    subprocess.run(cmd, check=True)
    print("\n" + "=" * 62)


if __name__ == "__main__":
    main()
