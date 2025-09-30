import React, { useState, useEffect } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useAuth } from "./../contexts/AuthContext";
import { ExecutionLog, getExecutionLogsForUser as apiGetExecutionLogsForUser } from "../utils/api";
import { Colors } from "../constants/colors";
import { TextStyles } from "../constants/typography";
import CustomButton from "./ui/Button";
import Card from "./ui/Card";

type Activity = {
  id: string;
  timestamp: string;
  action: string;
  service: string;
  status: "success" | "failed" | "processing";
  details: string;
};

export default function ActivityLogScreen() {
  const auth = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadActivities = async () => {
    if (!auth.token) {
      return;
    }
    // Only show loading indicator if this is initial load
    const shouldShowLoading = activities.length === 0;
    if (shouldShowLoading) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    
    try {
      // In a real implementation, this would call an actual activity logs endpoint
      // For now, since the API might not have a specific activity logs endpoint,
      // we'll fetch execution logs which represent user activities
      const executionLogs = await apiGetExecutionLogsForUser(auth.token);
      
      // Transform execution logs to activity format
      const transformedActivities: Activity[] = executionLogs.map((log: any) => ({
        id: log.id,
        timestamp: log.timestamp,
        action: log.status === "success" ? "AREA executed" : "AREA execution failed",
        service: `Area: ${log.area_id.substring(0, 8)}...`, // Show the area ID as the service
        status: log.status === "success" ? "success" : "failed",
        details: log.output || log.error_message || "AREA execution completed",
      }));
      
      setActivities(transformedActivities);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load activity log.";
      setError(message);
      if (message.includes("401")) {
        auth.logout();
        return;
      }
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void loadActivities();
  }, [auth]);

  const getStatusColor = (status: Activity["status"]) => {
    switch (status) {
      case "success":
        return { color: Colors.success, textColor: Colors.backgroundLight };
      case "failed":
        return { color: Colors.error, textColor: Colors.backgroundLight };
      case "processing":
        return { color: Colors.warning, textColor: Colors.textDark };
      default:
        return { color: Colors.muted, textColor: Colors.textDark };
    }
  };

  if (loading && activities.length === 0) { // Only show full loading screen if no activities exist yet
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Activity Log</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Activity Log</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Retry" onPress={() => void loadActivities()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  if (activities.length === 0) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Activity Log</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.muted}>No recent activity found.</Text>
        </Card>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Activity Log</Text>
      <Text style={[styles.smallMuted, { marginHorizontal: 16, marginBottom: 8 }]}>
        Your account activity history
      </Text>
      <ScrollView 
        style={{ flex: 1, padding: 16 }}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={loadActivities} />
        }
      >
        {activities.map((activity) => {
          const statusConfig = getStatusColor(activity.status);
          return (
            <Card key={activity.id} style={{ marginBottom: 16 }}>
              <View style={styles.rowBetween}>
                <View style={{ flex: 1, marginRight: 12 }}>
                  <Text style={styles.cardTitle} numberOfLines={1}>
                    {activity.action}
                  </Text>
                  <Text style={styles.muted} numberOfLines={1}>
                    {activity.service}
                  </Text>
                  <Text style={[styles.smallMuted, { fontSize: 11, marginTop: 4 }]}>
                    {activity.details}
                  </Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <View
                    style={{
                      backgroundColor: statusConfig.color,
                      paddingHorizontal: 8,
                      paddingVertical: 4,
                      borderRadius: 4,
                      marginBottom: 4,
                    }}
                  >
                    <Text style={{ color: statusConfig.textColor, fontSize: 12 }}>
                      {activity.status.charAt(0).toUpperCase() + activity.status.slice(1)}
                    </Text>
                  </View>
                  <Text style={styles.smallMuted}>
                    {new Date(activity.timestamp).toLocaleString()}
                  </Text>
                </View>
              </View>
            </Card>
          );
        })}
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
    justifyContent: "center" as const,
  },
  h1: { 
    ...TextStyles.h2,
    color: Colors.textDark,
    marginBottom: 12,
  },
  cardTitle: { 
    ...TextStyles.h3,
    color: Colors.textDark,
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
    flexDirection: "row" as "row",
    alignItems: "flex-start" as "flex-start",
    justifyContent: "space-between" as const,
  },
  errorText: { 
    color: Colors.error, 
    textAlign: "center" as const,
    ...TextStyles.small,
  },
};