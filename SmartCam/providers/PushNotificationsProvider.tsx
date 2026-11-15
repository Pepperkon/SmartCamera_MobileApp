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
import * as Notifications from "expo-notifications";
import { API_URL } from "@/constants/api";

type PushContextValue = {
  expoPushToken: string | null;
  lastNotification: Notifications.Notification | null;
  error: string | null;
};

const PushContext = createContext<PushContextValue | undefined>(undefined);

Notifications.setNotificationHandler({
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
    throw new Error("Powiadomienia push są obsługiwane tylko na Androidzie i iOS.");
  }
  if (!Device.isDevice) {
    throw new Error("Do testowania pushy użyj fizycznego urządzenia.");
  }

  // Android 13+ wymaga kanału przed uzyskaniem tokenu i prośbą o uprawnienia.
  if (platform === "android") {
    await Notifications.setNotificationChannelAsync("alerts", {
      name: "Alerty",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#FF231F7C",
    });
  }

  const current = await Notifications.getPermissionsAsync();
  let status = current.status;

  if (status !== "granted") {
    status = (await Notifications.requestPermissionsAsync()).status;
  }
  if (status !== "granted") {
    throw new Error("Użytkownik nie udzielił uprawnień do powiadomień.");
  }

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ??
    Constants.easConfig?.projectId;

  if (!projectId) {
    throw new Error(
      "Brak EAS projectId. Uruchom `eas init` i skonfiguruj app.json.",
    );
  }

  return {
    token: (await Notifications.getExpoPushTokenAsync({ projectId })).data,
    platform,
  };
}

async function savePushTokenOnServer(
  token: string,
  platform: "android" | "ios",
): Promise<void> {
  const response = await fetch(`${API_URL}/push-tokens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, platform }),
  });

  if (!response.ok) {
    throw new Error(`Serwer nie zapisał tokenu push (HTTP ${response.status}).`);
  }
}

export function PushNotificationsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [lastNotification, setLastNotification] =
    useState<Notifications.Notification | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    // Odbiera powiadomienie, gdy aplikacja jest otwarta.
    const received =
      Notifications.addNotificationReceivedListener(setLastNotification);

    // Uruchamia się, gdy użytkownik kliknie powiadomienie, także po powrocie
    // z tła lub uruchomieniu zamkniętej aplikacji.
    const response = Notifications.addNotificationResponseReceivedListener(
      ({ notification }) => setLastNotification(notification),
    );

    registerForPushNotifications()
      .then(async ({ token, platform }) => {
        if (mounted) setExpoPushToken(token);
        await savePushTokenOnServer(token, platform);
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
  }, []);

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
      "usePushNotifications musi być użyte wewnątrz PushNotificationsProvider.",
    );
  }
  return context;
}
