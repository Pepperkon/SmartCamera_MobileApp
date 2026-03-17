import CircleButton from "@/components/ui/circleButton";
import UserList from "@/components/ui/userList";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useRouter } from "expo-router";
import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";

function HouseholdView() {
  const router = useRouter();

  const addUser = () => {
    router.push("/new-user");
  };

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <UserList></UserList>
      <CircleButton iconName="plus" onPress={addUser}></CircleButton>
    </SafeAreaView>
  );
}

export default HouseholdView;
