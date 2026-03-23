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

function NewImage() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState<boolean>(false);

  const [image, setImage] = useState<string | null>(null);

  if (!id || typeof id !== "string") {
    Alert.alert("Błąd", "Nieprawidłowe ID użytkownika.");
    return;
  }

  const pickImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      aspect: [1, 1],
    });

    if (!result.canceled) {
      setImage(result.assets[0].uri);
    }
  };

  const handleSave = async () => {
    if (!image) {
      Alert.alert("Błąd", "Wybierz zdjęcie");
      return;
    }

    try {
      setLoading(true);
      const res = await addUserImage(id, image);
      setLoading(false);
      switch (res.status) {
        case 200:
          Alert.alert("Success", "The photo has been successfully added.");
          break;

        case 404:
          Alert.alert(
            "Invalid Photo",
            "A face must be present in the image to continue.",
          );
          break;

        default:
          Alert.alert("Something went wrong", `Error code: ${res.status}`);
      }
      setImage(null);
      router.back();
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
          <Text style={GlobalStyles.text_secondary}>Processing image...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <View style={styles.container}>
        <Pressable style={styles.button} onPress={pickImage}>
          <Text style={{ fontSize: 20, color: "white" }}>Choose image</Text>
        </Pressable>
        {image && <Image source={{ uri: image }} style={styles.preview} />}
        {image && (
          <Pressable style={styles.button} onPress={handleSave}>
            <Text style={{ fontSize: 20, color: "white" }}>Save</Text>
          </Pressable>
        )}
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
  },
  input: {
    backgroundColor: "white",
    padding: 10,
    marginBottom: 10,
    borderRadius: 5,
    fontSize: 30,
    width: "90%",
  },
  preview: {
    width: 300,
    height: 300,
    borderRadius: 20,
    borderWidth: 9,
    borderColor: COLORS.background,
  },
  button: {
    paddingVertical: SPACING.m,
    paddingHorizontal: SPACING.l,
    borderRadius: 5,
    backgroundColor: COLORS.secondary,
    marginVertical: SPACING.m,
  },
});

export default NewImage;
