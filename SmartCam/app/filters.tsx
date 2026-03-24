import {
  View,
  Text,
  Pressable,
  TextInput,
  StyleSheet,
  Alert,
  Image,
  ActivityIndicator,
} from "react-native";
import React, { useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { COLORS, SPACING } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { addUserImage } from "@/services/userService";
import { Ionicons } from "@expo/vector-icons";
import Checkbox from "@/components/ui/checkbox";

const FILTER_OPTIONS = [
  { id: "recognised", label: "Recognised" },
  { id: "unknown", label: "Unknown" },
];

function Filters() {
  const router = useRouter();
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggleOption = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleSave = async () => {
    try {
    } catch (e) {
      Alert.alert("Network Error", "The server is unreachable.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={GlobalStyles.container}>
        <View style={[styles.container, { justifyContent: "center" }]}>
          <ActivityIndicator size="large" color="white" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <View style={styles.container}>
        <Text style={GlobalStyles.text_secondary}>Alert type:</Text>
        <View style={styles.checkbox_container}>
          <Checkbox text="Recognised"></Checkbox>
          <Checkbox text="Unknown"></Checkbox>
        </View>
      </View>
    </SafeAreaView>
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
    paddingHorizontal: SPACING.m,
  },
  checkbox_container: {
    flexDirection: "row",
    marginTop: SPACING.m,
    padding: SPACING.s,
  },
  input: {
    backgroundColor: "white",
    padding: 10,
    marginBottom: 10,
    borderRadius: 5,
    fontSize: 30,
    width: "90%",
  },
  button: {
    paddingVertical: SPACING.m,
    paddingHorizontal: SPACING.l,
    borderRadius: 5,
    backgroundColor: COLORS.secondary,
    marginVertical: SPACING.m,
  },
});

export default Filters;
