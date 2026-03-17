import { COLORS, SPACING } from "@/constants/theme";
import { Ionicons, AntDesign } from "@expo/vector-icons";
import React from "react";
import { Pressable, StyleSheet } from "react-native";

interface Props {
  iconName: keyof typeof AntDesign.glyphMap;
  color?: "primary" | "secondary";
  onPress?: () => void;
}

function CircleButton({ iconName, onPress, color = "secondary" }: Props) {
  const backgroundColor =
    color === "secondary" ? COLORS.secondary : COLORS.primary;
  return (
    <Pressable style={[styles.circle, { backgroundColor }]} onPress={onPress}>
      <AntDesign name={iconName} color={"#ffff"} size={70}></AntDesign>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  circle: {
    borderRadius: 90,
    aspectRatio: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: SPACING.m,
    marginVertical: SPACING.m,
  },
});

export default CircleButton;
