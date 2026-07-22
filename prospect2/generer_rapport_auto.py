#!/usr/bin/env python3
"""
generer_rapport_auto.py — Prospect 2.0
Lit les réponses Google Forms, calcule les scores par section, génère le PDF diagnostic.
Les 'Actions recommandées' des 3 sections prioritaires sont générées par Claude (Anthropic API)
à partir des réponses texte libre du client.

Usage :
  python3 generer_rapport_auto.py
"""

import os, sys, pickle, warnings, importlib.util
warnings.filterwarnings("ignore")

FORM_ID      = "1cMJLbieugSF8QbpS9TU8Tl47kranoYoQarQBeR8w91Y"
CREDS_PATH   = os.path.expanduser("~/Documents/prospect2/credentials/token_forms.pickle")
RAPPORT_SCRIPT = os.path.expanduser(
    "~/Documents/backup-production/rapport_diagnostic_2026-07-01.py"
)

# Mapping clé interne (lowercase) → label affiché dans le rapport (capitalisé)
SECTION_KEY_TO_LABEL = {
    'organisation': 'Organisation',
    'outils':       'Outils',
    'ventes':       'Ventes',
    'finances':     'Finances',
    'equipe':       'Équipe',
    'vision':       'Vision',
}

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


# ─── Génération d'actions personnalisées via Claude API ──────────────────────

_ENV_PATH = os.path.expanduser("~/Documents/resume-matin/.env")

def _load_anthropic_key():
    """Lit ANTHROPIC_API_KEY depuis l'environnement ou ~/Documents/resume-matin/.env."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


def _generer_actions_claude(section_label, nom, secteur, score, textes_libres):
    """
    Appelle claude-sonnet-4-6 pour générer 3 actions concrètes et personnalisées
    basées sur les réponses texte libre du client pour une section donnée.

    Args:
        section_label  : nom affiché de la section (ex: 'Organisation')
        nom            : prénom/nom du client
        secteur        : secteur d'activité
        score          : score obtenu /20
        textes_libres  : liste de {"question": ..., "reponse": ...}

    Retourne une liste de 3 chaînes (actions à l'infinitif).
    """
    import anthropic
    api_key = _load_anthropic_key()

    contexte_qr = ""
    for item in textes_libres:
        q_short = item["question"][:100]
        r_short = item["reponse"][:300]
        contexte_qr += f"Q : {q_short}\nR : {r_short}\n\n"

    if not contexte_qr.strip():
        contexte_qr = "(Aucune réponse texte libre pour cette section.)"

    prompt = f"""Tu es consultant en développement de PME saisonnières au Québec (Prospect 2.0).
Tu dois générer 3 actions concrètes et personnalisées pour un client diagnostiqué.

Client : {nom}
Secteur : {secteur}
Section diagnostiquée : {section_label}
Score obtenu : {score}/20

Réponses du client dans cette section :
{contexte_qr}
Génère exactement 3 actions recommandées pour cette section, directement basées sur ce que le client a dit.
Les actions doivent :
- Commencer par un verbe à l'infinitif (Documenter, Automatiser, Créer, Mettre en place, Identifier, Calculer…)
- Être spécifiques à la réalité du client (mentionner ses outils, sa situation, son secteur si pertinent)
- Être courtes (max 15 mots chacune)
- Être classées du plus urgent au moins urgent

Réponds uniquement avec les 3 actions, une par ligne, sans numérotation ni tiret. Rien d'autre."""

    client_api = anthropic.Anthropic(api_key=api_key)
    message = client_api.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw     = message.content[0].text.strip()
    actions = [line.strip() for line in raw.split("\n") if line.strip()][:3]

    while len(actions) < 3:
        actions.append(f"Améliorer {section_label.lower()} avec l'aide de Prospect 2.0")

    return actions


# ─── Import du module rapport + patch SECTION_INFO + génération PDF ──────────

def _charger_module_rapport():
    """Importe rapport_diagnostic_2026-07-01.py comme module Python."""
    spec = importlib.util.spec_from_file_location("rapport_diagnostic", RAPPORT_SCRIPT)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _patch_and_generate(nom, entreprise, secteur, scores, textes, date_rapport=None):
    """
    Pour les 3 sections les plus faibles, génère des actions personnalisées via Claude API,
    patche SECTION_INFO du module rapport, puis appelle generate() directement.

    Args:
        nom, entreprise, secteur : infos client
        scores   : {section_key_lowercase: int}  ex: {'organisation': 8, 'ventes': 14, ...}
        textes   : {section_key_lowercase: [{question, reponse}]}
        date_rapport : str optionnel
    """
    # 3 sections les plus faibles
    top3_keys = [sk for sk, _ in sorted(scores.items(), key=lambda x: x[1])[:3]]

    print("\n  → Génération des actions personnalisées via Claude API…")
    actions_claude = {}
    for sk in top3_keys:
        label = SECTION_KEY_TO_LABEL.get(sk, sk.capitalize())
        score = scores[sk]
        tx    = textes.get(sk, [])
        print(f"     [{label}] score={score}/20 — {len(tx)} réponse(s) texte libre…",
              end=" ", flush=True)
        acts = _generer_actions_claude(label, nom, secteur, score, tx)
        actions_claude[label] = acts
        print("✓")

    # Charger le module rapport et patcher SECTION_INFO
    rapport = _charger_module_rapport()

    for label, acts in actions_claude.items():
        if label in rapport.SECTION_INFO:
            rapport.SECTION_INFO[label]['actions_low'] = acts
            rapport.SECTION_INFO[label]['actions_med'] = acts

    # Convertir clés lowercase → labels capitalisés pour le rapport
    scores_rapport = {
        SECTION_KEY_TO_LABEL.get(sk, sk.capitalize()): v
        for sk, v in scores.items()
    }

    print("\n" + "=" * 62)
    print("  → Génération du PDF…")
    print("=" * 62 + "\n")
    rapport.generate(nom, entreprise, secteur, scores_rapport, date_rapport)
    print("\n" + "=" * 62)
    print(f"  PDF : ~/Documents/prospect2/rapport_diagnostic_TEST.pdf")
    print("=" * 62)


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
        nom_r       = _get_field(r, id_champs["nom"])
        entreprise_r = _get_field(r, id_champs["entreprise"])
        date_r      = r.get("createTime", "")[:10]
        print(f"    [{i + 1}] {nom_r}  —  {entreprise_r}  ({date_r})")

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

    # Génération PDF avec actions Claude
    _patch_and_generate(nom, entreprise, secteur, scores, textes)


if __name__ == "__main__":
    main()
