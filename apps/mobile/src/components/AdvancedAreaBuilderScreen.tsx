import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  Alert,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useAuth } from '../contexts/AuthContext';
import { Colors } from '../constants/colors';
import { TextStyles, FontFamilies } from '../constants/typography';
import CustomButton from './ui/Button';
import Input from './ui/Input';
import Card from './ui/Card';
import StepCard from './area-builder/StepCard';
import StepConfigModal from './area-builder/StepConfigModal';
import {
  NodeData,
  TriggerNodeData,
  ActionNodeData,
  ConditionNodeData,
  DelayNodeData,
  isTriggerNode,
  isActionNode,
} from '../types/area-builder';

const API_BASE_URL = resolveApiBaseUrl();

function resolveApiBaseUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_API_URL;
  
  if (explicit && typeof explicit === "string" && explicit.trim() !== "") {
    let url = explicit.replace(/\/$/, "");
    
    // If the explicit URL uses localhost, adjust it for the platform
    // This ensures Android uses 10.0.2.2 and iOS uses localhost
    if (Platform.OS === "android" && url.includes("localhost")) {
      url = url.replace("localhost", "10.0.2.2");
    } else if (Platform.OS === "ios" && url.includes("10.0.2.2")) {
      url = url.replace("10.0.2.2", "localhost");
    }
    
    return url;
  }
  
  // Platform-specific defaults
  if (Platform.OS === "android") {
    // Android emulator maps host loopback to 10.0.2.2
    return "http://10.0.2.2:8080/api/v1";
  }
  // iOS Simulator usually reaches host via localhost
  return "http://localhost:8080/api/v1";
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const bodyIsJson = options.body && !(options.body instanceof FormData) && !headers.has('Content-Type');
  if (bodyIsJson) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    throw new Error('Unauthorized');
  }
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

const AdvancedAreaBuilderScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const auth = useAuth();
  const areaId = route.params?.areaId;
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');
  const [steps, setSteps] = useState<NodeData[]>([]);
  const [selectedStep, setSelectedStep] = useState<NodeData | null>(null);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [addMenuVisible, setAddMenuVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load area data if editing
  useEffect(() => {
    if (areaId && auth.token) {
      setLoading(true);
      requestJson<any>(`/areas/${areaId}`, { method: 'GET' }, auth.token)
        .then((area) => {
          setAreaName(area.name || '');
          setAreaDescription(area.description || '');

          // Convert area steps to NodeData format
          if (area.steps && Array.isArray(area.steps)) {
            const loadedSteps: NodeData[] = area.steps.map((step: any, index: number) => {
              const baseStep = {
                id: step.id || `${step.step_type}-${Date.now()}-${index}`,
                label: step.config?.label || `${step.step_type} Step`,
                type: step.step_type as 'trigger' | 'action' | 'condition' | 'delay',
                description: step.config?.description || '',
                order: step.order ?? index,
                connections: step.config?.targets || [],
                config: step.config || {},
              };

              if (step.step_type === 'trigger' || step.step_type === 'action') {
                // Extract params from config (they're flattened in)
                // Exclude standard config properties to get just the params
                const standardConfigKeys = ['clientId', 'label', 'description', 'targets', 'position', 'conditionType', 'conditionValue', 'duration', 'unit'];
                const params: Record<string, any> = {};
                if (step.config) {
                  Object.keys(step.config).forEach(key => {
                    if (!standardConfigKeys.includes(key)) {
                      params[key] = step.config![key];
                    }
                  });
                }

                return {
                  ...baseStep,
                  serviceId: step.service || '',
                  actionId: step.action || '',
                  params,
                } as TriggerNodeData | ActionNodeData;
              } else if (step.step_type === 'condition') {
                return {
                  ...baseStep,
                  conditionType: step.config?.conditionType || 'simple',
                  conditionValue: step.config?.conditionValue || '',
                } as ConditionNodeData;
              } else if (step.step_type === 'delay') {
                return {
                  ...baseStep,
                  duration: step.config?.duration || 1,
                  unit: step.config?.unit || 'seconds',
                } as DelayNodeData;
              }
              return baseStep as NodeData;
            });
            setSteps(loadedSteps);
          }
        })
        .catch((error) => {
          Alert.alert('Error', `Failed to load area: ${error.message}`);
          navigation.goBack();
        })
        .finally(() => setLoading(false));
    }
  }, [areaId, auth.token, navigation]);

  const addStep = useCallback((type: 'trigger' | 'action' | 'condition' | 'delay') => {
    const newStepId = `${type}-${Date.now()}`;
    let newStep: NodeData;

    switch (type) {
      case 'trigger':
        newStep = {
          id: newStepId,
          label: 'New Trigger',
          type: 'trigger',
          serviceId: '',
          actionId: '',
          order: steps.length,
        } as TriggerNodeData;
        break;
      case 'action':
        newStep = {
          id: newStepId,
          label: 'New Action',
          type: 'action',
          serviceId: '',
          actionId: '',
          order: steps.length,
        } as ActionNodeData;
        break;
      case 'condition':
        newStep = {
          id: newStepId,
          label: 'New Condition',
          type: 'condition',
          conditionType: 'simple',
          conditionValue: '',
          order: steps.length,
        } as ConditionNodeData;
        break;
      case 'delay':
        newStep = {
          id: newStepId,
          label: 'New Delay',
          type: 'delay',
          duration: 1,
          unit: 'seconds',
          order: steps.length,
        } as DelayNodeData;
        break;
    }

    setSteps([...steps, newStep]);
    setAddMenuVisible(false);
  }, [steps]);

  const handleEditStep = useCallback((step: NodeData) => {
    setSelectedStep(step);
    setConfigModalVisible(true);
  }, []);

  const handleSaveStep = useCallback((updatedStep: NodeData) => {
    setSteps(steps.map(s => s.id === updatedStep.id ? updatedStep : s));
    setSelectedStep(null);
  }, [steps]);

  const handleDeleteStep = useCallback((stepId: string) => {
    Alert.alert(
      'Delete Step',
      'Are you sure you want to delete this step?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            const newSteps = steps.filter(s => s.id !== stepId);
            // Reorder remaining steps
            const reorderedSteps = newSteps.map((s, index) => ({ ...s, order: index }));
            setSteps(reorderedSteps);
          },
        },
      ]
    );
  }, [steps]);

  const handleMoveUp = useCallback((index: number) => {
    if (index === 0) return;
    const newSteps = [...steps];
    [newSteps[index - 1], newSteps[index]] = [newSteps[index], newSteps[index - 1]];
    const reorderedSteps = newSteps.map((s, i) => ({ ...s, order: i }));
    setSteps(reorderedSteps);
  }, [steps]);

  const handleMoveDown = useCallback((index: number) => {
    if (index === steps.length - 1) return;
    const newSteps = [...steps];
    [newSteps[index], newSteps[index + 1]] = [newSteps[index + 1], newSteps[index]];
    const reorderedSteps = newSteps.map((s, i) => ({ ...s, order: i }));
    setSteps(reorderedSteps);
  }, [steps]);

  const handleSave = useCallback(async () => {
    if (!areaName) {
      Alert.alert('Validation Error', 'Please enter an area name');
      return;
    }

    if (!auth.token) {
      Alert.alert('Authentication Error', 'User not authenticated');
      return;
    }

    const triggerStep = steps.find(s => s.type === 'trigger');
    if (!triggerStep) {
      Alert.alert('Validation Error', 'Please add a trigger to your area');
      return;
    }

    setSaving(true);
    try {
      const castedTriggerNodeData = triggerStep as NodeData;
      const triggerParams = isTriggerNode(castedTriggerNodeData) ? castedTriggerNodeData.params : undefined;
      
      const areaData = {
        name: areaName,
        description: areaDescription,
        is_active: true,
        trigger_service: castedTriggerNodeData.type === 'trigger' ? (castedTriggerNodeData as TriggerNodeData).serviceId || 'manual' : 'manual',
        trigger_action: castedTriggerNodeData.type === 'trigger' ? (castedTriggerNodeData as TriggerNodeData).actionId || 'trigger' : 'trigger',
        trigger_params: triggerParams,
        reaction_service: 'manual',
        reaction_action: 'reaction',
        steps: steps.map((step, index) => {
          // Build step config - flatten params into config like the web app does
          const stepConfig: Record<string, any> = {
            ...(step.config || {}),
            clientId: step.id,
            label: step.label,
            description: step.description,
            targets: step.connections || [],
          };

          // Include params for trigger and action steps (flatten them into config)
          if (isTriggerNode(step) || isActionNode(step)) {
            if (step.params && Object.keys(step.params).length > 0) {
              // Flatten params into config
              Object.assign(stepConfig, step.params);
            }
          }

          // Include condition-specific config
          if (step.type === 'condition') {
            const conditionStep = step as ConditionNodeData;
            stepConfig.conditionType = conditionStep.conditionType;
            stepConfig.conditionValue = conditionStep.conditionValue;
          }

          // Include delay-specific config
          if (step.type === 'delay') {
            const delayStep = step as DelayNodeData;
            stepConfig.duration = delayStep.duration;
            stepConfig.unit = delayStep.unit;
          }

          return {
            step_type: step.type as 'trigger' | 'action' | 'condition' | 'delay',
            order: index,
            service: (isTriggerNode(step) || isActionNode(step)) ? step.serviceId : null,
            action: (isTriggerNode(step) || isActionNode(step)) ? step.actionId : null,
            config: stepConfig,
          };
        }),
      };

      if (areaId) {
        // Update existing area
        await requestJson(
          `/areas/${areaId}/with-steps`,
          {
            method: 'PUT',
            body: JSON.stringify(areaData),
          },
          auth.token
        );
        Alert.alert('Success', 'Area updated successfully!');
      } else {
        // Create new area
        await requestJson(
          '/areas/with-steps',
          {
            method: 'POST',
            body: JSON.stringify(areaData),
          },
          auth.token
        );
        Alert.alert('Success', 'Area created successfully!');
      }

      navigation.navigate('MainTabs', { screen: 'Dashboard' });
    } catch (error) {
      console.error('Error saving area:', error);
      const message = error instanceof Error ? error.message : 'Failed to save area';
      Alert.alert('Error', message);
    } finally {
      setSaving(false);
    }
  }, [areaName, areaDescription, steps, auth.token, navigation, areaId]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.subtitle}>Loading area...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        <Text style={styles.subtitle}>{areaId ? 'Modify your' : 'Create'} multi-step automation</Text>

        <Card style={styles.detailsCard}>
          <Text style={styles.sectionTitle}>Area Details</Text>
          <View style={styles.formGroup}>
            <Text style={styles.label}>Area Name *</Text>
            <Input
              value={areaName}
              onChangeText={setAreaName}
              placeholder="Enter area name"
            />
          </View>
          <View style={styles.formGroup}>
            <Text style={styles.label}>Description</Text>
            <Input
              value={areaDescription}
              onChangeText={setAreaDescription}
              placeholder="Enter area description (optional)"
            />
          </View>
        </Card>

        <View style={styles.stepsSection}>
          <View style={styles.stepsSectionHeader}>
            <Text style={styles.sectionTitle}>Automation Steps</Text>
            <CustomButton
              title="+ Add Step"
              onPress={() => setAddMenuVisible(!addMenuVisible)}
              variant="default"
            />
          </View>

          {addMenuVisible && (
            <Card style={styles.addMenu}>
              <TouchableOpacity
                style={styles.addMenuItem}
                onPress={() => addStep('trigger')}
              >
                <View style={[styles.addMenuBadge, { backgroundColor: '#DBEAFE' }]}>
                  <Text style={[styles.addMenuBadgeText, { color: '#1E40AF' }]}>TRIGGER</Text>
                </View>
                <Text style={styles.addMenuItemText}>Add Event</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.addMenuItem}
                onPress={() => addStep('action')}
              >
                <View style={[styles.addMenuBadge, { backgroundColor: '#D1FAE5' }]}>
                  <Text style={[styles.addMenuBadgeText, { color: '#065F46' }]}>ACTION</Text>
                </View>
                <Text style={styles.addMenuItemText}>Add Action</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.addMenuItem}
                onPress={() => addStep('condition')}
              >
                <View style={[styles.addMenuBadge, { backgroundColor: '#FEF3C7' }]}>
                  <Text style={[styles.addMenuBadgeText, { color: '#92400E' }]}>CONDITION</Text>
                </View>
                <Text style={styles.addMenuItemText}>Add If</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.addMenuItem}
                onPress={() => addStep('delay')}
              >
                <View style={[styles.addMenuBadge, { backgroundColor: '#E9D5FF' }]}>
                  <Text style={[styles.addMenuBadgeText, { color: '#6B21A8' }]}>DELAY</Text>
                </View>
                <Text style={styles.addMenuItemText}>Add Delay</Text>
              </TouchableOpacity>
            </Card>
          )}

          {steps.length === 0 ? (
            <Card style={styles.emptyState}>
              <Text style={styles.emptyStateText}>
                No steps added yet. Click "Add Step" to get started.
              </Text>
            </Card>
          ) : (
            steps.map((step, index) => (
              <StepCard
                key={step.id}
                step={step}
                index={index}
                onEdit={() => handleEditStep(step)}
                onDelete={() => handleDeleteStep(step.id)}
                onMoveUp={() => handleMoveUp(index)}
                onMoveDown={() => handleMoveDown(index)}
                canMoveUp={index > 0}
                canMoveDown={index < steps.length - 1}
              />
            ))
          )}
        </View>

        <View style={styles.footer}>
          <CustomButton
            title="Cancel"
            onPress={() => navigation.navigate('MainTabs', { screen: 'Dashboard' })}
            variant="outline"
            style={{ flex: 1, marginRight: 8 }}
          />
          <CustomButton
            title={saving ? 'Saving...' : (areaId ? 'Update AREA' : 'Save AREA')}
            onPress={handleSave}
            variant="default"
            disabled={saving}
            style={{ flex: 1 }}
          />
        </View>
      </ScrollView>

      <StepConfigModal
        visible={configModalVisible}
        step={selectedStep}
        availableSteps={steps}
        onClose={() => {
          setConfigModalVisible(false);
          setSelectedStep(null);
        }}
        onSave={handleSaveStep}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.backgroundLight,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 8,
    fontFamily: FontFamilies.heading,
  },
  subtitle: {
    fontSize: 14,
    color: Colors.mutedForeground,
    marginTop: 24,
    marginBottom: 16,
    marginHorizontal: 16,
    fontFamily: FontFamilies.body,
  },
  detailsCard: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 12,
    fontFamily: FontFamilies.body,
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textDark,
    marginBottom: 8,
    fontFamily: FontFamilies.body,
  },
  stepsSection: {
    marginBottom: 16,
  },
  stepsSectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  addMenu: {
    marginBottom: 12,
    padding: 8,
  },
  addMenuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  addMenuBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginRight: 12,
  },
  addMenuBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    fontFamily: FontFamilies.body,
  },
  addMenuItemText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  emptyState: {
    padding: 24,
    alignItems: 'center',
  },
  emptyStateText: {
    fontSize: 14,
    color: Colors.mutedForeground,
    textAlign: 'center',
    fontFamily: FontFamilies.body,
  },
  footer: {
    flexDirection: 'row',
    marginTop: 16,
    marginBottom: 32,
    gap: 8,
  },
});

export default AdvancedAreaBuilderScreen;
