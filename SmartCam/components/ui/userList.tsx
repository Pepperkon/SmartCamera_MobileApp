import { SPACING } from "@/constants/theme";
import { User } from "@/constants/types";
import {
  fetchUsers,
  getUsersFromCache,
  saveUsersToCache,
} from "@/services/userService";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet } from "react-native";
import UserEntry from "./userEntry";
import { useFocusEffect } from "@react-navigation/native";

function UserList() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);

  const syncWithCache = async () => {
    const cachedData = await getUsersFromCache();
    if (cachedData) {
      setUsers(cachedData);
    }
    setLoading(false);
  };

  const loadData = async (forceRefresh = false) => {
    if (forceRefresh) setRefreshing(true);

    const freshData = await fetchUsers();
    await saveUsersToCache(freshData);

    setUsers(freshData);
    setLoading(false);
    setRefreshing(false);
  };

  const handleRefresh = () => {
    loadData(true);
  };

  useFocusEffect(
    useCallback(() => {
      syncWithCache();
      loadData();
    }, []),
  );

  if (loading) {
    return <ActivityIndicator style={{ flex: 1 }} size="large" />;
  }

  return (
    <FlatList
      data={users}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <UserEntry user={item}></UserEntry>}
      onRefresh={handleRefresh}
      refreshing={isRefreshing}
      contentContainerStyle={styles.listContent}
      style={{ flex: 1, width: "100%" }}
    ></FlatList>
  );
}

const styles = StyleSheet.create({
  listContent: {
    padding: 20,
    paddingBottom: 40,
    gap: SPACING.m,
  },
});

export default UserList;
