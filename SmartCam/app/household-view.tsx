import CircleButton from "@/components/ui/circleButton";
import UserList from "@/components/ui/userList";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { View, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

function HouseholdView() {
  const router = useRouter();

  const [isTrustedView, setIsTrustedView] = useState(false);

  const addUser = () => {
    router.push("/new-user");
  };

  const toggleUserView = () => {
    setIsTrustedView((prev) => !prev);
  };

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <UserList isTrustedView={isTrustedView} />
      <View style={styles.button_container}>
        <CircleButton iconName="plus" onPress={addUser} />
        <CircleButton
          iconName={isTrustedView ? "warning" : "safety"}
          onPress={toggleUserView}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  button_container: {
    width: "70%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    marginTop: 10,
  },
});

export default HouseholdView;
