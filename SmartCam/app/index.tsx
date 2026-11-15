import { Pressable, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import MainButton from "@/components/ui/main-button";
import { COLORS } from "@/constants/theme";

export default function HomeScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <Pressable
        style={styles.settingsButton}
        onPress={() => router.push("/settings")}
        accessibilityLabel="Settings"
      >
        <Ionicons name="settings-outline" size={24} color="#FFFFFF" />
      </Pressable>

      <MainButton
        iconName="camera"
        onPress={() => router.push("/alerts-view")}
      />
      <MainButton
        iconName="home"
        onPress={() => router.push("/household-view")}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: COLORS.background,
  },
  settingsButton: {
    position: "absolute",
    top: 48,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.secondary,
    justifyContent: "center",
    alignItems: "center",
  },
});
