import { COLORS } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import React from "react";
import { Text, TextInput, View } from "react-native";
import { Image, Pressable, StyleSheet } from "react-native";
import CircleButton from "./circleButton";

function SearchBar() {
  return (
    <View style={styles.container}>
      <TextInput style={styles.input} placeholder="Search"></TextInput>
      <CircleButton iconName="filter" color="primary"></CircleButton>
    </View>
  );
}

export default SearchBar;

const styles = StyleSheet.create({
  input: {
    width: 200,
    height: 60,
    borderRadius: 10,
    backgroundColor: "white",
    padding: 10,
    fontSize: 30,
  },
  container: {
    backgroundColor: COLORS.secondary,
    height: 140,
    zIndex: 1000,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    width: "100%",
    borderRadius: 10,
    alignItems: "center",
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
  },
});
