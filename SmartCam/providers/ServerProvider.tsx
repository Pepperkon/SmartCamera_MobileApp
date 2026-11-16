import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  DEFAULT_SERVER_IP,
  normalizeServerHost,
  setServerHost,
} from "@/constants/api";

const STORAGE_KEY = "@smartcam_server_ip";

type ServerContextValue = {
  serverIp: string;
  apiUrl: string;
  wsUrl: string;
  updateServerIp: (newIp: string) => Promise<string>;
  testServerConnection: (
    candidateIp: string,
  ) => Promise<{ ok: boolean; message: string }>;
};

const ServerContext = createContext<ServerContextValue | undefined>(undefined);

export function ServerProvider({ children }: { children: ReactNode }) {
  const [serverIp, setServerIp] = useState<string>(DEFAULT_SERVER_IP);
  const [isReady, setIsReady] = useState<boolean>(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((savedIp) => {
        if (savedIp) {
          const applied = setServerHost(savedIp);
          setServerIp(applied);
        }
      })
      .catch((e) => console.log("Failed to load server IP:", e))
      .finally(() => setIsReady(true));
  }, []);

  const updateServerIp = async (newIp: string): Promise<string> => {
    const applied = setServerHost(newIp);
    await AsyncStorage.setItem(STORAGE_KEY, applied);
    setServerIp(applied);
    return applied;
  };

  const testServerConnection = async (
    candidateIp: string,
  ): Promise<{ ok: boolean; message: string }> => {
    const host = normalizeServerHost(candidateIp);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    try {
      const response = await fetch(`http://${host}:8000/alerts`, {
        method: "GET",
        signal: controller.signal,
      });

      if (response.ok) {
        return {
          ok: true,
          message: `Connected to server (${host}:8000)`,
        };
      }
      return {
        ok: false,
        message: `Server returned HTTP ${response.status}`,
      };
    } catch (error) {
      const isTimeout =
        error instanceof Error && error.name === "AbortError";
      return {
        ok: false,
        message: isTimeout
          ? `Connection timed out (${host}:8000)`
          : `Cannot reach ${host}:8000 (check Wi-Fi or Tailscale)`,
      };
    } finally {
      clearTimeout(timeoutId);
    }
  };

  if (!isReady) {
    return null;
  }

  return (
    <ServerContext.Provider
      value={{
        serverIp,
        apiUrl: `http://${serverIp}:8000`,
        wsUrl: `ws://${serverIp}:8000`,
        updateServerIp,
        testServerConnection,
      }}
    >
      {children}
    </ServerContext.Provider>
  );
}

export function useServer() {
  const context = useContext(ServerContext);
  if (!context) {
    throw new Error("useServer must be used within ServerProvider.");
  }
  return context;
}
