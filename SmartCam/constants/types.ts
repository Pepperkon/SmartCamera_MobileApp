// types/alert.ts
import { ImageSourcePropType } from "react-native";

export interface AlertItem {
  id: string;
  title: string;
  image: ImageSourcePropType; // Obsłuży zarówno require(...), jak i { uri: '...' }
  time: string;
  date: string;
  isNew: boolean;
  captured_user_id?: number;
}

export interface UserImage {
  id: number;
  filepath: string;
  user_id: number;
}

export interface User {
  id: string;
  name: string;
  images: UserImage[];
  alerts: AlertItem[];
}
