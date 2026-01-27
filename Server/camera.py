import cv2
import subprocess
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PHOTO_NAME = "test_photo.jpg"
PHOTO_PATH = str(BASE_DIR / PHOTO_NAME)
NEXT_SCRIPT = str(BASE_DIR / "model.py")

def take_photo():
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("❌ Błąd: Nie można otworzyć kamery!")
        return False

    time.sleep(2)

    ret, frame = cam.read()

    if ret:
        cv2.imwrite(PHOTO_PATH, frame)
        print(f"✅ Zdjęcie zapisane jako: {PHOTO_PATH}")
    else:
        print("❌ Błąd: Nie udało się przechwycić obrazu.")
    
    cam.release()
    return ret

def run_next_script():
    try:
        subprocess.run(["python", NEXT_SCRIPT], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd podczas uruchamiania skryptu: {e}")
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    if take_photo():
        run_next_script()
