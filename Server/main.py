import asyncio
import io
import os
import shutil
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, BinaryIO

import aiofiles
import httpx
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
    BackgroundTasks,
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
from PIL import Image
from redis.asyncio import Redis
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


async def mark_recognised(session_id: str, user_id: int) -> bool:
    key = f"session:{session_id}"

    added = await redis.sadd(key, user_id)

    if added:
        await redis.expire(key, 3600)

    return added == 1


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

    # --- POPRAWKA: Dodajemy timeout na odczyt (np. 30 sekund) ---
    # Możesz też zaimportować httpx i użyć httpx.Timeout(30.0),
    # ale przekazanie samej liczby jako float też zadziała dla wszystkich limitów.
    app.state.client = httpx.AsyncClient(timeout=30.0)

    # Starting the application
    yield

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


# Uploading a captured image
async def save_image_to_disk(filename: str, img_data: bytes | io.BytesIO | BinaryIO) -> None:
    filepath = f"data/images/captured/{filename}"

    if isinstance(img_data, bytes):
        data = img_data
    elif isinstance(img_data, io.BytesIO):
        data = img_data.getvalue()
    else:
        data = img_data.read()

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(data)


# Creating an alert
async def add_alert(data: dict[str, Any], session: AsyncSession) -> Alert:
    print(
        f"[ALERT] Creating database alert: '{data['title']}' for user ID: {data['recognised_user_id']}"
    )

    new_alert = Alert(
        title=data["title"],
        time=data["time"],
        date=data["date"],
        image=data["image"],
        isNew=data["isNew"],
        recognised_user_id=data["recognised_user_id"],
        embedding=data["embedding"],
        confidence=data["confidence"],
        location=data["location"],
    )

    session.add(new_alert)
    await session.commit()
    await session.refresh(new_alert)

    alert_dict = AlertRead.model_validate(new_alert).model_dump()
    alert_data = {"type": "new_alert", "alert": alert_dict}
    print(
        f"[WS] Broadcasting alert (ID: {new_alert.id}) to {len(manager.active_connections)} connected WebSocket clients."
    )
    # Notify all connected clients about the newly created alert
    await manager.broadcast(alert_data)

    return new_alert


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


async def add_user_image_logic(
    user_id: int,
    file: UploadFile | io.BytesIO,
    face_encoding: list[float],
    session: AsyncSession,
) -> FaceTemplate:
    new_template = FaceTemplate(filepath="pending", user_id=user_id, embedding=face_encoding)
    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)

    filename = f"template_{new_template.id}_{int(time.time())}.jpg"
    user_dir = f"data/images/users/{user_id}"
    filepath = f"{user_dir}/{filename}"

    os.makedirs(user_dir, exist_ok=True)
    # path for io.BytesIO objects
    if isinstance(file, io.BytesIO):
        data = file.getvalue()
    # path for UploadFile objects
    else:
        await file.seek(0)
        data = await file.read()

    async with aiofiles.open(filepath, "wb") as buffer:
        await buffer.write(data)

    new_template.filepath = filename
    session.add(new_template)
    await session.commit()

    return new_template


async def notify_model_sync(client: httpx.AsyncClient | None = None) -> None:
    try:
        if client and not isinstance(client, httpx.AsyncClient):
            client = None

        if client:
            response = await client.post(f"{MODEL_URL}/sync")
            response.raise_for_status()
        else:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.post(f"{MODEL_URL}/sync")
                response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error while connecting to the model: {e}")


def _process_file_writing(contents: bytes, coordinates: tuple[int, int, int, int]) -> io.BytesIO:
    # Scale properly the image for it to show only the wanted face
    base_image = Image.open(io.BytesIO(contents))
    cropped_im = base_image.crop(coordinates)
    img_bytes = io.BytesIO()
    cropped_im.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes


async def process_image_pipeline(
    contents: bytes, session_id: str, client: httpx.AsyncClient
) -> None:
    async with async_session_maker() as session:
        response = await client.post(
            f"{MODEL_URL}/identify",
            content=contents,
        )
        response.raise_for_status()

        results = response.json().get("results", [])
        print(f"[RECOGNIZE] Model returned {len(results)} recognized faces.")

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d.%m.%Y")
        time_stamp = now.strftime("%d.%m.%Y_%H-%M-%S")

        image_name = f"{time_stamp}.jpg"
        image_saved = False

        if not results:
            print("[RECOGNIZE] Decision: No faces detected. Saving empty image and exiting.")
            image_name = f"empty_{time_stamp}.jpg"
            await save_image_to_disk(image_name, contents)
            return

        new_template_added = False

        for i, res in enumerate(results):
            user_id = res["user_id"]
            print(f"[RECOGNIZE] Processing face {i + 1}/{len(results)}. Returned ID: {user_id}")

            top, right, bottom, left = res["location"]

            # When an uknown face is detected a new user is created
            # This user is untrusted and temporary
            # This means that when all their alerts are deleted the user is also deleted
            if user_id is None:
                print("[RECOGNIZE] Decision: Face is unknown. Creating a temporary user.")
                new_user = User(name="Stranger")
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                new_user.name += f"_{new_user.id}"
                await session.commit()
                assert new_user.id is not None, "Fresh user_id cannot be None"
                user_id = new_user.id
                print(f"[RECOGNIZE] Success: Created new user with ID: {user_id}")

            print(
                f"[RECOGNIZE] Checking for session duplication [{session_id}] for ID: {user_id}..."
            )
            if not await mark_recognised(session_id, user_id):
                print(
                    f"[RECOGNIZE] Rejected: User {user_id} already recognized in this session. Skipping."
                )
                continue

            print(f"[RECOGNIZE] Checking global Redis cooldown for ID: {user_id}...")
            cooldown_key = f"cooldown:user:{user_id}"
            cooldown_created = await redis.set(cooldown_key, "active", nx=True, ex=300)

            if not cooldown_created:
                print(
                    f"[RECOGNIZE] Rejected: Active cooldown (5 min) for user {user_id}. Skipping."
                )
                continue

            user = await session.get(User, user_id)

            if not user:
                print(
                    f"[RECOGNIZE] Error: User {user_id} does not exist in the database! Skipping."
                )
                continue
            print(
                f"[RECOGNIZE] Decision: User {user.name} qualified for an alert. Trusted status: {user.is_trusted}"
            )

            if not user.is_temporary:
                title = f"Recognized: {user.name}"
            else:
                title = f"Unknown: {user.name}"
                img_bytes = await asyncio.to_thread(
                    _process_file_writing, contents, (left, top, right, bottom)
                )
                # For temporary users add many faces for reference
                await add_user_image_logic(user_id, img_bytes, res["encoding"], session)
                new_template_added = True

            distance = res.get("distance")
            if distance is not None:
                confidence = max(0.0, 1 - distance) * 100
            else:
                confidence = 0.0

            if not image_saved:
                await save_image_to_disk(image_name, contents)
                image_saved = True

            await add_alert(
                {
                    "title": title,
                    "time": time_str,
                    "date": date_str,
                    "image": image_name,
                    "isNew": True,
                    "recognised_user_id": user_id,
                    "embedding": res["encoding"],
                    "confidence": confidence,
                    "location": [top, right, bottom, left],
                },
                session,
            )

        if new_template_added:
            await notify_model_sync(client)


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

    await notify_model_sync(client)

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

    await notify_model_sync()

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

    await notify_model_sync(client)

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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    client: httpx.AsyncClient = Depends(get_client),
) -> dict[str, str]:
    print(f"\n[RECOGNIZE] --- New request for session: {session_id} ---")

    contents = await file.read()

    background_tasks.add_task(process_image_pipeline, contents, session_id, client)

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20.0, ws_ping_timeout=20.0)
