#!/usr/bin/env python3
"""Skill photo-2k : Prise de photo en 2K avec MaixPy

✅ Fonctionne dans l'environnement MaixCAM2 !
"""

import sys
import os
import time

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SKILL_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from python_tools.maix_env import ensure_maix_env

ensure_maix_env()

from maix import camera, image, nn

def capture_photo(path_output="/root/.picoclaw/workspace/capture_photo_2k.jpg"):
    """Capture une photo 2K avec la caméra Maix"""
    
    try:
        # Initialiser la caméra
        cam = camera.Camera()
        
        # Définir la résolution 2K
        cam.set_resolution(width=2160, height=1440)
        
        # Skipper 30 images pour stabilisation
        cam.skip_frames(30)
        
        # Récupérer une image
        img = cam.read()
        
        # Sauvegarder l'image avec qualité 95%
        img.save(path=path_output, quality=95)
        
        print(f"✅ Photo 2K capturée avec succès !")
        print(f"📁 Fichier : {path_output}")
        print(f"📏 Résolution : 2160x1440")
        print(f"🎨 Qualité : 95%")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la capture : {e}")
        print("⚠️  Vérifiez que la caméra Maix est connectée et les drivers installés")
        return False

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/root/.picoclaw/workspace/capture_photo_2k.jpg"
    capture_photo(path)