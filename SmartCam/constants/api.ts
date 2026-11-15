export function normalizeServerHost(raw: string): string {
  const cleaned = raw
    .trim()
    .replace(/^(https?|wss?):\/\//i, "")
    .replace(/\/.*$/, "")
    .replace(/:\d+$/, "")
    .trim();

  return cleaned || "127.0.0.1";
}

export const DEFAULT_SERVER_IP = normalizeServerHost(
  process.env.EXPO_PUBLIC_SERVER_IP || "127.0.0.1",
);

export let API_URL = `http://${DEFAULT_SERVER_IP}:8000`;
export let WS_URL = `ws://${DEFAULT_SERVER_IP}:8000`;

export function setServerHost(rawHost: string): string {
  const host = normalizeServerHost(rawHost);
  API_URL = `http://${host}:8000`;
  WS_URL = `ws://${host}:8000`;
  return host;
}
