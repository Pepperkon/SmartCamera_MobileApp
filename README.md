# SmartCamera_MobileApp
Mobile application designed for an intelligent monitoring system

---

## Architecture
1. Smartcam (Mobile App) - The user interface
2. Server - Central database and alert management
3. Model - Face recognition service
4. Camera - Script for handling the physical camera on a Raspberry Pi
5. Redis - In-memory data store used for managing alert cooldowns and background job queues

---

## Quick Start (Docker)

The easiest and recommended way to run the entire backend infrastructure (Server, Model, Camera, and Redis) is using **Docker**.

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed on your machine.
- Node.js (for running the SmartCam mobile app).

### 2. Security Configuration (Single `.env` file)

  To prevent unauthorized execution of internal functions, the system requires a shared authorization key.
  
  **Step 1: Generate a secure key**
  Generate a long, random string using Python's built-in `secrets` module. Run this in your terminal:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
  (*Copy the generated string*)
  
  **Step 2: Create a single `.env` file in the root directory of the project and add your key:**
  ```text
  INTERNAL_API_KEY=your_copied_key_here
  ```

### 3. Run the Backend System

Open your terminal in the root directory and choose one of the profiles below:

  - **Option A: Simulation Mode (For PC/Mac/Linux testing)**

    Runs the server, model, and a simulated camera that continuously picks random images from the `Camera/test_images` directory.
      
    ```bash
    docker compose --profile sim up -d
    ```
      
    (*Note: If you change Python source files, append `--build` to the command to rebuild the images*).

  - **Option B: Production Mode (For Raspberry Pi)**

    Runs the server, model, and the actual physical camera script using GPIO and `rpicam-apps`.
      
    ```bash
    docker compose --profile pi up -d
    ```

### 4. Useful Docker Commands

  - **View live logs:** `docker compose --profile sim logs -f`
  
  - **Stop safely:** `docker compose --profile sim down` (keeps your database and saved images)
  
  - **Hard reset:** `docker compose --profile sim down -v` (wipes the database and all captured images)


### 5. Launch the Mobile App

The backend is now running. To start the user interface, follow the instructions in the [SmartCam/README.md](SmartCam/README.md).
  
---

### Multi-Device Deployment (Docker)

If you want to run the system across multiple devices (e.g., Server on a PC, Camera on a Raspberry Pi), you can use the exact same `docker-compose.yml` file.

  1. Copy the project repository to all devices.
  2. Update the `.env` file on all devices to include the local IP addresses of the Server and Model hosts:

      ```text
      INTERNAL_API_KEY=your_copied_key_here
      SERVER_URL=http://192.168.X.Y:8000
      MODEL_URL=http://192.168.X.Y:8001
      ```

  3. Run only the specific services you need on each device:

      - On the Server PC: `docker compose up -d redis server-api server-worker`
      - On the AI PC: `docker compose up -d model`
      - On the Raspberry Pi: `docker compose --profile pi up -d camera-pi`


---

### Network, Communication & Remote Access

The core infrastructure is designed to run locally within the same **Home LAN** network for low latency and security. Communication between services uses standard HTTP REST endpoints and WebSockets for real-time alert dispatching.

#### Accessing Your SmartCam from Outside (Remote Access)

If you want to monitor your home and receive alerts on your phone while away (e.g., from work or cellular data), the recommended and most secure solution is **[Tailscale](https://tailscale.com/)** (a zero-config WireGuard mesh VPN). This avoids dangerous port forwarding on your home router.

> **Quick Start:** Check out the official [Tailscale in 10 minutes tutorial on YouTube](https://www.youtube.com/watch?v=sPdvyR7bLqI) to see how easy it is to set up a private mesh network.

#### How it works:
1. Install **Tailscale** on the machine running the **Server** (PC/Raspberry Pi) and on your **Mobile Phone**.
2. Log into the same Tailscale account on both devices.
3. Note the Tailscale IP assigned to your server host (e.g., `100.x.y.z`).
4. Point your mobile application (in `SmartCam/.env`) to this Tailscale IP. All backend traffic and WebSocket streams will securely route straight to your home system.

---

### Windows/WSL Setup
Communication between devices is often blocked by system security layers.

#### WSL
To ensure WSL uses the same IP address as your Windows host, create or edit the file `C:\Users\user\.wslconfig`:
```text
[wsl2]
networkingMode=Mirrored
```
Then, restart WSL.

#### Firewall
Run PowerShell **as Administrator** and execute the following commands to open the necessary ports (open only the ones that you need):
```bash
# Allow traffic for Server
New-NetFirewallRule -DisplayName "Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private

# Allow traffic for Model
New-NetFirewallRule -DisplayName "Model" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow -Profile Private

# Allow traffic for Smartcam
New-NetFirewallRule -DisplayName "Smartcam" -Direction Inbound -LocalPort 8081 -Protocol TCP -Action Allow -Profile Private
```
Go to WiFi settings and change your **TRUSTED** WiFi as Private instead of Public.

These commands open ports to other devices on the same network as long as you marked this network as **PRIVATE**. Windows automatically sets networks as **PUBLIC** so these commands work **only on networks that you trust**.

If you later would want to remove these rules you can do it like this:
```bash
Remove-NetFirewallRule -DisplayName "name"
```

---

## Native Developer Setup & Quality Standards

If you plan to heavily modify the Python code, attach debuggers, or prefer not to use Docker, you can run the services natively. This project uses modern tooling for code quality and automated CI/CD checks.
  - Python modules (`Camera`, `Model`, `Server`): Managed with uv, formatted and linted with Ruff, and checked with Bandit and `pip-audit`.
  - Mobile app (`SmartCam`): Checked with ESLint and TypeScript (`tsc`).

1. **Initial Setup (One-Time)**
   Run these commands from the **root directory** of the repository:

   ```bash
   # 1. Sync the root Python environment
   uv sync

   # 2. Install pre-commit Git hooks
   uv run pre-commit install
   ```

2. **Workflow & Pre-commit Hooks**
   Once installed, `pre-commit` automatically runs before every git commit to format and check your Python code. You can also run all checks manually on the entire monorepo at any time:
   ```bash
   uv run pre-commit run --all-files
   ```

3. **CI Pipeline**
   - **Continuous Integration (CI)**: Every push and Pull Request triggers GitHub Actions to ensure code integrity (Ruff formatting/linting, Bandit security analysis, `pip-audit`, and ESLint/TypeScript checks).

4. **Running Natively**
   Each component contains its own **README.md** with specific installation instructions for native deployment. To start the entire system natively, follow these steps in order:
   1. Start **Redis** server locally.
   2. Configure `.env` files in each directory.
   3. Start **Server** (`main.py` and `worker.py`).
   4. Start **Model** (`model.py`).
   5. Launch **Smartcam** and open it on your phone.
   6. Run the **Camera** script (`simulation.py` or `movement_det.py`).
