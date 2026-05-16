# Person Detect Skill
# Détection de personne avec sauvegarde automatique de la première détection

## Usage

```bash
cd /root/.picoclaw/workspace/skills/person-detect
/usr/local/bin/python3 person_detect.py
```

## Description

Ce skill lance une détection de personne en temps réel et sauvegarde
automatiquement la première détection positive. Le script s'arrête
dès qu'une personne est détectée.

Le script initialise automatiquement l'environnement MaixPy via `python_tools/maix_env.py` (équivalent à l'export de `LD_LIBRARY_PATH`).

## Configuration

- **Modèle :** YOLO11s (par défaut : /root/models/yolo11s.mud)
- **Durée :** 15 secondes (maximum)
- **Seuil de confiance :** 0.5
- **Seuil IoU :** 0.45

## Résultat

- Affiche toujours le nombre de personnes détectées (même 0)
- Sauvegarde l'image annotée seulement si détection positive
- Produit toujours un rapport texte (`person_count_*.txt`)
- Produit une image annotée seulement si détection positive

## Politique de renvoi

- Si détection: renvoyer le rapport ET l'image annotée.
- Si aucune détection: renvoyer uniquement le rapport.

Le script expose explicitement en sortie:
- `REPORT_FILE: <path>`
- `DETECTION_IMAGE_FILE: <path|NONE>`
- `SEND_POLICY: report_and_image|report_only`

## Commandes

- `--run` : Lancer la détection (par défaut)
- `--duration SECONDS` : Durée de surveillance (par défaut: 15)
- `--model PATH` : Chemin vers le modèle YOLO

## Exemple

```bash
person-detect --run
# ou
person-detect --duration 30 --model /root/models/yolo11s.mud
```
