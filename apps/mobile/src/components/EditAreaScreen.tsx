import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  SafeAreaView,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useAuth, type ExecutionLog, requestJson } from "../..//App";
import { Colors } from "../constants/colors";
import { TextStyles } from "../constants/typography";
import { useNavigation } from "@react-navigation/native";
import CustomButton from "./ui/Button";
import Input from "./ui/Input";
import Card from "./ui/Card";

type Area = {
  id: string;
  name: string;
  trigger_service: string;
  trigger_action: string;
  reaction_service: string;
  reaction_action: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export default function EditAreaScreen({ route }: { route: any }) {
  const { areaId } = route.params;
  const auth = useAuth();
  const navigation = useNavigation();
  const [area, setArea] = useState<Area | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [triggerService, setTriggerService] = useState("");
  const [trigger, setTrigger] = useState("");
  const [actionService, setActionService] = useState("");
  const [action, setAction] = useState("");

  const loadArea = useCallback(async () => {
    if (!auth.token || !areaId) {
      return;
    }
    setLoading(true);
    try {
      const data = await requestJson<Area>(`/areas/${areaId}`, { method: "GET" }, auth.token);
      
      setArea(data);
      setName(data.name);
      setTriggerService(data.trigger_service);
      setTrigger(data.trigger_action);
      setActionService(data.reaction_service);
      setAction(data.reaction_action);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load area.";
      setError(message);
      if (message.includes("401")) {
        auth.logout();
        return;
      }
      Alert.alert("Error", message);
    } finally {
      setLoading(false);
    }
  }, [auth, areaId]);

  useEffect(() => {
    void loadArea();
  }, [loadArea]);

  const updateArea = async () => {
    if (!auth.token || !areaId) {
      return;
    }
    setSaving(true);
    try {
      await requestJson(`/areas/${areaId}`, {
        method: "PUT",
        body: JSON.stringify({
          name,
          trigger_service: triggerService,
          trigger_action: trigger,
          reaction_service: actionService,
          reaction_action: action,
        }),
      }, auth.token);
      
      Alert.alert("Success", "Area updated successfully!");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update area.";
      if (message.includes("401")) {
        auth.logout();
        return;
      }
      Alert.alert("Update failed", message);
    } finally {
      setSaving(false);
    }
  };

  const canSave = name.trim() !== "" && triggerService && trigger && actionService && action;

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Edit AREA</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Edit AREA</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Retry" onPress={() => void loadArea()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  if (!area) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Edit AREA</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.muted}>Area not found.</Text>
        </Card>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Edit AREA</Text>
      <ScrollView style={{ flex: 1, padding: 16 }}>
        <Card>
          <View style={{ marginBottom: 16 }}>
            <Text style={styles.cardTitle}>Area Name</Text>
            <Input
              value={name}
              onChangeText={setName}
              placeholder="Enter area name"
              editable={!saving}
            />
          </View>

          <View style={{ marginBottom: 16 }}>
            <Text style={styles.cardTitle}>Trigger Service</Text>
            <Input
              value={triggerService}
              onChangeText={setTriggerService}
              placeholder="Trigger service"
              editable={!saving}
            />
          </View>

          <View style={{ marginBottom: 16 }}>
            <Text style={styles.cardTitle}>Trigger</Text>
            <Input
              value={trigger}
              onChangeText={setTrigger}
              placeholder="Trigger action"
              editable={!saving}
            />
          </View>

          <View style={{ marginBottom: 16 }}>
            <Text style={styles.cardTitle}>Action Service</Text>
            <Input
              value={actionService}
              onChangeText={setActionService}
              placeholder="Action service"
              editable={!saving}
            />
          </View>

          <View style={{ marginBottom: 16 }}>
            <Text style={styles.cardTitle}>Action</Text>
            <Input
              value={action}
              onChangeText={setAction}
              placeholder="Action to perform"
              editable={!saving}
            />
          </View>

          <View style={{ flexDirection: "row" }}>
            <CustomButton 
              title="Cancel" 
              onPress={() => navigation.goBack()} 
              variant="outline"
              style={{ flex: 1, marginRight: 8 }}
              disabled={saving}
            />
            <CustomButton 
              title={saving ? "Saving..." : "Save"} 
              onPress={updateArea} 
              variant="default"
              style={{ flex: 1, marginLeft: 8 }}
              disabled={!canSave || saving}
            />
          </View>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = {
  screen: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight, 
    padding: 16,
  },
  centered: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight, 
    padding: 16, 
    justifyContent: "center",
  },
  h1: { 
    ...TextStyles.h2,
    color: Colors.textDark,
    marginBottom: 12,
  },
  cardTitle: { 
    ...TextStyles.h3,
    color: Colors.textDark,
    marginBottom: 4,
  },
  muted: { 
    color: Colors.mutedForeground, 
    marginTop: 4,
    ...TextStyles.small,
  },
  smallMuted: { 
    color: Colors.mutedForeground, 
    ...TextStyles.small,
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  errorText: { 
    color: Colors.error, 
    textAlign: "center",
    ...TextStyles.small,
  },
};