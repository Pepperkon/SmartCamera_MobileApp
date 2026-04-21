import subprocess
import os
import requests
from dotenv import load_dotenv
import requests

TEMP_PHOTO = "temp_capture.jpg"
load_dotenv()
MODEL_URL = os.environ.get("MODEL_URL")

if not MODEL_URL:
    raise RuntimeError("MODEL_URL not found, check README for instructions")

def take_photo():
    if os.path.exists(TEMP_PHOTO):
        os.remove(TEMP_PHOTO)

    print("📸 Przechwytywanie obrazu przez rpicam-still...")
    try:
        # -n: brak podglądu, -o: wyjście, -t 1: czekaj 1ms (szybkie zdjęcie)
        # --immediate: nie czekaj na stabilizację (jeśli zależy Ci na czasie)
        subprocess.run([
            "rpicam-still",
            "-o", TEMP_PHOTO,
            "-n",
            "-t", "500", # 500ms na ustawienie ostrości/światła
            "--width", "1280",
            "--height", "720"
        ], check=True)

        if os.path.exists(TEMP_PHOTO):
            print("✅ Zdjęcie zapisane pomyślnie!")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd rpicam-still: {e}")

    return False

def send_to_model():
    try:
        with open(TEMP_PHOTO, "rb") as f:
            files = {"file": (TEMP_PHOTO, f, "image/jpeg")}
            print(f"📡 Wysyłanie do modelu: {MODEL_URL}/recognize...")

            response = requests.post(f"{MODEL_URL}/recognize", files=files)

            if response.status_code == 200:
                print("🚀 Model odebrał zdjęcie i rozpoczął analizę.")
            else:
                print(f"⚠️ Serwer zwrócił błąd: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Nie udało się połączyć z modelem: {e}")

    os.remove(TEMP_PHOTO)

def execute():
    if take_photo():
        send_to_model()
    return True

if __name__ == "__main__":
    if take_photo():
        send_to_model()
