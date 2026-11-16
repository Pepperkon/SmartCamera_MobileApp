import { Stack } from "expo-router";
import { PushNotificationsProvider } from "../providers/PushNotificationsProvider";
import { ServerProvider } from "../providers/ServerProvider";

export default function RootLayout() {
  return (
    <ServerProvider>
      <PushNotificationsProvider>
        <Stack screenOptions={{ headerShown: false }} />
      </PushNotificationsProvider>
    </ServerProvider>
  );
}
