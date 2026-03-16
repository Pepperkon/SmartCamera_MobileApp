import { COLORS, SPACING } from "@/constants/theme";
import { AlertItem } from "@/constants/types";
import {
  deleteAlert,
  deleteAlertFromCache,
  getAlertsFromCache,
} from "@/services/alertService";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, Image, StyleSheet, Text, View } from "react-native";
import CircleButton from "./circleButton";
import NotificationMark from "./notificationMark";
import { API_URL } from "@/constants/api";

function AlertMax() {
  const router = useRouter();

  const { id } = useLocalSearchParams();
  const [alert, setAlert] = useState<AlertItem | null>(null);
  const [loading, setLoading] = useState(true);

  const handleDelete = async () => {
    if (typeof id == "string") {
      await deleteAlert(id);
      await deleteAlertFromCache(id);
      router.back();
    }
  };

  useEffect(() => {
    const loadAlert = async () => {
      const cachedAlerts = await getAlertsFromCache();
      if (cachedAlerts) {
        const found = cachedAlerts.find((a) => String(a.id) === String(id));
        setAlert(found || null);
      }
      setLoading(false);
    };

    loadAlert();
  }, [id]);

  if (loading) {
    return (
      <ActivityIndicator
        size="large"
        color={COLORS.secondary}
        style={{ flex: 1 }}
      />
    );
  }

  if (!alert) {
    return (
      <View style={styles.container}>
        <Text style={GlobalStyles.text_primary}>Nie znaleziono alertu</Text>
      </View>
    );
  }

  const filepath = `${API_URL}/data/images/captured/${alert.image}`;

  const imageSource =
    typeof alert.image === "string"
      ? { uri: filepath }
      : { uri: "https://ui-avatars.com/api/?name=" + alert.title };

  return (
    <View style={styles.container}>
      <Text style={GlobalStyles.text_primary}>{alert.title}</Text>
      <View style={styles.row_container}>
        <Text style={GlobalStyles.text_secondary}>{alert.time}</Text>
        <Text style={GlobalStyles.text_secondary}>{alert.date}</Text>
      </View>

      <Image source={imageSource} style={styles.image} />

      <View style={styles.button_container}>
        <CircleButton iconName="trash" onPress={handleDelete} />
        <CircleButton iconName="download" />
      </View>

      {alert.isNew && (
        <View style={GlobalStyles.mark}>
          <NotificationMark />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.primary,
    height: "80%",
    width: "95%",
    borderRadius: 20,
    alignItems: "center",
    paddingTop: SPACING.xl,
  },
  button_container: {
    width: "70%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    // padding: 10,
  },
  image: {
    width: 300,
    height: 300,
    borderRadius: 20,
    marginVertical: SPACING.l,
    borderWidth: 9,
    borderColor: COLORS.background,
  },
  row_container: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 10,
    width: "100%",
  },
});

export default AlertMax;
