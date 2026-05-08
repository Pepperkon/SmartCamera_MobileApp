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
import requests
import asyncio
from datetime import timedelta, datetime
from contextlib import asynccontextmanager

load_dotenv()
MODEL_URL = os.environ.get("MODEL_URL")

if not MODEL_URL:
    raise RuntimeError("MODEL_URL not found, check README for instructions")

async def cleanup_alerts(interval_seconds: int, max_age_hours: int):
    while True:
        threshold = datetime.now() - timedelta(hours=max_age_hours)
        with Session(engine) as session:
            old_alerts = session.exec(select(Alert).where(Alert.created_at < threshold)).all()
            for old_alert in old_alerts:
                image_path = f"data/images/captured/{old_alert.image}"
                if os.path.isfile(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Could not delete file {image_path}: {e}")
            session.exec(delete(Alert).where(Alert.created_at < threshold))
            session.commit()
            print(f"Deleted {len(old_alerts)} alerts")
        await asyncio.sleep(interval_seconds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: creating sql engine and all of the directories
    SQLModel.metadata.create_all(engine)
    os.makedirs("data/images/users", exist_ok=True)
    os.makedirs("data/images/captured", exist_ok=True)
    task = asyncio.create_task(cleanup_alerts(interval_seconds=60, max_age_hours=1))

    # Starting the application
    yield

    # Shutdown of the application
    task.cancel()

app = FastAPI(lifespan=lifespan)

app.mount("/data/images", StaticFiles(directory="data/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_encoding_from_model(file: UploadFile):
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = requests.post(f"{MODEL_URL}/encode", files=files)
        await file.seek(0)
        return response.json().get("encodings")
    except Exception as e:
        print(f"Error while connecting to the model: {e}")
        return None

def rematch_alerts(new_user: User, face_encoding: List[float], unrecognized_alerts: List[Alert], session: Session):
    data = {
        "user_id": new_user.id,
        "embedding": face_encoding,
        "unrecognized_alerts": [{"id": a.id, "embedding": a.embedding} for a in unrecognized_alerts]
    }
    try:
        response = requests.post(f"{MODEL_URL}/rematch", json=data, timeout=10)
        matched_ids = response.json().get("matched_ids", [])
        for alert_id in matched_ids:
            alert_to_update = session.get(Alert, alert_id)
            if alert_to_update:
                alert_to_update.recognised_user_id = new_user.id
                alert_to_update.title = f"Detected: {new_user.name}"
                alert_to_update.isNew = True
                session.add(alert_to_update)
        session.commit()
    except Exception as e:
        print(f"Rematch failed: {e}")

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

# Making it available for the model to get the embeddings of known users
@app.get("/templates")
async def get_templates(session: Session = Depends(get_session)):
    statement = select(FaceTemplate)
    results = session.exec(statement).all()
    return [{"user_id": f.user_id, "embedding": f.embedding} for f in results]

# Displaying users in the mobile app

@app.get("/users", response_model=List[UserRead])
async def get_users(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich użytkowników."""
    statement = select(User).options(selectinload(User.images), selectinload(User.alerts))
    results = session.exec(statement).all()
    return results

# Creating a new user
@app.post("/users")
async def create_user(name: str = Form(...), file: UploadFile = File(...), session: Session = Depends(get_session)):
    face_encodings = await get_encoding_from_model(file)

    if face_encodings is None:
        raise HTTPException(
            status_code=503,
            detail="Model server is not responding or returned an error."
        )

    if len(face_encodings) == 0:
        raise HTTPException(status_code=404, detail="NO_FACE")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=404, detail="MULTIPLE_FACES")

    new_user = User(name=name)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    await add_user_image_logic(new_user.id, file, face_encodings[0], session)
    statement = select(Alert).where(Alert.recognised_user_id == None, Alert.embedding != None)
    unrecognized_alerts = session.exec(statement).all()

    if unrecognized_alerts:
        rematch_alerts(new_user, face_encodings[0], unrecognized_alerts, session)

    statement = select(User).where(User.id == new_user.id).options(
        selectinload(User.images), selectinload(User.alerts)
    )
    full_user = session.exec(statement).first()

    return full_user

# Deleting a user
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

# Adding a new image for a user
@app.post("/users/{user_id}/images", response_model=UserRead)
async def add_user_image(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    face_encodings = await get_encoding_from_model(file)

    if len(face_encodings) == 0:
        raise HTTPException(status_code=404, detail="No face detected")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=404, detail="More than 1 face detected")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await file.seek(0)
    await add_user_image_logic(user_id, file, face_encodings[0], session)

    statement = select(User).where(User.id == user_id).options(
            selectinload(User.images),
            selectinload(User.alerts)
    )
    updated_user = session.exec(statement).first()

    return updated_user

# Get information about a certain user
@app.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: Session = Depends(get_session)):
    statement = select(User).where(User.id == user_id).options(selectinload(User.images))
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

    return user

# Returns the list of all alerts
@app.get("/alerts", response_model=List[AlertRead])
async def get_alerts(session: Session = Depends(get_session)):
    return session.exec(select(Alert)).all()

# Uploading a captured image
@app.post("/upload-captured")
async def upload_captured(file: UploadFile = File(...)):
    filepath = f"data/images/captured/{file.filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "success"}

# Creating an alert
@app.post("/alerts")
async def add_alert(item: AlertRead, session: Session = Depends(get_session)):
    title = item.title
    if item.recognised_user_id:
        user = session.get(User, item.recognised_user_id)
        if user:
            title = f"Detected: {user.name}"
    new_alert = Alert(
        title=title,
        time=item.time,
        date=item.date,
        image=item.image,   # TODO - might need some changes
        recognised_user_id=item.recognised_user_id,
        embedding=item.embedding
    )

    session.add(new_alert)
    session.commit()
    session.refresh(new_alert)

    return new_alert

# Checking alert's status from New to Read
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

# Deleting an alert
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
