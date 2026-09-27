import asyncio
import os
from datetime import datetime
from pathlib import Path

import httpx
from arq import Worker
from arq.connections import RedisSettings
from database import (
    Alert,
    AlertRead,
    User,
    async_session_maker,
)
from dotenv import load_dotenv
from redis.asyncio import Redis
from services import (
    _process_file_writing,
    add_user_image_logic,
    mark_recognised,
    notify_model_sync,
)


async def startup(ctx: dict) -> None:
    # creating an HTTP client for communication with Model and Server modules
    ctx["client"] = httpx.AsyncClient(timeout=30.0)
    load_dotenv()
    ctx["model_url"] = os.environ.get("MODEL_URL")
    ctx["redis"] = Redis(host="localhost", port=6379)


async def shutdown(ctx):
    client = ctx.get("client")
    if client:
        await client.aclose()


async def process_image_worker(ctx: dict, session_id: str, filename: str) -> None:
    client = ctx["client"]
    model_url = ctx["model_url"]
    redis = ctx["redis"]

    path = Path(f"data/images/captured/{filename}")
    contents = path.read_bytes()

    async with async_session_maker() as session:
        response = await client.post(
            f"{model_url}/identify",
            content=contents,
        )
        response.raise_for_status()

        results = response.json().get("results", [])
        print(f"[RECOGNIZE] Model returned {len(results)} recognized faces.")

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d.%m.%Y")

        if not results:
            print("[RECOGNIZE] Decision: No faces detected.")
            if path.exists():
                path.unlink()
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
            if not await mark_recognised(session_id, user_id, redis):
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

            new_alert = Alert(
                title=title,
                time=time_str,
                date=date_str,
                image=filename,
                isNew=True,
                recognised_user_id=user_id,
                embedding=res["encoding"],
                confidence=confidence,
                location=[top, right, bottom, left],
            )
            session.add(new_alert)
            await session.commit()
            await session.refresh(new_alert)

            alert_dict = AlertRead.model_validate(new_alert).model_dump()

            try:
                await client.post(
                    "http://localhost:8000/internal/broadcast",
                    json={"type": "new_alert", "alert": alert_dict},
                )
            except httpx.HTTPError as e:
                print(f"[WORKER] Communication error with FastAPI during broadcast: {e}")

        if new_template_added:
            await notify_model_sync(model_url, client)


async def start_worker():
    worker = Worker(
        functions=[process_image_worker],
        redis_settings=RedisSettings(host="localhost", port=6379),
        on_startup=startup,
        on_shutdown=shutdown,
        max_jobs=1,
    )
    print("[WORKER] Worker ready and waits for tasks")
    await worker.main()


if __name__ == "__main__":
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        print("\n[WORKER] Turning off the worker")
