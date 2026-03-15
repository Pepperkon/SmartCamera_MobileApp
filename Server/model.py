import face_recognition
from fastapi import FastAPI, Depends
import os
import shutil
import numpy as np
import requests
import uvicorn
from datetime import datetime
from sqlmodel import Session, select
from database import engine, get_session, FaceTemplate # Importy z Twojej bazy
import sys

API_URL = "http://localhost:8000/alerts"
TOLERANCE = 0.50
FILEPATH = "/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg"
CAPTURE_DIR = "data/images/captured"
UNKNOWN = -1

app = FastAPI()

def identify(known_encodes, target_filepath=FILEPATH):
    if not os.path.exists(target_filepath):
        print(f"Błąd: Brak pliku {target_filepath}")
        return None

    image = face_recognition.load_image_file(target_filepath)
    unknown_encoding = face_recognition.face_encodings(image)

    if len(unknown_encoding) == 0:
        return None

    distances = face_recognition.face_distance(known_encodes, unknown_encoding[0])

    if len(distances) > 0:
        best_match_index = np.argmin(distances)
        if distances[best_match_index] < TOLERANCE:
            return best_match_index
    return UNKNOWN

@app.post("/recognize")
async def recognize_face(session: Session = Depends(get_session)):
    known_faces = session.exec(select(FaceTemplate)).all()
    known_encodes = [np.array(f.embedding) for f in known_faces]

    index = identify(known_encodes)

    if index is None:
        return {"status": "error", "message": "No faces detected."}

    user_id = None if index == UNKNOWN else known_faces[index].user_id

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    status_label = "unknown" if user_id is None else f"user_{user_id}"
    image_name = f"{status_label}_{date_str}.jpg"
    
    save_path = os.path.join(CAPTURE_DIR, image_name)

    try:
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        shutil.copy2(FILEPATH, save_path)
        print(f"✅ Zdjęcie zapisane: {save_path}")
    except Exception as e:
        print(f"❌ Błąd kopiowania: {e}")

    alert_data = {
        "name": "Known face" if user_id else "Unknown face",
        "time": date_str,
        "image": image_name,
        "isNew": True,
        "captured_user_id": user_id
    }

    try:
        requests.post(API_URL, json=alert_data)
    except Exception as e:
        print(f"❌ Błąd komunikacji z main.py: {e}")

    return {"status": "success", "user_id": user_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)