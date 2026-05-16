# Image Analyzer Skill

## Description
Analyse des images capturées par la caméra en utilisant un modèle de vision pour décrire le contenu, les couleurs et les objets visibles.

## Usage
```bash
# Analyser une image
python analyze_image.py --image "/root/.picoclaw/workspace/capture.jpg"
```

## Functions
- `analyze_image(path)` - Analyse une image et génère un rapport détaillé
- `get_image_summary(path)` - Retourne un résumé concis de l'image

## Configuration
- Modèle de vision utilisé pour l'analyse
- Options de description (couleurs, objets, contexte)
- Format du rapport de sortie

## Example
```python
from image_analyzer import analyze_image

# Analyser l'image capture
result = analyze_image("/root/.picoclaw/workspace/capture.jpg")
print(result)
```

## Notes
- Supporte les formats JPEG, PNG, GIF, WebP, BMP
- Analyse automatique du contenu visuel
- Génération de rapports structurés