import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Device from "expo-device";
import {
  AndroidImportance,
  addNotificationReceivedListener,
  addNotificationResponseReceivedListener,
  getExpoPushTokenAsync,
  getPermissionsAsync,
  requestPermissionsAsync,
  setNotificationChannelAsync,
  setNotificationHandler,
  type Notification,
} from "expo-notifications";
import { useServer } from "./ServerProvider";

type PushContextValue = {
  expoPushToken: string | null;
  lastNotification: Notification | null;
  error: string | null;
};

const PushContext = createContext<PushContextValue | undefined>(undefined);

setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

async function registerForPushNotifications(): Promise<{
  token: string;
  platform: "android" | "ios";
}> {
  const platform = Platform.OS;
  if (platform !== "android" && platform !== "ios") {
    throw new Error("Push notifications are only supported on Android and iOS.");
  }
  if (!Device.isDevice) {
    throw new Error("Use a physical device to test push notifications.");
  }

  // Android 13+ wymaga kanału przed uzyskaniem tokenu i prośbą o uprawnienia.
  if (platform === "android") {
    await setNotificationChannelAsync("alerts", {
      name: "Alerts",
      importance: AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#FF231F7C",
    });
  }

  const current = await getPermissionsAsync();
  let status = current.status;

  if (status !== "granted") {
    status = (await requestPermissionsAsync()).status;
  }
  if (status !== "granted") {
    throw new Error("Notification permissions were not granted.");
  }

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ??
    Constants.easConfig?.projectId;

  if (!projectId) {
    throw new Error(
      "Missing EAS projectId. Run `eas init` and configure app.json.",
    );
  }

  return {
    token: (await getExpoPushTokenAsync({ projectId })).data,
    platform,
  };
}

async function savePushTokenOnServer(
  token: string,
  platform: "android" | "ios",
  apiUrl: string,
): Promise<void> {
  const response = await fetch(`${apiUrl}/push-tokens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, platform }),
  });

  if (!response.ok) {
    throw new Error(`Server failed to save push token (HTTP ${response.status}).`);
  }
}

export function PushNotificationsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { apiUrl } = useServer();
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [lastNotification, setLastNotification] =
    useState<Notification | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    // Odbiera powiadomienie, gdy aplikacja jest otwarta.
    const received = addNotificationReceivedListener(setLastNotification);

    // Uruchamia się, gdy użytkownik kliknie powiadomienie, także po powrocie
    // z tła lub uruchomieniu zamkniętej aplikacji.
    const response = addNotificationResponseReceivedListener(
      ({ notification }) => setLastNotification(notification),
    );

    registerForPushNotifications()
      .then(async ({ token, platform }) => {
        if (mounted) setExpoPushToken(token);
        await savePushTokenOnServer(token, platform, apiUrl);
        if (mounted) setError(null);
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      });

    return () => {
      mounted = false;
      received.remove();
      response.remove();
    };
  }, [apiUrl]);

  return (
    <PushContext.Provider value={{ expoPushToken, lastNotification, error }}>
      {children}
    </PushContext.Provider>
  );
}

export function usePushNotifications() {
  const context = useContext(PushContext);
  if (!context) {
    throw new Error(
      "usePushNotifications must be used within PushNotificationsProvider.",
    );
  }
  return context;
}
