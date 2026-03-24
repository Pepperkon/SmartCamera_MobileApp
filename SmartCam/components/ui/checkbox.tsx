import { COLORS, SPACING } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

interface Props {
  text: string;
}

function Checkbox({ text }: Props) {
  const [isSelected, setIsSelected] = useState(false);

  const toggleOption = () => {
    setIsSelected(!isSelected);
  };

  return (
    <Pressable
      style={GlobalStyles.checkbox}
      key={text}
      onPress={() => toggleOption()}
    >
      <Text style={GlobalStyles.text_small}>{text}</Text>
      {isSelected && <Ionicons name="checkmark" size={30} color="white" />}
    </Pressable>
  );
}

export default Checkbox;
