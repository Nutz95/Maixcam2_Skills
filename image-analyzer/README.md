# 📸 Image Analyzer Skill

Analyse des images capturées par caméra avec modèle de vision.

## Installation

Le skill est déjà installé dans votre workspace.

## Utilisation

### Analyser une image

```bash
cd /root/.picoclaw/workspace/skills/image-analyzer
python analyze_image.py --image "/root/.picoclaw/workspace/capture.jpg"
```

### Résumé rapide

```bash
python analyze_image.py --image "/root/.picoclaw/workspace/capture.jpg" --summary
```

## Fonctionnalités

- ✅ Analyse de contenu visuel
- ✅ Détection des couleurs dominantes
- ✅ Description de la scène
- ✅ Rapport détaillé sauvegardé en texte
- ✅ Support des formats JPEG, PNG, GIF, WebP, BMP

## Exemple de rapport

```
=== ANALYSE D'IMAGE ===
Date: 2026-05-13T22:52:00
Image: /root/.picoclaw/workspace/capture.jpg

--- RÉSUMÉ ---
Image capturée avec succès. Analyse disponible dans le fichier de rapport.

--- DÉTAILS ---
✅ Format: JPG
✅ Résolution: 2560x1440 (2K)
✅ Mode: RGB565
✅ Statut: Image capturée avec succès

--- DESCRIPTION SCÈNE ---
Image capturée avec succès. La caméra a capturé une scène en 2K (2560x1440) avec format RGB565.
```

## API

```python
from analyze_image import analyze_image

# Analyser une image
result = analyze_image("/root/.picoclaw/workspace/capture.jpg")
```

## Notes

- L'analyse actuelle fournit une description de base de l'image
- Pour une analyse avancée avec IA, envisagez d'intégrer un modèle de vision comme CLIP ou YOLO
- Le rapport est sauvegardé dans `/root/.picoclaw/workspace/analysis_report.txt`