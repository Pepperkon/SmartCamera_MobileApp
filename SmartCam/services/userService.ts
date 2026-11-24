import * as FileSystem from "expo-file-system/legacy";
import { User, UserMergeResult } from "@/constants/types";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "@/constants/api";

const getStorageKey = (isTrusted: boolean, includeTemporary: boolean) => {
  if (isTrusted) return "@users_cache_trusted";
  return includeTemporary
    ? "@users_cache_untrusted_with_temporary_v2"
    : "@users_cache_untrusted_without_temporary_v2";
};

export const fetchUsers = async (
  isTrusted: boolean = false,
  includeTemporary: boolean = true,
): Promise<User[]> => {
  try {
    const temporaryFilter =
      isTrusted || includeTemporary ? "" : "&is_temporary=false";
    const response = await fetch(
      `${API_URL}/users?is_trusted=${isTrusted}${temporaryFilter}`,
    );
    if (!response.ok) throw new Error("Problem z połączeniem");
    return await response.json();
  } catch (e) {
    console.log("Błąd pobierania użytkowników z FastAPI:", e);
    return [];
  }
};

export const fetchPermanentUsers = async (): Promise<User[]> => {
  const users: User[] = [];
  const pageSize = 100;
  for (let offset = 0; ; offset += pageSize) {
    const response = await fetch(
      `${API_URL}/users?is_temporary=false&limit=${pageSize}&offset=${offset}`,
    );
    if (!response.ok) {
      throw new Error(`Could not load permanent users (HTTP ${response.status})`);
    }
    const page: User[] = await response.json();
    users.push(...page);
    if (page.length < pageSize) return users;
  }
};

export const mergeUsers = async (
  sourceUserId: number | string,
  targetUserId: number | string,
  includeTemplates: boolean,
): Promise<UserMergeResult> => {
  const response = await fetch(`${API_URL}/users/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_user_id: Number(sourceUserId),
      target_user_id: Number(targetUserId),
      include_templates: includeTemplates,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export const saveUsersToCache = async (
  users: User[],
  isTrusted: boolean = false,
  includeTemporary: boolean = true,
) => {
  try {
    const key = getStorageKey(isTrusted, includeTemporary);
    const jsonValue = JSON.stringify(users);
    await AsyncStorage.setItem(key, jsonValue);
  } catch (e) {
    console.log("Cache error:", e);
  }
};

export const getUsersFromCache = async (
  isTrusted: boolean = false,
  includeTemporary: boolean = true,
): Promise<User[] | null> => {
  try {
    const key = getStorageKey(isTrusted, includeTemporary);
    const jsonValue = await AsyncStorage.getItem(key);
    return jsonValue != null ? JSON.parse(jsonValue) : null;
  } catch (e) {
    console.log("Cache error:", e);
    return null;
  }
};

export const addUser = async (name: string, imageUri: string) => {
  const uploadResult = await FileSystem.uploadAsync(
    `${API_URL}/users`,
    imageUri,
    {
      fieldName: "file",
      httpMethod: "POST",
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
      parameters: {
        name: name,
      },
    },
  );

  return {
    ok: uploadResult.status >= 200 && uploadResult.status < 300,
    status: uploadResult.status,
    json: async () => JSON.parse(uploadResult.body),
    text: async () => uploadResult.body,
  };
};

export const addUserImage = async (id: string, imageUri: string) => {
  const uploadResult = await FileSystem.uploadAsync(
    `${API_URL}/users/${id}/images`,
    imageUri,
    {
      fieldName: "file",
      httpMethod: "POST",
      uploadType: FileSystem.FileSystemUploadType.MULTIPART,
    },
  );

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

export const updateUserTrust = async (
  id: string,
  isTrusted: boolean,
): Promise<{ is_trusted: boolean; is_temporary: boolean }> => {
  const response = await fetch(
    `${API_URL}/users/${id}/trust?is_trusted=${isTrusted}`,
    { method: "PATCH" },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export const saveTemporaryUser = async (
  id: string,
  name: string,
): Promise<{ message: string }> => {
  const response = await fetch(
    `${API_URL}/users/${id}?name=${encodeURIComponent(name)}`,
    { method: "PATCH" },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export const updateUserName = async (
  id: string,
  name: string,
): Promise<{ message: string }> => {
  const response = await fetch(
    `${API_URL}/users/${id}/name?name=${encodeURIComponent(name)}`,
    { method: "PATCH" },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export const deleteUserFromCache = async (id: string) => {
  try {
    for (const includeTemporary of [false, true]) {
      const untrustedUsers = await getUsersFromCache(
        false,
        includeTemporary,
      );
      if (untrustedUsers) {
        const updatedUntrusted = untrustedUsers.filter(
          (user) => String(user.id) !== String(id),
        );
        await saveUsersToCache(updatedUntrusted, false, includeTemporary);
      }
    }

    const trustedUsers = await getUsersFromCache(true);
    if (trustedUsers) {
      const updatedTrusted = trustedUsers.filter(
        (user) => String(user.id) !== String(id),
      );
      await saveUsersToCache(updatedTrusted, true);
    }
  } catch (e) {
    throw e;
  }
};
