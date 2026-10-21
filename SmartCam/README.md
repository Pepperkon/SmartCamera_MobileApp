# SmartCam Mobile Client
Mobile application built with **React Native** and **Expo**. It serves as the primary user interface for the SmartCam ecosystem, enabling real-time alert monitoring via WebSockets, user registration (with facial biometric templates), and access control management.

---

## Getting Started

1. **Prerequisites**
    - **Node.js** & **npm**
    - **Expo Go** app installed on your physical mobile device (Android / iOS)

2. **Environment Configuration**

    Create a **.env** file inside the **SmartCam/** root directory. It requires your server's IP address and the client authorization key.
    
    ```text
    # Local Network (Home Wi-Fi):
    EXPO_PUBLIC_SERVER_IP=192.168.X.Y

    # Client access key (Must match APP_API_KEY on the Server)
    EXPO_PUBLIC_APP_API_KEY=your_app_secret_key
    
    # Remote Access (Tailscale VPN):
    # EXPO_PUBLIC_SERVER_IP=100.X.Y.Z
    ```

3. **Installation**

    Install all required project dependencies:
    ```bash
    npm install
    ```

4. **Running the Application**

    - **Option A**: Local Network (Same Wi-Fi)
      ```bash
      npx expo start
      ```
    - **Option B**: Remote Access via Tailscale
      - **Windows (PowerShell)**: 
        ```powershell
        $env:REACT_NATIVE_PACKAGER_HOSTNAME="100.X.Y.Z"; npx expo start
        ```
      - **Windows (CMD)**:
        ```cmd
        set REACT_NATIVE_PACKAGER_HOSTNAME=100.X.Y.Z && npx expo start
        ```
      - **Linux / macOS**:
        ```bash
        REACT_NATIVE_PACKAGER_HOSTNAME=100.X.Y.Z npx expo start
        ```
      *(Replace `100.X.Y.Z` with your PC's Tailscale IPv4 address).*
