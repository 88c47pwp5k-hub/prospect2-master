#!/usr/bin/env python3
"""
Comptabilité de Prospect 2.0 — 9477-9782 Québec inc.

Entièrement séparée de Solarium Pro : ce module ne lit RIEN de Solarium Pro et
n'additionne jamais les deux compagnies. DécoPatio et Nano Protection ne sont
pas des compagnies : ce sont des ACTIVITÉS (marques) de Prospect 2.0, d'où le
libellé « Prospect 2.0 / <activité> » partout — écran, boutons, exports,
rapports. Le libellé vient d'ici et de nulle part ailleurs.

Départ à neuf au 1er novembre 2026 : aucune pièce antérieure n'entre ici.
"""

import json
import os
import re
from datetime import date, datetime, timedelta

# ── Les activités : UNE seule source pour le libellé ───────────────────────
# « à préciser » reste tel quel (décision de Benoit, 15 nov. 2026) : ce n'est
# pas une activité, c'est l'absence de décision.
COMPAGNIE   = "Prospect 2.0"
A_PRECISER  = "a_preciser"

ACTIVITES = {
    "decopatio":  COMPAGNIE + " / DécoPatio",
    "nano":       COMPAGNIE + " / Nano Protection",
    "general":    COMPAGNIE + " / Général",
    A_PRECISER:   "à préciser",
}
# L'ordre d'affichage, partout pareil : les deux marques, le général, puis
# ce qui n'est pas tranché.
ORDRE_ACTIVITES = ["decopatio", "nano", "general", A_PRECISER]
# Les activités qu'on peut CHOISIR (les boutons de classement) — « à préciser »
# n'en fait pas partie : on ne choisit pas de ne pas choisir.
ACTIVITES_CHOISISSABLES = ["decopatio", "nano", "general"]


def libelle_activite(code):
    """Le libellé lisible d'une activité. Un code inconnu n'invente rien :
    il retombe sur « à préciser », jamais sur une marque."""
    return ACTIVITES.get(code, ACTIVITES[A_PRECISER])


# ── Taxes et dates ─────────────────────────────────────────────────────────
TAUX_TPS = 0.05
TAUX_TVQ = 0.09975

# L'exercice se ferme le 31 octobre, comme celui de Solarium Pro.
MOIS_DEBUT_EXERCICE = 11
# Départ à neuf : rien d'avant cette date n'entre dans l'outil.
DEBUT_COMPTABILITE = date(2026, 11, 1)
# Un forfait annuel ne se renouvelle PAS tout seul : on prévient 30 jours avant.
JOURS_ALERTE_RENOUVELLEMENT = 30


def aujourdhui():
    return date.today()


def exercice_de(d):
    """« 2026-2027 » pour toute date du 1er nov. 2026 au 31 oct. 2027."""
    an = d.year if d.month >= MOIS_DEBUT_EXERCICE else d.year - 1
    return "%d-%d" % (an, an + 1)


def bornes_exercice(exercice):
    """(premier jour, dernier jour) d'un exercice nommé « AAAA-AAAA »."""
    an = int(exercice.split("-")[0])
    return date(an, 11, 1), date(an + 1, 10, 31)


def trimestres(exercice):
    """Les quatre trimestres de l'exercice, dans l'ordre."""
    an = int(exercice.split("-")[0])
    decoupe = [
        ("T1", date(an, 11, 1),     date(an + 1, 1, 31)),
        ("T2", date(an + 1, 2, 1),  date(an + 1, 4, 30)),
        ("T3", date(an + 1, 5, 1),  date(an + 1, 7, 31)),
        ("T4", date(an + 1, 8, 1),  date(an + 1, 10, 31)),
    ]
    mois = ["", "janv.", "févr.", "mars", "avril", "mai", "juin",
            "juill.", "août", "sept.", "oct.", "nov.", "déc."]
    return [{
        "code": code,
        "libelle": "%s — %s %d à %s %d" % (code, mois[debut.month], debut.year,
                                           mois[fin.month], fin.year),
        "debut": debut, "fin": fin,
    } for code, debut, fin in decoupe]


def exercices_disponibles(today=None):
    """Les exercices que le sélecteur propose. Il commence à 2026-2027 et ne
    propose JAMAIS rien avant : il n'y a pas de rétroactif ici."""
    today = today or aujourdhui()
    premier = exercice_de(DEBUT_COMPTABILITE)
    courant = exercice_de(today)
    an1, an2 = int(premier.split("-")[0]), int(courant.split("-")[0])
    if an2 < an1:
        return [premier]
    return ["%d-%d" % (a, a + 1) for a in range(an1, an2 + 1)]


# ── Le fichier de données ──────────────────────────────────────────────────
# Une ENVELOPPE, jamais une liste nue : la version et la date de mise à jour
# vivent à côté des pièces.
RACINE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(RACINE, "data", "comptabilite.json")

VIDE = {"version": 1, "maj_le": None, "revenus": [], "depenses": []}


def _chemin(chemin=None):
    """Le chemin du fichier, résolu À L'APPEL.

    Surtout pas `chemin=FICHIER` en valeur par défaut : une constante en
    défaut est figée à la définition du module, et une suite de tests qui
    déplace le fichier écrirait quand même dans le vrai.
    """
    return chemin or os.environ.get("PROSPECT2_COMPTA") or FICHIER


def charger(chemin=None):
    p = _chemin(chemin)
    if not os.path.exists(p):
        return json.loads(json.dumps(VIDE))
    with open(p, encoding="utf-8") as f:
        donnees = json.load(f)
    if not isinstance(donnees, dict):
        raise ValueError("comptabilite.json doit être une enveloppe, pas une liste")
    donnees.setdefault("revenus", [])
    donnees.setdefault("depenses", [])
    return donnees


def sauver(donnees, chemin=None):
    p = _chemin(chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    donnees["maj_le"] = datetime.now().isoformat(timespec="seconds")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)       # écriture atomique : jamais de fichier à moitié écrit
    return donnees


# ── Validation et écriture d'une pièce ─────────────────────────────────────
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _date_valide(brut, champ):
    if not brut or not RE_DATE.match(str(brut)):
        raise ValueError("%s : date attendue au format AAAA-MM-JJ" % champ)
    return date.fromisoformat(str(brut))


def _montant(brut):
    """« 1 234,56 » ou « 1234.56 » -> float. Refuse ce qui n'est pas un
    montant plutôt que de rendre 0 : un zéro silencieux fausse un total."""
    s = str(brut if brut is not None else "").strip()
    s = s.replace(" ", "").replace("\xa0", "").replace(" ", "").replace("$", "")
    s = s.replace(",", ".")
    if not re.fullmatch(r"-?\d+(\.\d+)?", s or ""):
        raise ValueError("montant invalide : %r" % brut)
    v = float(s)
    if v < 0:
        raise ValueError("un montant négatif ne s'inscrit pas ici")
    return round(v, 2)


def taxes_de(avant_taxes, taxable=True):
    """TPS 5 % et TVQ 9,975 %, calculées sur le montant avant taxes."""
    if not taxable:
        return 0.0, 0.0
    return (round(avant_taxes * TAUX_TPS, 2), round(avant_taxes * TAUX_TVQ, 2))


def _prochain_id(lignes, prefixe):
    n = 0
    for l in lignes:
        m = re.match(r"^%s-(\d+)$" % prefixe, str(l.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return "%s-%04d" % (prefixe, n + 1)


def _piece_commune(champs, prefixe, lignes):
    d = _date_valide(champs.get("date"), "date")
    if d < DEBUT_COMPTABILITE:
        raise ValueError(
            "aucun rétroactif : la comptabilité de Prospect 2.0 commence le %s"
            % DEBUT_COMPTABILITE.isoformat())
    activite = champs.get("activite") or A_PRECISER
    if activite not in ACTIVITES:
        raise ValueError("activité inconnue : %r" % activite)
    taxable = bool(champs.get("taxable", True))
    avant = _montant(champs.get("avant_taxes"))
    tps, tvq = taxes_de(avant, taxable)
    return {
        "id": _prochain_id(lignes, prefixe),
        "date": d.isoformat(),
        "exercice": exercice_de(d),
        "activite": activite,
        "description": (champs.get("description") or "").strip(),
        "avant_taxes": avant,
        "taxable": taxable,
        "tps": tps,
        "tvq": tvq,
        "total": round(avant + tps + tvq, 2),
        "inscrit_le": datetime.now().isoformat(timespec="seconds"),
    }


def ajouter_revenu(champs, chemin=None):
    donnees = charger(chemin)
    ligne = _piece_commune(champs, "REV", donnees["revenus"])
    ligne["client"] = (champs.get("client") or "").strip()
    if not ligne["client"]:
        raise ValueError("le nom du client est obligatoire")
    # Un forfait annuel a une échéance ; un publireportage ponctuel n'en a pas.
    ech = (champs.get("echeance") or "").strip()
    ligne["echeance"] = _date_valide(ech, "échéance").isoformat() if ech else None
    # Les forfaits de DécoPatio ne se renouvellent PAS tout seuls : l'outil
    # prévient, il ne renouvelle rien.
    ligne["renouvellement"] = "manuel" if ligne["echeance"] else "aucun"
    donnees["revenus"].append(ligne)
    sauver(donnees, chemin)
    return ligne


def ajouter_depense(champs, chemin=None):
    donnees = charger(chemin)
    ligne = _piece_commune(champs, "DEP", donnees["depenses"])
    ligne["fournisseur"] = (champs.get("fournisseur") or "").strip()
    if not ligne["fournisseur"]:
        raise ValueError("le nom du fournisseur est obligatoire")
    ligne["paye_par"] = (champs.get("paye_par") or "").strip()
    donnees["depenses"].append(ligne)
    sauver(donnees, chemin)
    return ligne


def classer(type_piece, identifiant, activite, chemin=None):
    """Range une ligne « à préciser » dans une activité. Le seul chemin par
    lequel une pièce change d'activité : jamais une devinette automatique."""
    if activite not in ACTIVITES_CHOISISSABLES:
        raise ValueError("activité inconnue : %r" % activite)
    cle = {"revenu": "revenus", "depense": "depenses"}.get(type_piece)
    if not cle:
        raise ValueError("type de pièce inconnu : %r" % type_piece)
    donnees = charger(chemin)
    for ligne in donnees[cle]:
        if ligne.get("id") == identifiant:
            ligne["activite"] = activite
            ligne["classe_le"] = datetime.now().isoformat(timespec="seconds")
            sauver(donnees, chemin)
            return ligne
    raise LookupError("pièce inconnue : %r" % identifiant)


# ── Lecture : le sommaire affiché par l'onglet ─────────────────────────────
def _dans(ligne, debut, fin):
    d = date.fromisoformat(ligne["date"])
    return debut <= d <= fin


def etat_renouvellement(ligne, today=None):
    """Rend (code, libellé, jours) pour un revenu à échéance.

    Rien ne se renouvelle tout seul : l'alerte part 30 jours avant, et une
    échéance dépassée reste affichée — elle ne disparaît pas toute seule.
    """
    today = today or aujourdhui()
    ech = ligne.get("echeance")
    if not ech:
        return ("aucune", "ponctuel — aucune échéance", None)
    jours = (date.fromisoformat(ech) - today).days
    if jours < 0:
        return ("echu", "échu depuis %d jour%s" % (-jours, "s" if -jours > 1 else ""), jours)
    if jours <= JOURS_ALERTE_RENOUVELLEMENT:
        return ("a_renouveler", "à renouveler — dans %d jour%s"
                % (jours, "s" if jours > 1 else ""), jours)
    return ("en_cours", "échéance dans %d jours" % jours, jours)


def _ligne_affichee(ligne, today=None):
    vue = dict(ligne)
    vue["activite_libelle"] = libelle_activite(ligne.get("activite"))
    vue["a_preciser"] = ligne.get("activite", A_PRECISER) == A_PRECISER
    if "client" in ligne:
        code, libelle, jours = etat_renouvellement(ligne, today)
        vue["renouv_code"] = code
        vue["renouv_libelle"] = libelle
        vue["renouv_jours"] = jours
    return vue


def sommaire(exercice=None, today=None, chemin=None):
    """Tout ce que l'onglet affiche, calculé ici — l'écran ne fait que rendre."""
    today = today or aujourdhui()
    exercice = exercice or exercice_de(today)
    debut, fin = bornes_exercice(exercice)
    donnees = charger(chemin)

    revenus  = [l for l in donnees["revenus"]  if _dans(l, debut, fin)]
    depenses = [l for l in donnees["depenses"] if _dans(l, debut, fin)]

    def somme(lignes, champ):
        return round(sum(l.get(champ) or 0 for l in lignes), 2)

    # Ventilation par activité. Les quatre lignes sont TOUJOURS là, même à
    # zéro : une ligne « à préciser » absente ne prouverait rien.
    ventilation = []
    for code in ORDRE_ACTIVITES:
        r = [l for l in revenus  if l.get("activite", A_PRECISER) == code]
        d = [l for l in depenses if l.get("activite", A_PRECISER) == code]
        ventilation.append({
            "code": code,
            "libelle": libelle_activite(code),
            "a_preciser": code == A_PRECISER,
            "revenus":  somme(r, "avant_taxes"),
            "depenses": somme(d, "avant_taxes"),
            "resultat": round(somme(r, "avant_taxes") - somme(d, "avant_taxes"), 2),
            "tps": round(somme(r, "tps") - somme(d, "tps"), 2),
            "tvq": round(somme(r, "tvq") - somme(d, "tvq"), 2),
            "pieces": len(r) + len(d),
        })

    # Taxes par trimestre. Un trimestre à venir rend None, jamais 0 : zéro
    # voudrait dire « vérifié, rien trouvé ».
    taxes = []
    for t in trimestres(exercice):
        a_venir = t["debut"] > today
        r = [l for l in revenus  if _dans(l, t["debut"], t["fin"])]
        d = [l for l in depenses if _dans(l, t["debut"], t["fin"])]
        tps_p, tvq_p = somme(r, "tps"), somme(r, "tvq")
        tps_v, tvq_v = somme(d, "tps"), somme(d, "tvq")
        net = round((tps_p + tvq_p) - (tps_v + tvq_v), 2)
        if a_venir:
            sens = "à venir"
        elif net > 0:
            sens = "remise à faire"
        elif net < 0:
            sens = "remboursement à recevoir"
        else:
            sens = "rien à déclarer pour l'instant"
        taxes.append({
            "code": t["code"], "libelle": t["libelle"],
            "en_cours": t["debut"] <= today <= t["fin"],
            "a_venir": a_venir,
            "tps_percue": None if a_venir else tps_p,
            "tps_payee":  None if a_venir else tps_v,
            "tvq_percue": None if a_venir else tvq_p,
            "tvq_payee":  None if a_venir else tvq_v,
            "net":        None if a_venir else net,
            # Le sens s'écrit en MOTS : un crédit de taxes ne doit jamais se
            # lire comme une dette parce qu'il porte un signe moins.
            "sens": sens,
        })

    vues_revenus  = [_ligne_affichee(l, today) for l in
                     sorted(revenus,  key=lambda l: (l["date"], l["id"]))]
    vues_depenses = [_ligne_affichee(l, today) for l in
                     sorted(depenses, key=lambda l: (l["date"], l["id"]))]
    alertes = [v for v in vues_revenus if v.get("renouv_code") in ("a_renouveler", "echu")]

    rev_ht, dep_ht = somme(revenus, "avant_taxes"), somme(depenses, "avant_taxes")
    trimestre_courant = next((t for t in taxes if t["en_cours"]), None)

    return {
        "compagnie": COMPAGNIE,
        "exercice": exercice,
        "exercices": exercices_disponibles(today),
        "debut": debut.isoformat(),
        "fin": fin.isoformat(),
        "debut_comptabilite": DEBUT_COMPTABILITE.isoformat(),
        "aujourdhui": today.isoformat(),
        "jour_exercice": (today - debut).days + 1 if debut <= today <= fin else None,
        "totaux": {
            "revenus": rev_ht,
            "depenses": dep_ht,
            "resultat": round(rev_ht - dep_ht, 2),
            "taxes_trimestre": trimestre_courant["net"] if trimestre_courant else 0.0,
            "trimestre_libelle": trimestre_courant["libelle"] if trimestre_courant else "—",
            "pieces": len(revenus) + len(depenses),
            "a_preciser": len([l for l in revenus + depenses
                               if l.get("activite", A_PRECISER) == A_PRECISER]),
        },
        "ventilation": ventilation,
        "taxes": taxes,
        "revenus": vues_revenus,
        "depenses": vues_depenses,
        "alertes": alertes,
        "activites": [{"code": c, "libelle": ACTIVITES[c]}
                      for c in ACTIVITES_CHOISISSABLES],
        "jours_alerte": JOURS_ALERTE_RENOUVELLEMENT,
    }


# ── Export CSV — mêmes libellés que l'écran ────────────────────────────────
COLONNES_EXPORT = ["Type", "Date", "Exercice", "Activité", "Tiers", "Description",
                   "Avant taxes", "TPS", "TVQ", "Total", "Échéance", "Renouvellement"]


def lignes_export(exercice=None, today=None, chemin=None):
    s = sommaire(exercice, today, chemin)
    lignes = []
    for r in s["revenus"]:
        lignes.append(["Revenu", r["date"], r["exercice"], r["activite_libelle"],
                       r.get("client", ""), r.get("description", ""),
                       "%.2f" % r["avant_taxes"], "%.2f" % r["tps"], "%.2f" % r["tvq"],
                       "%.2f" % r["total"], r.get("echeance") or "",
                       r.get("renouv_libelle", "")])
    for d in s["depenses"]:
        lignes.append(["Dépense", d["date"], d["exercice"], d["activite_libelle"],
                       d.get("fournisseur", ""), d.get("description", ""),
                       "%.2f" % d["avant_taxes"], "%.2f" % d["tps"], "%.2f" % d["tvq"],
                       "%.2f" % d["total"], "", d.get("paye_par", "")])
    return lignes
