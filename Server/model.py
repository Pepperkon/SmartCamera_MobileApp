import face_recognition
from fastapi import FastAPI
import os
import shutil
import numpy as np
import cv2
import requests
from datetime import datetime

API_URL = "http://localhost:8000/alerts"

DIRECTORY = "data/images/users"
TOLERANCE = 0.50
FILEPATH = "test_photo.jpg"

app = FastAPI()

@app.post("/recognize")
async def recognize_face():
    result = identify_face("test_photo.jpg", known_encodes, known_names)

    print(result)

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    image_name = f"{result}-{date}.jpg"

    alert_data = {
        "title": result,
        "time": date,
        "image": image_name
    }

    requests.post(API_URL, json=alert_data)


def get_known_encodings(base_dir):
    known_encodes = []
    known_names = []

    if not os.path.exists(base_dir):
        print(f"Folder {base_dir} nie istnieje!")
        return known_encodes, known_names

    # Przechodzimy przez foldery użytkowników (1, 2, 3...)
    for user_id in os.listdir(base_dir):
        user_folder = os.path.join(base_dir, user_id)
        
        if os.path.isdir(user_folder):
            # Przechodzimy przez zdjęcia wewnątrz folderu użytkownika
            for filename in os.listdir(user_folder):
                if filename.endswith((".jpg", ".png", ".jpeg")):
                    img_path = os.path.join(user_folder, filename)
                    image = face_recognition.load_image_file(img_path)
                    encodings = face_recognition.face_encodings(image)

                    if len(encodings) > 0:
                        known_encodes.append(encodings[0])
                        # Jako nazwę bierzemy ID folderu (user_id)
                        known_names.append(user_id)
                        print(f"Załadowano wzorzec dla User ID: {user_id} ({filename})")
    
    return known_encodes, known_names

def identify_face(input_image_path, known_encodes, known_names):
    unknown_image = face_recognition.load_image_file(input_image_path)

    unknown_encodings = face_recognition.face_encodings(unknown_image)

    if len(unknown_encodings) == 0:
        return "no_face_detected"

    face_to_check = unknown_encodings[0]
    distances = face_recognition.face_distance(known_encodes, face_to_check)

    if len(distances) > 0:
        best_match_index = np.argmin(distances)
        if distances[best_match_index] < TOLERANCE:
            return known_names[best_match_index]

    return "unknown"

known_encodes, known_names = get_known_encodings(DIRECTORY)

result = identify_face("test_photo.jpg", known_encodes, known_names)

print(result)

date = datetime.now()
date_label = date.strftime("%Y-%m-%d_%H-%M")
time_label = date.strftime("%H:%M")
image_name = f"{result}-{date_label}.jpg"

alert_data = {
    "name": result,
    "time": time_label,
    "image": image_name
}

capture_path = os.path.join("data/images/captured/", image_name)
try:
    shutil.copy2("/home/raspi/SmartCamera_MobileApp/Server/test_photo.jpg", capture_path)
except FileNotFoundError:
    print(f"ERROR: File not found")

res = requests.post(API_URL, json=alert_data)

print(res)

# Camera script needs to wait for movement, take photo and save it, call face recognition from this file by API
# This file recognizes it and posts the result to main.py
