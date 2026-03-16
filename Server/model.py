from fastapi import FastAPI, Depends, UploadFile
import os
import io
import shutil
import numpy as np
import requests
import uvicorn
from datetime import datetime
from sqlmodel import Session, select
from database import engine, get_session, FaceTemplate # Importy z Twojej bazy
import sys

API_URL = "http://localhost:8000"
TOLERANCE = 0.50
FILEPATH = "/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg"
CAPTURE_DIR = "data/images/captured"
UNKNOWN = -1

app = FastAPI()

def identify(known_encodes, target_filepath=FILEPATH):
    import face_recognition
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

async def get_encoding(upload_file: UploadFile):
    import face_recognition

    contents =  await upload_file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))
    return face_recognition.face_encodings(image)

@app.post("/recognize")
async def recognize_face(session: Session = Depends(get_session)):
    import face_recognition
    import requests
    from datetime import datetime

    known_faces = session.exec(select(FaceTemplate)).all()
    known_encodes = [np.array(f.embedding) for f in known_faces]

    index = identify(known_encodes)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    user_id = None
    
    if index is None:   # no face detected
        title = "No face detected"
        status = "empty"
        print("No faces detected - sending empty alert.")
    elif index == UNKNOWN:  # unknown face detected
        title = "Unknown"
        status = "unknown"
        print("Unknown face detected.")
    else:   # known user detected
        user_id = known_faces[index].user_id
        res = requests.get(f"{API_URL}/users/{user_id}")
        user = res.json()
        user_name = user["name"]
        title = f"Detected: {user_name}"
        status = f"user_{user_id}"
        print(f"Recognized user: {user_name}")

    # 4. Kopiowanie zdjęcia (robimy to zawsze, żeby mieć dowód)
    image_name = f"{status}_{date_str}.jpg"
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    capture_path = os.path.join(CAPTURE_DIR, image_name)

    try:
        if os.path.exists(FILEPATH):
            shutil.copy2(FILEPATH, capture_path)
    except Exception as e:
        print(f"Błąd kopiowania: {e}")

    # 5. Przygotowanie i wysyłka alertu
    alert_data = {
	"id": None,
        "title": title,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "image": image_name,
        "isNew": True,
        "recognised_user_id": user_id  # Będzie to liczba lub None
    }

    try:
        r = requests.post(f"{API_URL}/alerts", json=alert_data)
        if r.status_code == 422:
            # TO CI POWIE DOKŁADNIE CO JEST ŹLE
            print(f"Błąd walidacji (422): {r.json()}") 
        r.raise_for_status()
    except Exception as e:
        print(f"Błąd wysyłania alertu: {e}")

    return {"status": "processed", "result": status}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
