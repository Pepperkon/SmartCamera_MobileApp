import { GlobalStyles } from "@/styles/GlobalStyles";
import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Pressable, StyleProp, Text, ViewStyle } from "react-native";

interface Props {
  text: string;
  isSelected?: boolean;
  onSelectionChange?: (isSelected: boolean) => void;
  containerStyle?: StyleProp<ViewStyle>;
}

function Checkbox({
  text,
  isSelected,
  onSelectionChange,
  containerStyle,
}: Props) {
  const [localIsSelected, setLocalIsSelected] = useState(false);
  const selected = isSelected ?? localIsSelected;

  const toggleOption = () => {
    const nextSelection = !selected;
    if (onSelectionChange) {
      onSelectionChange(nextSelection);
    } else {
      setLocalIsSelected(nextSelection);
    }
  };

  return (
    <Pressable
      style={[GlobalStyles.checkbox, containerStyle]}
      key={text}
      onPress={toggleOption}
    >
      <Text style={[GlobalStyles.text_small, { flexShrink: 1 }]}>{text}</Text>
      {selected && (
        <Ionicons
          name="checkmark"
          size={24}
          color="white"
          style={{ flexShrink: 0, marginLeft: 8 }}
        />
      )}
    </Pressable>
  );
}

export default Checkbox;
