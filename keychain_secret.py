"""Lecture de secrets dans le trousseau macOS, avec repli vers l'ancienne source.

Utilisation :
    from keychain_secret import keychain_secret
    APP_PASSWORD = keychain_secret("gmail-app-password") or APP_PASSWORD

Repli temporaire pendant la transition : si l'entrée du trousseau n'existe pas
encore, keychain_secret() retourne None et l'appelant garde l'ancienne valeur
(déjà chargée via .env / variable d'environnement).
"""
import subprocess


def keychain_secret(service, account=None):
    cmd = ["security", "find-generic-password", "-w", "-s", service]
    if account:
        cmd += ["-a", account]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=True)
        val = out.stdout.strip()
        return val or None
    except Exception:
        return None
