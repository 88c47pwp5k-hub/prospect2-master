"""
Utilitaires partagés — Solarium Pro
"""

# Couleurs considérées "en stock" — correspondance EXACTE, sans approximation
COULEURS_STOCK = ["Blanc RAL 9016", "Noir RAL 9005"]

def est_couleur_stock(couleur):
    """
    Retourne True si la couleur est une couleur standard en stock.
    Toute couleur non listée ici est traitée comme couleur spéciale (CAS 2).
    """
    return couleur.strip() in COULEURS_STOCK
