import asyncio
import io
import math
import os
import re
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from auth import INTERNAL_API_KEY, verify_api_key
from database import (
    Alert,
    AlertRead,
    AlertUserStatus,
    FaceTemplate,
    PushToken,
    PushTokenRegistration,
    User,
    UserMergeRequest,
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
from PIL import Image, UnidentifiedImageError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from services import (
    add_user_image_logic,
    notify_model_sync,
    save_image_to_disk,
)
from sqlalchemy import inspect
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

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
redis = Redis(host=REDIS_HOST, port=6379)


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
        alert_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("alert")}
        )
        if "detection_confidence" not in alert_columns:
            await conn.exec_driver_sql("ALTER TABLE alert ADD COLUMN detection_confidence FLOAT")
    os.makedirs("data/images/users", exist_ok=True)
    os.makedirs("data/images/captured", exist_ok=True)
    task = asyncio.create_task(cleanup_alerts(interval_seconds=60, max_age_hours=1))

    redis_pool = await create_pool(RedisSettings(host=REDIS_HOST))
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

Path("data/images").mkdir(parents=True, exist_ok=True)
Path("data/images/captured").mkdir(parents=True, exist_ok=True)

app.mount("/data/images", StaticFiles(directory="data/images"), name="images")

# Constants for file validation
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/jpg", "image/png"]
MIN_IMAGE_DIMENSION = 160  # pixels
MAX_IMAGE_DIMENSION = 4096  # pixels

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def validate_image_file(file: UploadFile) -> None:
    file_content = await file.read()
    await file.seek(0)

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.0f}MB",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid content type. Allowed types: {ALLOWED_CONTENT_TYPES}",
        )

    try:
        with Image.open(io.BytesIO(file_content)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid image format: {e}") from e

    if min(width, height) < MIN_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=422,
            detail=f"Image too small. Minimum dimension is {MIN_IMAGE_DIMENSION}px",
        )

    if max(width, height) > MAX_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=422,
            detail=f"Image too large. Maximum dimension is {MAX_IMAGE_DIMENSION}px",
        )


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.client


async def get_encoding_from_model(
    client: httpx.AsyncClient, file: UploadFile
) -> list[list[float]] | None:
    try:
        headers = {"X-Internal-Token": INTERNAL_API_KEY}
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await client.post(f"{MODEL_URL}/encode", files=files, headers=headers)
        await file.seek(0)
        return response.json().get("encodings")
    except httpx.HTTPError as e:
        print(f"Error while connecting to the model: {e}")
        return None


# Making it available for the model to get the embeddings of known users
async def get_templates(session: AsyncSession) -> list[dict[str, Any]]:
    statement = select(FaceTemplate).join(User).where(col(User.is_temporary).is_(False))
    results = (await session.exec(statement)).all()
    return [{"user_id": f.user_id, "embedding": f.embedding} for f in results]


async def add_suggested_matches(alerts: list[AlertRead], session: AsyncSession) -> None:
    templates = (
        await session.exec(
            select(FaceTemplate, User.name)
            .join(User, FaceTemplate.user_id == User.id)
            .where(User.is_temporary.is_(False))
            .order_by(FaceTemplate.id)
        )
    ).all()

    for alert in alerts:
        embedding = alert.embedding
        if (
            alert.recognised_user_is_temporary is not True
            or embedding is None
            or alert.detection_confidence is None
            or alert.detection_confidence < 0.78
        ):
            continue

        best_by_user: dict[int, tuple[float, str]] = {}
        avatar_paths: dict[int, str] = {}
        for template, name in templates:
            if template.user_id is None:
                continue
            avatar_paths.setdefault(template.user_id, template.filepath)
            vector = template.embedding
            if len(vector) != len(embedding):
                continue
            dot = math.fsum(left * right for left, right in zip(embedding, vector, strict=True))
            left_norm = math.sqrt(math.fsum(value * value for value in embedding))
            right_norm = math.sqrt(math.fsum(value * value for value in vector))
            if left_norm == 0 or right_norm == 0:
                continue
            similarity = dot / (left_norm * right_norm)
            current = best_by_user.get(template.user_id)
            if current is None or similarity > current[0]:
                best_by_user[template.user_id] = (
                    similarity,
                    name,
                )

        if not best_by_user:
            continue

        user_id, (similarity, name) = max(best_by_user.items(), key=lambda item: item[1][0])
        if 0.22 <= similarity < 0.33:
            alert.suggested_match = {
                "user_id": user_id,
                "name": name,
                "avatar_url": f"/data/images/users/{user_id}/{avatar_paths[user_id]}",
                "similarity": round(similarity, 4),
                "is_permanent": True,
            }


@app.get("/faces/templates", dependencies=[Depends(verify_api_key)])
async def get_faces_templates(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await get_templates(session)


# Displaying users in the mobile app
@app.get("/users", response_model=list[UserRead])
async def get_users(
    is_temporary: bool | None = Query(default=None, description="Filter by temporary status"),
    is_trusted: bool | None = Query(default=None, description="Filter by trust status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Zwraca listę wszystkich użytkowników."""
    statement = (
        select(User)
        .options(
            selectinload(User.images),
            selectinload(User.alerts),
        )
        .order_by(col(User.name))
        .offset(offset)
        .limit(limit)
    )
    if is_trusted is not None:
        statement = statement.where(User.is_trusted == is_trusted)
    if is_temporary is not None:
        statement = statement.where(User.is_temporary == is_temporary)
    elif is_trusted is None:
        statement = statement.where(User.is_temporary.is_(False))

    results = (await session.exec(statement)).all()
    return results


async def clear_merged_user_redis_state(user_id: int) -> str | None:
    try:
        await redis.delete(f"cooldown:user:{user_id}")

        async for key in redis.scan_iter(match="session:*:stranger"):
            stranger_id = await redis.get(key)
            if stranger_id in (str(user_id).encode(), str(user_id)):
                await redis.delete(key)

        async for key in redis.scan_iter(match="session:*"):
            key_name = key.decode() if isinstance(key, bytes) else key
            if key_name.endswith(":stranger"):
                continue
            if await redis.type(key) == b"set":
                await redis.srem(key, user_id)
    except RedisError as error:
        return f"Redis cleanup failed: {error}"
    return None


@app.post("/users/merge")
async def merge_users(
    payload: UserMergeRequest,
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
) -> dict[str, Any]:
    if payload.source_user_id == payload.target_user_id:
        raise HTTPException(status_code=400, detail="Source and target users must differ")

    source = await session.get(User, payload.source_user_id)
    target = await session.get(User, payload.target_user_id)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Source or target user not found")
    if target.is_temporary:
        raise HTTPException(
            status_code=400,
            detail="Target user must be permanent; temporary users cannot be merge targets",
        )

    source_templates = (
        await session.exec(
            select(FaceTemplate).where(FaceTemplate.user_id == payload.source_user_id)
        )
    ).all()
    source_alerts = (
        await session.exec(select(Alert).where(Alert.recognised_user_id == payload.source_user_id))
    ).all()

    source_dir = Path(f"data/images/users/{payload.source_user_id}")
    target_dir = Path(f"data/images/users/{payload.target_user_id}")
    moved_files: list[tuple[Path, Path]] = []
    discarded_files: list[Path] = []

    try:
        for template in source_templates:
            old_path = source_dir / template.filepath
            if payload.include_templates:
                new_path = target_dir / template.filepath
                if old_path.is_file():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(old_path, new_path)
                    moved_files.append((old_path, new_path))
                template.user_id = payload.target_user_id
                session.add(template)
            else:
                if old_path.is_file():
                    discarded_files.append(old_path)
                await session.delete(template)

        for alert in source_alerts:
            alert.recognised_user_id = payload.target_user_id
            alert.title = f"Recognized: {target.name}"
            session.add(alert)

        await session.flush()
        await session.delete(source)
        await session.flush()
        await session.commit()
    except Exception:
        await session.rollback()
        for old_path, new_path in reversed(moved_files):
            if new_path.exists():
                old_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(new_path, old_path)
        raise

    warnings: list[str] = []
    for path in discarded_files:
        if path.exists():
            try:
                path.unlink()
            except OSError as error:
                warnings.append(f"Template cleanup failed for {path}: {error}")
    if source_dir.exists():
        try:
            shutil.rmtree(source_dir)
        except OSError as error:
            warnings.append(f"Source directory cleanup failed: {error}")

    redis_warning = await clear_merged_user_redis_state(payload.source_user_id)
    if redis_warning:
        warnings.append(redis_warning)
    if MODEL_URL:
        try:
            response = await client.post(
                f"{MODEL_URL}/sync",
                headers={"X-Internal-Token": INTERNAL_API_KEY},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            warnings.append(f"Model synchronization failed: {error}")

    target_statement = (
        select(User)
        .where(User.id == payload.target_user_id)
        .options(selectinload(User.images), selectinload(User.alerts))
    )
    updated_target = (await session.exec(target_statement)).first()
    if updated_target is None:
        raise HTTPException(status_code=500, detail="Merged target user could not be loaded")

    await manager.broadcast(
        {
            "type": "user_merged",
            "source_user_id": payload.source_user_id,
            "target_user_id": payload.target_user_id,
            "target_name": updated_target.name,
            "target_is_trusted": updated_target.is_trusted,
        }
    )
    return {
        "target_user": UserRead.model_validate(updated_target).model_dump(mode="json"),
        "moved_alerts": len(source_alerts),
        "added_templates": len(source_templates) if payload.include_templates else 0,
        "warnings": warnings,
    }


# Creating a new user
@app.post("/users")
async def create_user(
    name: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
) -> User:
    # Walidacja pliku przed przetwarzaniem
    await validate_image_file(file)

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
    # Validate uploaded image before processing
    await validate_image_file(file)

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

    user_read = UserRead.model_validate(user)
    if user.is_temporary:
        ordered_alerts = sorted(
            user.alerts,
            key=lambda alert: alert.created_at,
            reverse=True,
        )
        alert_reads = []
        for alert in ordered_alerts:
            alert_read = AlertRead.model_validate(alert.model_dump())
            alert_read.recognised_user_is_temporary = True
            alert_reads.append(alert_read)
        await add_suggested_matches(alert_reads, session)
        user_read.suggested_match = next(
            (alert.suggested_match for alert in alert_reads if alert.suggested_match is not None),
            None,
        )
    return user_read


# Returns the list of all alerts
@app.get("/alerts", response_model=list[AlertRead])
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.exec(
            select(Alert, User.is_trusted, User.is_temporary)
            .outerjoin(User, Alert.recognised_user_id == User.id)
            .order_by(col(Alert.id).desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()

    # Attach the current user flags to each alert.
    result: list[AlertRead] = []
    for alert, is_trusted, is_temporary in rows:
        alert_read = AlertRead.model_validate(alert.model_dump())
        alert_read.recognised_user_is_trusted = is_trusted
        alert_read.recognised_user_is_temporary = is_temporary
        if alert.recognised_user_id is not None:
            alert_read.user = AlertUserStatus(
                is_temporary=is_temporary,
            )
        result.append(alert_read)

    await add_suggested_matches(result, session)
    return result


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep the connection alive until the client drops
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/push-tokens")
async def register_push_token(
    registration: PushTokenRegistration,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    token = registration.token.strip()
    if not re.fullmatch(r"(?:Expo|Exponent)PushToken\[[^\]\s]+\]", token):
        raise HTTPException(status_code=422, detail="Invalid Expo push token")

    push_token = (await session.exec(select(PushToken).where(PushToken.token == token))).first()
    if push_token:
        push_token.platform = registration.platform
        session.add(push_token)
    else:
        session.add(PushToken(token=token, platform=registration.platform))

    await session.commit()
    return {"status": "registered"}


@app.delete("/push-tokens")
async def unregister_push_token(
    registration: PushTokenRegistration,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await session.exec(delete(PushToken).where(PushToken.token == registration.token.strip()))
    await session.commit()
    return {"status": "unregistered"}


async def send_alert_pushes(
    alert: dict[str, Any],
    session: AsyncSession,
    client: httpx.AsyncClient,
) -> None:
    push_tokens = (await session.exec(select(PushToken))).all()
    if not push_tokens:
        return

    messages = [
        {
            "to": push_token.token,
            "title": "SmartCam — nowy alert",
            "body": str(alert.get("title") or "Wykryto osobę"),
            "sound": "default",
            "channelId": "alerts",
            "priority": "high",
            "data": {"type": "new_alert", "alertId": alert.get("id")},
        }
        for push_token in push_tokens
    ]

    # Expo accepts batches of up to 100 messages per request.
    for batch_start in range(0, len(messages), 100):
        batch = messages[batch_start : batch_start + 100]
        batch_tokens = push_tokens[batch_start : batch_start + 100]
        tickets: Any = None
        for attempt in range(3):
            try:
                response = await client.post(
                    "https://exp.host/--/api/v2/push/send",
                    json=batch,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                response_data = response.json()
                tickets = response_data.get("data") if isinstance(response_data, dict) else None
                break
            except httpx.HTTPStatusError as error:
                retryable = error.response.status_code == 429 or error.response.status_code >= 500
                if retryable and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                print(f"[PUSH] Expo request failed for alert {alert.get('id')}: {error}")
            except httpx.RequestError as error:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                print(f"[PUSH] Expo request failed for alert {alert.get('id')}: {error}")
            except ValueError as error:
                print(f"[PUSH] Expo returned invalid JSON for alert {alert.get('id')}: {error}")
            break

        if not isinstance(tickets, list) or len(tickets) != len(batch):
            print(
                f"[PUSH] Unexpected Expo response for alert {alert.get('id')}: "
                f"expected {len(batch)} tickets"
            )
            continue

        for push_token, ticket in zip(batch_tokens, tickets, strict=True):
            if not isinstance(ticket, dict):
                print(f"[PUSH] Invalid Expo ticket for alert {alert.get('id')}")
                continue
            if ticket.get("status") == "ok":
                continue
            details = ticket.get("details", {})
            print(
                f"[PUSH] Expo rejected token for alert {alert.get('id')}: "
                f"{ticket.get('message', 'unknown error')}"
            )
            if details.get("error") == "DeviceNotRegistered":
                await session.exec(delete(PushToken).where(PushToken.id == push_token.id))
                await session.commit()


@app.post("/internal/broadcast", dependencies=[Depends(verify_api_key)])
async def broadcast_alert(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session),
):
    await manager.broadcast(payload)
    if payload.get("type") == "new_alert":
        await send_alert_pushes(payload.get("alert", {}), session, app.state.client)
    return {"status": "ok"}


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

    alert_dict = AlertRead.model_validate(alert.model_dump()).model_dump()
    user = (
        await session.get(User, alert.recognised_user_id)
        if alert.recognised_user_id is not None
        else None
    )
    alert_dict["recognised_user_is_trusted"] = user.is_trusted if user else None
    alert_dict["recognised_user_is_temporary"] = user.is_temporary if user else None
    alert_dict["user"] = {"is_temporary": user.is_temporary} if user else None
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


@app.patch("/users/{user_id}/name")
async def update_user_name(
    user_id: int, name: str, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    user = await session.get(User, user_id, options=[selectinload(User.alerts)])  # type: ignore
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_name = name.strip()
    if not updated_name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")

    if user.name == updated_name:
        return {"message": "Name unchanged"}

    user.name = updated_name
    title_prefix = "Unknown" if user.is_temporary else "Recognized"
    alert_updates = []
    for alert in user.alerts:
        alert.title = f"{title_prefix}: {updated_name}"
        alert_dict = AlertRead.model_validate(alert.model_dump()).model_dump(mode="json")
        alert_dict["recognised_user_is_trusted"] = user.is_trusted
        alert_dict["recognised_user_is_temporary"] = user.is_temporary
        alert_dict["user"] = {"is_temporary": user.is_temporary}
        alert_updates.append({"type": "updated_alert", "alert": alert_dict})

    await session.commit()

    for alert_update in alert_updates:
        await manager.broadcast(alert_update)

    return {"message": f"User {updated_name} updated"}


# Upgrading a temporary user to a permanent one and updating their old alerts
@app.patch("/users/{user_id}")
async def save_temporary_user(
    user_id: int,
    name: str,
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
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
        alert_dict = AlertRead.model_validate(alert.model_dump()).model_dump()
        alert_dict["recognised_user_is_trusted"] = user.is_trusted
        alert_dict["recognised_user_is_temporary"] = user.is_temporary
        alert_dict["user"] = {"is_temporary": user.is_temporary}
        alert_data = {"type": "updated_alert", "alert": alert_dict}
        await manager.broadcast(alert_data)

    await session.commit()

    if MODEL_URL:
        await notify_model_sync(MODEL_URL, client)

    return {"message": f"User {user.name} saved"}


# Changing user's trust status
@app.patch("/users/{user_id}/trust")
async def update_trust_status(
    user_id: int,
    is_trusted: bool,
    session: AsyncSession = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_client),
) -> dict[str, Any]:
    user = await session.get(User, user_id, options=[selectinload(User.alerts)])  # type: ignore
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    was_temporary = user.is_temporary
    user.is_trusted = is_trusted
    if is_trusted:
        user.is_temporary = False

    # Update historical alert titles when a temporary user becomes permanent
    alert_updates = []
    if was_temporary and not user.is_temporary:
        new_title = f"Recognized: {user.name}"
        for alert in user.alerts:
            alert.title = new_title
            alert_dict = AlertRead.model_validate(alert.model_dump()).model_dump(mode="json")
            alert_dict["recognised_user_is_trusted"] = user.is_trusted
            alert_dict["recognised_user_is_temporary"] = user.is_temporary
            alert_dict["user"] = {"is_temporary": user.is_temporary}
            alert_updates.append({"type": "updated_alert", "alert": alert_dict})

    await session.commit()

    if was_temporary and not user.is_temporary and MODEL_URL:
        await notify_model_sync(MODEL_URL, client)

    for alert_update in alert_updates:
        await manager.broadcast(alert_update)

    # Notify connected mobile clients about the trust status change
    await manager.broadcast(
        {
            "type": "user_trust_updated",
            "user_id": user.id,
            "is_trusted": user.is_trusted,
            "is_temporary": user.is_temporary,
        }
    )

    return {
        "message": "Status updated",
        "is_trusted": user.is_trusted,
        "is_temporary": user.is_temporary,
    }


@app.post("/recognize", dependencies=[Depends(verify_api_key)])
async def recognize_face(
    request: Request, file: UploadFile = File(...), session_id: str = Form(...)
) -> dict[str, str]:
    contents = await file.read()

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        print(f"[WARN] Invalid content type for recognize: {file.content_type}")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024):.0f}MB",
        )

    print(f"\n[RECOGNIZE] --- New request for session: {session_id} ---")

    filename = f"{str(uuid.uuid4())}.jpg"

    await save_image_to_disk(filename, contents)

    await app.state.redis_pool.enqueue_job("process_image_worker", session_id, filename)

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20.0, ws_ping_timeout=20.0)
