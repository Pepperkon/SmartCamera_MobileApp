# Model
This module serves as the intelligence layer of the SmartCam system. It is responsible for processing images, detecting faces, and performing biometric matching using deep learning embeddings.

---

## Getting Started

1. **Prerequisites**
    - **Python 3.13+**
    - **uv** (Modern Python package manager - [Install uv](https://github.com/astral-sh/uv))
    - **C++ Compiler**: Required to compile the dlib library (e.g., build-essential on Linux or Visual Studio Build Tools on Windows)
    - **CMake**: Required for the face_recognition installation.

2. **System Dependencies**
    Before installing Python packages, ensure your system has the necessary build tools:
    - **Ubuntu/Raspberry Pi OS**:
        ```bash
        sudo apt install cmake g++ build-essential
        ```
    - **Fedora**:
        ```bash
        sudo dnf install cmake gcc-c++ make
        ```

3. **Environment Configuration**

    Create a .env file in this directory to store your network configuration (URL to connect with the device that runs the server):
    
    ```text
    SERVER_URL=http://192.168.1.XX:8000
    ```

4. **Installation**

    Using ```uv```, you can install all dependencies and set up the virtual environment with a single command:
    ```bash
    uv sync
    ```
5. **Running the Model**

    To start the AI Brain:
    ```bash
    uv run model.py
    ```
    
6. **Adding new packages**

    If you want to add a new package to the project use the following command:
    ```bash
    uv add package-name
    ```
