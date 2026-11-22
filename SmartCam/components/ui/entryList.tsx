import { SPACING } from "@/constants/theme";
import { AlertItem } from "@/constants/types";
import {
  fetchAlerts,
  getAlertsFromCache,
  saveAlertsToCache,
  markAsReadOnServer,
} from "@/services/alertService";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, View } from "react-native";
import AlertMin from "./alertMin";
import SearchBar from "./searchBar";
import { useAlertsWebSocket } from "@/hooks/use-alerts-websocket";
import {
  DEFAULT_ALERT_FILTERS,
  getAlertFilters,
} from "@/services/alertFilterService";

function EntryList() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  useAlertsWebSocket(setAlerts);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [alertFilters, setAlertFilters] = useState(DEFAULT_ALERT_FILTERS);

  const filteredAlerts = (alerts || []).filter((alert) => {
    const title = alert?.title?.toLowerCase() || "";
    const isTemporary =
      alert.user?.is_temporary ??
      alert.recognised_user_is_temporary ??
      true;
    const isTrusted = alert.recognised_user_is_trusted === true;
    const matchesTemporary = isTemporary
      ? alertFilters.showTemporary
      : alertFilters.showPermanent;
    const matchesTrust = isTrusted
      ? alertFilters.showTrusted
      : alertFilters.showUntrusted;
    const matchesUnread = !alertFilters.unreadOnly || alert.isNew;
    const matchesSearch = title.includes(searchQuery.toLowerCase());

    return matchesTemporary && matchesTrust && matchesUnread && matchesSearch;
  });

  const syncWithCache = async () => {
    const cachedData = await getAlertsFromCache();
    if (cachedData) {
      setAlerts(cachedData);
    }
    setIsLoading(false);
  };

  const loadData = async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(true);

    const freshData = await fetchAlerts();
    await saveAlertsToCache(freshData);

    setAlerts(freshData);
    setIsLoading(false);
    setRefreshing(false);
  };

  const handleRefresh = () => {
    loadData(true);
  };

  const markAsRead = async (id: string) => {
    await markAsReadOnServer(id);
    const updatedAlerts = alerts.map((alert) =>
      alert.id === id ? { ...alert, isNew: false } : alert,
    );
    setAlerts(updatedAlerts);
    await saveAlertsToCache(updatedAlerts);
  };

  useFocusEffect(
    useCallback(() => {
      syncWithCache();
      loadData();
    }, []),
  );

  useFocusEffect(
    useCallback(() => {
      let active = true;
      getAlertFilters().then((savedFilters) => {
        if (active) setAlertFilters(savedFilters);
      });

      return () => {
        active = false;
      };
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
      <SearchBar value={searchQuery} onChangeText={setSearchQuery}></SearchBar>
      <FlatList
        data={filteredAlerts}
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
