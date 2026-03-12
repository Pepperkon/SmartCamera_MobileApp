import { COLORS, SPACING } from "@/constants/theme";
import { addUser } from "@/services/userService";
import { GlobalStyles } from "@/styles/GlobalStyles";
import * as ImagePicker from "expo-image-picker";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
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
      Alert.alert("Błąd", "Podaj nazwę i wybierz zdjęcie!");
      return;
    }

    try {
      await addUser(name, image);
      Alert.alert("Sukces", "Użytkownik dodany!");
      setName("");
      setImage(null);
      router.back();
    } catch (e) {
      Alert.alert("Błąd", "Nie udało się połączyć z serwerem.");
    }
  };

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
