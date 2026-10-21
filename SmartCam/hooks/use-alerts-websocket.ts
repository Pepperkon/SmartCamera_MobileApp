import { useEffect } from "react";
import { AlertItem } from "@/constants/types";
import { WS_URL } from "@/constants/api";
import { saveAlertsToCache } from "@/services/alertService";

const APP_API_KEY = process.env.EXPO_PUBLIC_APP_API_KEY || "";

// Connects to the alerts WebSocket and directly updates the parent component's state
export const useAlertsWebSocket = (
  setAlerts: React.Dispatch<React.SetStateAction<AlertItem[]>>,
) => {
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/alerts?app_api_key=${APP_API_KEY}`);

    ws.onopen = () => {
      console.log("🟢 Connected to WebSocket server!");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WS Message:", data.type);

      setAlerts((prev) => {
        const prevAlerts = prev || [];
        // Clone the array to guarantee a React state update
        let updatedAlerts = [...prevAlerts];

        switch (data.type) {
          case "new_alert":
            // Add the new alert, checking for duplicates just in case
            if (
              !updatedAlerts.find((a) => String(a.id) === String(data.alert.id))
            ) {
              updatedAlerts = [data.alert, ...updatedAlerts];
            }
            break;

          case "updated_alert":
          case "alert_read":
            // Replace the outdated alert with the new incoming data
            updatedAlerts = updatedAlerts.map((a) =>
              String(a.id) === String(data.alert.id) ? data.alert : a,
            );
            break;

          case "alert_deleted":
            // Filter out the deleted alert
            updatedAlerts = updatedAlerts.filter(
              (a) => String(a.id) !== String(data.alert_id),
            );
            break;
        }

        setTimeout(() => saveAlertsToCache(updatedAlerts), 0);

        return updatedAlerts;
      });
    };

    ws.onerror = (e) => {
      console.log("🔴 WebSocket error:", e);
    };

    // Cleanup connection on component unmount
    return () => {
      ws.close();
    };
  }, [setAlerts]);
};
