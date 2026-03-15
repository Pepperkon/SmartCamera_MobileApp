import subprocess
import os
import time
import requests

def take_photo_system():
    PHOTO_PATH = "/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg"

    # Usuwamy stary plik, żeby mieć pewność, że powstał nowy
    if os.path.exists(PHOTO_PATH):
        os.remove(PHOTO_PATH)

    print("📸 Przechwytywanie obrazu przez rpicam-still...")
    try:
        # -n: brak podglądu, -o: wyjście, -t 1: czekaj 1ms (szybkie zdjęcie)
        # --immediate: nie czekaj na stabilizację (jeśli zależy Ci na czasie)
        subprocess.run([
            "rpicam-still",
            "-o", PHOTO_PATH,
            "-n",
            "-t", "500", # 500ms na ustawienie ostrości/światła
            "--width", "1280",
            "--height", "720"
        ], check=True)

        if os.path.exists(PHOTO_PATH):
            print("✅ Zdjęcie zapisane pomyślnie!")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd rpicam-still: {e}")

    return False

if take_photo_system():
    requests.post("http://localhost:8001/recognize")
