# Camera
This module is responsible for the physical interface with the camera. It captures high-quality images and streams them directly to the AI Model for real-time analysis.

---

## Getting Started

1. **Prerequisites**
    - Python 3.13+
    - uv (Modern Python package manager - [Install uv](https://github.com/astral-sh/uv))
    - Raspberry Pi with a compatible Camera Module and Raspberry Pi OS (not needed for simulation)

2. **Environment Configuration**

    Create a .env file in this directory to store your network configuration (URL to connect with the device that runs the model):
    
    ```text
    MODEL_URL=http://192.168.1.XX:8001
    ```

3. **Installation**

    Using ```uv```, you can install all dependencies and set up the virtual environment with a single command:
    ```bash
    uv sync
    ```
4. **Running the Camera**

    To take a single photo and send it for recognition:
    ```bash
    uv run camera.py
    ```
5. **Running the simulation**

    Instead of running the camera.py script, you can run the **simulation.py** script. It takes the images in the **test_images** directory and acts like it took pictures of them and sends them to the server:
    ```bash
    uv run simulation.py
    ```
    
6. **Adding new packages**

    If you want to add a new package to the project use the following command:
    ```bash
    uv add package-name
    ```
