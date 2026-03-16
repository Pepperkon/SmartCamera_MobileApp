import { API_URL } from "@/constants/api";
import { COLORS } from "@/constants/theme";
import { User } from "@/constants/types";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useRouter } from "expo-router";
import React from "react";
import { Image, Pressable, StyleSheet, Text } from "react-native";

interface Props {
  user: User;
}

function UserEntry({ user }: Props) {
  const router = useRouter();

  // 1. Sprawdzamy bezpiecznie, czy obrazek istnieje
  const firstImage = user?.images?.[0];

  // 2. Budujemy ścieżkę tylko, jeśli mamy dane
  const filepath = firstImage
    ? `${API_URL}/data/images/users/${user.id}/${firstImage.filepath}`
    : null;

  // 3. Wybieramy źródło obrazka (filepath lub avatar zastępczy)
  const imageSource = filepath
    ? { uri: filepath }
    : { uri: "https://ui-avatars.com/api/?name=" + (user?.name || "User") };

  return (
    <Pressable
      style={({ pressed }) => [
        GlobalStyles.singleEntry,
        pressed && GlobalStyles.pressed,
      ]}
      onPress={() => {
        router.push({ pathname: "/user-details", params: { id: user.id } });
      }}
    >
      <Image source={imageSource} style={styles.image} />
      <Text style={GlobalStyles.text_primary}>{user?.name}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  image: {
    width: 100,
    height: 100,
    borderRadius: 10,
    borderWidth: 3,
    borderColor: COLORS.background,
  },
});

export default UserEntry;
