import { useEffect } from "react";
import { AlertItem } from "@/constants/types";
import { saveAlertsToCache } from "@/services/alertService";
import { useServer } from "@/providers/ServerProvider";

// Connects to the alerts WebSocket and directly updates the parent component's state
export const useAlertsWebSocket = (
  setAlerts: React.Dispatch<React.SetStateAction<AlertItem[]>>,
) => {
  const { wsUrl } = useServer();

  useEffect(() => {
    const ws = new WebSocket(`${wsUrl}/ws/alerts`);

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

          case "user_trust_updated":
            // Update trust status across all alerts for this recognized user
            updatedAlerts = updatedAlerts.map((a) =>
              a.recognised_user_id !== null &&
              a.recognised_user_id !== undefined &&
              String(a.recognised_user_id) === String(data.user_id)
                ? {
                    ...a,
                    recognised_user_is_trusted: data.is_trusted,
                    recognised_user_is_temporary: data.is_temporary,
                    user: { is_temporary: data.is_temporary },
                  }
                : a,
            );
            break;

          case "user_merged":
            updatedAlerts = updatedAlerts.map((a) =>
              String(a.recognised_user_id) === String(data.source_user_id)
                ? {
                    ...a,
                    title: `Recognized: ${data.target_name}`,
                    recognised_user_id: data.target_user_id,
                    recognised_user_is_trusted: data.target_is_trusted,
                    recognised_user_is_temporary: false,
                    user: { is_temporary: false },
                  }
                : a,
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
  }, [setAlerts, wsUrl]);
};
