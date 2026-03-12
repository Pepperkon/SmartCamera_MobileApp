import { View, Text, Image, ActivityIndicator } from "react-native";
import React, { useEffect, useState } from "react";
import { StyleSheet } from "react-native";
import { COLORS, SPACING } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  deleteUser,
  deleteUserFromCache,
  getUsersFromCache,
} from "@/services/userService";
import { User } from "@/constants/types";
import { API_URL } from "@/constants/api";
import CircleButton from "./circleButton";

function UserMax() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const handleDelete = async () => {
    if (typeof id == "string") {
      await deleteUser(id);
      await deleteUserFromCache(id);
      router.back();
    }
  };

  useEffect(() => {
    const loadUser = async () => {
      const cachedUsers = await getUsersFromCache();
      if (cachedUsers) {
        const found = cachedUsers.find((a) => String(a.id) === String(id));
        setUser(found || null);
      }
      setLoading(false);
    };

    loadUser();
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

  if (!user) {
    return (
      <View style={styles.container}>
        <Text style={GlobalStyles.text_primary}>User not found</Text>
      </View>
    );
  }

  const filepath = `${API_URL}/images/users/${user.image}`;
  const imageSource =
    typeof user.image === "string"
      ? { uri: filepath }
      : { uri: "https://ui-avatars.com/api/?name=" + user.name };

  return (
    <View style={styles.container}>
      <Text style={GlobalStyles.text_primary}>{user.name}</Text>
      <Image source={imageSource} style={styles.image} />

      <View style={styles.button_container}>
        <CircleButton iconName="trash" onPress={handleDelete} />
        <CircleButton iconName="download" />
      </View>
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
});

export default UserMax;
