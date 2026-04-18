import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
MODEL_URL = os.environ.get("MODEL_URL")
IMAGE_DIR = "test_images"

def run_simulation():

    images = [f for f in os.listdir(IMAGE_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))]

    for img_name in images:
        img_path = os.path.join(IMAGE_DIR, img_name)

        print(f"\n📸 Taken a photo: {img_name}")

        try:
            with open(img_path, "rb") as f:
                # Creating and sending the UploadFile object as json
                files = {"file": (img_name, f, "image/jpeg")}
                response = requests.post(f"{MODEL_URL}/recognize", files=files)

                if response.status_code == 200:
                    print(f"✅ Success with {img_name}")
                else:
                    print(f"⚠️ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)

    print("ALL PHOTOS HAVE BEEN TAKEN")

if __name__ == "__main__":
    run_simulation()
