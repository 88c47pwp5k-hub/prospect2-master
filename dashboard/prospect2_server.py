#!/usr/bin/env python3
"""
Serveur Flask — Dashboard Prospect 2.0
Port 7374 (le dashboard Solarium Pro tourne sur 7373)
"""

import base64, csv, io, json, os, sys
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, make_response, request, send_file, send_from_directory

sys.path.insert(0, str(Path(__file__).parent))
import comptabilite as compta

BASE_DIR      = Path(__file__).parent.parent          # ~/Documents/prospect2/
RAPPORTS_DIR  = BASE_DIR / "RAPPORTS_CLIENTS"
CSV_PATH      = RAPPORTS_DIR / "suivi_global.csv"
HTML_PATH     = Path(__file__).parent / "dashboard_prospect2.html"
PORT          = int(os.environ.get("PROSPECT2_PORT", 7374))

app = Flask(__name__)

# ── CORS ────────────────────────────────────────────────────────────────────

@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options(path):
    return "", 204


# ── Utilitaires CSV ─────────────────────────────────────────────────────────

COLONNES = ["nom_client", "entreprise", "score", "etape",
            "sous_etape", "raison", "date_dernier_envoi", "chemin_rapport_pdf"]

def lire_statut_txt(nom_client: str) -> dict:
    """Lit etape/sous_etape/raison depuis statut.txt si présent."""
    # Cherche le dossier du client (format NomPrenom_Entreprise)
    slug = nom_client.replace(" ", "_")
    for dossier in RAPPORTS_DIR.iterdir():
        if not dossier.is_dir():
            continue
        if slug.lower() in dossier.name.lower():
            statut_path = dossier / "statut.txt"
            if statut_path.exists():
                kv = {}
                for ligne in statut_path.read_text(encoding="utf-8").splitlines():
                    if "=" in ligne:
                        cle, _, val = ligne.partition("=")
                        kv[cle.strip()] = val.strip()
                return kv
    return {}

def lire_clients() -> list[dict]:
    """Lit suivi_global.csv, surcharge avec statut.txt si nécessaire."""
    if not CSV_PATH.exists():
        return []
    clients = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            client = {col: (row.get(col) or "").strip() for col in COLONNES}
            # Priorité statut.txt pour les champs de pilotage
            kv = lire_statut_txt(client["nom_client"])
            for champ in ("etape", "sous_etape", "raison"):
                if kv.get(champ):
                    client[champ] = kv[champ]
            clients.append(client)
    return clients

def ecrire_clients(clients: list[dict]):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLONNES)
        writer.writeheader()
        writer.writerows(clients)

def mettre_a_jour_statut_txt(nom_client: str, etape: str,
                              sous_etape: str, raison: str):
    slug = nom_client.replace(" ", "_")
    for dossier in RAPPORTS_DIR.iterdir():
        if not dossier.is_dir():
            continue
        if slug.lower() in dossier.name.lower():
            statut_path = dossier / "statut.txt"
            # Lit lignes existantes (hors champs pilotage)
            lignes_existantes = []
            if statut_path.exists():
                for ligne in statut_path.read_text(encoding="utf-8").splitlines():
                    cle = ligne.partition("=")[0].strip()
                    if cle not in ("etape", "sous_etape", "raison"):
                        lignes_existantes.append(ligne)
            # Ajoute/met à jour les 3 champs
            lignes_existantes += [
                f"etape={etape}",
                f"sous_etape={sous_etape}",
                f"raison={raison}",
            ]
            statut_path.write_text("\n".join(lignes_existantes) + "\n",
                                   encoding="utf-8")
            return


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(HTML_PATH)


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(Path(__file__).parent / "assets"), filename)


@app.route("/api/clients")
def api_clients():
    return jsonify(lire_clients())


@app.route("/api/update-statut", methods=["POST"])
def api_update_statut():
    body       = request.get_json(silent=True) or {}
    nom_client = body.get("nom_client", "").strip()
    etape      = body.get("etape", "").strip()
    sous_etape = body.get("sous_etape", "").strip()
    raison     = body.get("raison", "").strip()

    if not nom_client or not etape:
        return jsonify({"ok": False, "error": "nom_client et etape requis"}), 400

    etapes_valides = {"client_actif", "en_prospection", "pas_pret", "refuse"}
    if etape not in etapes_valides:
        return jsonify({"ok": False, "error": f"etape invalide: {etape}"}), 400

    clients = lire_clients()
    trouve  = False
    for c in clients:
        if c["nom_client"].lower() == nom_client.lower():
            c["etape"]      = etape
            c["sous_etape"] = sous_etape if etape == "en_prospection" else ""
            c["raison"]     = raison if etape in ("pas_pret", "refuse") else ""
            trouve = True
            break

    if not trouve:
        return jsonify({"ok": False, "error": "Client introuvable"}), 404

    ecrire_clients(clients)
    mettre_a_jour_statut_txt(nom_client, etape, sous_etape, raison)
    return jsonify({"ok": True})


@app.route("/rapport/<path:nom_client>")
def servir_rapport(nom_client):
    clients = lire_clients()
    for c in clients:
        if c["nom_client"].replace(" ", "_").lower() == nom_client.lower():
            chemin = BASE_DIR / c["chemin_rapport_pdf"]
            if chemin.exists():
                return send_file(str(chemin), mimetype="application/pdf")
            return jsonify({"error": "PDF introuvable"}), 404
    return jsonify({"error": "Client inconnu"}), 404


FICHE_DEFAUT = {
    "outils": {
        "inventaire": {"actif": False, "chemin": "", "lien": ""},
        "sd":         {"actif": False, "chemin": "", "lien": ""},
        "sm":         {"actif": False, "chemin": "", "lien": ""},
        "sp":         {"actif": False, "chemin": "", "lien": ""},
        "personnalises": [],
    },
    "identifiants": [],
    "historique": [],
}

def trouver_dossier_client(nom_client: str):
    slug = nom_client.replace(" ", "_")
    for dossier in RAPPORTS_DIR.iterdir():
        if dossier.is_dir() and slug.lower() in dossier.name.lower():
            return dossier
    return None


@app.route("/api/fiche/<path:nom_client>", methods=["GET"])
def api_get_fiche(nom_client):
    import copy
    dossier = trouver_dossier_client(nom_client)
    if not dossier:
        return jsonify({"error": "Client introuvable"}), 404
    fiche_path = dossier / "fiche_outils.json"
    if fiche_path.exists():
        data = json.loads(fiche_path.read_text(encoding="utf-8"))
    else:
        data = copy.deepcopy(FICHE_DEFAUT)
    return jsonify(data)


@app.route("/api/fiche/<path:nom_client>", methods=["POST"])
def api_post_fiche(nom_client):
    dossier = trouver_dossier_client(nom_client)
    if not dossier:
        return jsonify({"error": "Client introuvable"}), 404
    data = request.get_json(silent=True) or {}
    fiche_path = dossier / "fiche_outils.json"
    fiche_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True})


# ── Suppression client ───────────────────────────────────────────────────────

@app.route("/api/client/<path:nom_client>", methods=["DELETE"])
def api_supprimer_client(nom_client):
    nom_client = nom_client.strip()
    clients = lire_clients()
    avant = len(clients)
    clients = [c for c in clients if c["nom_client"].lower() != nom_client.lower()]
    if len(clients) == avant:
        return jsonify({"ok": False, "error": "Client introuvable"}), 404
    ecrire_clients(clients)
    return jsonify({"ok": True})


# ── Export CSV ───────────────────────────────────────────────────────────────

def _filtrer_clients(etape: str, sous: str, q: str) -> list[dict]:
    clients = lire_clients()
    return [c for c in clients if
            (not q     or q in (c["nom_client"] + " " + c["entreprise"]).lower()) and
            (not etape or c["etape"] == etape) and
            (not sous  or c["sous_etape"] == sous)]


@app.route("/api/export/csv")
def api_export_csv():
    etape = request.args.get("etape", "").strip()
    sous  = request.args.get("sous_etape", "").strip()
    q     = request.args.get("recherche", "").lower().strip()

    filtres = _filtrer_clients(etape, sous, q)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLONNES)
    writer.writeheader()
    writer.writerows(filtres)

    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="prospect2_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    return resp


# ── Export PDF ────────────────────────────────────────────────────────────────

_ETAPES_LIB = {
    "client_actif":   "Client actif",
    "en_prospection": "En prospection",
    "pas_pret":       "Pas prêt",
    "refuse":         "Refusé",
}


@app.route("/api/export/pdf")
def api_export_pdf():
    from weasyprint import HTML as WP_HTML

    etape = request.args.get("etape", "").strip()
    sous  = request.args.get("sous_etape", "").strip()
    q     = request.args.get("recherche", "").lower().strip()

    filtres = _filtrer_clients(etape, sous, q)

    # Logo base64
    logo_path = Path(__file__).parent / "assets" / "logo_prospect.png"
    logo_tag  = ""
    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_tag = f'<img src="data:image/png;base64,{b64}" class="logo" />'

    filtre_desc = ""
    if etape:
        filtre_desc += f" &nbsp;·&nbsp; Étape : {_ETAPES_LIB.get(etape, etape)}"
    if q:
        filtre_desc += f" &nbsp;·&nbsp; Recherche : {q}"

    rows = "".join(
        f"<tr>"
        f"<td>{c['nom_client']}</td>"
        f"<td>{c['entreprise']}</td>"
        f"<td class='score'>{c['score'] or '—'}</td>"
        f"<td>{_ETAPES_LIB.get(c['etape'], c['etape'])}</td>"
        f"<td>{c['date_dernier_envoi'] or '—'}</td>"
        f"</tr>"
        for c in filtres
    )

    now_str = datetime.now().strftime("%d %B %Y à %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8" />
<style>
  @page {{ margin: 1.5cm; }}
  body {{ font-family: "Helvetica Neue", Arial, sans-serif; color: #201C20; font-size: 10pt; }}
  header {{ background: #1B3A5C; color: #fff; padding: 14px 18px; display: flex;
            align-items: center; gap: 14px; border-radius: 6px; margin-bottom: 18px; }}
  header .logo {{ height: 42px; width: 42px; object-fit: contain;
                  background: #fff; border-radius: 6px; padding: 2px; }}
  header h1 {{ font-size: 1.2rem; font-weight: 700; margin: 0; }}
  header .sub {{ font-size: .72rem; color: #9BBBD8; margin-top: 3px; }}
  .meta {{ font-size: .78rem; color: #666; margin-bottom: 14px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
  thead tr {{ background: #1B3A5C; color: #fff; }}
  thead th {{ padding: 8px 12px; text-align: left; font-size: .72rem;
              text-transform: uppercase; letter-spacing: .5px; font-weight: 700; }}
  tbody tr:nth-child(even) {{ background: #F7F6F2; }}
  tbody tr {{ border-bottom: 1px solid #E0E0E0; }}
  td {{ padding: 8px 12px; vertical-align: middle; }}
  .score {{ font-weight: 700; color: #1B3A5C; text-align: center; }}
  footer {{ margin-top: 22px; font-size: .7rem; color: #aaa;
            text-align: center; border-top: 1px solid #eee; padding-top: 8px; }}
</style></head>
<body>
<header>
  {logo_tag}
  <div>
    <h1>Dashboard Prospect 2.0</h1>
    <div class="sub">Gestion du pipeline de prospection{filtre_desc}</div>
  </div>
</header>
<div class="meta">{len(filtres)} client(s) exporté(s) · {now_str}</div>
<table>
  <thead><tr>
    <th>Client</th><th>Entreprise</th><th>Score</th><th>Étape</th><th>Dernier envoi</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<footer>Généré le {now_str} &nbsp;·&nbsp; Prospect 2.0</footer>
</body></html>"""

    pdf_bytes = WP_HTML(string=html).write_pdf()
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="prospect2_{datetime.now().strftime("%Y%m%d")}.pdf"'
    )
    return resp


# ── Comptabilité de Prospect 2.0 ─────────────────────────────────────────────
# Tout le calcul vit dans comptabilite.py ; ces routes ne font que passer les
# plats. Aucune route ne lit ni n'écrit quoi que ce soit de Solarium Pro.

def _erreur(e, code=400):
    return jsonify({"ok": False, "error": str(e)}), code


@app.route("/api/comptabilite")
def api_comptabilite():
    exercice = (request.args.get("exercice") or "").strip() or None
    try:
        return jsonify({"ok": True, "data": compta.sommaire(exercice)})
    except ValueError as e:
        return _erreur(e)


@app.route("/api/comptabilite/revenu", methods=["POST"])
def api_compta_revenu():
    try:
        return jsonify({"ok": True, "ligne": compta.ajouter_revenu(
            request.get_json(silent=True) or {})})
    except ValueError as e:
        return _erreur(e)


@app.route("/api/comptabilite/depense", methods=["POST"])
def api_compta_depense():
    try:
        return jsonify({"ok": True, "ligne": compta.ajouter_depense(
            request.get_json(silent=True) or {})})
    except ValueError as e:
        return _erreur(e)


@app.route("/api/comptabilite/activite", methods=["POST"])
def api_compta_activite():
    body = request.get_json(silent=True) or {}
    try:
        ligne = compta.classer(body.get("type"), body.get("id"), body.get("activite"))
        return jsonify({"ok": True, "ligne": ligne,
                        "libelle": compta.libelle_activite(ligne["activite"])})
    except ValueError as e:
        return _erreur(e)
    except LookupError as e:
        return _erreur(e, 404)


@app.route("/api/comptabilite/export/csv")
def api_compta_csv():
    exercice = (request.args.get("exercice") or "").strip() or None
    s = compta.sommaire(exercice)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Comptabilité " + compta.COMPAGNIE, "exercice " + s["exercice"]])
    w.writerow(compta.COLONNES_EXPORT)
    for ligne in compta.lignes_export(s["exercice"]):
        w.writerow(ligne)
    w.writerow([])
    w.writerow(["Ventilation par activité"])
    w.writerow(["Activité", "Revenus", "Dépenses", "Résultat", "Pièces"])
    for v in s["ventilation"]:
        w.writerow([v["libelle"], "%.2f" % v["revenus"], "%.2f" % v["depenses"],
                    "%.2f" % v["resultat"], v["pieces"]])

    resp = make_response("﻿" + buf.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = (
        'attachment; filename="prospect2_comptabilite_%s.csv"' % s["exercice"])
    return resp


def _html_rapport(s):
    """Le rapport PDF — mêmes libellés que l'écran, mêmes totaux."""
    def argent(v):
        return ("%.2f" % v).replace(".", ",") + " $"

    lignes_v = "".join(
        "<tr class='%s'><td>%s</td><td class='n'>%s</td><td class='n'>%s</td>"
        "<td class='n'>%s</td><td class='n'>%d</td></tr>"
        % ("prec" if v["a_preciser"] else "", v["libelle"], argent(v["revenus"]),
           argent(v["depenses"]), argent(v["resultat"]), v["pieces"])
        for v in s["ventilation"])

    def tbl(lignes, tiers, extra_t, extra):
        if not lignes:
            return ("<p class='vide'>Aucune pièce inscrite pour cet exercice.</p>")
        corps = "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='n'>%s</td>"
            "<td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td>%s</td></tr>"
            % (l["date"], l.get(tiers, ""), l.get("description", ""),
               l["activite_libelle"], argent(l["avant_taxes"]), argent(l["tps"]),
               argent(l["tvq"]), argent(l["total"]), extra(l))
            for l in lignes)
        return ("<table><thead><tr><th>Date</th><th>%s</th><th>Description</th>"
                "<th>Activité</th><th class='n'>Avant taxes</th><th class='n'>TPS</th>"
                "<th class='n'>TVQ</th><th class='n'>Total</th><th>%s</th></tr></thead>"
                "<tbody>%s</tbody></table>"
                % (tiers.capitalize(), extra_t, corps))

    lignes_t = "".join(
        "<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td>"
        "<td class='n'>%s</td><td>%s</td></tr>"
        % (t["libelle"],
           "—" if t["a_venir"] else argent(t["tps_percue"]),
           "—" if t["a_venir"] else argent(t["tps_payee"]),
           "—" if t["a_venir"] else argent(t["tvq_percue"]),
           "—" if t["a_venir"] else argent(t["tvq_payee"]),
           t["sens"])
        for t in s["taxes"])

    alertes = ""
    if s["alertes"]:
        alertes = ("<h2>À renouveler</h2><p class='note'>Les forfaits annuels ne se "
                   "renouvellent pas tout seuls : l'alerte part %d jours avant "
                   "l'échéance.</p><ul>%s</ul>"
                   % (s["jours_alerte"], "".join(
                       "<li><b>%s</b> — %s (%s) · %s</li>"
                       % (a.get("client", ""), a.get("description", ""),
                          a["activite_libelle"], a["renouv_libelle"])
                       for a in s["alertes"])))

    return """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8" /><style>
  /* La phrase du bas vit dans la MARGE de la page : sinon elle se pousse
     toute seule sur une page blanche supplémentaire. */
  @page {{ size: A4 landscape; margin: 1.2cm 1.2cm 1.5cm;
           @bottom-left {{ content: "Prospect 2.0 — DécoPatio et Nano Protection sont des activités de la compagnie, pas des compagnies. Aucune donnée de Solarium Pro n\'entre dans ce rapport.";
                           font-size: 6.9pt; color: #9a9a9a; }}
           @bottom-right {{ content: "page " counter(page) " / " counter(pages);
                            font-size: 6.9pt; color: #9a9a9a; }} }}
  body {{ font-family: "Helvetica Neue", Arial, sans-serif; color:#201C20; font-size:9pt; }}
  header {{ background:#1B3A5C; color:#fff; border-radius:9px; padding:11px 15px;
            display:flex; justify-content:space-between; align-items:flex-end; }}
  header h1 {{ font-size:13pt; }} header h1 span {{ color:#FF6B35; }}
  header .s {{ font-size:7.6pt; color:#9BBBD8; margin-top:3px; }}
  header .d {{ font-size:7.4pt; color:#CFE0EF; text-align:right; }}
  h2 {{ font-size:10pt; color:#1B3A5C; margin:13px 0 6px; padding-bottom:3px;
        border-bottom:2px solid #FF6B35; }}
  table {{ width:100%; border-collapse:collapse; font-size:7.8pt; margin-top:4px; }}
  thead tr {{ background:#1B3A5C; color:#fff; }}
  th {{ padding:5px 7px; text-align:left; font-size:6.9pt; text-transform:uppercase; }}
  td {{ padding:4px 7px; border-bottom:1px solid #EFEDE8; }}
  .n {{ text-align:right; }}
  tr.prec td {{ background:#FFF0E8; color:#8a4420; }}
  .tuiles {{ display:flex; gap:8px; margin-top:8px; }}
  .tuile {{ flex:1; border:1px solid #E2DED6; border-radius:9px; padding:8px 10px; }}
  .tuile .l {{ font-size:6.8pt; text-transform:uppercase; color:#7a7a7a; font-weight:700; }}
  .tuile .v {{ font-size:14pt; font-weight:700; color:#1B3A5C; }}
  .note {{ font-size:7.6pt; color:#5c5c5c; }}
  .vide {{ font-size:8pt; color:#8a8a8a; border:1px dashed #c9c4ba; border-radius:8px;
           padding:9px; text-align:center; }}
  ul {{ margin-left:15px; font-size:8pt; }}
</style></head><body>
<header>
  <div><h1>Comptabilité <span>{compagnie}</span></h1>
    <div class="s">9477-9782 Québec inc. — exercice {exercice} ({debut} au {fin}) ·
    séparée de Solarium Pro, aucun chiffre additionné</div></div>
  <div class="d">Produit le {imprime}<br />{pieces} pièce(s) · {aprec} à préciser</div>
</header>
<div class="tuiles">
  <div class="tuile"><div class="l">Revenus</div><div class="v">{revenus}</div></div>
  <div class="tuile"><div class="l">Dépenses</div><div class="v">{depenses}</div></div>
  <div class="tuile"><div class="l">Résultat</div><div class="v">{resultat}</div></div>
  <div class="tuile"><div class="l">Taxes du trimestre</div><div class="v">{taxes}</div>
     <div class="note">{trim}</div></div>
</div>
<h2>Ventilation par activité</h2>
<table><thead><tr><th>Activité</th><th class="n">Revenus</th><th class="n">Dépenses</th>
<th class="n">Résultat</th><th class="n">Pièces</th></tr></thead><tbody>{vent}</tbody></table>
<h2>Revenus</h2>{rev}
<h2>Dépenses</h2>{dep}
<h2>Taxes par trimestre</h2>
<table><thead><tr><th>Trimestre</th><th class="n">TPS perçue</th><th class="n">TPS payée</th>
<th class="n">TVQ perçue</th><th class="n">TVQ payée</th><th>Sens</th></tr></thead>
<tbody>{tax}</tbody></table>
{alertes}
</body></html>""".format(
        compagnie=s["compagnie"], exercice=s["exercice"], debut=s["debut"], fin=s["fin"],
        imprime=datetime.now().strftime("%Y-%m-%d %H:%M"),
        pieces=s["totaux"]["pieces"], aprec=s["totaux"]["a_preciser"],
        revenus=argent(s["totaux"]["revenus"]), depenses=argent(s["totaux"]["depenses"]),
        resultat=argent(s["totaux"]["resultat"]), taxes=argent(s["totaux"]["taxes_trimestre"]),
        trim=s["totaux"]["trimestre_libelle"], vent=lignes_v,
        rev=tbl(s["revenus"], "client", "Renouvellement", lambda l: l["renouv_libelle"]),
        dep=tbl(s["depenses"], "fournisseur", "Payé par", lambda l: l.get("paye_par", "")),
        tax=lignes_t, alertes=alertes)


@app.route("/api/comptabilite/export/pdf")
def api_compta_pdf():
    from weasyprint import HTML as WP_HTML
    exercice = (request.args.get("exercice") or "").strip() or None
    s = compta.sommaire(exercice)
    pdf = WP_HTML(string=_html_rapport(s)).write_pdf()
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = (
        'attachment; filename="prospect2_comptabilite_%s.pdf"' % s["exercice"])
    return resp


# ── Démarrage ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Dashboard Prospect 2.0 → http://localhost:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
