import os
import shutil
import time
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

app = FastAPI()
IP = "192.168.1.48"

if not os.path.exists("images"):
    os.makedirs("images")

app.mount("/images", StaticFiles(directory="images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Alert(BaseModel):
    id: str
    title: str
    time: str
    image: str
    isNew: bool

class PseudoAlert(BaseModel):
    name: str
    time: str
    image: str

class User(BaseModel):
    id: str
    name: str
    image: str

alerts_db = [
    {
        "id": "1",
        "title": "Kacper",
        "time": "12:45",
        "image": f"http://{IP}:8000/images/kacper.jpg",
        "isNew": True
    },
    {
        "id": "2",
        "title": "Maciej",
        "time": "13:10",
        "image": f"http://{IP}:8000/images/maciej.jpg",
        "isNew": True
    },
    {
        "id": "3",
        "title": "Maciejunio",
        "time": "6:10",
        "image": f"http://{IP}:8000/images/maciej.jpg",
        "isNew": True
    },
    {
        "id": "4",
        "title": "Zupstein",
        "time": "11:11",
        "image": f"http://{IP}:8000/images/zupa.jpg",
        "isNew": True
    },
    {
        "id": "5",
        "title": "Robercik",
        "time": "09:09",
        "image": f"http://{IP}:8000/images/lewy.jpg",
        "isNew": True
    },
    {
        "id": "6",
        "title": "Repcak",
        "time": "11:11",
        "image": f"http://{IP}:8000/images/kacper.jpg",
        "isNew": True
    },
]

users_db = [
    {
        "id": "1",
        "name": "Maciej",
        "image": f"http://{IP}:8000/images/maciej.jpg"
    },
    {
        "id": "2",
        "name": "Kacper",
        "image": f"http://{IP}:8000/images/kacper.jpg"
    },
    {
        "id": "3",
        "name": "Lewy",
        "image": f"http://{IP}:8000/images/lewy.jpg"
    },
    {
        "id": "4",
        "name": "Zupa",
        "image": f"http://{IP}:8000/images/zupa.jpg"
    },
]

@app.get("/alerts", response_model=List[Alert])
async def get_alerts():
    """Zwraca listę wszystkich alertów."""
    return alerts_db

@app.post("/alerts/{alert_id}/read")
async def mark_as_read(alert_id: str):
    """Znajduje alert po ID i zmienia isNew na False."""
    for alert in alerts_db:
        if alert["id"] == alert_id:
            alert["isNew"] = False
            return {"status": "success", "message": f"Alert {alert_id} przeczytany"}
    return {"status": "error", "message": "Nie znaleziono alertu"}

@app.post("/alerts")
async def add_alert(item: PseudoAlert):
    new_alert = {
        "id": str(time.time_ns()),  # TODO deleting alerts results in duplicated ids -> different id generation needed
        "title": item.name,
        "time": item.time,
        "image": f"http://{IP}:8000/images/captured/{item.image}",
        "isNew": True
    }

    alerts_db.append(new_alert)

    return new_alert

@app.get("/users", response_model=List[User])
async def get_users():
    """Zwraca listę wszystkich użytkowników."""
    return users_db

@app.post("/users")
async def create_user(name: str = Form(...), file: UploadFile = File(...)):
    file_path = f"images/users/{name}.jpg"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"http://{IP}:8000/images/users/{name}.jpg"

    new_user = {
        "id": str(len(users_db)+1),
        "name": name,
        "image": image_url
    }
    users_db.append(new_user)

    return new_user

@app.delete("/alerts/{alert_id}")
async def dlete_alert(alert_id: str):
    global alerts_db

    alert_to_remove = next((a for a in alerts_db if str(a["id"]) == str(alert_id)), None)

    if alert_to_remove is None:
        raise HTTPException(status_code=404, detail="Alert nie znaleziony")
    
    alerts_db = [a for a in alerts_db if str(a["id"]) != str(alert_id)]

    print(f"DEBUG: Usunięto {alert_id}. Pozostało elementów: {len(alerts_db)}")
    
    return {"message": f"Alert {alert_id} was removed", "deleted_id": alert_id}
