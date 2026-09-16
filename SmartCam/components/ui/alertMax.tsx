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

  const [imgDimensions, setImgDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const handleDelete = async () => {
    if (typeof id === "string") {
      await deleteAlert(id);
      await deleteAlertFromCache(id);
      router.back();
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) {
      return "#4ade80";
    }
    if (confidence >= 50) {
      return "#facc15";
    }
    return "#f87171";
  };

  // TODO: Refactor color logic to rely on user.is_trusted instead of title.
  // Currently, any non-temporary recognized face gets green, even if marked untrusted.
  // Blocked by: backend API needs to expose is_trusted in the alert.
  const getBoundingBoxColor = (title: string) => {
    if (title.startsWith("Recognized:")) {
      return "#4ade80";
    }
    return "#f87171";
  };

  useEffect(() => {
    const loadAlert = async () => {
      const cachedAlerts = await getAlertsFromCache();
      if (cachedAlerts) {
        const found = cachedAlerts.find((a) => String(a.id) === String(id));
        setAlert(found || null);

        if (found && typeof found.image === "string") {
          const uri = `${API_URL}/data/images/captured/${found.image}`;
          Image.getSize(
            uri,
            (width, height) => {
              setImgDimensions({ width, height });
            },
            (error) => {
              console.error("Error retrieving photo size:", error);
            }
          );
        }
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
        <Text style={GlobalStyles.text_primary}>Alert not found</Text>
      </View>
    );
  }

  const filepath = `${API_URL}/data/images/captured/${alert.image}`;
  const imageSource =
    typeof alert.image === "string"
      ? { uri: filepath }
      : { uri: "https://ui-avatars.com/api/?name=" + alert.title };

  const [prefix, name] = alert.title ? alert.title.split(": ") : ["", ""];

  const renderBoundingBox = () => {
      if (!alert.location || alert.location.length !== 4 || !imgDimensions) {
        return null;
      }

      const [rawTop, rawRight, rawBottom, rawLeft] = alert.location;
      const { width: origW, height: origH } = imgDimensions;

      const faceWidth = rawRight - rawLeft;
      const faceHeight = rawBottom - rawTop;

      const padX = faceWidth * 0.2;
      const padY = faceHeight * 0.2;

      const top = Math.max(0, rawTop - padY);
      const bottom = Math.min(origH, rawBottom + padY);
      const left = Math.max(0, rawLeft - padX);
      const right = Math.min(origW, rawRight + padX);

      const boxStyle = {
        top: `${(top / origH) * 100}%` as const,
        left: `${(left / origW) * 100}%` as const,
        width: `${((right - left) / origW) * 100}%` as const,
        height: `${((bottom - top) / origH) * 100}%` as const,
        borderColor: getBoundingBoxColor(alert.title),
      };

      return <View style={[styles.boundingBox, boxStyle]} />;
    };

  const containerAspectRatio =
    imgDimensions && imgDimensions.height > 0
      ? imgDimensions.width / imgDimensions.height
      : 16 / 9;

  return (
    <View style={styles.container}>
      <Text style={GlobalStyles.text_primary}>{prefix}</Text>
      <Text style={GlobalStyles.text_primary}>{name}</Text>
      <View style={styles.row_container}>
        <Text style={GlobalStyles.text_secondary}>{alert.time}</Text>
        <Text style={GlobalStyles.text_secondary}>{alert.date}</Text>
      </View>

      <Text
        style={[
          GlobalStyles.text_secondary,
          { color: getConfidenceColor(alert.confidence), marginTop: 5 },
        ]}
      >
        Confidence: {Math.round(alert.confidence)}%
      </Text>

      <View style={[styles.imageWrapper, { aspectRatio: containerAspectRatio }]}>
        <Image
          source={imageSource}
          style={styles.image}
          resizeMode="stretch"
        />
        {renderBoundingBox()}
      </View>

      <View style={styles.button_container}>
        <CircleButton iconName="delete" onPress={handleDelete} />
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
  },
  imageWrapper: {
    width: 320,
    borderRadius: 20,
    marginVertical: SPACING.l,
    overflow: "hidden",
    borderWidth: 6,
    borderColor: COLORS.background,
    position: "relative",
  },
  image: {
    width: "100%",
    height: "100%",
  },
  boundingBox: {
    position: "absolute",
    borderWidth: 3,
    borderRadius: 4,
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
