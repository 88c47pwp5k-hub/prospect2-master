# Règles obligatoires — Prospect 2.0 (prospect2-master)

Ces règles s'appliquent à TOUTES les sessions de travail sur ce projet, sans exception.

---

## RÈGLE 0 — Preuve visuelle réelle, jamais une référence

Quand une tâche demande une preuve (capture d'écran, contenu de courriel, rendu de page), le fichier ou le contenu réel doit être physiquement présent dans le message de rapport final — jamais une phrase qui y fait référence sans le montrer.

Interdit :
- "Voir détails ci-dessus"
- "Capture déjà affichée plus haut"
- "Le fichier s'est ouvert dans Preview"
- Toute description de ce qu'une image montre, sans l'image elle-même jointe au message

Le rapport final d'une tâche avec preuve requise doit soit :
1. Attacher le fichier réel (image, PDF) directement dans ce message, ou
2. Coller le contenu texte exact (ex. le HTML complet d'un courriel reçu), ou
3. Publier une page de preuve accessible et donner le lien, avec le contenu réellement visible dessus (pas juste un lien vers "où ça devrait être")

Si aucune de ces trois options n'est techniquement possible dans le contexte de la tâche, dis-le explicitement ("je ne peux pas joindre de fichier ici parce que X") plutôt que de référer vaguement à une preuve donnée ailleurs. Ne jamais déclarer une tâche terminée tant que la preuve n'est pas physiquement là.

---

## RÈGLE DESTRUCTIVE-STOP — Arrêt obligatoire avant toute commande destructive

Dès qu'une commande de vérification (git status, git diff, ls, etc.) révèle des changements non commités, non sauvegardés, ou non poussés, TOUTE commande destructive qui écraserait ce travail (git reset --hard, git checkout --force, git clean -fd, rm -rf, écrasement de fichier, ou équivalent) doit être un point d'ARRÊT séparé — jamais enchaînée dans la même action ou le même bloc de commandes que la vérification qui l'a révélé.

Concrètement : si `git status --short` montre des fichiers modifiés non commités, ne jamais exécuter `git reset --hard` (ou toute commande destructive équivalente) dans la même commande ou le même tour — s'arrêter, signaler ce qui serait perdu, et attendre une confirmation explicite avant de procéder.

Cette règle s'applique à toute commande destructive, pas seulement git — chaque fois qu'une action irréversible menace du travail non sauvegardé qui vient d'être détecté, le réflexe est de s'arrêter et demander, jamais de continuer dans la foulée.

Si un fichier suivi (tracked) doit être écrasé/réinitialisé, propose d'abord de le sauvegarder ailleurs (copie, stash) avant l'action destructive, même si ça semble redondant.
