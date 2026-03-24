import { COLORS, SPACING } from "@/constants/theme";
import { StyleSheet } from "react-native";

export const GlobalStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    alignItems: "center",
    padding: SPACING.m,
  },

  singleEntry: {
    width: "100%",
    paddingVertical: SPACING.m,
    paddingHorizontal: SPACING.m,
    minHeight: 80,

    borderRadius: 15,

    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: COLORS.primary,

    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },

  checkbox: {
    width: "50%",
    paddingVertical: SPACING.m,
    paddingHorizontal: SPACING.m,
    marginHorizontal: SPACING.xs,

    minHeight: 50,

    borderRadius: 15,

    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: COLORS.secondary,

    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },

  text_primary: {
    fontSize: 40,
    fontWeight: "600",
    color: "#ffff",
  },

  text_secondary: {
    fontSize: 30,
    fontWeight: "600",
    color: "#ffff",
  },

  text_small: {
    fontSize: 20,
    fontWeight: "400",
    color: "#ffff",
  },

  pressed: {
    backgroundColor: COLORS.secondary,
    transform: [{ scale: 0.98 }],
  },

  mark: {
    position: "absolute",
    top: -8,
    right: -8,
    zIndex: 1,
  },
});
