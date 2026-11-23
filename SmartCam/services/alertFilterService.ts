import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "@alert_filters";

export interface AlertFilters {
  showTemporary: boolean;
  showPermanent: boolean;
  showTrusted: boolean;
  showUntrusted: boolean;
  unreadOnly: boolean;
}

export const DEFAULT_ALERT_FILTERS: AlertFilters = {
  showTemporary: true,
  showPermanent: true,
  showTrusted: true,
  showUntrusted: true,
  unreadOnly: false,
};

export const getAlertFilters = async (): Promise<AlertFilters> => {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (!stored) return { ...DEFAULT_ALERT_FILTERS };

    const parsed: Partial<
      AlertFilters & { showRecognised: boolean; showUnknown: boolean }
    > = JSON.parse(stored);
    return {
      showTemporary:
        typeof parsed.showTemporary === "boolean"
          ? parsed.showTemporary
          : typeof parsed.showUnknown === "boolean"
            ? parsed.showUnknown
            : DEFAULT_ALERT_FILTERS.showTemporary,
      showPermanent:
        typeof parsed.showPermanent === "boolean"
          ? parsed.showPermanent
          : typeof parsed.showRecognised === "boolean"
            ? parsed.showRecognised
            : DEFAULT_ALERT_FILTERS.showPermanent,
      showTrusted:
        typeof parsed.showTrusted === "boolean"
          ? parsed.showTrusted
          : DEFAULT_ALERT_FILTERS.showTrusted,
      showUntrusted:
        typeof parsed.showUntrusted === "boolean"
          ? parsed.showUntrusted
          : DEFAULT_ALERT_FILTERS.showUntrusted,
      unreadOnly:
        typeof parsed.unreadOnly === "boolean"
          ? parsed.unreadOnly
          : DEFAULT_ALERT_FILTERS.unreadOnly,
    };
  } catch (error) {
    console.error("Error loading alert filters:", error);
    return { ...DEFAULT_ALERT_FILTERS };
  }
};

export const saveAlertFilters = async (filters: AlertFilters): Promise<void> => {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch (error) {
    console.error("Error saving alert filters:", error);
    throw error;
  }
};
