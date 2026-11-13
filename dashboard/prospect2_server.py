#!/usr/bin/env python3
"""
Serveur Flask — Dashboard Prospect 2.0
Port 7374 (le dashboard Solarium Pro tourne sur 7373)
"""

import base64, csv, io, json, os, sys
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, make_response, request, send_file, send_from_directory

BASE_DIR      = Path(__file__).parent.parent          # ~/Documents/prospect2/
RAPPORTS_DIR  = BASE_DIR / "RAPPORTS_CLIENTS"
CSV_PATH      = RAPPORTS_DIR / "suivi_global.csv"
HTML_PATH     = Path(__file__).parent / "dashboard_prospect2.html"
PORT          = 7374

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


# ── Démarrage ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Dashboard Prospect 2.0 → http://localhost:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
