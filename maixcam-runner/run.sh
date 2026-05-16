#!/bin/sh

# MaixCamRunner - Wrapper pour exécuter des scripts Python dans les skills
# Usage: ./run.sh <dossier_skill> <script_python>

export LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/opt/lib:/opt/usr/lib:/soc/lib

# Récupérer les paramètres
SKILL_DIR="$1"
SCRIPT_NAME="$2"

# Vérifier que les paramètres sont fournis
if [ -z "$SKILL_DIR" ] || [ -z "$SCRIPT_NAME" ]; then
    echo "Usage: $0 <dossier_skill> <script_python>"
    exit 1
fi

# Construire le chemin complet
SCRIPT_PATH="${SKILL_DIR}/${SCRIPT_NAME}"

# Vérifier que le script existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Erreur: Le script '$SCRIPT_PATH' n'existe pas"
    exit 1
fi

# Exécuter le script Python
cd "${SKILL_DIR}"
exec /usr/local/bin/python3 "${SCRIPT_NAME}"