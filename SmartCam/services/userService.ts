import * as FileSystem from "expo-file-system/legacy";
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
    const jsonValue = await AsyncStorage.getItem(STORAGE_KEY);
    return jsonValue != null ? JSON.parse(jsonValue) : null;
  } catch (e) {
    console.log("Cahce error:", e);
    return null;
  }
};

export const addUser = async (name: string, imageUri: string) => {
  const uploadResult = await FileSystem.uploadAsync(`${API_URL}/users`, imageUri, {
    fieldName: "file",
    httpMethod: "POST",
    uploadType: FileSystem.FileSystemUploadType.MULTIPART,
    parameters: {
      name: name,
    },
  });

  return {
    ok: uploadResult.status >= 200 && uploadResult.status < 300,
    status: uploadResult.status,
    json: async () => JSON.parse(uploadResult.body),
    text: async () => uploadResult.body,
  };
};

export const addUserImage = async (id: string, imageUri: string) => {
  const uploadResult = await FileSystem.uploadAsync(`${API_URL}/users/${id}/images`, imageUri, {
    fieldName: "file",
    httpMethod: "POST",
    uploadType: FileSystem.FileSystemUploadType.MULTIPART,
  });

  return {
    ok: uploadResult.status >= 200 && uploadResult.status < 300,
    status: uploadResult.status,
    json: async () => JSON.parse(uploadResult.body),
    text: async () => uploadResult.body,
  };
};

export const deleteUser = async (id: string) => {
  try {
    const response = await fetch(`${API_URL}/users/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Error");
    }

    return await response.json();
  } catch (e) {
    throw e;
  }
};

export const deleteUserFromCache = async (id: string) => {
  try {
    const currentUsers = await getUsersFromCache();
    if (currentUsers) {
      const updatedUsers = currentUsers.filter(
        (user) => String(user.id) !== String(id),
      );
      await saveUsersToCache(updatedUsers);
      return updatedUsers;
    }
  } catch (e) {
    throw e;
  }
};
