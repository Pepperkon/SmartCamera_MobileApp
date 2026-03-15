import face_recognition
from fastapi import FastAPI
import os
import shutil
import numpy as np
import cv2
import requests
from datetime import datetime
from database import engine
import sys

API_URL = "http://localhost:8000/alerts"
TOLERANCE = 0.50
FILEPATH = "/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg"
CAPTURE_DIR = "data/images/captured"
UNKNOWN = -1

@app.post("/recognize")
async def recognize_face(session: Session = Depends(get_session)):
    known_faces = session.exec(select(FaceTemplate)).all()
    known_encodes = [np.array(f.embedding) for f in known_faces]

    index = identify(known_encodes)

    if index is None:
        print("No faces detected.")
        sys.exit(0)

    user_id = None if index == UNKNOWN else known_faces[index].user_id

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    status = "unknown" if user_id is None else f"user_{user_id}"
    image_name = f"{status}_{date_label}.jpg"

    alert_data = {
        "title": "Known face" if user_id else "Unknown face",
        "time": time_label,
        "image": date,
        "isNew": True,
        "captured_user_id": user_id
    }

    requests.post(API_URL, json=alert_data)

async def get_encoding(upload_file: UploadFile):
    contents =  await upload_file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))
    return face_recognition.face_encodings(image)

def identify(known_encodes, target_filepath=FILEPATH):
    if not os.path.exists(target_filepath):
        return None

    image = face_recognition.load_image_file(target_filepath)
    unknown_encoding = face_recognition.face_encodings(image)

    if len(unknown_encoding) == 0:
        return None

    # TODO: Alert for each separate face detected
    distances = face_recognition.face_distance(known_encodes, unknown_encoding[0])

    if len(distances) > 0:
        best_match_index = np.argmin(distances)
        if distances[best_match_index] < TOLERANCE:
            return best_match_index
    return UNKNOWN


with Session(engine) as session:
    known_faces = session.exec(select(FaceTemplate)).all()
    known_encodes = [np.array(f.embedding) for f in known_faces]

    index = identify(known_encodes)

    if index is None:
        print("No faces detected.")
        sys.exit(0)

    user_id = None if index == UNKNOWN else known_faces[index].user_id

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    status = "unknown" if user_id is None else f"user_{user_id}"
    image_name = f"{status}_{date}.jpg"
    capture_path = os.path.join(CAPTURE_DIR, image_name)

    try:
        shutil.copy2(FILEPATH, capture_path)
    except Exception as e:
        print(f"Błąd kopiowania: {e}")

    alert_data = {
        "title": "Known face" if user_id else "Unknown face",
        "time": date,
        "image": image_name,
        "isNew": True,
        "captured_user_id": user_id
    }

    requests.post(API_URL, json=alert_data)
