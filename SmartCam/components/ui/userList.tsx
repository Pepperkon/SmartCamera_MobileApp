import { SPACING } from "@/constants/theme";
import { User } from "@/constants/types";
import {
  fetchUsers,
  getUsersFromCache,
  saveUsersToCache,
} from "@/services/userService";
import React, { useCallback, useRef, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, View } from "react-native";
import UserEntry from "./userEntry";
import { useFocusEffect } from "expo-router/react-navigation";
import Checkbox from "./checkbox";

interface Props {
  isTrustedView: boolean;
}

function UserList({ isTrustedView }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setRefreshing] = useState(false);
  const [includeTemporary, setIncludeTemporary] = useState(false);
  const includeTemporaryUsers = isTrustedView || includeTemporary;
  const loadRequestId = useRef(0);

  const loadData = useCallback(
    async (forceRefresh = false) => {
      const requestId = ++loadRequestId.current;
      if (forceRefresh) setRefreshing(true);

      if (!forceRefresh) {
        const cachedData = await getUsersFromCache(
          isTrustedView,
          includeTemporaryUsers,
        );
        if (requestId !== loadRequestId.current) return;
        if (cachedData) {
          setUsers(cachedData);
          setLoading(false);
        }
      }

      const freshData = await fetchUsers(isTrustedView, includeTemporaryUsers);
      await saveUsersToCache(freshData, isTrustedView, includeTemporaryUsers);

      if (requestId !== loadRequestId.current) return;
      setUsers(freshData);
      setLoading(false);
      setRefreshing(false);
    },
    [includeTemporaryUsers, isTrustedView],
  );

  const handleRefresh = useCallback(() => {
    void loadData(true);
  }, [loadData]);

  useFocusEffect(
    useCallback(() => {
      void loadData();
      return () => {
        loadRequestId.current += 1;
      };
    }, [loadData]),
  );

  if (loading) {
    return <ActivityIndicator style={{ flex: 1 }} size="large" />;
  }

  return (
    <View style={styles.container}>
      {!isTrustedView && (
        <Checkbox
          text="Include temporary"
          isSelected={includeTemporary}
          onSelectionChange={setIncludeTemporary}
        />
      )}
      <FlatList
        data={users}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <UserEntry user={item}></UserEntry>}
        onRefresh={handleRefresh}
        refreshing={isRefreshing}
        contentContainerStyle={styles.listContent}
        style={{ flex: 1, width: "100%" }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: "100%",
  },
  listContent: {
    padding: 20,
    paddingBottom: 40,
    gap: SPACING.m,
  },
});

export default UserList;
