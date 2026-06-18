#!/bin/bash
# ============================================================
#  TEST SANTÉ SYSTÈME — Solarium Pro
#  Exécuté à 6h50 par launchd
#  Si tout OK → silencieux
#  Si un seul échoue → courriel d'alerte
# ============================================================

# Lecture config.json
CONFIG=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['serveurs']['dashboard_port'])")
DASHBOARD_PORT=$CONFIG

CONFIG_BASE=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['chemins']['base'])")

CONFIG_DASH=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['chemins']['dashboard'])")

CONFIG_EMAIL_FROM=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['envoi_gmail'])")
CONFIG_EMAIL_TO=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['reception'])")
CONFIG_IMAP_HOST=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['imap_host'])")
CONFIG_IMAP_PORT=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['imap_port'])")
CONFIG_IMAP_PASS=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['imap_password'])")
CONFIG_GMAIL_PASS=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['gmail_app_password'])")
CONFIG_ANTHROPIC=$(python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/prospect2-master/config.json'))); print(c['emails']['anthropic_key'])")

ERREURS=()
LOG="/tmp/sante_solarium_$(date +%Y%m%d).log"
EMAIL_FROM="$CONFIG_EMAIL_FROM"
EMAIL_TO="$CONFIG_EMAIL_TO"
SOLARIUMDASH="$CONFIG_BASE/$CONFIG_DASH"
BACKUP_DIR="$CONFIG_BASE/Documents/backup-production"
RESUME_DIR="$CONFIG_BASE/Documents/resume-matin"

echo "=== Santé système Solarium Pro — $(date '+%Y-%m-%d %H:%M:%S') ===" > "$LOG"

fail() { ERREURS+=("$1"); echo "  ❌ $1" >> "$LOG"; }
ok()   { echo "  ✅ $1" >> "$LOG"; }

# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
echo "── DASHBOARD ──────────────────────────────────────────" >> "$LOG"

# Port $DASHBOARD_PORT
if curl -sf http://localhost:$DASHBOARD_PORT/ -o /dev/null --max-time 5; then
    ok "Serveur port $DASHBOARD_PORT répond"
else
    fail "Serveur port $DASHBOARD_PORT ne répond pas"
fi

# leads_dashboard.json lisible et non vide
LEADS_JSON="$SOLARIUMDASH/leads_dashboard.json"
if [[ -r "$LEADS_JSON" ]]; then
    COUNT=$(python3 -c "import json; d=json.load(open('$LEADS_JSON')); print(len(d))" 2>/dev/null)
    if [[ "$COUNT" -gt 0 ]]; then
        ok "leads_dashboard.json OK ($COUNT entrées)"
    else
        fail "leads_dashboard.json vide ou non parsable"
    fi
else
    fail "leads_dashboard.json inaccessible"
fi

# POST /update-statut
LEAD_ID=$(python3 -c "import json; d=json.load(open('$LEADS_JSON')); print(d[0]['id'])" 2>/dev/null)
LEAD_STATUT_ORIG=$(python3 -c "import json; d=json.load(open('$LEADS_JSON')); print(d[0].get('statut','Nouveau'))" 2>/dev/null)
if [[ -n "$LEAD_ID" ]]; then
    RES=$(curl -sf -X POST http://localhost:$DASHBOARD_PORT/update-statut \
        -H "Content-Type: application/json" \
        -d "{\"id\":$LEAD_ID,\"statut\":\"__test__\"}" --max-time 5 2>/dev/null)
    # Remettre le statut original
    curl -sf -X POST http://localhost:$DASHBOARD_PORT/update-statut \
        -H "Content-Type: application/json" \
        -d "{\"id\":$LEAD_ID,\"statut\":\"$LEAD_STATUT_ORIG\"}" --max-time 5 > /dev/null 2>&1
    if echo "$RES" | grep -q '"ok":true'; then
        ok "POST /update-statut sauvegarde OK"
    else
        fail "POST /update-statut ne sauvegarde pas ($RES)"
    fi
else
    fail "POST /update-statut — impossible de lire l'ID du lead"
fi

# POST /update-soumission-statut
SOUM_JSON="$SOLARIUMDASH/soumissions.json"
SOUM_ID=$(python3 -c "import json; d=json.load(open('$SOUM_JSON')); print(d[0]['msg_id'])" 2>/dev/null)
SOUM_STATUT_ORIG=$(python3 -c "import json; d=json.load(open('$SOUM_JSON')); print(d[0].get('statut','À faire'))" 2>/dev/null)
if [[ -n "$SOUM_ID" ]]; then
    RES=$(curl -sf -X POST http://localhost:$DASHBOARD_PORT/update-soumission-statut \
        -H "Content-Type: application/json" \
        -d "{\"msg_id\":\"$SOUM_ID\",\"statut\":\"__test__\"}" --max-time 5 2>/dev/null)
    curl -sf -X POST http://localhost:$DASHBOARD_PORT/update-soumission-statut \
        -H "Content-Type: application/json" \
        -d "{\"msg_id\":\"$SOUM_ID\",\"statut\":\"$SOUM_STATUT_ORIG\"}" --max-time 5 > /dev/null 2>&1
    if echo "$RES" | grep -q '"ok":true'; then
        ok "POST /update-soumission-statut sauvegarde OK"
    else
        fail "POST /update-soumission-statut ne sauvegarde pas ($RES)"
    fi
else
    fail "POST /update-soumission-statut — soumissions.json vide ou inaccessible"
fi

# generer_dashboard.py tourne sans erreur
if python3 "$SOLARIUMDASH/generer_dashboard.py" >> "$LOG" 2>&1; then
    ok "generer_dashboard.py OK"
else
    fail "generer_dashboard.py a échoué (voir log)"
fi

# ─────────────────────────────────────────────────────────────
# PRODUCTION
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
echo "── PRODUCTION ─────────────────────────────────────────" >> "$LOG"

# Port 5757
if curl -sf http://localhost:5757/ -o /dev/null --max-time 5; then
    ok "solarium_production.py port 5757 répond"
else
    fail "solarium_production.py port 5757 ne répond pas"
fi

# Modules production
python3 - >> "$LOG" 2>&1 <<PYCHECK
import sys, os
sys.path.insert(0, "$BACKUP_DIR")
modules = ['cadre_module','neoscenica_module','esthetika_module','aika_6mm_module','cover_10mm_module']
for mod in modules:
    try:
        __import__(mod)
        print(f"  ✅ {mod} importe OK")
    except Exception as e:
        print(f"  ❌ {mod} ERREUR: {e}")
        sys.exit(1)
sys.exit(0)
PYCHECK
if [[ $? -eq 0 ]]; then
    ok "Tous les modules production importent OK"
else
    fail "Un ou plusieurs modules production échouent à l'import"
fi

# Logo PDF
LOGO="$BACKUP_DIR/Logo_Pro_Horizontal.pdf"
if [[ -f "$LOGO" ]]; then
    ok "Logo_Pro_Horizontal.pdf existe"
else
    fail "Logo_Pro_Horizontal.pdf introuvable dans backup-production"
fi

# ─────────────────────────────────────────────────────────────
# RÉSUMÉ MATIN
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
echo "── RÉSUMÉ MATIN ───────────────────────────────────────" >> "$LOG"

# Token OAuth valide
python3 - >> "$LOG" 2>&1 <<PYCHECK
import pickle, os, sys
from datetime import datetime, timezone
f = "$RESUME_DIR/token.pickle"
try:
    with open(f,'rb') as fh: creds = pickle.load(fh)
    if not creds.valid and not (creds.expired and creds.refresh_token):
        print("  ❌ token.pickle invalide et non renouvelable")
        sys.exit(1)
    print(f"  ✅ token.pickle valide (expiry: {creds.expiry})")
    sys.exit(0)
except Exception as e:
    print(f"  ❌ token.pickle erreur: {e}")
    sys.exit(1)
PYCHECK
[[ $? -eq 0 ]] && ok "token.pickle OAuth OK" || fail "token.pickle OAuth invalide"

# Connexion IMAP
python3 - >> "$LOG" 2>&1 <<PYCHECK
import imaplib, sys
try:
    m = imaplib.IMAP4_SSL("$CONFIG_IMAP_HOST", $CONFIG_IMAP_PORT)
    m.login("$CONFIG_EMAIL_TO", "$CONFIG_IMAP_PASS")
    m.logout()
    print("  ✅ IMAP $CONFIG_IMAP_HOST OK")
    sys.exit(0)
except Exception as e:
    print(f"  ❌ IMAP erreur: {e}")
    sys.exit(1)
PYCHECK
[[ $? -eq 0 ]] && ok "Connexion IMAP OK" || fail "Connexion IMAP mail.mailconfig.net échouée"

# API Claude répond en moins de 30s
python3 - >> "$LOG" 2>&1 <<PYCHECK
import requests, time, sys
KEY = "$CONFIG_ANTHROPIC"
t = time.time()
try:
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key":KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
        json={"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"ok"}]},
        timeout=30)
    dur = time.time()-t
    if r.status_code == 200:
        print(f"  ✅ API Claude répond en {dur:.1f}s")
        sys.exit(0)
    else:
        print(f"  ❌ API Claude HTTP {r.status_code}")
        sys.exit(1)
except requests.exceptions.Timeout:
    print("  ❌ API Claude timeout (>30s)")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ API Claude erreur: {e}")
    sys.exit(1)
PYCHECK
[[ $? -eq 0 ]] && ok "API Claude OK (<30s)" || fail "API Claude ne répond pas en moins de 30s"

# ─────────────────────────────────────────────────────────────
# LAUNCHD — IMPORT LEADS V4
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
echo "── LAUNCHD ────────────────────────────────────────────" >> "$LOG"

# Vérifie que importleadsv4 est chargé
if launchctl list | grep -q "com.benoitdupuis.importleadsv4"; then
    ok "com.benoitdupuis.importleadsv4 chargé dans launchd"
else
    fail "com.benoitdupuis.importleadsv4 absent de launchd"
fi

# Vérifie qu'il a tourné dans les 15 dernières minutes
IMPORT_LOG="$SOLARIUMDASH/import_leads_v4.log"
if [[ -f "$IMPORT_LOG" ]]; then
    DERNIERE_LIGNE=$(grep "^Import leads —" "$IMPORT_LOG" | tail -1)
    DERNIERE_DATE=$(echo "$DERNIERE_LIGNE" | sed 's/Import leads — //')
    if [[ -n "$DERNIERE_DATE" ]]; then
        TS_DERNIERE=$(date -j -f "%Y-%m-%d %H:%M" "$DERNIERE_DATE" "+%s" 2>/dev/null)
        TS_NOW=$(date +%s)
        AGE_MIN=$(( (TS_NOW - TS_DERNIERE) / 60 ))
        if [[ $AGE_MIN -le 15 ]]; then
            ok "import_leads_v4 a tourné il y a ${AGE_MIN} min ($DERNIERE_DATE)"
        else
            fail "import_leads_v4 n'a pas tourné depuis ${AGE_MIN} min (dernière: $DERNIERE_DATE)"
        fi
    else
        fail "import_leads_v4 — aucune entrée trouvée dans le log"
    fi
else
    fail "import_leads_v4 — log introuvable ($IMPORT_LOG)"
fi

# ─────────────────────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
echo "── BACKUP ─────────────────────────────────────────────" >> "$LOG"

SEUIL_JOURS=30
VIEUX=()
for f in "$BACKUP_DIR"/*.py "$BACKUP_DIR"/*.pdf "$BACKUP_DIR"/*.png; do
    [[ -f "$f" ]] || continue
    AGE=$(( ( $(date +%s) - $(stat -f %m "$f") ) / 86400 ))
    if [[ $AGE -gt $SEUIL_JOURS ]]; then
        VIEUX+=("$(basename $f) (${AGE}j)")
    fi
done

if [[ ${#VIEUX[@]} -eq 0 ]]; then
    ok "Tous les fichiers backup < $SEUIL_JOURS jours"
else
    fail "Fichiers backup trop vieux (>$SEUIL_JOURS j) : ${VIEUX[*]}"
fi

# ─────────────────────────────────────────────────────────────
# RAPPORT FINAL
# ─────────────────────────────────────────────────────────────
echo "" >> "$LOG"
if [[ ${#ERREURS[@]} -eq 0 ]]; then
    echo "✅ TOUT OK — $(date '+%H:%M')" >> "$LOG"
    exit 0
fi

# Au moins une erreur — envoyer courriel
echo "❌ ${#ERREURS[@]} ERREUR(S) DÉTECTÉE(S)" >> "$LOG"
for e in "${ERREURS[@]}"; do echo "   • $e" >> "$LOG"; done

BODY_TEXT=""
for e in "${ERREURS[@]}"; do BODY_TEXT+="• $e\n"; done

python3 - "$BODY_TEXT" <<PYMAIL
import smtplib, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

erreurs_txt = sys.argv[1]
now = datetime.now().strftime("%Y-%m-%d %H:%M")

html = f"""<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto'>
<div style='background:#7f1d1d;padding:20px;text-align:center'>
  <h1 style='color:white;margin:0'>⚠️ ALERTE SYSTÈME</h1>
  <p style='color:#fca5a5;margin:6px 0 0'>Solarium Pro — {now}</p>
</div>
<div style='padding:24px;background:#fff'>
  <p style='color:#1F3864;font-weight:bold;font-size:15px'>Les vérifications suivantes ont échoué :</p>
  <div style='background:#fef2f2;border-left:4px solid #ef4444;padding:16px;margin:16px 0;border-radius:4px'>
    <pre style='margin:0;font-size:13px;color:#7f1d1d;white-space:pre-wrap'>{erreurs_txt}</pre>
  </div>
  <p style='color:#666;font-size:12px'>Log complet : /tmp/sante_solarium_{datetime.now().strftime('%Y%m%d')}.log</p>
</div>
<div style='background:#1F3864;padding:12px;text-align:center'>
  <p style='color:#C68B00;margin:0;font-size:12px'>Solarium Pro — Système de surveillance automatique</p>
</div>
</div>"""

msg = MIMEMultipart("alternative")
msg["Subject"] = f"⚠️ Alerte système Solarium Pro — {now}"
msg["From"]    = "$CONFIG_EMAIL_FROM"
msg["To"]      = "$CONFIG_EMAIL_TO"
msg.attach(MIMEText(html, "html"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login("$CONFIG_EMAIL_FROM", "$CONFIG_GMAIL_PASS")
    s.sendmail("$CONFIG_EMAIL_FROM", "$CONFIG_EMAIL_TO", msg.as_string())
print("Courriel d'alerte envoyé.")
PYMAIL

exit 1
