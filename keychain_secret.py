"""Lecture de secrets dans le trousseau macOS — ré-exporte le module partagé.

Utilisation :
    from keychain_secret import keychain_secret
    APP_PASSWORD = keychain_secret("gmail-app-password-prospect2") or APP_PASSWORD
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Library/SolariumDashboard"))
from secrets_mac import get_secret as keychain_secret  # noqa: E402,F401
