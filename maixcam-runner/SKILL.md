# maixcam-runner - Runner pour exécuter des scripts Python dans les skills

## Description
Ce skill fournit un wrapper shell réutilisable pour exécuter des scripts Python dans les skills MaixCAM. Il configure correctement les chemins de bibliothèques LD_LIBRARY_PATH et gère les arguments pour le dossier du skill et le nom du script à exécuter.

## Fonctionnalités

- ✅ Configuration automatique de LD_LIBRARY_PATH
- ✅ Support des paramètres pour dossier skill et script Python
- ✅ Vérification de l'existence du script
- ✅ Exécution dans le bon dossier contextuel
- ✅ Réutilisable par tous les skills MaixCAM

## Utilisation

### Dans un autre skill (ex: photo-2k)

```bash
./run.sh /root/.picoclaw/workspace/skills/photo-2k capture.py
```

### Paramètres

- `SKILL_DIR` : Dossier du skill contenant le script Python
- `SCRIPT_NAME` : Nom du script Python à exécuter

## Code du wrapper

```bash
#!/bin/sh

export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/opt/lib:/opt/usr/lib:/soc/lib

SKILL_DIR="$1"
SCRIPT_NAME="$2"

if [ -z "$SKILL_DIR" ] || [ -z "$SCRIPT_NAME" ]; then
    echo "Usage: $0 <dossier_skill> <script_python>"
    exit 1
fi

SCRIPT_PATH="${SKILL_DIR}/${SCRIPT_NAME}"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Erreur: Le script '$SCRIPT_PATH' n'existe pas"
    exit 1
fi

cd "${SKILL_DIR}"
exec /usr/local/bin/python3 "${SCRIPT_NAME}"
```

## Avantages

- **Réutilisation** : Un seul runner pour tous les skills
- **Maintenabilité** : Configuration unique de LD_LIBRARY_PATH
- **Flexibilité** : Supporte n'importe quel script Python dans n'importe quel skill
- **Robustesse** : Vérification des paramètres et existence du script

## Exemples d'utilisation

### photo-2k
```bash
./run.sh /root/.picoclaw/workspace/skills/photo-2k capture.py
```

### person-detect
```bash
./run.sh /root/.picoclaw/workspace/skills/person-detect detect.py
```

### weather
```bash
./run.sh /root/.picoclaw/workspace/skills/weather get_weather.py
```