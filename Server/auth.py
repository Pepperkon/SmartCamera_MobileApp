import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-Internal-Token", auto_error=False)
app_key_header = APIKeyHeader(name="X-App-Token", auto_error=False)

load_dotenv()
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")
APP_API_KEY = os.environ.get("APP_API_KEY")

if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY not found, check README for instructions")

if not APP_API_KEY:
    raise RuntimeError("APP_API_KEY not found, check README for instructions")


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or missing api key"
        )


async def verify_app_key(app_key: str = Depends(app_key_header)):
    if app_key != APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or missing app api key"
        )
