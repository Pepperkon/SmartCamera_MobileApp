import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Alert,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import React, { useEffect, useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { COLORS, SPACING } from "@/constants/theme";
import { GlobalStyles } from "@/styles/GlobalStyles";
import { useRouter } from "expo-router";
import Checkbox from "@/components/ui/checkbox";
import {
  AlertFilters,
  DEFAULT_ALERT_FILTERS,
  getAlertFilters,
  saveAlertFilters,
} from "@/services/alertFilterService";

function Filters() {
  const router = useRouter();
  const [filters, setFilters] =
    useState<AlertFilters>(DEFAULT_ALERT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    getAlertFilters().then((savedFilters) => {
      if (active) setFilters(savedFilters);
      if (active) setLoading(false);
    });

    return () => {
      active = false;
    };
  }, []);

  const setFilter = (key: keyof AlertFilters, value: boolean) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const handleApply = async () => {
    setSaving(true);
    try {
      await saveAlertFilters(filters);
      router.back();
    } catch {
      Alert.alert("Error", "Could not save alert filters.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={GlobalStyles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="white" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={GlobalStyles.container}>
      <View style={styles.container}>
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.filterSections}
        >
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Temporary status</Text>
            <View style={styles.checkboxContainer}>
              <Checkbox
                text="Temporary"
                isSelected={filters.showTemporary}
                onSelectionChange={(value) =>
                  setFilter("showTemporary", value)
                }
                containerStyle={styles.checkbox}
              />
              <Checkbox
                text="Permanent"
                isSelected={filters.showPermanent}
                onSelectionChange={(value) => setFilter("showPermanent", value)}
                containerStyle={styles.checkbox}
              />
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Trust status</Text>
            <View style={styles.checkboxContainer}>
              <Checkbox
                text="Trusted"
                isSelected={filters.showTrusted}
                onSelectionChange={(value) => setFilter("showTrusted", value)}
                containerStyle={styles.checkbox}
              />
              <Checkbox
                text="Not trusted"
                isSelected={filters.showUntrusted}
                onSelectionChange={(value) =>
                  setFilter("showUntrusted", value)
                }
                containerStyle={styles.checkbox}
              />
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Other</Text>
            <View style={styles.checkboxContainer}>
              <Checkbox
                text="Unread only"
                isSelected={filters.unreadOnly}
                onSelectionChange={(value) => setFilter("unreadOnly", value)}
                containerStyle={styles.checkbox}
              />
            </View>
          </View>
        </ScrollView>

        <View style={styles.actions}>
          <Pressable
            style={[styles.button, styles.resetButton]}
            onPress={() => setFilters({ ...DEFAULT_ALERT_FILTERS })}
            disabled={saving}
          >
            <Text style={styles.buttonText}>Reset</Text>
          </Pressable>
          <Pressable
            style={[styles.button, styles.applyButton]}
            onPress={handleApply}
            disabled={saving}
          >
            <Text style={styles.buttonText}>
              {saving ? "Saving..." : "Apply"}
            </Text>
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    width: "95%",
    justifyContent: "center",
  },
  container: {
    flex: 1,
    backgroundColor: COLORS.primary,
    width: "95%",
    borderRadius: 20,
    padding: SPACING.m,
  },
  scrollView: {
    flex: 1,
  },
  filterSections: {
    gap: SPACING.l,
    paddingBottom: SPACING.m,
  },
  section: {
    gap: SPACING.s,
  },
  sectionTitle: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "600",
  },
  checkboxContainer: {
    gap: SPACING.s,
  },
  checkbox: {
    width: "100%",
    marginHorizontal: 0,
  },
  actions: {
    flexDirection: "row",
    gap: SPACING.s,
    marginTop: SPACING.m,
  },
  button: {
    flex: 1,
    alignItems: "center",
    paddingVertical: SPACING.m,
    borderRadius: 10,
  },
  resetButton: {
    backgroundColor: "#254E6B",
  },
  applyButton: {
    backgroundColor: COLORS.secondary,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "600",
  },
});

export default Filters;
