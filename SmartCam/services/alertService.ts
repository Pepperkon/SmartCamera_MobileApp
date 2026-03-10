import { AlertItem } from "@/constants/types";
import AsyncStorage from "@react-native-async-storage/async-storage";

const API_URL = "http://192.168.1.48:8000";

const MOCK_ALERTS: AlertItem[] = [
  {
    id: "1",
    title: "Maciej",
    time: "16:20",
    image: require("../assets/images/maciej.jpg"),
    isNew: true,
  },
  {
    id: "2",
    title: "Krzysztof",
    time: "14:20",
    image: require("../assets/images/maciej.jpg"),
    isNew: true,
  },
  {
    id: "3",
    title: "Kacper",
    time: "12:20",
    image: require("../assets/images/kacper.jpg"),
    isNew: false,
  },
  {
    id: "4",
    title: "Lewy",
    time: "10:20",
    image: require("../assets/images/lewy.jpg"),
    isNew: false,
  },
  {
    id: "5",
    title: "Zupa",
    time: "69:67",
    image: require("../assets/images/zupa.jpg"),
    isNew: false,
  },
];

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

export const fetchAlertsMock = async (): Promise<AlertItem[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_ALERTS);
    }, 500);
  });
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
  } catch (error) {
    console.error("Nie udało się zaktualizować statusu na serwerze");
  }
};
