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

load_dotenv()
IP = os.environ.get("IP")

if not IP:
    raise RuntimeError("IP not found, check README for instructions")

class PseudoAlert(BaseModel):   # LEAVE AS IS, crucial system element
    name: str
    time: str
    image: str

app = FastAPI()

app.mount("/data/images", StaticFiles(directory="data/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/alerts")
async def add_alert(item: PseudoAlert, session: Session = Depends(get_session)):
    new_alert = Alert(
        title=item.name,
        time=item.time,
        image=item.image,   # TODO - might need some changes 
        isNew=True
    )

    session.add(new_alert)
    session.commit()
    session.refresh(new_alert)  

    return new_alert

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


@app.get("/users", response_model=List[UserRead])
async def get_users(session: Session = Depends(get_session)):
    """Zwraca listę wszystkich użytkowników."""
    statement = select(User).options(selectinload(User.images))
    results = session.exec(statement).all()
    return results

@app.post("/users")
async def create_user(name: str = Form(...), file: UploadFile = File(...), session: Session = Depends(get_session)):
    new_user = User(name=name)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    user_dir = f"data/images/users/{new_user.id}"
    os.makedirs(user_dir, exist_ok=True)

    filename = f"{new_user.id}_{int(time.time())}.jpg"      # timestamp fixes problems with id reuse
    file_path = f"data/images/users/{new_user.id}/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_face_template = FaceTemplate(
        filepath=filename,
        user_id=new_user.id,
    )

    session.add(new_face_template)
    session.commit()

    statement = select(User).where(User.id == new_user.id).options(selectinload(User.images))
    full_user = session.exec(statement).first()
    
    return full_user

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, session: Session = Depends(get_session)):

    alert_to_remove = session.get(Alert, alert_id)

    if not alert_to_remove:
        raise HTTPException(status_code=404, detail="Alert not found")

    session.delete(alert_to_remove)
    session.commit()

    return {"message": f"Alert {alert_id} was removed", "deleted_id": alert_id}

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

    return {"message": f"User {user_id} and all their data removed", "deleted_id": user_id}

@app.post("/users/{user_id}/images", response_model=UserRead)
async def add_user_image(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    filename = f"{user_id}_{int(time.time())}.jpg"
    filepath = f"data/images/users/{user_id}/{filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_face_template = FaceTemplate(
        filepath=filename,
        user_id=user_id,
    )

    session.add(new_face_template)
    session.commit()

    statement = select(User).where(User.id == user_id).options(selectinload(User.images))
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
