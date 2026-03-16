import os
import shutil
import time
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from database import *
from sqlalchemy.orm import selectinload
from model import get_encoding

load_dotenv()
IP = os.environ.get("IP")

if not IP:
    raise RuntimeError("IP not found, check README for instructions")

app = FastAPI()

app.mount("/data/images", StaticFiles(directory="data/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def add_user_image_logic(user_id: int, file: UploadFile, face_encoding: list[float], session: Session):
    new_template = FaceTemplate(filepath="pending", user_id=user_id, embedding=face_encoding)
    session.add(new_template)
    session.commit()
    session.refresh(new_template)

    filename = f"template_{new_template.id}_{int(time.time())}.jpg"
    user_dir = f"data/images/users/{user_id}"
    filepath = f"{user_dir}/{filename}"

    os.makedirs(user_dir, exist_ok=True)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_template.filepath = filename
    session.add(new_template)
    session.commit()

    return new_template

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    os.makedirs("data/images/users", exist_ok=True)
    os.makedirs("data/images/captured", exist_ok=True)


@app.get("/users", response_model=List[UserRead])
async def get_users(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich użytkowników."""
    statement = select(User).options(selectinload(User.images), selectinload(User.alerts))
    results = session.exec(statement).all()
    return results

@app.post("/users")
async def create_user(name: str = Form(...), file: UploadFile = File(...), session: Session = Depends(get_session)):
    face_encodings = await get_encoding(file)

    await file.seek(0)
    if len(face_encodings) == 0:
        raise HTTPException(status_code=404, detail="No face detected")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=404, detail="More than 1 face detected")

    new_user = User(name=name)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    await add_user_image_logic(new_user.id, file, face_encodings[0].tolist(), session)

    statement = select(User).where(User.id == new_user.id).options(
        selectinload(User.images), selectinload(User.alerts)
    )
    full_user = session.exec(statement).first()

    return full_user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    statement = select(User).where(User.id == user_id).options(selectinload(User.images))
    user_to_remove = session.exec(statement).first()

    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User not found")

    for img in user_to_remove.images:
        session.delete(img)

    folder_path = f"data/images/users/{user_id}"
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            print(f"Błąd przy usuwaniu plików: {e}")

    session.delete(user_to_remove)
    session.commit()

    return {"message": f"User {user_id} and all their data removed",
            "deleted_id": user_id}

@app.post("/users/{user_id}/images", response_model=UserRead)
async def add_user_image(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    face_encodings = await get_encoding(file)

    if len(face_encodings) == 0:
        raise HTTPException(status_code=404, detail="No face detected")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=404, detail="More than 1 face detected")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await file.seek(0)
    await add_user_image_logic(user_id, file, face_encodings[0].tolist(), session)

    statement = select(User).where(User.id == user_id).options(
            selectinload(User.images),
            selectinload(User.alerts)
    )
    updated_user = session.exec(statement).first()

    return updated_user

@app.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: Session = Depends(get_session)):
    """Pobiera dane konkretnego użytkownika wraz z jego zdjęciami."""
    statement = select(User).where(User.id == user_id).options(selectinload(User.images))
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

    return user

@app.get("/alerts", response_model=List[AlertRead])
async def get_alerts(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich alertów."""
    return session.exec(select(Alert)).all()

@app.post("/alerts")
async def add_alert(item: AlertRead, session: Session = Depends(get_session)):
    new_alert = Alert(
        title=item.title,
        time=item.time,
        image=item.image,   # TODO - might need some changes
        recognised_user_id=item.recognised_user_id
    )

    session.add(new_alert)
    session.commit()
    session.refresh(new_alert)

    return new_alert

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

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, session: Session = Depends(get_session)):

    alert_to_remove = session.get(Alert, alert_id)

    if not alert_to_remove:
        raise HTTPException(status_code=404, detail="Alert not found")

    session.delete(alert_to_remove)
    session.commit()

    return {"message": f"Alert {alert_id} was removed",
            "deleted_id": alert_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# needed to change the way of starting the server due to face recognition not wanting to cooperate
# to start the server type 'python main.py'
