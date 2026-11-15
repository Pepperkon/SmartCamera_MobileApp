import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { DEFAULT_SERVER_IP } from "@/constants/api";
import { COLORS, ROUNDING, SPACING } from "@/constants/theme";
import { useServer } from "@/providers/ServerProvider";

export default function SettingsScreen() {
  const router = useRouter();
  const { serverIp, updateServerIp, testServerConnection } = useServer();

  const [inputIp, setInputIp] = useState(serverIp);
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(
    null,
  );

  const handleTest = async () => {
    setTesting(true);
    setStatus(null);
    const result = await testServerConnection(inputIp);
    setStatus(result);
    setTesting(false);
  };

  const handleSave = async () => {
    const saved = await updateServerIp(inputIp);
    setInputIp(saved);
    setStatus({
      ok: true,
      message: `Server IP saved (${saved})`,
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Pressable
          style={styles.backButton}
          onPress={() => router.back()}
          accessibilityLabel="Back"
        >
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </Pressable>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Section: Server Connection */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="server-outline" size={20} color="#FFFFFF" />
            <Text style={styles.sectionTitle}>Server Connection</Text>
          </View>

          <Text style={styles.sectionDescription}>
            Enter local network IP (e.g., 192.168.0.59) or Tailscale IP
            (e.g., 100.125.98.10):
          </Text>

          <TextInput
            style={styles.input}
            value={inputIp}
            onChangeText={(text) => {
              setInputIp(text);
              setStatus(null);
            }}
            placeholder={DEFAULT_SERVER_IP}
            placeholderTextColor="#8FA3B8"
            autoCapitalize="none"
            autoCorrect={false}
          />

          {status && (
            <View
              style={[
                styles.statusBox,
                status.ok ? styles.statusSuccess : styles.statusError,
              ]}
            >
              <Text style={styles.statusText}>{status.message}</Text>
            </View>
          )}

          <View style={styles.buttonRow}>
            <Pressable
              style={[styles.actionBtn, styles.testBtn]}
              onPress={handleTest}
              disabled={testing}
            >
              {testing ? (
                <ActivityIndicator color="#FFFFFF" size="small" />
              ) : (
                <Text style={styles.btnText}>Test</Text>
              )}
            </Pressable>

            <Pressable
              style={[styles.actionBtn, styles.saveBtn]}
              onPress={handleSave}
            >
              <Text style={styles.btnText}>Save</Text>
            </Pressable>
          </View>
        </View>

        {/* Placeholder for future settings sections (e.g., Notifications, Camera, Appearance) */}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: SPACING.m,
    paddingVertical: SPACING.m,
    gap: SPACING.m,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.secondary,
    justifyContent: "center",
    alignItems: "center",
  },
  headerTitle: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "700",
  },
  scrollContent: {
    padding: SPACING.m,
    gap: SPACING.m,
  },
  sectionCard: {
    backgroundColor: COLORS.secondary,
    borderRadius: ROUNDING.medium,
    padding: SPACING.l,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.s,
    marginBottom: SPACING.xs,
  },
  sectionTitle: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },
  sectionDescription: {
    color: "#CBD5E1",
    fontSize: 13,
    marginBottom: SPACING.m,
  },
  input: {
    backgroundColor: "#13364F",
    color: "#FFFFFF",
    borderRadius: ROUNDING.small,
    paddingHorizontal: SPACING.m,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: SPACING.m,
  },
  statusBox: {
    padding: SPACING.s,
    borderRadius: ROUNDING.small,
    marginBottom: SPACING.m,
  },
  statusSuccess: {
    backgroundColor: "rgba(22, 163, 74, 0.25)",
  },
  statusError: {
    backgroundColor: "rgba(220, 38, 38, 0.25)",
  },
  statusText: {
    color: "#FFFFFF",
    fontSize: 13,
  },
  buttonRow: {
    flexDirection: "row",
    gap: SPACING.s,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: ROUNDING.small,
    alignItems: "center",
  },
  testBtn: {
    backgroundColor: "#254E6B",
  },
  saveBtn: {
    backgroundColor: COLORS.primary,
  },
  btnText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
  },
});
