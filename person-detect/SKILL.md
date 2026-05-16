# Person Detect Skill
# Détection de personne avec sauvegarde automatique de la première détection

## Usage

```bash
/root/.picoclaw/workspace/skills/maixcam-runner/run.sh /root/.picoclaw/workspace/skills/person-detect person_detect.py --run
```

## Description

Ce skill lance une détection de personne en temps réel et sauvegarde
automatiquement la première détection positive. Le script s'arrête
dès qu'une personne est détectée.

## Configuration

- **Modèle :** YOLO11s (par défaut : /root/models/yolo11s.mud)
- **Durée :** 15 secondes (maximum)
- **Seuil de confiance :** 0.5
- **Seuil IoU :** 0.45

## Résultat

- Affiche toujours le nombre de personnes détectées (même 0)
- Sauvegarde l'image annotée seulement si détection positive
- Envoie l'image si une détection est faite

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
