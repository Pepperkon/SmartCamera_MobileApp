const IP = process.env.EXPO_PUBLIC_SERVER_IP || "127.0.0.1";

export const API_URL = `http://${IP}:8000`;
export const WS_URL = `ws://${IP}:8000`;
