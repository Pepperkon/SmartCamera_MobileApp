# SmartCamera_MobileApp
Mobile application designed for an intelligent monitoring system

---

## Architecture
1. Smartcam (Mobile App) - The user interface
2. Server - Central database and alert management
3. Model - Face recognition service
4. Camera - Script for handling the physical camera on a Raspberry Pi
5. Redis - In-memory data store used for managing alert cooldowns to prevent notification spam

---

## Network & Communication
- All components (App, Server, Model, Camera) must be connected to **the same local network**.
- Communication between modules is handled via the **HTTP** protocol (REST API) and **WebSockets** (for real-time UI updates).

---

## Developer Setup & Quality Standards

This project uses modern tooling for code quality and automated CI checks:

- **Python modules (`Camera`, `Model`, `Server`)**: Managed with [`uv`](https://docs.astral.sh/uv/), formatted and linted with **Ruff**, and checked with **Bandit** and `pip-audit`.
- **Mobile app (`SmartCam`)**: Checked with **ESLint** and **TypeScript (`tsc`)**.

### 1. Prerequisites
- [uv](https://docs.astral.sh/uv/) (Python package & environment manager)
- [Node.js](https://nodejs.org/) (v20+ or v24+) & npm

### 2. Initial Setup (One-Time)
Run these commands from the **root directory** of the repository:

```bash
# 1. Sync the root Python environment
uv sync

# 2. Install pre-commit Git hooks
uv run pre-commit install
```

### 3. Workflow & Pre-commit Hooks
Once installed, `pre-commit` automatically runs before every git commit to format and check your Python code:
- If files need formatting, `ruff` reformats them automatically and marks the hook as failed. Stage the changes (`git add .`) and commit again.
- If errors remain, inspect the line numbers printed in the terminal.

You can also run all checks manually on the entire monorepo at any time:
```bash
uv run pre-commit run --all-files
```

### 4. CI Pipeline
Every push and Pull Request triggers GitHub Actions to ensure code integrity:
- Python Matrix Checks: Ruff formatting (`--check`), Ruff linting, Bandit security analysis, and `pip-audit` for dependency vulnerabilities.
- SmartCam Checks: `tsc --noEmit` (type checking) and `eslint`.

---

## Getting Started
Each component contains its own **README.md** with specific installation instructions. To start the entire system, follow these steps in order:
1. Start **Redis** server
2. Configure and start **Server**
2. Configure and start **Model**
3. Launch **Smartcam** and open it on your phone
4. Run the **Camera** script to begin sending images for analysis

---

## Windows/WSL Setup
Communication between devices is often blocked by system security layers.

### WSL
To ensure WSL uses the same IP address as your Windows host, create or edit the file `C:\Users\user\.wslconfig`:
```text
[wsl2]
networkingMode=Mirrored
```
Then, restart WSL.

### Firewall
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
