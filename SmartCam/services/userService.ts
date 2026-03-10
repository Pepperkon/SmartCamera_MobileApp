import { User } from "@/constants/types";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "@/constants/api";

const STORAGE_KEY = "@users_cache";

export const fetchUsers = async (): Promise<User[]> => {
  try {
    const response = await fetch(`${API_URL}/users`);
    if (!response.ok) throw new Error("Problem z połączeniem");
    return await response.json();
  } catch (e) {
    console.log("Błąd pobierania użytkowników z FastAPI:", e);
    return [];
  }
};

export const saveUsersToCache = async (users: User[]) => {
  try {
    const jsonValue = JSON.stringify(users);
    await AsyncStorage.setItem(STORAGE_KEY, jsonValue);
  } catch (e) {
    console.log("Cache error:", e);
  }
};

export const getUsersFromCache = async (): Promise<User[] | null> => {
  try {
    console.log("caching");
    const jsonValue = await AsyncStorage.getItem(STORAGE_KEY);
    return jsonValue != null ? JSON.parse(jsonValue) : null;
  } catch (e) {
    console.log("Cahce error:", e);
    return null;
  }
};

export const addUser = async (name: string, imageUri: string) => {
  const formData = new FormData();

  formData.append("name", name);

  const filename = imageUri.split("/").pop() || "photo.jpg";
  const match = /\.(\w+)$/.exec(filename);
  const type = match ? `image/${match[1]}` : `image`;

  formData.append("file", {
    uri: imageUri,
    name: filename,
    type: type,
  } as any);

  const response = await fetch(`${API_URL}/users`, {
    method: "POST",
    body: formData,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return await response.json();
};
