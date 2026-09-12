import { COLORS, SPACING } from "@/constants/theme";
import { addUser } from "@/services/userService";
import { GlobalStyles } from "@/styles/GlobalStyles";
import * as ImagePicker from "expo-image-picker";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

function NewUser() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [loading, setLoading] = useState<boolean>(false);
  const [image, setImage] = useState<string | null>(null);

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
    if (!name || !image) {
      Alert.alert("Error", "Please provide a name and select an image!");
      return;
    }

    try {
      setLoading(true);
      const res = await addUser(name, image);
      setLoading(false);

      if (res.ok) {
        Alert.alert("Success", "User has been successfully added.");
        setName("");
        setImage(null);
        router.back();
        return;
      }

      const data = await res.json().catch(() => null);
      const detail = data?.detail;

      if (res.status === 422 || res.status === 400) {
        if (detail === "MULTIPLE_FACES" || detail === "More than 1 face detected") {
          Alert.alert(
            "Invalid Photo",
            "Multiple faces detected. Please select a photo with only one person."
          );
        } else if (detail === "NO_FACE" || detail === "No face detected") {
          Alert.alert(
            "Invalid Photo",
            "No face detected. Please ensure the face is clearly visible."
          );
        } else {
          Alert.alert("Invalid Photo", "Failed to detect face properly.");
        }
      } else if (res.status === 503) {
        Alert.alert("Server Error", "Face recognition model is currently unavailable.");
      } else {
        Alert.alert("Error", `Something went wrong. Status code: ${res.status}`);
      }
    } catch {
      Alert.alert("Network Error", "Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={GlobalStyles.container}>
        <View style={[styles.container, { justifyContent: "center" }]}>
          <ActivityIndicator size="large" color="white" />
          <Text style={GlobalStyles.text_secondary}>Adding user...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <View style={styles.container}>
        <TextInput
          style={styles.input}
          placeholder="Nazwa użytkownika"
          placeholderTextColor={COLORS.primary}
          value={name}
          onChangeText={(value) => setName(value)}
        />
        <Pressable onPress={pickImage} style={styles.button}>
          <Text style={{ fontSize: 20, color: "white" }}>Wybierz zdjęcie</Text>
        </Pressable>
        {image && <Image source={{ uri: image }} style={styles.preview} />}
        {image && name && (
          <Pressable style={styles.button} onPress={handleSave}>
            <Text style={{ fontSize: 20, color: "white" }}>Zapisz</Text>
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

export default NewUser;
