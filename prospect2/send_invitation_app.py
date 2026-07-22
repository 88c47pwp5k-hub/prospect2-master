#!/usr/bin/env python3
import os, smtplib, csv, webbrowser, threading
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request

EXPEDITEUR   = "bdprospect2.0@gmail.com"
APP_PASSWORD = "flulubownzmovziq"
SUJET        = "Votre diagnostic confidentiel — Prospect 2.0"
HTML_PATH    = os.path.expanduser("~/Documents/prospect2/invitation_courriel.html")
CSV_PATH     = os.path.expanduser("~/Documents/prospect2/prospects.csv")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html_body = f.read()

app = Flask(__name__)

PAGE = """
<html><body style="font-family:sans-serif;max-width:400px;margin:60px auto;">
<h2>Prospect 2.0 — Envoyer une invitation</h2>
<form method="POST" action="/envoyer">
  <label>Nom du prospect</label><br>
  <input name="nom" style="width:100%;padding:8px;margin:8px 0;" required><br>
  <label>Adresse courriel</label><br>
  <input name="courriel" type="email" style="width:100%;padding:8px;margin:8px 0;" required><br>
  <button style="padding:10px 20px;margin-top:10px;">Envoyer l'invitation</button>
</form>
<p>{msg}</p>
</body></html>
"""

@app.route("/", methods=["GET"])
def home():
    return PAGE.format(msg="")

@app.route("/envoyer", methods=["POST"])
def envoyer():
    nom = request.form["nom"].strip()
    destinataire = request.form["courriel"].strip()
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Benoit Dupuis — Prospect 2.0 <{EXPEDITEUR}>"
    msg["To"] = destinataire
    msg["Subject"] = SUJET
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
            serveur.login(EXPEDITEUR, APP_PASSWORD)
            serveur.sendmail(EXPEDITEUR, destinataire, msg.as_bytes())
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([nom, destinataire, datetime.now().strftime("%Y-%m-%d %H:%M"), "envoyé"])
        return PAGE.format(msg=f"<b style='color:#1B6CA8'>✓ Invitation envoyée à {destinataire}</b>")
    except Exception as e:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([nom, destinataire, datetime.now().strftime("%Y-%m-%d %H:%M"), f"erreur: {e}"])
        return PAGE.format(msg=f"<b style='color:#cc0000'>Erreur : {e}</b>")

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5959")).start()
    app.run(port=5959, debug=False)
