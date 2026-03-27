from fastapi import FastAPI, Depends, UploadFile
import os
import io
import shutil
import numpy as np
import requests
import uvicorn
from datetime import datetime
from sqlmodel import Session, select
from database import engine, get_session, FaceTemplate, User
import sys

FaceEncoding = np.ndarray
FaceLocation = tuple[int, int, int, int]
API_URL = "http://localhost:8000"
TOLERANCE = 0.50
FILEPATH = "/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg"
CAPTURE_DIR = "data/images/captured"

app = FastAPI()


def identify(
    known_encodes: list[FaceEncoding],
    image: np.ndarray
) -> tuple[list[int | None], list[FaceLocation], list[FaceEncoding]]:
    import face_recognition

    locations = face_recognition.face_locations(image)
    unknown_encodings = face_recognition.face_encodings(image, locations)

    indexes = []
    for unknown_encoding in unknown_encodings:
        distances = face_recognition.face_distance(known_encodes, unknown_encoding)
        if len(distances) > 0:
            best_match_index = np.argmin(distances)
            if distances[best_match_index] < TOLERANCE:
                indexes.append(best_match_index)
            else:
                indexes.append(None)
        else:
            indexes.append(None)

    return indexes, locations, unknown_encodings

async def get_encoding(upload_file: UploadFile) -> list[FaceEncoding]:
    import face_recognition

    contents =  await upload_file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))
    return face_recognition.face_encodings(image)

def send_alert(alert_data: AlertRead) -> None:
    try:
        r = requests.post(f"{API_URL}/alerts", json=alert_data)
        if r.status_code == 422:
            print(f"Błąd walidacji (422): {r.json()}")
        r.raise_for_status()
    except Exception as e:
        print(f"Błąd wysyłania alertu: {e}")

@app.post("/recognize")
async def recognize_face(session: Session = Depends(get_session)) -> dict[str, str]:
    import face_recognition
    import requests
    from datetime import datetime
    from PIL import Image, ImageDraw

    if not os.path.exists(FILEPATH):
        return {"status": "error", "message": "File not found"}

    known_faces = session.exec(select(FaceTemplate)).all()
    known_encodes = [np.array(f.embedding) for f in known_faces]

    image = face_recognition.load_image_file(FILEPATH)

    indexes, locations, embeddings = identify(known_encodes, image)

    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d.%m.%Y")
    time_stamp = now.strftime("%d.%m.%Y_%H-%M-%S")

    if not indexes:
        print("No faces detected - sending empty alert.")
        status = "empty"
        image_name = f"{status}_{time_stamp}.jpg"
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        capture_path = os.path.join(CAPTURE_DIR, image_name)
        try:
            if os.path.exists(FILEPATH):
                shutil.copy2(FILEPATH, capture_path)
        except Exception as e:
            print(f"Błąd kopiowania: {e}")
        send_alert({
            "id": None,
            "title": "No face detected",
            "time": time_str,
            "date": date_str,
            "image": image_name,
            "isNew": True,
            "recognised_user_id": None,
            "embedding": []
        })
        return {"status": "processed", "result": "empty"}

    for i in range(len(indexes)):
        user_id = None
        if indexes[i] is not None:
            user_id = known_faces[indexes[i]].user_id
            user = session.get(User, user_id)
            title = f"Detected: {user.name}"
            status = f"user_{user_id}"
            print(f"Recognized user: {user.name}")
        else:
            title = "Unknown"
            status = "unknown"
            print("Unknown face detected.")

        image_name = f"{status}_{time_stamp}_{i}.jpg"
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        capture_path = os.path.join(CAPTURE_DIR, image_name)

        im = Image.fromarray(image)
        d = ImageDraw.Draw(im)
        top, right, bottom, left = locations[i]
        d.rectangle([left, top, right, bottom], outline="red", width=3)
        im.save(capture_path)

        send_alert({
            "id": None,
            "title": title,
            "time": time_str,
            "date": date_str,
            "image": image_name,
            "isNew": True,
            "recognised_user_id": user_id,
            "embedding": embeddings[i].tolist()
        })

    return {"status": "processed", "result": "TEMPORARY RESULT"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
