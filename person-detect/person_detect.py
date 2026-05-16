#!/usr/bin/env python3
# Person Detect Skill - Détection de personne en temps réel
# Sauvegarde la première détection positive et s'arrête automatiquement

import sys
import os
import time
from maix import camera, image, nn

# --- Configuration ---
MODEL_PATH = "/root/models/yolo11s.mud"
CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.45
RUN_DURATION = 15
OUTPUT_DIR = "/root/.picoclaw/workspace/detection_output"

# Vérification des dépendances
if not os.path.exists(MODEL_PATH):
    print(f"ERREUR: Le modèle YOLO11s n'a pas été trouvé à {MODEL_PATH}. Veuillez vérifier le chemin.")
    sys.exit(1)

try:
    detector = nn.YOLO11(model=MODEL_PATH, dual_buff=True)
except Exception as e:
    print(f"Erreur lors de l'initialisation du détecteur : {e}")
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Démarrage de la détection pendant {RUN_DURATION} secondes...")
start_time = time.time()
frame_count = 0
person_detection_count = 0
last_detection_path = None

try:
    cam = camera.Camera(detector.input_width(), detector.input_height(), detector.input_format())
    print("Détecteur et caméra initialisés avec succès.")

    while time.time() - start_time < RUN_DURATION:
        frame_count += 1
        img = cam.read()
        objs = detector.detect(img, conf_th=CONFIDENCE_THRESHOLD, iou_th=IOU_THRESHOLD)

        detection_status = "Aucune personne détectée."

        if objs:
            for obj in objs:
                img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_RED)
                msg = f'{detector.labels[obj.class_id]}: {obj.score:.2f}'
                img.draw_string(obj.x, obj.y, msg, color=image.COLOR_RED)
                
                if detector.labels[obj.class_id] == "person":
                    person_detection_count += 1
                    detection_status = f"PERSONNE détectée! ({detector.labels[obj.class_id]}) | Confiance: {obj.score:.2f} | Coords: ({obj.x}, {obj.y}, {obj.w}, {obj.h})"
                    
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    save_path = os.path.join(OUTPUT_DIR, f"frame_{timestamp}_{frame_count}.jpg")
                    img.save(save_path)
                    last_detection_path = save_path
                    
                    print(f"\n[STATUS] {detection_status}")
                    print(f"[ACTION] Première détection sauvegardée : {save_path}")
                    
                    # Arrêter le script dès la première détection
                    print(f"[ARRÊT] Fin de la surveillance après détection.")
                    break  # Sortir de la boucle for

        else:
            detection_status = "Aucune personne détectée."
            print(f"\n[STATUS] {detection_status}")

        if last_detection_path:
            break  # Arrêter si une détection a été faite

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nProcessus arrêté par l'utilisateur.")
except Exception as e:
    print(f"\nUne erreur inattendue s'est produite : {e}")

finally:
    print("\nFin du processus. Nettoyage des ressources.")
    if 'detector' in locals():
        del detector
    if 'cam' in locals():
        del cam
    
    # Sauvegarder le comptage de personnes dans un fichier
    count_file = os.path.join(OUTPUT_DIR, f"person_count_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(count_file, 'w') as f:
        f.write(f"Nombre de personnes détectées : {person_detection_count}\n")
        f.write(f"Date/Heure : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Dossier image : {OUTPUT_DIR}\n")
        if person_detection_count > 0:
            f.write(f"✓ Personne détectée ! Image sauvegardée : {last_detection_path}\n")
        else:
            f.write("✗ Aucune personne détectée.\n")
    
    print(f"Comptage sauvegardé dans : {count_file}")
    print("Script terminé.")
    
    # Afficher le résumé final avec le compteur de personnes
    print(f"*** RÉSUMÉ FINAL : {person_detection_count} personne(s) détectée(s). ***")
    
    if last_detection_path:
        print(f"[ENVOI] L'image sauvegardée à : {last_detection_path}")
    else:
        print(f"[ENVOI] Aucun fichier image détecté. Veuillez lire le fichier de rapport : {count_file}")
