import { SPACING } from "@/constants/theme";
import { AlertItem } from "@/constants/types";
import {
  fetchAlerts,
  getAlertsFromCache,
  saveAlertsToCache,
} from "@/services/alertService";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, View } from "react-native";
import AlertMin from "./alertMin";
import SearchBar from "./searchBar";

function EntryList() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);

  const loadData = async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(true);

    try {
      const freshData = await fetchAlerts();
      if (freshData && freshData.length > 0) {
        setAlerts(freshData);
        await saveAlertsToCache(freshData);
      }
    } catch (error) {
      console.error("Błąd pobierania:", error);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadData(true);
  };

  const markAsRead = async (id: string) => {
    const updatedAlerts = alerts.map((alert) =>
      alert.id === id ? { ...alert, isNew: false } : alert,
    );
    setAlerts(updatedAlerts);
    await saveAlertsToCache(updatedAlerts);
  };

  useFocusEffect(
    useCallback(() => {
      const updateFromCache = async () => {
        const cachedData = await getAlertsFromCache();

        if (cachedData && cachedData.length > 0) {
          setAlerts(cachedData);
          setIsLoading(false);
        } else {
          await loadData();
        }
      };

      updateFromCache();
    }, []),
  );

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center" }}>
        <ActivityIndicator size="large" color="coral" />
      </View>
    );
  }

  return (
    <>
      <SearchBar></SearchBar>
      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <AlertMin alert={item} markAsRead={markAsRead}></AlertMin>
        )}
        onRefresh={handleRefresh}
        refreshing={isRefreshing}
        contentContainerStyle={styles.listContent}
        style={{ flex: 1, width: "100%", height: "100%" }}
      />
    </>
  );
}

const styles = StyleSheet.create({
  listContent: {
    padding: 20,
    paddingBottom: 40,
    gap: SPACING.m,
  },
});

export default EntryList;
