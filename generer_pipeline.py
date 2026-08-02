#!/usr/bin/env python3
import os, csv, json, socket, threading, webbrowser
from datetime import datetime
from flask import Flask, request, jsonify

CSV_PATH   = os.path.expanduser("~/Documents/prospect2/prospects.csv")
SUIVI_PATH = os.path.expanduser("~/Documents/prospect2/RAPPORTS_CLIENTS/suivi_global.csv")
_SUIVI_COLS = ["nom_client", "entreprise", "score", "etape", "sous_etape",
               "raison", "date_dernier_envoi", "chemin_rapport_pdf"]

def _port_libre():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]

PORT = _port_libre()
app  = Flask(__name__)

# ── CSV ───────────────────────────────────────────────────────────────────────

def lire_csv():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        lines = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    if not lines:
        return []
    header     = [c.lower() for c in lines[0]]
    has_header = "nom" in header or "courriel" in header
    rows = []
    for cols in (lines[1:] if has_header else lines):
        while len(cols) < 8:
            cols.append("")
        rows.append({
            "nom":        cols[0].strip(),
            "entreprise": cols[1].strip(),
            "courriel":   cols[2].strip(),
            "date_inv":   cols[3].strip(),
            "s_envoi":    cols[4].strip(),
            "ouvert":     cols[5].strip(),
            "date_rap":   cols[6].strip(),
            "statut":     cols[7].strip() or cols[4].strip(),
        })
    return rows

def ecrire_csv(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom","entreprise","courriel","date_envoi","statut_envoi",
                    "invitation_ouverte","date_rapport","statut"])
        for r in rows:
            w.writerow([r["nom"], r["entreprise"], r["courriel"], r["date_inv"],
                        r["s_envoi"], r["ouvert"], r["date_rap"], r["statut"]])

# ── Sync Pipeline → Dashboard ────────────────────────────────────────────────

def sync_converti_vers_dashboard(nom, entreprise=""):
    """Ajoute une entrée dans suivi_global.csv quand un prospect est converti.
    Skip silencieusement si nom_client existe déjà."""
    existants = []
    if os.path.exists(SUIVI_PATH):
        with open(SUIVI_PATH, newline="", encoding="utf-8") as f:
            existants = list(csv.DictReader(f))

    for e in existants:
        if e.get("nom_client", "").strip().lower() == nom.strip().lower():
            print(f"[Pipeline→Dashboard] SKIP doublon : {nom!r} déjà présent dans suivi_global.csv",
                  flush=True)
            return

    already_has_file = os.path.exists(SUIVI_PATH)
    with open(SUIVI_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_SUIVI_COLS)
        if not already_has_file:
            w.writeheader()
        w.writerow({
            "nom_client":         nom,
            "entreprise":         entreprise,
            "score":              "",
            "etape":              "en_prospection",
            "sous_etape":         "diagnostic_envoye",
            "raison":             "",
            "date_dernier_envoi": datetime.now().strftime("%Y-%m-%d"),
            "chemin_rapport_pdf": "",
        })
    print(f"[Pipeline→Dashboard] SYNC OK : {nom!r} → suivi_global.csv "
          f"(en_prospection / diagnostic_envoye, {datetime.now().strftime('%Y-%m-%d')})",
          flush=True)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    rows     = lire_csv()
    data_js  = json.dumps(rows, ensure_ascii=False)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return HTML.replace("__DATA__", data_js) \
               .replace("__TIME__", gen_time) \
               .replace("__PORT__", str(PORT))

@app.route("/update", methods=["POST"])
def update():
    data     = request.get_json()
    courriel = (data.get("courriel") or "").strip()
    action   = (data.get("action")   or "").strip()
    now      = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows     = lire_csv()

    for r in rows:
        if r["courriel"] == courriel:
            if action == "ouvert":
                r["ouvert"] = now
                r["statut"] = "ouvert"
            elif action == "rapport":
                r["ouvert"]   = r["ouvert"] or now
                r["date_rap"] = now
                r["statut"]   = "rapport"
            elif action == "converti":
                r["ouvert"]   = r["ouvert"] or "oui"
                r["date_rap"] = r["date_rap"] or now
                r["statut"]   = "converti"
                sync_converti_vers_dashboard(r["nom"], r["entreprise"])
            break

    ecrire_csv(rows)
    return jsonify(ok=True, rows=rows)

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pipeline Prospects — Prospect 2.0</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f9; color: #201C20;
      min-height: 100vh; padding: 40px 32px;
    }
    header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; }
    h1 { font-size: 1.4rem; font-weight: 700; }
    h1 span { color: #E8B014; }
    #ts { font-size: .8rem; color: #bbb; }
    #stats { display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }
    .stat {
      background: #fff; border-radius: 10px;
      box-shadow: 0 2px 12px rgba(0,0,0,.07);
      padding: 16px 24px; text-align: center; min-width: 120px;
    }
    .stat .n { font-size: 2rem; font-weight: 700; color: #E8B014; }
    .stat .l { font-size: .78rem; color: #888; margin-top: 2px; }
    .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 16px rgba(0,0,0,.07); overflow: hidden; }
    .toolbar {
      padding: 14px 20px; border-bottom: 1px solid #f0f0f0;
      display: flex; align-items: center; gap: 12px;
    }
    .toolbar input {
      padding: 7px 12px; border: 1.5px solid #e0e0e0; border-radius: 7px;
      font-size: .9rem; outline: none; width: 220px; transition: border-color .2s;
    }
    .toolbar input:focus { border-color: #E8B014; }
    .toolbar select {
      padding: 7px 10px; border: 1.5px solid #e0e0e0; border-radius: 7px;
      font-size: .9rem; outline: none; cursor: pointer; background: #fff;
    }
    table { width: 100%; border-collapse: collapse; font-size: .88rem; }
    thead tr { background: #fafafa; border-bottom: 2px solid #f0f0f0; }
    th {
      padding: 11px 14px; text-align: left; font-size: .75rem;
      font-weight: 600; color: #888; text-transform: uppercase;
      letter-spacing: .04em; cursor: pointer; user-select: none; white-space: nowrap;
    }
    th:hover { color: #E8B014; }
    tbody tr { border-bottom: 1px solid #f5f5f5; transition: background .15s; }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: #fffbf0; }
    td { padding: 10px 14px; vertical-align: middle; }
    td.nom { font-weight: 600; }
    td.nom .entreprise-sous { font-weight: 400; font-size: .81rem; color: #888; margin-top: 1px; }
    td.courriel { color: #555; font-size: .83rem; }
    td.date { color: #888; font-size: .81rem; white-space: nowrap; }
    .badge {
      display: inline-block; padding: 3px 10px;
      border-radius: 20px; font-size: .76rem; font-weight: 600;
    }
    .badge-envoyé   { background: #e8f4fd; color: #1B6CA8; }
    .badge-ouvert   { background: #fff8e0; color: #b07800; }
    .badge-rapport  { background: #e8fdf0; color: #1a8042; }
    .badge-converti { background: #fef3d0; color: #8a6000; }
    .badge-autre    { background: #f5f5f5; color: #bbb; }
    .check-yes { color: #1a8042; font-weight: 700; }
    .check-no  { color: #ddd; }
    .actions { display: flex; gap: 6px; flex-wrap: nowrap; }
    .btn-action {
      padding: 4px 10px; border: none; border-radius: 6px;
      font-size: .75rem; font-weight: 600; cursor: pointer;
      transition: opacity .15s, transform .1s; white-space: nowrap;
    }
    .btn-action:hover { opacity: .8; transform: scale(1.04); }
    .btn-action:disabled { opacity: .35; cursor: default; transform: none; }
    .btn-ouvert   { background: #fff8e0; color: #b07800; }
    .btn-rapport  { background: #e8fdf0; color: #1a8042; }
    .btn-converti { background: #fef3d0; color: #8a6000; }
    #empty { text-align: center; padding: 60px; color: #bbb; font-size: .95rem; display: none; }
    .spinner { display: none; width: 14px; height: 14px; border: 2px solid #ddd;
      border-top-color: #E8B014; border-radius: 50%; animation: spin .6s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<header>
  <h1>Pipeline <span>Prospect 2.0</span></h1>
  <span id="ts">Généré le __TIME__</span>
</header>

<div id="stats">
  <div class="stat"><div class="n" id="s-total">0</div><div class="l">Invitations</div></div>
  <div class="stat"><div class="n" id="s-ouverts">0</div><div class="l">Ouvertes</div></div>
  <div class="stat"><div class="n" id="s-rapports">0</div><div class="l">Rapports envoyés</div></div>
  <div class="stat"><div class="n" id="s-convertis">0</div><div class="l">Convertis</div></div>
</div>

<div class="card">
  <div class="toolbar">
    <input type="text" id="search" placeholder="Rechercher…" oninput="render()">
    <select id="filtre-statut" onchange="render()">
      <option value="">Tous les statuts</option>
      <option value="envoy">Envoyé</option>
      <option value="ouvert">Ouvert</option>
      <option value="rapport">Rapport envoyé</option>
      <option value="converti">Converti</option>
    </select>
  </div>
  <table>
    <thead>
      <tr>
        <th onclick="sortBy(0)">Nom / Entreprise ↕</th>
        <th onclick="sortBy(2)">Courriel ↕</th>
        <th onclick="sortBy(3)">Date invitation ↕</th>
        <th>Invitation ouverte</th>
        <th>Rapport envoyé</th>
        <th onclick="sortBy(6)">Date rapport ↕</th>
        <th onclick="sortBy(7)">Statut ↕</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div id="empty">Aucun prospect trouvé.</div>
</div>

<script>
const PORT = __PORT__;
let rows = __DATA__;
let sortCol = 3, sortAsc = false;

function badgeStatut(s) {
  const v = (s||'').toLowerCase();
  if (v.includes('converti')) return `<span class="badge badge-converti">Converti</span>`;
  if (v.includes('rapport'))  return `<span class="badge badge-rapport">Rapport envoyé</span>`;
  if (v.includes('ouvert'))   return `<span class="badge badge-ouvert">Ouvert</span>`;
  if (v.includes('envoy'))    return `<span class="badge badge-envoyé">Envoyé</span>`;
  return `<span class="badge badge-autre">${s||'—'}</span>`;
}
function check(v) {
  return (v||'').toLowerCase()==='oui'
    ? '<span class="check-yes">✓</span>'
    : '<span class="check-no">—</span>';
}
function updateStats() {
  document.getElementById('s-total').textContent     = rows.length;
  document.getElementById('s-ouverts').textContent   = rows.filter(r=>(r.ouvert||'').toLowerCase()==='oui').length;
  document.getElementById('s-rapports').textContent  = rows.filter(r=>(r.statut||'').toLowerCase().includes('rapport')).length;
  document.getElementById('s-convertis').textContent = rows.filter(r=>(r.statut||'').toLowerCase().includes('converti')).length;
}

function btnDisabled(statut, action) {
  const s = (statut||'').toLowerCase();
  if (action === 'ouvert')   return s === 'ouvert' || s === 'rapport' || s === 'converti';
  if (action === 'rapport')  return s === 'rapport' || s === 'converti';
  if (action === 'converti') return s === 'converti';
  return false;
}

async function updateStatut(courriel, action, btn) {
  btn.disabled = true;
  const spinner = btn.parentElement.querySelector('.spinner');
  if (spinner) spinner.style.display = 'inline-block';

  try {
    const res  = await fetch(`http://127.0.0.1:${PORT}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ courriel, action })
    });
    const data = await res.json();
    if (data.ok) {
      rows = data.rows;
      updateStats();
      render();
    }
  } catch(e) {
    btn.disabled = false;
  } finally {
    if (spinner) spinner.style.display = 'none';
  }
}

function render() {
  const q  = document.getElementById('search').value.toLowerCase();
  const fs = document.getElementById('filtre-statut').value.toLowerCase();
  const keys = ['nom','entreprise','courriel','date_inv','s_envoi','ouvert','date_rap','statut'];

  let data = rows.filter(r => {
    const match  = !q  || r.nom.toLowerCase().includes(q)
                       || (r.entreprise||'').toLowerCase().includes(q)
                       || r.courriel.toLowerCase().includes(q);
    const fmatch = !fs || (r.statut||'').toLowerCase().includes(fs);
    return match && fmatch;
  });

  data.sort((a,b) => {
    const va = a[keys[sortCol]]||'', vb = b[keys[sortCol]]||'';
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  });

  const tbody = document.getElementById('tbody');
  const empty = document.getElementById('empty');
  if (!data.length) { tbody.innerHTML=''; empty.style.display='block'; return; }
  empty.style.display = 'none';

  tbody.innerHTML = data.map(r => `
    <tr>
      <td class="nom">${r.nom}${r.entreprise ? `<div class="entreprise-sous">${r.entreprise}</div>` : ''}</td>
      <td class="courriel">${r.courriel}</td>
      <td class="date">${r.date_inv||'—'}</td>
      <td class="date">${r.ouvert||'—'}</td>
      <td>${r.date_rap ? '<span class="check-yes">✓</span>' : '<span class="check-no">—</span>'}</td>
      <td class="date">${r.date_rap||'—'}</td>
      <td>${badgeStatut(r.statut)}</td>
      <td>
        <div class="actions">
          <button class="btn-action btn-ouvert"
            ${btnDisabled(r.statut,'ouvert') ? 'disabled' : ''}
            onclick="updateStatut('${r.courriel}','ouvert',this)">Ouvert</button>
          <button class="btn-action btn-rapport"
            ${btnDisabled(r.statut,'rapport') ? 'disabled' : ''}
            onclick="updateStatut('${r.courriel}','rapport',this)">Rapport envoyé</button>
          <button class="btn-action btn-converti"
            ${btnDisabled(r.statut,'converti') ? 'disabled' : ''}
            onclick="updateStatut('${r.courriel}','converti',this)">Converti</button>
          <div class="spinner"></div>
        </div>
      </td>
    </tr>`).join('');
}

function sortBy(col) {
  if (sortCol===col) sortAsc=!sortAsc; else { sortCol=col; sortAsc=true; }
  render();
}

updateStats();
render();
</script>
</body>
</html>"""

# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    app.run(port=PORT, debug=False)
