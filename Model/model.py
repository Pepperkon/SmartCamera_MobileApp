import asyncio
import os
from contextlib import asynccontextmanager

import httpx
import numpy as np
import uvicorn
from auth import INTERNAL_API_KEY, verify_api_key
from c_inference import CFaceEngine
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile

SFACE_COSINE_THRESHOLD = 0.363
load_dotenv()
SERVER_URL = os.environ.get("SERVER_URL")


async def sync_known_faces(app: FastAPI) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-Internal-Token": INTERNAL_API_KEY}
            templates = await client.get(f"{SERVER_URL}/faces/templates", headers=headers)
            templates.raise_for_status()

            synced = []
            for item in templates.json():
                vec = np.array(item["embedding"], dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                synced.append({"user_id": item["user_id"], "embedding": vec})

            app.state.known_faces = synced
            app.state.is_synced = True
        except httpx.HTTPError as e:
            print(f"Error while connecting to the server: {e}")
            app.state.is_synced = False

    return app.state.is_synced


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the inference engine
    engine = CFaceEngine()
    engine.initialize()
    app.state.engine = engine

    # Initialize global resource
    app.state.known_faces = []
    app.state.is_synced = False
    await sync_known_faces(app)

    yield

    app.state.engine.shutdown()


app = FastAPI(lifespan=lifespan)


# Separating the identification logic allows running it in a worker thread
# without blocking the main event loop
def _process_identification(engine: CFaceEngine, contents: bytes, known_faces: list) -> list:

    detections = engine.detect_and_encode(contents)

    results = []
    for det in detections:
        unknown_encoding = det["encoding"]
        user_id = None
        best_sim = None
        calibrated_conf = 0.0

        if known_faces:
            known_encodes = np.stack([f["embedding"] for f in known_faces])
            similarities = np.dot(known_encodes, unknown_encoding)

            best_match_index = int(np.argmax(similarities))
            best_sim = float(similarities[best_match_index])

            # Score Calibration
            # 0.363 represents the 50% threshold
            if best_sim >= SFACE_COSINE_THRESHOLD:
                user_id = known_faces[best_match_index]["user_id"]
                # Mapping range [0.363, 1.0] -> [0.50, 1.00]
                calibrated_conf = 0.5 + 0.5 * (
                    (best_sim - SFACE_COSINE_THRESHOLD) / (1.0 - SFACE_COSINE_THRESHOLD)
                )
            else:
                # Mapping range [0.0, 0.363) -> [0.00, 0.50)
                clamped_sim = max(0.0, best_sim)
                calibrated_conf = 0.5 * (clamped_sim / SFACE_COSINE_THRESHOLD)

        results.append(
            {
                "user_id": user_id,
                "location": det["location"],
                "encoding": unknown_encoding.tolist(),
                "confidence": round(calibrated_conf, 4),
            }
        )

    return results


# Core function for recognizing faces
# Takes all known encodes and an image
# Returns results for all detected faces
@app.post("/identify", dependencies=[Depends(verify_api_key)])
async def identify(request: Request):
    contents = await request.body()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received")

    if not request.app.state.is_synced:
        success = await sync_known_faces(request.app)
        if not success:
            raise HTTPException(status_code=503, detail="Synchronization failed")

    try:
        results = await asyncio.to_thread(
            _process_identification,
            request.app.state.engine,
            contents,
            request.app.state.known_faces,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return {"results": results}


# Endpoint for Server to get an image's encoding
@app.post("/encode", dependencies=[Depends(verify_api_key)])
async def encode_image(request: Request, file: UploadFile):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received")

    try:
        detections = await asyncio.to_thread(request.app.state.engine.detect_and_encode, contents)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return {"encodings": [d["encoding"].tolist() for d in detections]}


@app.post("/sync", dependencies=[Depends(verify_api_key)])
async def sync(request: Request):
    success = await sync_known_faces(request.app)
    if not success:
        raise HTTPException(status_code=503, detail="Synchronization failed")
    return {"status": "synced", "count": len(request.app.state.known_faces)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
