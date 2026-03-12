// types/alert.ts
import { ImageSourcePropType } from "react-native";

export interface AlertItem {
  id: string;
  title: string;
  image: ImageSourcePropType; // Obsłuży zarówno require(...), jak i { uri: '...' }
  time: string;
  isNew: boolean;
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
}
