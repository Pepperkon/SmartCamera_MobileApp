import { GlobalStyles } from "@/styles/GlobalStyles";
import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import UserMax from "@/components/ui/userMax";

function userDetails() {
  return (
    <SafeAreaView style={GlobalStyles.container}>
      <UserMax />
    </SafeAreaView>
  );
}

export default userDetails;
