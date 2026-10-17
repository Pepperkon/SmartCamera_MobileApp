# Backend Server
This is the central hub of the SmartCam system. It manages the SQLite database, handles user registrations, stores alert history, broadcasts real-time updates via WebSockets, and runs background cleanup tasks.

---

## Getting Started

1. **Prerequisites**
    - Python 3.13+
    - uv (Modern Python package manager - [Install uv](https://github.com/astral-sh/uv))
    - Redis Server

2. **Redis**

    The server requires Redis to manage alert cooldowns and prevent notification spam. You can install it natively on your OS or run it via Docker.

    - **Ubuntu / Raspberry Pi OS**:
        ```bash
        sudo apt install redis-server
        sudo systemctl enable --now redis-server
        ```
    
    - **Fedora**:
        ```bash
        sudo dnf install redis
        sudo systemctl enable --now redis
        ```

3. **Environment Configuration**

    Create a `.env` file in this directory to store your network configuration and internal security key:
      
    ```text
    MODEL_URL=http://192.168.X.X:8001
    INTERNAL_API_KEY=your_shared_secret_key
    ```
    *(Refer to the root README for instructions on generating the `INTERNAL_API_KEY`)*

4. **Installation**

    Using ```uv```, you can install all dependencies and set up the virtual environment with a single command:
    ```bash
    uv sync
    ```
5. **Running the Server & Worker**

    To prevent the AI model from overloading during rapid image captures, the image processing logic is offloaded to a background worker. You must run **both** the FastAPI server and the ARQ worker in separate terminal windows.
  
    **Terminal 1 (FastAPI Server):**
    ```bash
    uv run main.py
    ```
  
    **Terminal 2 (Background Worker):**
    ```bash
    uv run worker.py
    ```

6. **Adding new packages**

    If you want to add a new package to the project use the following command:
    ```bash
    uv add package-name
    ```
