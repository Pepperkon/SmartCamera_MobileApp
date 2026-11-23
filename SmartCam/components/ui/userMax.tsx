import {
  View,
  Text,
  Image,
  ActivityIndicator,
  Modal,
  Pressable,
  FlatList,
  Dimensions,
  StyleSheet,
  Alert,
  TextInput,
} from "react-native";
import React, { useCallback, useState } from "react";
import { COLORS, SPACING, TRUST_COLORS } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import {
  deleteUser,
  deleteUserFromCache,
  saveTemporaryUser,
  updateUserName,
  updateUserTrust,
} from "@/services/userService";
import { User } from "@/constants/types";
import { API_URL } from "@/constants/api";
import CircleButton from "./circleButton";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

function UserMax() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGalleryVisble, setGalleryVisible] = useState(false);
  const [isNameEditorVisible, setNameEditorVisible] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [isSavingName, setSavingName] = useState(false);

  const handleDelete = (userName: string) => {
    Alert.alert(
      "Removing User",
      `Are you sure you want to remove user ${userName}?`,
      [
        {
          text: "Cancel",
          style: "cancel",
        },
        {
          text: "Remove",
          style: "destructive",
          onPress: async () => {
            if (typeof id === "string") {
              await deleteUser(id);
              await deleteUserFromCache(id);
              router.back();
            }
          },
        },
      ],
    );
  };

  const addImage = () => {
    router.push({ pathname: "/add-image", params: { id: id } });
  };

  const openNameEditor = () => {
    if (!user) return;
    setEditedName(user.name);
    setNameEditorVisible(true);
  };

  const handleSaveName = async () => {
      if (!user) return;

      const newName = editedName.trim();
      if (!newName) {
        Alert.alert("Invalid name", "Name cannot be empty.");
        return;
      }

      if (newName === user.name) {
        setNameEditorVisible(false);
        return;
      }

      setSavingName(true);
      try {
        await updateUserName(user.id, newName);
        setUser((prev) => (prev ? { ...prev, name: newName } : prev));
        setNameEditorVisible(false);
      } catch (error) {
        console.error("Failed to update user name:", error);
        Alert.alert("Error", "Could not update the user's name.");
      } finally {
        setSavingName(false);
      }
    };

    const handleToggleTrust = async () => {
      if (!user) return;

      const newStatus = !user.is_trusted;

      try {
        const data = await updateUserTrust(user.id, newStatus);

        setUser((prev) =>
          prev
            ? {
                ...prev,
                is_trusted: data.is_trusted,
                is_temporary: data.is_temporary,
              }
            : prev,
        );

        Alert.alert(
          "Trust status updated",
          data.is_trusted
            ? `${user.name} is now a trusted user.`
            : `${user.name} is now an untrusted user.`,
        );
      } catch (error) {
        console.error("Failed to update user trust status:", error);
        Alert.alert("Error", "Could not update user trust status.");
      }
    };

    const handleSetPermanent = async () => {
      if (!user || !user.is_temporary) return;

      try {
        await saveTemporaryUser(user.id, user.name);
        setUser((prev) => (prev ? { ...prev, is_temporary: false } : prev));
        Alert.alert("User updated", `${user.name} is now permanent.`);
      } catch (error) {
        console.error("Failed to save temporary user:", error);
        Alert.alert("Error", "Could not set the user as permanent.");
      }
    };

  useFocusEffect(
    useCallback(() => {
      const loadUser = async () => {
        try {
          const response = await fetch(`${API_URL}/users/${id}`);
          if (response.ok) {
            const freshUser = await response.json();
            setUser(freshUser);
          }
        } catch (error) {
          console.error("Błąd pobierania użytkownika:", error);
        } finally {
          setLoading(false);
        }
      };

      loadUser();
    }, [id]),
  );

  if (loading) {
    return (
      <ActivityIndicator
        size="large"
        color={COLORS.secondary}
        style={{ flex: 1 }}
      />
    );
  }

  if (!user) {
    return (
      <View style={styles.container}>
        <Text style={GlobalStyles.text_primary}>User not found</Text>
      </View>
    );
  }
  const filepath = `${API_URL}/data/images/users/${user.id}/${user.images[0].filepath}`;
  const imageSource = typeof user.images[0]
    ? { uri: filepath }
    : { uri: "https://ui-avatars.com/api/?name=" + user.name };

  return (
    <View
      style={[
        styles.container,
        {
          borderLeftWidth: 4,
          borderLeftColor: user.is_trusted
            ? TRUST_COLORS.trusted
            : TRUST_COLORS.untrusted,
        },
      ]}
    >
      <Pressable onPress={openNameEditor} accessibilityRole="button">
        <Text style={GlobalStyles.text_primary}>{user.name}</Text>
      </Pressable>
      <Pressable onPress={() => setGalleryVisible(true)}>
        <Image source={imageSource} style={styles.image} />
      </Pressable>

      <View style={styles.button_container}>
        <CircleButton
          iconName="delete"
          onPress={() => handleDelete(user.name)}
        />
        <CircleButton iconName="plus" onPress={addImage} />
        <CircleButton iconName="download" />
      </View>

      <View style={styles.action_buttons_container}>
        {user.is_temporary && (
          <Pressable
            style={({ pressed }) => [
              styles.action_button,
              styles.permanent_button,
              pressed && GlobalStyles.pressed,
            ]}
            onPress={handleSetPermanent}
          >
            <Text style={styles.action_button_text}>Set as permanent</Text>
          </Pressable>
        )}
        <Pressable
          style={({ pressed }) => [
            styles.action_button,
            user.is_trusted ? styles.untrust_button : styles.trust_button,
            pressed && GlobalStyles.pressed,
          ]}
          onPress={handleToggleTrust}
        >
          <Text style={styles.action_button_text}>
            {user.is_trusted ? "Remove trust" : "Trust user"}
          </Text>
        </Pressable>
      </View>

      <Modal visible={isGalleryVisble} transparent={true} animationType="fade">
        <View style={styles.modalContainer}>
          <FlatList
            data={user.images}
            horizontal
            pagingEnabled
            extraData={user}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <View style={styles.fullScreenImageContainer}>
                <Pressable onPress={() => setGalleryVisible(false)}>
                  <Image
                    source={{
                      uri: `${API_URL}/data/images/users/${user.id}/${item.filepath}`,
                    }}
                    style={styles.fullScreenImage}
                    resizeMode="contain"
                  />
                </Pressable>
              </View>
            )}
          />
        </View>
      </Modal>
      <Modal
        visible={isNameEditorVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setNameEditorVisible(false)}
      >
        <View style={styles.name_modal_backdrop}>
          <View style={styles.name_modal}>
            <Text style={GlobalStyles.text_secondary}>Change name</Text>
            <TextInput
              style={styles.name_input}
              value={editedName}
              onChangeText={setEditedName}
              autoFocus
              autoCapitalize="words"
              returnKeyType="done"
              onSubmitEditing={() => void handleSaveName()}
              editable={!isSavingName}
            />
            <View style={styles.name_modal_buttons}>
              <Pressable
                style={[styles.name_modal_button, styles.cancel_button]}
                onPress={() => setNameEditorVisible(false)}
                disabled={isSavingName}
              >
                <Text style={styles.name_modal_button_text}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[styles.name_modal_button, styles.save_button]}
                onPress={() => void handleSaveName()}
                disabled={isSavingName}
              >
                <Text style={styles.name_modal_button_text}>
                  {isSavingName ? "Saving..." : "Save"}
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.primary,
    width: "95%",
    borderRadius: 20,
    alignItems: "center",
    paddingTop: SPACING.xl,
  },
  button_container: {
    width: "90%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    marginTop: 10,
  },
  permanent_action_container: {
    width: "90%",
  },
  action_button: {
    flex: 1,
    minHeight: 56,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: SPACING.s,
    paddingVertical: SPACING.s,
    borderRadius: 15,
  },
  permanent_button_text: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "600",
    textAlign: "center",
    flexShrink: 1,
  },
  image: {
    width: 300,
    height: 300,
    borderRadius: 20,
    marginVertical: SPACING.l,
    borderWidth: 9,
    borderColor: COLORS.background,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.85)",
  },
  fullScreenImageContainer: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
    justifyContent: "center",
    alignItems: "center",
  },
  fullScreenImage: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.8,
  },
  closeButton: {
    position: "absolute",
    top: 50,
    right: 20,
    zIndex: 10,
    padding: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 10,
  },
  closeButtonText: {
    color: "white",
    fontSize: 18,
    fontWeight: "bold",
  },
  name_modal_backdrop: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: SPACING.m,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
  },
  name_modal: {
    width: "100%",
    padding: SPACING.m,
    borderRadius: 20,
    backgroundColor: COLORS.primary,
  },
  name_input: {
    marginTop: SPACING.m,
    marginBottom: SPACING.m,
    paddingHorizontal: SPACING.m,
    paddingVertical: SPACING.s,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
    color: COLORS.secondary,
    fontSize: 20,
  },
  name_modal_buttons: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: SPACING.s,
  },
  name_modal_button: {
    minWidth: 90,
    paddingHorizontal: SPACING.m,
    paddingVertical: SPACING.s,
    borderRadius: 10,
    alignItems: "center",
  },
  cancel_button: {
    backgroundColor: COLORS.secondary,
  },
  save_button: {
    backgroundColor: "#254E6B",
  },
  name_modal_button_text: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  action_buttons_container: {
    width: "90%",
    flexDirection: "row",
    gap: SPACING.s,
    marginTop: SPACING.m,
  },
  permanent_button: {
    backgroundColor: COLORS.secondary,
  },
  trust_button: {
    backgroundColor: "#16a34a",
  },
  untrust_button: {
    backgroundColor: "#dc2626",
  },
  action_button_text: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
    flexShrink: 1,
  },
});

export default UserMax;
