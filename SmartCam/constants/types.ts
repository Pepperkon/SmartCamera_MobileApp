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
  confidence: number | null;
  detection_confidence?: number | null;
  suggested_match?: SuggestedMatch | null;
  location?: [number, number, number, number] | null;
}

export interface SuggestedMatch {
  user_id: number;
  name: string;
  avatar_url: string | null;
  similarity: number;
  is_permanent: true;
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
  suggested_match?: SuggestedMatch | null;
}

export interface UserMergeResult {
  target_user: User;
  moved_alerts: number;
  added_templates: number;
  warnings?: string[];
}
