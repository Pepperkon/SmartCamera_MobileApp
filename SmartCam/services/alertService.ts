import { AlertItem } from "@/constants/types";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "@/constants/api";

const STORAGE_KEY = "@alerts_cache";

export const saveAlertsToCache = async (alerts: AlertItem[]) => {
  try {
    const jsonValue = JSON.stringify(alerts);
    await AsyncStorage.setItem(STORAGE_KEY, jsonValue);
  } catch (e) {
    console.log("Cache error:", e);
  }
};

export const getAlertsFromCache = async (): Promise<AlertItem[] | null> => {
  try {
    const jsonValue = await AsyncStorage.getItem(STORAGE_KEY);
    return jsonValue != null ? JSON.parse(jsonValue) : null;
  } catch (e) {
    console.log("Cahce error:", e);
    return null;
  }
};

export const deleteAlertFromCache = async (id: string) => {
  try {
    const currentAlerts = await getAlertsFromCache();
    if (currentAlerts) {
      const updatedAlerts = currentAlerts.filter((alert) => alert.id !== id);
      await saveAlertsToCache(updatedAlerts);
      return updatedAlerts;
    }
  } catch (e) {
    throw e;
  }
};

export const deleteAlert = async (id: string) => {
  try {
    const response = await fetch(`${API_URL}/alerts/${id}`, {
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

export const fetchAlerts = async (): Promise<AlertItem[]> => {
  try {
    const response = await fetch(`${API_URL}/alerts`);
    if (!response.ok) throw new Error("Problem z połączeniem");
    return await response.json();
  } catch (error) {
    console.error("Błąd pobierania danych z FastAPI:", error);
    return [];
  }
};

export const markAsReadOnServer = async (id: string) => {
  try {
    await fetch(`${API_URL}/alerts/${id}/read`, {
      method: "POST",
    });
  } catch {
    console.error("Nie udało się zaktualizować statusu na serwerze");
  }
};
