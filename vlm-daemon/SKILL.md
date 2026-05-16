# VLM-DAEMON — MaixCAM2 Skill (API + Contrôle)

## Description
Ce skill permet de démarrer, arrêter, interroger et piloter le démon VLM (Vision Language Model) sur MaixCAM2, en Python natif (aucune dépendance shell requise). Toutes les commandes sont accessibles via des scripts Python simples, robustes et documentés.

**Entrées principales (préférées pour Picoclaw et LLM) :**
- `python3 start_daemon.py` — démarre le démon
- `python3 stop_daemon.py` — arrête le démon
- `python3 status_daemon.py` — affiche l’état du démon et du modèle
- `python3 vlmctl.py ...` — contrôle complet (voir ci-dessous)

**Compatibilité :**
- Les scripts `.sh` (`start_daemon.sh`, etc.) sont toujours présents et appellent les versions Python.
- `ensure_maix_env()` est appelé automatiquement pour garantir l’environnement MaixPy.

---

## Commandes Python (recommandé)

```bash
cd /root/.picoclaw/workspace/skills/vlm-daemon

# Démarrer le démon
python3 start_daemon.py

# Arrêter le démon
python3 stop_daemon.py

# Statut du démon
python3 status_daemon.py

# Contrôle complet (modèle, capture, question, etc.)
python3 vlmctl.py status
python3 vlmctl.py health
python3 vlmctl.py models
python3 vlmctl.py load qwen3vl
python3 vlmctl.py unload
python3 vlmctl.py capture
python3 vlmctl.py capture /tmp/scene.jpg
python3 vlmctl.py describe
python3 vlmctl.py ask "Décris la scène"
python3 vlmctl.py ask-image /chemin/vers/image.jpg "Que vois-tu ?"
```

---

## Exemples d’utilisation

### Démarrer et vérifier le démon
```bash
python3 start_daemon.py
python3 status_daemon.py
```

### Charger un modèle et poser une question
```bash
python3 vlmctl.py load qwen3vl
python3 vlmctl.py describe
python3 vlmctl.py ask "Décris la scène en une phrase"
```


### Analyser une image ou capturer directement
```bash
# Capture seule (sans question VLM)
python3 vlmctl.py capture

# Capture seule avec chemin explicite
python3 vlmctl.py capture /root/.picoclaw/workspace/shot.jpg

# Demander une analyse avec capture automatique (par défaut)
python3 vlmctl.py ask "Décris la scène en une phrase"

# Raccourci fiable pour agents: capture + description en 1 phrase, retour texte seul
python3 vlmctl.py describe

# Demander une analyse sur une image existante
python3 vlmctl.py ask-image /chemin/vers/image.jpg "Que vois-tu ?"
```

La sortie inclut par défaut des marqueurs explicites :
- `IMAGE_FILE: <chemin>`
- `SEND_POLICY: report_and_image`
- `PICOCLAW_RESULT_JSON=...`

Important:
- `capture`: capture photo uniquement (pas de texte VLM)
- `ask` / `ask-image`: description + image (si image disponible)
- `describe`: description texte uniquement (pas de `IMAGE_FILE`, pas de `image_path` dans la sortie)

---

## Sorties attendues

- `status_daemon.py` :
  - `status=running|stopped|stale_pid`
  - `model_loaded=true|false`
  - `model_alias=qwen3vl|internvl|smolvlm|none`
  - `autoload_ok=true|false`
- `vlmctl.py ask ...` :
  - JSON : `{ "answer": "...", "image_path": "...", ... }`
- `vlmctl.py capture ...` :
  - JSON : `{ "image_path": "...", ... }`
- `vlmctl.py describe ...` :
  - JSON : `{ "answer": "...", ... }` (sans `image_path`)

---

## Modèles supportés
| alias      | description                        |
|------------|------------------------------------|
| qwen3vl    | Qwen3-VL 2B Int4 (par défaut)      |
| internvl   | InternVL2.5 1B                     |
| smolvlm    | SmolVLM 256M instruct              |

---

## Pour Picoclaw et LLM
- **Toujours privilégier les commandes Python** (`vlmctl.py`, `start_daemon.py`, etc.)
- Pour vérifier l’état ou charger un modèle, utiliser :
  - `python3 status_daemon.py`
  - `python3 vlmctl.py load qwen3vl`
- Pour poser une question :
  - `python3 vlmctl.py ask "Décris la scène"`
- Pour capturer une image seule (sans question) :
  - `python3 vlmctl.py capture`
- Pour une description simple et robuste (capture + texte seul) :
  - `python3 vlmctl.py describe`
- Pour arrêter proprement :
  - `python3 stop_daemon.py`

---

## Legacy (shell)
Les scripts `.sh` restent utilisables et appellent les versions Python :
- `./start_daemon.sh`, `./stop_daemon.sh`, `./status_daemon.sh`, `./vlmctl.sh`

---

## Conseils pour agents LLM
- Toujours vérifier l’état avant d’agir (`status_daemon.py`)
- Attendre 2-5s après un `start` avant de charger un modèle ou de poser une question
- Utiliser les alias de modèle : `qwen3vl`, `internvl`, `smolvlm`
- Les réponses sont toujours en JSON, faciles à parser

### Contrat tool-call Picoclaw (important)
- Le problème `error parsing tool call` vient généralement d'un format invalide (texte libre au lieu d'un JSON d'action), pas des accents.
- Pour une description simple, préférer une commande sans argument utilisateur :
  - `python3 /root/.picoclaw/workspace/skills/vlm-daemon/vlmctl.py describe`
- Le tool-call doit contenir uniquement l'objet d'action (pas de préambule `User: ...`, pas d'explication autour).
- Exemple valide :
```json
{
  "action": "run",
  "background": false,
  "command": "python3 /root/.picoclaw/workspace/skills/vlm-daemon/vlmctl.py describe",
  "cwd": "/root/.picoclaw/workspace/skills/vlm-daemon",
  "timeout": 30
}
```
- Éviter `vlm_daemon` (underscore) et utiliser `vlm-daemon` (tiret).

---

## Pour toute action, privilégier :
- `python3 vlmctl.py ...`
- ou les scripts `.sh` si vraiment nécessaire

---

**Ce skill est optimisé pour être piloté par Picoclaw, un agent LLM, ou tout humain en SSH.**
