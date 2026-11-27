import { COLORS, SPACING, TRUST_COLORS } from "@/constants/theme";
import { AlertItem, User, UserMergeResult } from "@/constants/types";
import {
  deleteAlert,
  deleteAlertFromCache,
  fetchAlerts,
  getAlertsFromCache,
  markAsReadOnServer,
  saveAlertsToCache,
} from "@/services/alertService";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  StyleSheet,
  Text,
  View,
  ScrollView,
  Pressable,
} from "react-native";
import CircleButton from "./circleButton";
import NotificationMark from "./notificationMark";
import { API_URL } from "@/constants/api";
import UserMergeModal from "./userMergeModal";

function AlertMax() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [alert, setAlert] = useState<AlertItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [mergeSource, setMergeSource] = useState<User | null>(null);
  const [mergeVisible, setMergeVisible] = useState(false);
  const [suggestionDismissed, setSuggestionDismissed] = useState(false);

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

  const getBoundingBoxColor = () => {
    // Show green box only for recognized, trusted users
    if (alert && alert.recognised_user_id && alert.recognised_user_is_trusted) {
      return TRUST_COLORS.trusted;
    }
    return TRUST_COLORS.untrusted;
  };

  const isTemporaryUser =
      alert?.user?.is_temporary ??
      alert?.recognised_user_is_temporary ??
      true;

  const openMerge = async () => {
    if (!alert?.recognised_user_id) return;
    try {
      const response = await fetch(
        `${API_URL}/users/${alert.recognised_user_id}`,
      );
      if (!response.ok) {
        throw new Error(`Could not load source profile (HTTP ${response.status})`);
      }
      setMergeSource(await response.json());
      setMergeVisible(true);
    } catch (error) {
      console.error("Could not open merge dialog:", error);
      Alert.alert(
        "Error",
        error instanceof Error ? error.message : "Could not load the source profile.",
      );
    }
  };

  const handleMerged = (result: UserMergeResult) => {
      setMergeVisible(false);
      setAlert((current) =>
        current
          ? {
              ...current,
              title: `Recognized: ${result.target_user.name}`,
              recognised_user_id: Number(result.target_user.id),
              recognised_user_is_trusted: result.target_user.is_trusted,
              recognised_user_is_temporary: false,
              user: { is_temporary: false },
            }
          : current,
      );
    };

    const renderConfidence = () => {
      if (!alert) return null;

      if (alert.confidence === -2) {
        return null;
      }

      if (
        alert.confidence === null ||
        alert.confidence === undefined ||
        alert.confidence < 0
      ) {
        return (
          <Text
            style={[
              GlobalStyles.text_secondary,
              { color: "#cbd5e1", marginTop: 5 },
            ]}
          >
            First appearance
          </Text>
        );
      }

      const rounded = Math.round(alert.confidence);
      const label = isTemporaryUser
        ? `Match: ${rounded}%`
        : `Confidence: ${rounded}%`;

      return (
        <Text
          style={[
            GlobalStyles.text_secondary,
            { color: getConfidenceColor(alert.confidence), marginTop: 5 },
          ]}
        >
          {label}
        </Text>
      );
    }
  const [prevId, setPrevId] = useState(id);
    if (id !== prevId) {
      setPrevId(id);
      setLoading(true);
      setSuggestionDismissed(false);
      setMergeSource(null);
      setMergeVisible(false);
    }

  useEffect(() => {
    let active = true;

    const loadAlert = async () => {
      const alertId = Array.isArray(id) ? id[0] : id;
      if (!alertId) {
        if (active) setLoading(false);
        return;
      }

      let alertsList = await getAlertsFromCache();
      let found = alertsList?.find((a) => String(a.id) === String(alertId));

      if (!found) {
        const freshAlerts = await fetchAlerts();
        if (freshAlerts.length > 0) {
          alertsList = freshAlerts;
          await saveAlertsToCache(freshAlerts);
          found = freshAlerts.find((a) => String(a.id) === String(alertId));
        }
      }

      if (!active) return;

      if (found) {
        if (found.isNew) {
          found = { ...found, isNew: false };
          void markAsReadOnServer(String(found.id));
          if (alertsList) {
            const updatedCache = alertsList.map((a) =>
              String(a.id) === String(found!.id) ? { ...a, isNew: false } : a,
            );
            void saveAlertsToCache(updatedCache);
          }
        }

        setAlert(found);

        if (typeof found.image === "string") {
          const uri = `${API_URL}/data/images/captured/${found.image}`;
          Image.getSize(
            uri,
            (width, height) => {
              if (active) {
                setImgDimensions({ width, height });
              }
            },
            (error) => {
              console.error("Error retrieving photo size:", error);
            },
          );
        }
      } else {
        setAlert(null);
      }

      setLoading(false);
    };

    void loadAlert();

    return () => {
      active = false;
    };
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
      borderColor: getBoundingBoxColor(),
    };

    return <View style={[styles.boundingBox, boxStyle]} />;
  };

  const containerAspectRatio =
    imgDimensions && imgDimensions.height > 0
      ? imgDimensions.width / imgDimensions.height
      : 16 / 9;

  return (
    <View style={styles.mainWrapper}>
      {alert.isNew && (
        <View style={GlobalStyles.mark}>
          <NotificationMark />
        </View>
      )}
      <ScrollView
        style={[
          styles.scrollContainer,
          {
            borderLeftWidth: 4,
            borderLeftColor: getBoundingBoxColor(),
          },
        ]}
        contentContainerStyle={{ alignItems: "center" }}
        showsVerticalScrollIndicator={false}
      >
        <Text style={GlobalStyles.text_primary}>{prefix}</Text>
        <Text style={GlobalStyles.text_primary}>{name}</Text>
        <View style={styles.row_container}>
          <Text style={GlobalStyles.text_secondary}>{alert.time}</Text>
          <Text style={GlobalStyles.text_secondary}>{alert.date}</Text>
        </View>

        {renderConfidence()}

        <View
          style={[
            styles.imageWrapper,
            { aspectRatio: containerAspectRatio },
          ]}
        >
          <Image
            source={imageSource}
            style={styles.image}
            resizeMode="contain"
          />
          {renderBoundingBox()}
        </View>

        {isTemporaryUser && alert.recognised_user_id != null && (
          <View style={styles.mergeSection}>
            {alert.suggested_match && !suggestionDismissed && (
              <View style={styles.suggestion}>
                {alert.suggested_match.avatar_url && (
                  <Image
                    source={{
                      uri: alert.suggested_match.avatar_url.startsWith("http")
                        ? alert.suggested_match.avatar_url
                        : `${API_URL}${alert.suggested_match.avatar_url}`,
                    }}
                    style={styles.suggestionAvatar}
                  />
                )}
                <View style={styles.suggestionText}>
                  <Text style={styles.suggestionTitle}>
                    Podobny do: {alert.suggested_match.name} • profil #
                    {alert.suggested_match.user_id}
                  </Text>
                  <Text style={styles.suggestionDetail}>
                    Potwierdź, czy to ta sama osoba
                  </Text>
                </View>
                <Pressable onPress={() => void openMerge()}>
                  <Text style={styles.suggestionAction}>Tak, połącz</Text>
                </Pressable>
                <Pressable onPress={() => setSuggestionDismissed(true)}>
                  <Text style={styles.suggestionAction}>Nie</Text>
                </Pressable>
              </View>
            )}
            {(suggestionDismissed || !alert.suggested_match) && (
              <Pressable
                style={styles.mergeButton}
                onPress={() => void openMerge()}
              >
                <Text style={styles.mergeButtonText}>
                  Przypisz do użytkownika
                </Text>
              </Pressable>
            )}
          </View>
        )}

        <View style={styles.button_container}>
          <CircleButton iconName="delete" onPress={handleDelete} />
          <CircleButton iconName="download" />
        </View>
      </ScrollView>
      {mergeSource && (
        <UserMergeModal
          visible={mergeVisible}
          source={mergeSource}
          detectionConfidence={alert.detection_confidence}
          suggestedUserId={alert.suggested_match?.user_id}
          onClose={() => setMergeVisible(false)}
          onMerged={handleMerged}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  mainWrapper: {
    flex: 1,
    width: "95%",
    position: "relative",
    overflow: "visible",
  },
  container: {
    flex: 1,
    backgroundColor: COLORS.primary,
    height: "100%",
    width: "95%",
    borderRadius: 20,
    alignItems: "center",
    paddingTop: SPACING.xl,
  },
  scrollContainer: {
    flex: 1,
    backgroundColor: COLORS.primary,
    borderRadius: 20,
  },
  contentContainer: {
    flexGrow: 1,
    alignItems: "center",
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.xl,
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
  mergeSection: {
    width: "92%",
    marginBottom: SPACING.m,
  },
  suggestion: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 8,
    padding: 10,
    borderRadius: 12,
    backgroundColor: "#1e293b",
  },
  suggestionAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
  },
  suggestionText: {
    flex: 1,
  },
  suggestionTitle: {
    color: "#fff",
    fontWeight: "600",
  },
  suggestionDetail: {
    color: "#cbd5e1",
    fontSize: 12,
  },
  suggestionAction: {
    color: "#93c5fd",
    fontWeight: "700",
    padding: 5,
  },
  mergeButton: {
    padding: 12,
    alignItems: "center",
    borderRadius: 10,
    backgroundColor: "#254e6b",
  },
  mergeButtonText: {
    color: "#fff",
    fontWeight: "700",
  },
});

export default AlertMax;
