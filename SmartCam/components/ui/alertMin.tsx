import { AlertItem } from "@/constants/types";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useRouter } from "expo-router";
import React from "react";
import { Pressable, Text, View } from "react-native";
import NotificationMark from "./notificationMark";

interface Props {
  alert: AlertItem;
  markAsRead: (id: string) => void;
}

function AlertMin({ alert, markAsRead }: Props) {
  const router = useRouter();

  return (
    <Pressable
      style={({ pressed }) => [
        GlobalStyles.singleEntry,
        pressed && GlobalStyles.pressed,
      ]}
      onPress={() => {
        markAsRead(alert.id);
        router.push({ pathname: "/alert-details", params: { id: alert.id } });
      }}
    >
      <Text style={[GlobalStyles.text_secondary, { maxWidth: "50%" }]}>
        {alert.title}
      </Text>
      <Text style={GlobalStyles.text_secondary}>{alert.time}</Text>
      {alert.isNew && (
        <View style={GlobalStyles.mark}>
          <NotificationMark />
        </View>
      )}
    </Pressable>
  );
}

export default AlertMin;
