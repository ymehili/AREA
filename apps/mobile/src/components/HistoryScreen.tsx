import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  Text,
  View,
  Modal,
  TouchableOpacity,
} from "react-native";
import { useAuth } from "./../contexts/AuthContext";
import { getExecutionLogsForUser, ExecutionLog } from "../utils/api";
import { Colors } from "../constants/colors";
import { TextStyles } from "../constants/typography";
import CustomButton from "./ui/Button";
import Card from "./ui/Card";

export default function HistoryScreen() {
  const auth = useAuth();
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<ExecutionLog | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadExecutionLogs = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    // Only show loading indicator if this is initial load
    const shouldShowLoading = executionLogs.length === 0;
    if (shouldShowLoading) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    
    try {
      const logs = await getExecutionLogsForUser(auth.token);
      // Sort logs by timestamp, newest first
      const sortedLogs = logs.sort(
        (a: ExecutionLog, b: ExecutionLog) => 
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      setExecutionLogs(sortedLogs);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load execution logs.";
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
  }, [auth, executionLogs.length]);

  useEffect(() => {
    void loadExecutionLogs();
  }, [loadExecutionLogs]);

  const getStatusColor = (status: string): { color: string; textColor: string } => {
    const lowerStatus = status.toLowerCase();
    switch (lowerStatus) {
      case "success":
        return { color: Colors.success, textColor: Colors.backgroundLight };
      case "failed":
        return { color: Colors.error, textColor: Colors.backgroundLight };
      case "running":
        return { color: Colors.warning, textColor: Colors.textDark };
      case "pending":
        return { color: Colors.muted, textColor: Colors.textDark };
      default:
        return { color: Colors.secondary, textColor: Colors.textDark };
    }
  };

  const handleLogPress = (log: ExecutionLog) => {
    setSelectedLog(log);
    setIsModalVisible(true);
  };

  if (loading && executionLogs.length === 0) { // Only show full loading screen if no logs exist yet
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Execution History</Text>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Execution History</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.errorText}>{error}</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Retry" onPress={() => void loadExecutionLogs()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  if (executionLogs.length === 0) {
    return (
      <SafeAreaView style={styles.screen}>
        <Text style={styles.h1}>Execution History</Text>
        <Card style={{ margin: 16 }}>
          <Text style={styles.muted}>No execution logs yet.</Text>
          <View style={{ height: 12 }} />
          <CustomButton title="Refresh" onPress={() => void loadExecutionLogs()} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.h1}>Execution History</Text>
      <Text style={[styles.smallMuted, { marginHorizontal: 16, marginBottom: 8 }]}>
        {executionLogs.length} {executionLogs.length === 1 ? "log" : "logs"}
      </Text>
      <ScrollView 
        style={{ flex: 1, padding: 16 }}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={loadExecutionLogs} />
        }
      >
        {executionLogs.map((log) => {
          const statusConfig = getStatusColor(log.status);
          return (
            <TouchableOpacity
              key={log.id}
              onPress={() => handleLogPress(log)}
              style={{ marginBottom: 16 }}
            >
              <Card>
                <View style={styles.rowBetween}>
                  <Text style={styles.cardTitle}>
                    Execution #{log.id.substring(0, 8)}
                  </Text>
                  <View
                    style={{
                      backgroundColor: statusConfig.color,
                      paddingHorizontal: 8,
                      paddingVertical: 4,
                      borderRadius: 4,
                    }}
                  >
                    <Text style={{ color: statusConfig.textColor, fontSize: 12 }}>
                      {log.status}
                    </Text>
                  </View>
                </View>
                <Text style={styles.muted}>
                  AREA: {log.area_id.substring(0, 6)}...
                </Text>
                <Text style={styles.smallMuted}>
                  {new Date(log.timestamp).toLocaleString()}
                </Text>
                {log.output && (
                  <View style={{ marginTop: 8 }}>
                    <Text style={styles.smallMuted}>Output:</Text>
                    <Text style={[styles.smallMuted, { fontSize: 11 }]} numberOfLines={2}>
                      {log.output}
                    </Text>
                  </View>
                )}
                {log.error_message && (
                  <View style={{ marginTop: 8 }}>
                    <Text style={[styles.smallMuted, { color: Colors.error }]}>
                      Error: {log.error_message}
                    </Text>
                  </View>
                )}
              </Card>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Detailed Log Modal */}
      <Modal
        animationType="slide"
        transparent={false}
        visible={isModalVisible}
        onRequestClose={() => setIsModalVisible(false)}
      >
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Execution Details</Text>
            <CustomButton 
              title="Close" 
              onPress={() => setIsModalVisible(false)} 
              variant="outline" 
            />
          </View>
          
          {selectedLog && (
            <ScrollView style={{ flex: 1, padding: 16 }}>
              <Card style={{ marginBottom: 16 }}>
                <Text style={styles.cardTitle}>Execution Information</Text>
                <View style={styles.detailRow}>
                  <Text style={styles.detailLabel}>ID:</Text>
                  <Text style={styles.detailValue}>{selectedLog.id}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailLabel}>Area ID:</Text>
                  <Text style={styles.detailValue}>{selectedLog.area_id}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailLabel}>Status:</Text>
                  <View
                    style={[
                      styles.statusBadge,
                      { backgroundColor: getStatusColor(selectedLog.status).color }
                    ]}
                  >
                    <Text style={{ color: getStatusColor(selectedLog.status).textColor }}>
                      {selectedLog.status}
                    </Text>
                  </View>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailLabel}>Timestamp:</Text>
                  <Text style={styles.detailValue}>
                    {new Date(selectedLog.timestamp).toLocaleString()}
                  </Text>
                </View>
              </Card>

              {selectedLog.step_details && (
                <Card style={{ marginBottom: 16 }}>
                  <Text style={styles.cardTitle}>Step Details</Text>
                  <View style={styles.detailContainer}>
                    <Text style={styles.detailValue}>
                      {JSON.stringify(selectedLog.step_details, null, 2)}
                    </Text>
                  </View>
                </Card>
              )}

              {selectedLog.output && (
                <Card style={{ marginBottom: 16 }}>
                  <Text style={styles.cardTitle}>Output</Text>
                  <View style={styles.detailContainer}>
                    <Text style={styles.detailValue}>{selectedLog.output}</Text>
                  </View>
                </Card>
              )}

              {selectedLog.error_message && (
                <Card style={{ marginBottom: 16, borderColor: Colors.error }}>
                  <Text style={[styles.cardTitle, { color: Colors.error }]}>Error Message</Text>
                  <View style={styles.detailContainer}>
                    <Text style={[styles.detailValue, { color: Colors.error }]}>
                      {selectedLog.error_message}
                    </Text>
                  </View>
                </Card>
              )}
            </ScrollView>
          )}
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = {
  screen: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight, 
    padding: 16,
  },
  modalScreen: { 
    flex: 1, 
    backgroundColor: Colors.backgroundLight,
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
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  modalTitle: { 
    ...TextStyles.h2,
    color: Colors.textDark,
    fontSize: 20,
  },
  cardTitle: { 
    ...TextStyles.h3,
    color: Colors.textDark,
    marginBottom: 12,
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
    alignItems: "center" as "center",
    justifyContent: "space-between" as const,
    marginBottom: 8,
  },
  detailRow: {
    flexDirection: "row" as "row",
    justifyContent: "space-between" as "space-between",
    paddingVertical: 4,
  },
  detailLabel: {
    flex: 1,
    fontSize: 14,
    color: Colors.mutedForeground,
    ...TextStyles.body,
  },
  detailValue: {
    flex: 2,
    fontSize: 14,
    color: Colors.textDark,
    textAlign: "right" as "right",
    ...TextStyles.body,
  },
  detailContainer: {
    padding: 12,
    backgroundColor: Colors.cardLight,
    borderRadius: 4,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  errorText: { 
    color: Colors.error, 
    textAlign: "center" as const,
    ...TextStyles.small,
  },
};