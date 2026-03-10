import os
import shutil
import time
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from database import *

app = FastAPI()
IP = "192.168.1.48"

app.mount("/images", StaticFiles(directory="data/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    os.makedirs("data/images/users", exist_ok=True)
    os.makedirs("data/images/captured", exist_ok=True)

@app.get("/alerts", response_model=List[Alert])
async def get_alerts(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich alertów."""
    return session.exec(select(Alert)).all()

@app.post("/alerts/{alert_id}/read")
async def mark_as_read(alert_id: int, session: Session = Depends(get_session)):
    """Znajduje alert po ID i zmienia isNew na False."""
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Nie znaleziono alertu")
    alert.isNew = False
    session.add(alert)
    session.commit()
    return {"status": "success", "message": f"Alert {alert_id} przeczytany"}


@app.get("/users", response_model=List[User])
async def get_users(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich użytkowników."""
    return session.exec(select(User)).all()

@app.post("/users")
async def create_user(name: str = Form(...), file: UploadFile = File(...), session: Session = Depends(get_session)):
    new_user = User(name=name, image="")
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    filename = f"{new_user.id}.jpg"
    file_path = f"data/images/users/{filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_user.image = f"http://{IP}:8000/images/users/{filename}"
    session.add(new_user)
    session.commit()

    return new_user

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, session: Session = Depends(get_session)):

    alert_to_remove = session.get(Alert, alert_id)

    if not alert_to_remove:
        raise HTTPException(status_code=404, detail="Alert nie znaleziony")

    session.delete(alert_to_remove)
    session.commit()

    # print(f"DEBUG: Usunięto {alert_id}. Pozostało elementów: {len(alerts_db)}")

    return {"message": f"Alert {alert_id} was removed", "deleted_id": alert_id}


# alerts_db = [
#     {
#         "id": "1",
#         "title": "Kacper",
#         "time": "12:45",
#         "image": f"http://{IP}:8000/images/kacper.jpg",
#         "isNew": True
#     },
#     {
#         "id": "2",
#         "title": "Maciej",
#         "time": "13:10",
#         "image": f"http://{IP}:8000/images/maciej.jpg",
#         "isNew": True
#     },
#     {
#         "id": "3",
#         "title": "Maciejunio",
#         "time": "6:10",
#         "image": f"http://{IP}:8000/images/maciej.jpg",
#         "isNew": True
#     },
#     {
#         "id": "4",
#         "title": "Zupstein",
#         "time": "11:11",
#         "image": f"http://{IP}:8000/images/zupa.jpg",
#         "isNew": True
#     },
#     {
#         "id": "5",
#         "title": "Robercik",
#         "time": "09:09",
#         "image": f"http://{IP}:8000/images/lewy.jpg",
#         "isNew": True
#     },
#     {
#         "id": "6",
#         "title": "Repcak",
#         "time": "11:11",
#         "image": f"http://{IP}:8000/images/kacper.jpg",
#         "isNew": True
#     },
# ]

# users_db = [
#     {
#         "id": "1",
#         "name": "Maciej",
#         "image": f"http://{IP}:8000/images/maciej.jpg"
#     },
#     {
#         "id": "2",
#         "name": "Kacper",
#         "image": f"http://{IP}:8000/images/kacper.jpg"
#     },
#     {
#         "id": "3",
#         "name": "Lewy",
#         "image": f"http://{IP}:8000/images/lewy.jpg"
#     },
#     {
#         "id": "4",
#         "name": "Zupa",
#         "image": f"http://{IP}:8000/images/zupa.jpg"
#     },
# ]
#
# # @app.post("/alerts")
# async def add_alert(item: PseudoAlert):
#     new_alert = {
#         "id": str(time.time_ns()),  # TODO deleting alerts results in duplicated ids -> different id generation needed
#         "title": item.name,
#         "time": item.time,
#         "image": f"http://{IP}:8000/images/captured/{item.image}",
#         "isNew": True
#     }

#     alerts_db.append(new_alert)

#     return new_alert
