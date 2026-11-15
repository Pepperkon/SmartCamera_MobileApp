import { Stack } from "expo-router";
import { PushNotificationsProvider } from "../providers/PushNotificationsProvider";

export default function RootLayout() {
  return (
    <PushNotificationsProvider>
      <Stack screenOptions={{ headerShown: false }} />
    </PushNotificationsProvider>
  );
}
