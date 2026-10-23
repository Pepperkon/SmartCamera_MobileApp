import os
import random
import secrets
import time

import requests
from dotenv import load_dotenv

load_dotenv()
SERVER_URL = os.environ.get("SERVER_URL")
IMAGE_DIR = "test_images"
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

if not SERVER_URL or not INTERNAL_API_KEY:
    raise RuntimeError("SERVER_URL or INTERNAL_API_KEY not found, check README for instructions")


def run_simulation():
    print("🚀 Starting continuous simulation (interval: 20s)...")

    while True:
        try:
            images = [f for f in os.listdir(IMAGE_DIR) if f.endswith((".jpg", ".jpeg", ".png"))]
        except FileNotFoundError:
            os.makedirs(IMAGE_DIR, exist_ok=True)
            images = []

        if not images:
            print("⚠️ No photos in test_images directory. Waiting 20s...")
            time.sleep(20)
            continue

        img_name = random.choice(images)
        img_path = os.path.join(IMAGE_DIR, img_name)

        session_id = secrets.token_hex(16)
        payload = {"session_id": session_id}

        print(f"\n📸 [Simulation] Chosen image: {img_name} (Session: {session_id[:8]}...)")

        try:
            with open(img_path, "rb") as f:
                files = {"file": (img_name, f, "image/jpeg")}
                headers = {"X-Internal-Token": INTERNAL_API_KEY}

                response = requests.post(
                    f"{SERVER_URL}/recognize",
                    files=files,
                    data=payload,
                    headers=headers,
                    timeout=60,
                )

                if response.status_code == 200:
                    print(f"✅ Success: Sent {img_name}")
                else:
                    print(f"⚠️ Server error: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            print(f"❌ No connection: {e}")

        time.sleep(20)


if __name__ == "__main__":
    run_simulation()
