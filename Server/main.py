import asyncio
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from database import (
    Alert,
    AlertRead,
    FaceTemplate,
    User,
    UserRead,
    async_session_maker,
    engine,
    get_session,
)
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from services import (
    add_user_image_logic,
    notify_model_sync,
    save_image_to_disk,
)
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession


# Manages active WebSocket connections to push real-time updates to the frontend
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    # Sends data to all active clients.
    # Automatically cleans up zombie connections to prevent crashes
    async def broadcast(self, message: dict) -> None:
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)


load_dotenv()
MODEL_URL = os.environ.get("MODEL_URL")
manager = ConnectionManager()

if not MODEL_URL:
    raise RuntimeError("MODEL_URL not found, check README for instructions")

redis = Redis(host="localhost", port=6379)


async def cleanup_alerts(interval_seconds: int, max_age_hours: int) -> None:
    while True:
        threshold = datetime.now() - timedelta(hours=max_age_hours)
        async with async_session_maker() as session:
            old_alerts = (
                await session.exec(select(Alert).where(Alert.created_at < threshold))
            ).all()
            if old_alerts:
                deleted_alerts = []
                for old_alert in old_alerts:
                    image_path = f"data/images/captured/{old_alert.image}"
                    if os.path.isfile(image_path):
                        try:
                            os.remove(image_path)
                        except OSError as e:
                            print(f"Could not delete file {image_path}: {e}")
                    deleted_alerts.append(old_alert.id)

                await session.exec(delete(Alert).where(col(Alert.created_at) < threshold))
                await session.commit()
                print(f"Deleted {len(old_alerts)} alerts")

                # Broadcasting about deleting of old alerts
                for alert_id in deleted_alerts:
                    await manager.broadcast({"type": "alert_deleted", "alert_id": alert_id})

                # Automatic removal of temporary users with no alerts left
                statement = (
                    select(User).where(User.is_temporary).options(selectinload(User.alerts))  # type: ignore
                )
                users = (await session.exec(statement)).all()

                for user in users:
                    if user.id is not None and not user.alerts:
                        await delete_user(user.id, session)

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: creating sql engine and all of the directories
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    os.makedirs("data/images/users", exist_ok=True)
    os.makedirs("data/images/captured", exist_ok=True)
    task = asyncio.create_task(cleanup_alerts(interval_seconds=60, max_age_hours=1))

    redis_pool = await create_pool(RedisSettings())
    app.state.redis_pool = redis_pool
    # --- POPRAWKA: Dodajemy timeout na odczyt (np. 30 sekund) ---
    # Możesz też zaimportować httpx i użyć httpx.Timeout(30.0),
    # ale przekazanie samej liczby jako float też zadziała dla wszystkich limitów.
    app.state.client = httpx.AsyncClient(timeout=30.0)

    # Starting the application
    yield

    await app.state.redis_pool.close()
    # Shutdown of the application
    task.cancel()
    await app.state.client.aclose()
    await redis.aclose()


app = FastAPI(lifespan=lifespan)

app.mount("/data/images", StaticFiles(directory="data/images"), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.client


async def get_encoding_from_model(
    client: httpx.AsyncClient, file: UploadFile
) -> list[list[float]] | None:
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await client.post(f"{MODEL_URL}/encode", files=files)
        await file.seek(0)
        return response.json().get("encodings")
    except httpx.HTTPError as e:
        print(f"Error while connecting to the model: {e}")
        return None


# Making it available for the model to get the embeddings of known users
async def get_templates(session: AsyncSession) -> list[dict[str, Any]]:
    statement = select(FaceTemplate)
    results = (await session.exec(statement)).all()
    return [{"user_id": f.user_id, "embedding": f.embedding} for f in results]


@app.get("/faces/templates")
async def get_faces_templates(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await get_templates(session)


# Displaying users in the mobile app
@app.get("/users", response_model=list[UserRead])
async def get_users(
    is_temporary: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Zwraca listę wszystkich użytkowników."""
    statement = (
        select(User)
        .options(
            selectinload(User.images),  # type: ignore
            selectinload(User.alerts),  # type: ignore
        )
        .where(User.is_temporary == is_temporary)
        .order_by(col(User.name))
        .offset(offset)
        .limit(limit)
    )
    results = (await session.exec(statement)).all()
    return results


# Creating a new user
@app.post("/users")
async def create_user(
    name: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
) -> User:
    face_encodings = await get_encoding_from_model(client, file)

    if face_encodings is None:
        raise HTTPException(
            status_code=503,
            detail="Model server is not responding or returned an error.",
        )

    if len(face_encodings) == 0:
        raise HTTPException(status_code=422, detail="NO_FACE")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=422, detail="MULTIPLE_FACES")

    new_user = User(name=name, is_temporary=False)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    assert new_user.id is not None, "User id cannot be None"

    await add_user_image_logic(new_user.id, file, face_encodings[0], session)

    statement = (
        select(User)
        .where(User.id == new_user.id)
        .options(
            selectinload(User.images),  # type: ignore
            selectinload(User.alerts),  # type: ignore
        )
    )
    full_user = (await session.exec(statement)).first()
    assert full_user is not None, "Created user not found in database"

    if MODEL_URL:
        await notify_model_sync(MODEL_URL, client)

    return full_user


# Deleting a user
@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    statement = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.images),  # type: ignore
            selectinload(User.alerts),  # type: ignore
        )
    )
    user_to_remove = (await session.exec(statement)).first()

    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User not found")

    for img in user_to_remove.images:
        await session.delete(img)

    folder_to_delete = f"data/images/users/{user_id}"
    files_to_delete = []
    for alert in user_to_remove.alerts:
        if alert.id is not None:
            files_to_delete.append(f"data/images/captured/{alert.image}")
            await delete_alert(alert.id, False, session)

    await session.delete(user_to_remove)
    await session.commit()

    cooldown_key = f"cooldown:user:{user_id}"
    await redis.delete(cooldown_key)

    if os.path.exists(folder_to_delete):
        try:
            shutil.rmtree(folder_to_delete)
        except Exception as e:  # noqa: BLE001
            print(f"Error while removing direcotry {folder_to_delete}: {e}")

    for file in files_to_delete:
        if os.path.exists(file):
            os.remove(file)

    if MODEL_URL:
        await notify_model_sync(MODEL_URL)

    return {
        "message": f"User {user_id} and all their data removed",
        "deleted_id": user_id,
    }


# Adding a new image for a user
@app.post("/users/{user_id}/images", response_model=UserRead)
async def add_user_image(
    user_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
):
    face_encodings = await get_encoding_from_model(client, file)

    if face_encodings is None:
        raise HTTPException(
            status_code=503,
            detail="Model server is not responding or returned an error.",
        )

    if len(face_encodings) == 0:
        raise HTTPException(status_code=422, detail="NO_FACE")

    if len(face_encodings) > 1:
        raise HTTPException(status_code=422, detail="MULTIPLE_FACES")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await file.seek(0)
    await add_user_image_logic(user_id, file, face_encodings[0], session)

    statement = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.images),  # type: ignore
            selectinload(User.alerts),  # type: ignore
        )
    )
    updated_user = (await session.exec(statement)).first()

    if MODEL_URL:
        await notify_model_sync(MODEL_URL, client)

    return updated_user


# Get information about a certain user
@app.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    statement = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.images), selectinload(User.alerts))  # type: ignore
    )
    user = (await session.exec(statement)).first()

    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

    return user


# Returns the list of all alerts
@app.get("/alerts", response_model=list[AlertRead])
async def get_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return (
        await session.exec(select(Alert).order_by(col(Alert.id).desc()).offset(offset).limit(limit))
    ).all()


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep the connection alive until the client drops
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Checking alert's status from New to Read
@app.post("/alerts/{alert_id}/read")
async def mark_as_read(
    alert_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    """Znajduje alert po ID i zmienia isNew na False."""
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Nie znaleziono alertu")
    alert.isNew = False
    session.add(alert)
    await session.commit()
    await session.refresh(alert)

    alert_dict = AlertRead.model_validate(alert).model_dump()
    # Instruct clients to update the alert's state
    await manager.broadcast({"type": "alert_read", "alert": alert_dict})

    return {"status": "success", "message": f"Alert {alert_id} przeczytany"}


# Deleting an alert
@app.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: int, auto_commit: bool = True, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    alert_to_remove = await session.get(Alert, alert_id)

    if not alert_to_remove:
        raise HTTPException(status_code=404, detail="Alert not found")

    user_id = alert_to_remove.recognised_user_id

    await session.delete(alert_to_remove)

    # If auto_commit is False, this was triggered by the delete_user function which already deletes the user
    # If True, it's a direct call from the mobile app, so we need to clean up temporary users if they have no alerts left
    if auto_commit:
        await session.commit()
        file_path = f"data/images/captured/{alert_to_remove.image}"
        if os.path.exists(file_path):
            os.remove(file_path)
        if user_id is not None:
            user = await session.get(User, user_id, options=[selectinload(User.alerts)])  # type: ignore
            if user and user.is_temporary and not user.alerts:
                await delete_user(user_id, session)

    # Instruct clients to instantly drop this alert from their active list
    await manager.broadcast({"type": "alert_deleted", "alert_id": alert_id})

    return {"message": f"Alert {alert_id} was removed", "deleted_id": alert_id}


# Upgrading a temporary user to a permanent one and updating their old alerts
@app.patch("/users/{user_id}")
async def save_temporary_user(
    user_id: int, name: str, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    user = await session.get(User, user_id, options=[selectinload(User.alerts)])  # type: ignore
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_temporary:
        return {"message": "User was already saved"}

    user.is_temporary = False
    user.name = name
    new_title = f"Recognized: {user.name}"

    # Updating the titles of all previous alerts connected to this user
    for alert in user.alerts:
        alert.title = new_title
        alert_dict = AlertRead.model_validate(alert).model_dump()
        alert_data = {"type": "updated_alert", "alert": alert_dict}
        await manager.broadcast(alert_data)

    await session.commit()

    return {"message": f"User {user.name} saved"}


# Changing user's trust status
@app.patch("/users/{user_id}/trust")
async def update_trust_status(
    user_id: int, is_trusted: bool, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_trusted = is_trusted
    await session.commit()
    return {"message": "Status updated", "is_trusted": user.is_trusted}


@app.post("/recognize")
async def recognize_face(
    request: Request, file: UploadFile = File(...), session_id: str = Form(...)
) -> dict[str, str]:
    print(f"\n[RECOGNIZE] --- New request for session: {session_id} ---")

    contents = await file.read()
    filename = f"{str(uuid.uuid4())}.jpg"

    await save_image_to_disk(filename, contents)

    await app.state.redis_pool.enqueue_job("process_image_worker", session_id, filename)

    return {"status": "success"}


@app.post("/internal/broadcast")
async def broadcast_alert(payload: dict):
    await manager.broadcast(payload)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20.0, ws_ping_timeout=20.0)
