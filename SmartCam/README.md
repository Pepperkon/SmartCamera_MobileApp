# SmartCam Mobile Client
Mobile application built with **React Native** and **Expo**. It serves as the primary user interface for the SmartCam ecosystem, enabling real-time alert monitoring via WebSockets, user registration (with facial biometric templates), and access control management.

---

## Getting Started

1. **Prerequisites**
    - **Node.js** & **npm**
    - A physical Android or iOS device. Remote push notifications require a development or production build; Expo Go is not supported for this flow.

2. **Environment Configuration**

    Create a **.env** file inside the **SmartCam/** root directory
    
    ```text
    # Local Network (Home Wi-Fi):
    EXPO_PUBLIC_SERVER_IP=192.168.X.Y
    
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

## Push notifications

This project uses Expo Push Service. After a successful alert is saved, the
backend sends a visible push to every device registered at `POST /push-tokens`.
The app registers its Expo push token automatically when it starts and the user
grants notification permission. Since the app does not currently have accounts,
tokens are not associated with individual users: every registered installation
receives every alert.

### Android setup (recommended for development)

#### Requirements

- A physical Android phone with Google Play services and a computer on the same
  Wi-Fi network.
- Node.js/npm and an Expo account.
- Access to the Firebase project associated with the Android app. The configured
  package ID is `com.pepperkon.smartcam`.
- Docker Desktop if running the backend using the repository's Docker Compose
  setup.

#### 1. Install the app dependencies

From this directory (`SmartCam/`), run:

```powershell
npm install
```

#### 2. Configure the API address used by the phone

Create or update `SmartCam/.env`:

```dotenv
EXPO_PUBLIC_SERVER_IP=192.168.1.24
```

Replace the example with the computer's current LAN/Wi-Fi IPv4 address (not
`127.0.0.1`, `localhost`, or a Docker/WSL virtual-network address). The phone
and computer must be on the same network, and Windows Firewall must allow
incoming TCP traffic to port `8000` on a private network. Check connectivity by
opening `http://<computer-LAN-IP>:8000/docs` in the phone's browser.

#### 3. Check Firebase and obtain the FCM V1 service-account key

1. Open the app's Firebase project in the
   [Firebase Console](https://console.firebase.google.com/).
2. Under **Project settings → General**, check that its Android app has package
   ID `com.pepperkon.smartcam`. The existing `google-services.json` and
   `app.json` are configured for this ID; do not replace them with files for a
   different Firebase app.
3. In **Project settings → Service accounts**, choose **Generate new private
   key** and download the JSON file.
4. Open this project's [EAS Credentials page](https://expo.dev/accounts/mawin05/projects/SmartCam/credentials),
   choose **Android**, then add the JSON under **FCM V1 service account key**.
   The exact label may appear as **Google Service Account Key for Push
   Notifications (FCM V1)**.
5. Keep the downloaded JSON private. Do not commit it, put it in the mobile app,
   or upload it as an Android keystore. If a key has been exposed, revoke it in
   Google Cloud Console and generate a replacement.

The Firebase service-account JSON is for FCM push delivery. The Android upload
keystore is a separate signing credential; EAS can generate that keystore during
the build setup. Never upload the Firebase JSON in the keystore field.

#### 4. Use or create an EAS project

This repository is already linked to the EAS project owned by `mawin05`, with
its project ID in `app.json`. If you have access to that EAS project, keep the
existing `owner`, `extra.eas.projectId`, and Android package settings.

If you are setting up your own copy under a different Expo account:

1. From `SmartCam/`, log in with `npx --yes eas-cli@latest login`.
2. Run `npx --yes eas-cli@latest init` and create/link a project in your
   account.
3. Register the same Android package (`com.pepperkon.smartcam`) in your own
   Firebase project, download its matching `google-services.json`, and update
   the Firebase file and FCM credentials as described above. Keep the package
   ID identical in Firebase and `app.json`.

Do not copy an EAS project ID from another project or use a placeholder.

#### 5. Build and install a development build

From `SmartCam/`, run:

```powershell
npx --yes eas-cli@latest build --profile development --platform android
```

If EAS asks for an Android keystore, select the option to generate a new one
(or use the keystore already saved for this app in EAS). This is not the Firebase
JSON. Wait for the build to finish, open the build page/link on the Android
phone, and install the generated development APK. Remote push notifications do
not work in Expo Go on Android; installing the development build is required.

#### 6. Start the backend and Metro

In a terminal at the repository root, start the backend (and simulator if
desired):

```powershell
docker compose --profile sim up -d --build
```

In a second terminal, from `SmartCam/`, start Metro for a development build:

```powershell
npx expo start --dev-client
```

Open the installed SmartCam development build on the phone and connect it to
Metro. Grant the notification permission when prompted. The app obtains an Expo
push token and registers it with the backend automatically. If `.env` or native
notification configuration changed, restart Metro; rebuild/reinstall the app
after native configuration changes.

#### 7. Test a new alert

With the API, worker, and (for a simulated camera) `camera-sim` running, generate
a new alert. The backend sends pushes only for alerts newly created after the
device registered its token; existing alerts are not sent retroactively. Check
the phone's notification tray with SmartCam both foregrounded and backgrounded.
The foreground handler displays the notification; the operating system displays
background notifications.

If no push arrives, check in order:

1. SmartCam is the development build, not Expo Go, and notifications are allowed
   in Android system settings.
2. The phone can open `http://<computer-LAN-IP>:8000/docs`.
3. The app's Expo token registration reached the API (check `server-api` logs).
4. EAS has the FCM V1 service-account key for the same Firebase project and
   package ID as the app.
5. The alert is new and the `server-worker`/`server-api` containers are running.

### iOS

iOS also requires an EAS development/production build and a physical device.
Configure an APNs key in the linked EAS project's iOS credentials; creating
that key requires an active Apple Developer Program membership. Build with
`npx --yes eas-cli@latest build --profile development --platform ios`. Expo Go
is not a substitute for testing the app's remote push setup.

### Deployment note

The token-registration endpoint is currently unauthenticated, consistent with
the existing mobile API. Before exposing the backend to untrusted networks, add
user/device authentication and rate limiting. Normal visible pushes are shown
by the operating system while the app is backgrounded; this app does not use a
headless background task.
