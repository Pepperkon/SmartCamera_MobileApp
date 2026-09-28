import io
import os
import time
from typing import BinaryIO

import aiofiles
import httpx
from auth import INTERNAL_API_KEY
from database import FaceTemplate
from fastapi import UploadFile
from PIL import Image
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession


async def mark_recognised(session_id: str, user_id: int, redis: Redis) -> bool:
    key = f"session:{session_id}"

    added = await redis.sadd(key, user_id)

    if added:
        await redis.expire(key, 3600)

    return added == 1


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


def _process_file_writing(contents: bytes, coordinates: tuple[int, int, int, int]) -> io.BytesIO:
    # Scale properly the image for it to show only the wanted face
    base_image = Image.open(io.BytesIO(contents))
    cropped_im = base_image.crop(coordinates)
    img_bytes = io.BytesIO()
    cropped_im.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes


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


async def notify_model_sync(model_url: str, client: httpx.AsyncClient | None = None) -> None:
    try:
        if client and not isinstance(client, httpx.AsyncClient):
            client = None

        headers = {"X-Internal-Token": INTERNAL_API_KEY}

        if client:
            response = await client.post(f"{model_url}/sync", headers=headers)
            response.raise_for_status()
        else:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.post(f"{model_url}/sync", headers=headers)
                response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error while connecting to the model: {e}")
