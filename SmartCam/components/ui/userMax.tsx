import {
  View,
  Text,
  Image,
  ActivityIndicator,
  Modal,
  Pressable,
  FlatList,
  Dimensions,
} from "react-native";
import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet } from "react-native";
import { COLORS, SPACING } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import {
  deleteUser,
  deleteUserFromCache,
  getUsersFromCache,
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

  const handleDelete = async () => {
    if (typeof id == "string") {
      await deleteUser(id);
      await deleteUserFromCache(id);
      router.back();
    }
  };

  const addImage = () => {
    router.push({ pathname: "/add-image", params: { id: id } });
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

  const filepath = `${API_URL}/images/users/${user.id}/${user.images[0].filepath}`;
  const imageSource = typeof user.images[0]
    ? { uri: filepath }
    : { uri: "https://ui-avatars.com/api/?name=" + user.name };

  return (
    <View style={styles.container}>
      <Text style={GlobalStyles.text_primary}>{user.name}</Text>
      <Pressable onPress={() => setGalleryVisible(true)}>
        <Image source={imageSource} style={styles.image} />
      </Pressable>

      <View style={styles.button_container}>
        <CircleButton iconName="trash" onPress={handleDelete} />
        <CircleButton iconName="download" />
      </View>
      <View style={styles.button_container}>
        <CircleButton iconName="add" onPress={addImage} />
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
                      uri: `${API_URL}/images/users/${user.id}/${item.filepath}`,
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
    width: "70%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    marginTop: 10,
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
});

export default UserMax;
