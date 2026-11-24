import { API_URL } from "@/constants/api";
import { COLORS, SPACING } from "@/constants/theme";
import { User, UserMergeResult } from "@/constants/types";
import { updateAlertsAfterMerge } from "@/services/alertService";
import {
  deleteUserFromCache,
  fetchPermanentUsers,
  mergeUsers,
} from "@/services/userService";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Modal,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

interface Props {
  visible: boolean;
  source: User;
  detectionConfidence?: number | null;
  suggestedUserId?: number;
  onClose: () => void;
  onMerged: (result: UserMergeResult) => void;
}

function UserIdentity({ user, compact = false }: { user: User; compact?: boolean }) {
  const displayName = user.is_temporary ? `Stranger #${user.id}` : user.name;
  const firstImage = user.images?.[0];
  return (
    <View style={[styles.identity, compact && styles.compactIdentity]}>
      {firstImage ? (
        <Image
          source={{
            uri: `${API_URL}/data/images/users/${user.id}/${firstImage.filepath}`,
          }}
          style={styles.avatar}
        />
      ) : (
        <View style={[styles.avatar, styles.avatarFallback]}>
          <Text style={styles.avatarInitial}>{displayName.charAt(0)}</Text>
        </View>
      )}
      <View style={styles.identityText}>
        <Text style={styles.name} numberOfLines={1}>
          {displayName}{" "}
          <Text style={styles.badge}>
            {user.is_temporary ? "Tymczasowy" : "Stały"}
          </Text>
        </Text>
        <Text style={styles.detail}>
          ID: {user.id} • {user.images?.length ?? 0} wzorców
        </Text>
      </View>
    </View>
  );
}

function UserMergeModal({
  visible,
  source,
  detectionConfidence,
  suggestedUserId,
  onClose,
  onMerged,
}: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [search, setSearch] = useState("");
  const [includeTemplates, setIncludeTemplates] = useState(
    detectionConfidence == null || detectionConfidence >= 0.82,
  );
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    let active = true;
    setLoading(true);
    setSelectedUser(null);
    setSearch("");
    setConfirming(false);
    setIncludeTemplates(
      detectionConfidence == null || detectionConfidence >= 0.82,
    );
    setLoadError(null);
    void fetchPermanentUsers()
      .then((result) => {
        if (active) setUsers(result.filter((user) => !user.is_temporary));
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(
            error instanceof Error ? error.message : "Nie udało się pobrać profili.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [visible, detectionConfidence]);

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return users
      .filter((user) => String(user.id) !== String(source.id))
      .filter(
        (user) =>
          !query ||
          user.name.toLocaleLowerCase().includes(query) ||
          String(user.id).includes(query),
      )
      .sort((left, right) => {
        if (String(left.id) === String(suggestedUserId)) return -1;
        if (String(right.id) === String(suggestedUserId)) return 1;
        return left.name.localeCompare(right.name);
      });
  }, [search, source.id, suggestedUserId, users]);

  const handleMerge = async () => {
    if (!selectedUser) return;
    setSaving(true);
    try {
      const result = await mergeUsers(
        source.id,
        selectedUser.id,
        includeTemplates,
      );
      await deleteUserFromCache(String(source.id));
      await updateAlertsAfterMerge(source.id, result.target_user);
      onMerged(result);
      Alert.alert(
        result.warnings?.length
          ? "Profile merged with warnings"
          : "Profile merged",
        [
          `Przeniesiono ${result.moved_alerts} alertów i dodano ${result.added_templates} wzorców.`,
          ...(result.warnings ?? []),
        ].join("\n\n"),
      );
    } catch (error) {
      console.error("Failed to merge users:", error);
      Alert.alert(
        "Merge failed",
        error instanceof Error ? error.message : "Nie udało się połączyć profili.",
      );
    } finally {
      setSaving(false);
    }
  };

  const renderUser = ({ item }: { item: User }) => (
    <Pressable
      style={[
        styles.userRow,
        selectedUser?.id === item.id && styles.selectedRow,
      ]}
      onPress={() => setSelectedUser(item)}
    >
      <UserIdentity user={item} compact />
      {String(item.id) === String(suggestedUserId) && (
        <Text style={styles.suggestedTag}>Najbardziej prawdopodobny</Text>
      )}
    </Pressable>
  );

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.modal}>
          <Text style={styles.title}>
            {confirming ? "Potwierdź połączenie" : "Wybierz profil docelowy"}
          </Text>

          {!confirming ? (
            <>
              <Text style={styles.subtitle}>Źródło zostanie usunięte:</Text>
              <UserIdentity user={source} compact />
              <TextInput
                value={search}
                onChangeText={setSearch}
                placeholder="Szukaj po nazwie lub ID"
                placeholderTextColor="#718096"
                style={styles.search}
              />
              {loading ? (
                <ActivityIndicator color={COLORS.secondary} />
              ) : loadError ? (
                <Text style={styles.error}>{loadError}</Text>
              ) : filteredUsers.length === 0 ? (
                <Text style={styles.subtitle}>Nie znaleziono stałych profili.</Text>
              ) : (
                <>
                  {suggestedUserId && !search.trim() && (
                    <Text style={styles.sectionTitle}>Najbardziej prawdopodobny</Text>
                  )}
                  <FlatList
                    data={filteredUsers}
                    keyExtractor={(item) => String(item.id)}
                    renderItem={renderUser}
                    style={styles.userList}
                    keyboardShouldPersistTaps="handled"
                  />
                </>
              )}
              <View style={styles.actions}>
                <ActionButton label="Anuluj" onPress={onClose} />
                <ActionButton
                  label="Dalej"
                  disabled={!selectedUser}
                  onPress={() => setConfirming(true)}
                />
              </View>
            </>
          ) : selectedUser ? (
            <>
              <View style={styles.direction}>
                <View style={styles.directionCard}>
                  <Text style={styles.role}>Źródło • zostanie usunięte</Text>
                  <UserIdentity user={source} />
                  <Text style={styles.detail}>
                    Przeniesie: {source.alerts?.length ?? 0} alertów
                  </Text>
                </View>
                <Text style={styles.arrow}>→</Text>
                <View style={styles.directionCard}>
                  <Text style={styles.role}>Cel • zostanie zachowany</Text>
                  <UserIdentity user={selectedUser} />
                  <Text style={styles.detail}>Docelowy profil</Text>
                </View>
              </View>
              <View style={styles.templateOption}>
                <View style={styles.templateText}>
                  <Text style={styles.name}>
                    Dodaj zdjęcia do wzorców rozpoznawania
                  </Text>
                  {detectionConfidence != null && detectionConfidence < 0.82 && (
                    <Text style={styles.warning}>
                      Zdjęcie słabszej jakości — zalecamy przeniesienie samej historii.
                    </Text>
                  )}
                </View>
                <Switch
                  value={includeTemplates}
                  onValueChange={setIncludeTemplates}
                  disabled={saving}
                />
              </View>
              <View style={styles.actions}>
                <ActionButton
                  label="Wróć"
                  disabled={saving}
                  onPress={() => setConfirming(false)}
                />
                <ActionButton
                  label={saving ? "Łączenie..." : "Połącz profile"}
                  disabled={saving}
                  onPress={() => void handleMerge()}
                />
              </View>
              {saving && <ActivityIndicator color={COLORS.secondary} />}
            </>
          ) : null}
        </View>
      </View>
    </Modal>
  );
}

function ActionButton({
  label,
  onPress,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      style={[styles.actionButton, disabled && styles.disabledButton]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={styles.actionText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: "center",
    padding: SPACING.m,
    backgroundColor: "rgba(0,0,0,0.65)",
  },
  modal: {
    maxHeight: "90%",
    padding: SPACING.m,
    borderRadius: 18,
    backgroundColor: COLORS.primary,
  },
  title: {
    color: "#fff",
    fontSize: 21,
    fontWeight: "700",
    marginBottom: SPACING.s,
  },
  subtitle: {
    color: "#cbd5e1",
    marginBottom: SPACING.s,
  },
  identity: {
    flex: 1,
    alignItems: "center",
    gap: 7,
  },
  compactIdentity: {
    flexDirection: "row",
    justifyContent: "flex-start",
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "#334155",
  },
  avatarFallback: {
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "700",
  },
  identityText: {
    flexShrink: 1,
    gap: 4,
  },
  name: {
    color: "#fff",
    fontWeight: "600",
  },
  badge: {
    color: "#86efac",
    fontSize: 12,
  },
  detail: {
    color: "#cbd5e1",
    fontSize: 12,
  },
  search: {
    backgroundColor: "#fff",
    borderRadius: 10,
    color: "#172033",
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginVertical: SPACING.s,
  },
  sectionTitle: {
    color: "#93c5fd",
    fontWeight: "700",
    marginBottom: 4,
  },
  userList: {
    maxHeight: 300,
  },
  userRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 8,
    marginBottom: 4,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#475569",
  },
  selectedRow: {
    borderColor: "#60a5fa",
    backgroundColor: "#1e3a5f",
  },
  suggestedTag: {
    color: "#93c5fd",
    fontSize: 11,
    marginLeft: 6,
  },
  direction: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 5,
    marginVertical: SPACING.m,
  },
  directionCard: {
    flex: 1,
    alignItems: "center",
    padding: 7,
    gap: 8,
    borderRadius: 12,
    backgroundColor: "#1e293b",
  },
  role: {
    minHeight: 32,
    color: "#cbd5e1",
    fontSize: 11,
    textAlign: "center",
  },
  arrow: {
    color: "#fff",
    fontSize: 24,
  },
  templateOption: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.s,
    paddingVertical: SPACING.s,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: "#475569",
  },
  templateText: {
    flex: 1,
    gap: 5,
  },
  warning: {
    color: "#fbbf24",
    fontSize: 12,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: SPACING.s,
    marginTop: SPACING.m,
  },
  actionButton: {
    minWidth: 100,
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: COLORS.secondary,
  },
  disabledButton: {
    opacity: 0.45,
  },
  actionText: {
    color: "#fff",
    fontWeight: "700",
  },
  error: {
    color: "#fca5a5",
    marginVertical: SPACING.s,
  },
});

export default UserMergeModal;
