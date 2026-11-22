// types/alert.ts
import { ImageSourcePropType } from "react-native";

export interface AlertItem {
  id: string;
  title: string;
  image: ImageSourcePropType;
  time: string;
  date?: string;
  isNew: boolean;
  recognised_user_id?: number | null;
  recognised_user_is_trusted?: boolean | null;
  recognised_user_is_temporary?: boolean | null;
  user?: {
    is_temporary: boolean | null;
  } | null;
  confidence: number;
  location?: [number, number, number, number] | null;
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
  image: any;
  alerts: AlertItem[];
  is_trusted: boolean;
  is_temporary: boolean;
}
