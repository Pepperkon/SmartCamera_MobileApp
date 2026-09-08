import asyncio
import io
import os
from contextlib import asynccontextmanager

import face_recognition
import httpx
import numpy as np
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile

TOLERANCE = 0.50
load_dotenv()
SERVER_URL = os.environ.get("SERVER_URL")


async def sync_known_faces(app: FastAPI) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            templates = await client.get(f"{SERVER_URL}/faces/templates")
            templates.raise_for_status()
            app.state.known_faces = [
                {"user_id": item["user_id"], "embedding": np.array(item["embedding"])}
                for item in templates.json()
            ]
            app.state.is_synced = True
        except httpx.HTTPError as e:
            print(f"Error while connecting to the server: {e}")
            app.state.is_synced = False

    return app.state.is_synced


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize global resource
    app.state.known_faces = []
    app.state.is_synced = False
    await sync_known_faces(app)

    yield


app = FastAPI(lifespan=lifespan)


# Separating the identification logic allows running it in a worker thread
# without blocking the main event loop
def _process_identification(contents: bytes, known_faces: list) -> list:
    image = face_recognition.load_image_file(io.BytesIO(contents))
    locations = face_recognition.face_locations(image)
    unknown_encodings = face_recognition.face_encodings(image, locations)
    known_encodes = [f["embedding"] for f in known_faces]

    results = []
    for i, unknown_encoding in enumerate(unknown_encodings):
        user_id = None

        if known_faces:
            distances = face_recognition.face_distance(known_encodes, unknown_encoding)
            if len(distances) > 0:
                best_match_index = np.argmin(distances)
                if distances[best_match_index] < TOLERANCE:
                    user_id = known_faces[best_match_index]["user_id"]

        results.append(
            {
                "user_id": user_id,
                "location": locations[i],
                "encoding": unknown_encoding.tolist(),
            }
        )

    return results


# Core function for recognizing faces
# Takes all known encodes and an image
# Returns results for all detected faces
@app.post("/identify")
async def identify(request: Request, file: UploadFile = File(...)):
    if not request.app.state.is_synced:
        success = await sync_known_faces(request.app)
        if not success:
            raise HTTPException(status_code=503, detail="Synchronization failed")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received")
    known_faces = request.app.state.known_faces
    results = await asyncio.to_thread(_process_identification, contents, known_faces)
    return {"results": results}


# Separating the encoding logic allows running it in a worker thread
# without blocking the main event loop.
def _process_encoding(contents: bytes):
    image = face_recognition.load_image_file(io.BytesIO(contents))
    encodings = face_recognition.face_encodings(image)
    return encodings


# Endpoint for Server to get an image's encoding
@app.post("/encode")
async def encode_image(file: UploadFile):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received")
    encodings = await asyncio.to_thread(_process_encoding, contents)
    return {"encodings": [e.tolist() for e in encodings]}


@app.post("/sync")
async def sync(request: Request):
    success = await sync_known_faces(request.app)
    if not success:
        raise HTTPException(status_code=503, detail="Synchronization failed")
    return {"status": "synced", "count": len(request.app.state.known_faces)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
