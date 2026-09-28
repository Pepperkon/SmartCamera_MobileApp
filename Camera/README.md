# Camera
This module is responsible for the physical interface with the camera and motion detection. It captures high-quality images triggered by a PIR sensor and streams them directly to the central Server for further processing.

---

## Getting Started

1. **Prerequisites**
    - Python 3.13+
    - uv (Modern Python package manager - [Install uv](https://github.com/astral-sh/uv))
    - Raspberry Pi with a compatible Camera Module, a PIR Motion Sensor (connected to GPIO 25), and Raspberry Pi OS (not needed for simulation)

2. **Environment Configuration**

    Create a `.env` file in this directory to store your network configuration and internal security key:
    
    ```text
    SERVER_URL=http://192.168.X.X:8000
    INTERNAL_API_KEY=your_shared_secret_key
    ```
    *(Refer to the root README for instructions on generating the `INTERNAL_API_KEY`)*

3. **Installation**

    Using ```uv```, you can install all dependencies and set up the virtual environment with a single command:
    ```bash
    uv sync
    ```
4. **Running the Camera**

    To run the continuous motion detection loop (takes a photo automatically when movement is detected):
    ```bash
    uv run movement_det.py
    ```
    *(Optional)* To manually take a single photo and send it to the server without motion detection:
    ```bash
    uv run camera.py
    ```

5. **Running the simulation**

    Instead of using physical hardware, you can run the **simulation.py** script. It iterates through images in the **test_images** directory and sends them to the server as if they were just captured:
    ```bash
    uv run simulation.py
    ```
    
6. **Adding new packages**

    If you want to add a new package to the project use the following command:
    ```bash
    uv add package-name
    ```
