import { useSyncExternalStore } from "react";
import { useColorScheme as useRNColorScheme } from "react-native";

/**
 * To support static rendering, this value needs to be re-calculated on the client side for web
 */
 const emptySubscribe = () => () => {};

 export function useColorScheme() {
   const hasHydrated = useSyncExternalStore(
     emptySubscribe,
     () => true,  // Client-side value after moun
     () => false, // Server-side value (SSR)
   );

   const colorScheme = useRNColorScheme();

   if (hasHydrated) {
     return colorScheme;
   }

   return 'light';
 }
