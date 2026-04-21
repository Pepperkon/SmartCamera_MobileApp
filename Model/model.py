from fastapi import FastAPI, Depends, UploadFile, File
import os
import io
import shutil
import numpy as np
import requests
import uvicorn
from datetime import datetime
import sys
from PIL import Image, ImageDraw
import face_recognition
from dotenv import load_dotenv


TOLERANCE = 0.50

load_dotenv()
SERVER_URL = os.environ.get("SERVER_URL")

if not SERVER_URL:
    raise RuntimeError("SERVER_URL not found, check README for instructions")

app = FastAPI()

def identify(known_encodes, image):
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

# Checking faces of old alerts after adding a new user
@app.post("/rematch")
async def rematch_unknown_faces(data: dict):
    user_id = data["user_id"]
    embedding = np.array(data["embedding"])
    alerts = data["unrecognized_alerts"]

    if not alerts:
        return {"status": "No alerts to process"}

    alerts_encodings = [np.array(alert["embedding"]) for alert in alerts]

    distances = face_recognition.face_distance(alerts_encodings, embedding)
    indices = np.where(distances < TOLERANCE)[0]
    matched_ids = [alerts[index]["id"] for index in indices]

    return {"matched_ids": matched_ids}

# Endpoint for Server to get an image's encoding
@app.post("/encode")
async def encode_image(file: UploadFile):
    contents = await file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))
    encodings = face_recognition.face_encodings(image)
    return {"encodings": [e.tolist() for e in encodings]}

# Endpoint where Camera uploads the taken photo
@app.post("/recognize")
async def recognize_face(file: UploadFile):
    contents = await file.read()
    image = face_recognition.load_image_file(io.BytesIO(contents))

    try:
        response = requests.get(f"{SERVER_URL}/templates")
        known_faces = response.json()
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {e}"}

    known_encodes = [np.array(f["embedding"]) for f in known_faces]

    indexes, locations, unknown_encodings = identify(known_encodes, image)

    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d.%m.%Y")
    time_stamp = now.strftime("%d.%m.%Y_%H-%M-%S")

    if not indexes:
        await file.seek(0)
        image_name = f"empty_{time_stamp}.jpg"
        img_json = {"file": (image_name, await file.read(), "image/jpeg")}
        requests.post(f"{SERVER_URL}/upload-captured", files=img_json)
        requests.post(f"{SERVER_URL}/alerts", json={
            "title": "No face detected",
            "time": time_str,
            "date": date_str,
            "image": image_name,
            "isNew": True,
            "recognised_user_id": None,
            "embedding": None
        })
        return {"status": "processed", "result": "no_faces"}

    for i in range(len(indexes)):
        user_id = None
        if indexes[i] is not None:
            user_id = known_faces[indexes[i]]["user_id"]
            title = f"Detected User ID: {user_id}"
            status = f"user_{user_id}"
            print(f"Recognized user: {user_id}")
        else:
            title = "Unknown"
            status = "unknown"
            print("Unknown face detected.")

        image_name = f"{status}_{time_stamp}_{i}.jpg"

        im = Image.fromarray(image)
        d = ImageDraw.Draw(im)
        top, right, bottom, left = locations[i]
        d.rectangle([left, top, right, bottom], outline="red", width=3)

        img_bytes = io.BytesIO()
        im.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        files = {"file": (image_name, img_bytes, "image/jpeg")}
        requests.post(f"{SERVER_URL}/upload-captured", files=files)

        requests.post(f"{SERVER_URL}/alerts", json={
            "title": title,
            "time": time_str,
            "date": date_str,
            "image": image_name,
            "isNew": True,
            "recognised_user_id": user_id,
            "embedding": unknown_encodings[i].tolist()
        })

    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
