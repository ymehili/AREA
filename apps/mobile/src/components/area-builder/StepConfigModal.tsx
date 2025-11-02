import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { NodeData, isTriggerNode, isActionNode, isConditionNode, isDelayNode } from '../../types/area-builder';
import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';
import CustomButton from '../ui/Button';
import Input from '../ui/Input';
import { useAuth } from '../../contexts/AuthContext';

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

type CatalogService = {
  slug: string;
  name: string;
  description: string;
  actions: Array<{ key: string; name: string; description: string }>;
  reactions: Array<{ key: string; name: string; description: string }>;
};

interface StepConfigModalProps {
  visible: boolean;
  step: NodeData | null;
  availableSteps: NodeData[]; // All steps to allow connection selection
  onClose: () => void;
  onSave: (updatedStep: NodeData) => void;
}

const StepConfigModal: React.FC<StepConfigModalProps> = ({
  visible,
  step,
  availableSteps,
  onClose,
  onSave,
}) => {
  const auth = useAuth();
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [actionId, setActionId] = useState('');
  const [conditionType, setConditionType] = useState<'simple' | 'expression'>('simple');
  const [conditionValue, setConditionValue] = useState('');
  const [duration, setDuration] = useState('1');
  const [unit, setUnit] = useState<'seconds' | 'minutes' | 'hours'>('seconds');
  const [connections, setConnections] = useState<string[]>([]);
  const [catalogServices, setCatalogServices] = useState<CatalogService[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [params, setParams] = useState<Record<string, any>>({});

  // Load catalog services when modal opens
  useEffect(() => {
    if (visible && auth.token && catalogServices.length === 0) {
      setLoadingCatalog(true);
      requestJson<{ services: CatalogService[] }>(
        '/services/actions-reactions',
        { method: 'GET' },
        auth.token
      )
        .then((data) => {
          console.log(`[StepConfigModal] Loaded ${data.services.length} services from catalog`);
          setCatalogServices(data.services);
        })
        .catch((err) => {
          console.error('[StepConfigModal] Failed to load catalog:', err.message);
          Alert.alert('Error', 'Failed to load services catalog');
        })
        .finally(() => setLoadingCatalog(false));
    }
  }, [visible, auth.token, catalogServices.length]);

  // Get services with actions (for triggers)
  const servicesWithActions = catalogServices.filter((service) => service.actions && service.actions.length > 0);

  // Get services with reactions (for actions)
  const servicesWithReactions = catalogServices.filter((service) => service.reactions && service.reactions.length > 0);

  // Get available actions/reactions for selected service
  const availableOptions = React.useMemo(() => {
    const service = catalogServices.find((s) => s.slug === serviceId);
    if (!service) return [];
    
    if (step && isTriggerNode(step)) {
      return service.actions || [];
    } else if (step && isActionNode(step)) {
      return service.reactions || [];
    }
    return [];
  }, [catalogServices, serviceId, step]);

  useEffect(() => {
    if (step) {
      setLabel(step.label || '');
      setDescription(step.description || '');
      setConnections(step.connections || []);

      if (isTriggerNode(step) || isActionNode(step)) {
        setServiceId(step.serviceId || '');
        setActionId(step.actionId || '');
        setParams(step.params || {});
      } else if (isConditionNode(step)) {
        setConditionType(step.conditionType || 'simple');
        setConditionValue(step.conditionValue || '');
      } else if (isDelayNode(step)) {
        setDuration(String(step.duration || 1));
        setUnit(step.unit || 'seconds');
      }
    }
  }, [step]);

  const handleSave = () => {
    if (!step) return;

    let updatedStep: NodeData = { ...step };

    updatedStep.label = label;
    updatedStep.description = description;
    updatedStep.connections = connections;

    if (isTriggerNode(step) || isActionNode(step)) {
      updatedStep = {
        ...updatedStep,
        serviceId,
        actionId,
        params,
      } as any;
    } else if (isConditionNode(step)) {
      updatedStep = {
        ...updatedStep,
        conditionType,
        conditionValue,
      } as any;
    } else if (isDelayNode(step)) {
      updatedStep = {
        ...updatedStep,
        duration: parseInt(duration, 10) || 1,
        unit,
      } as any;
    }

    onSave(updatedStep);
    onClose();
  };

  const toggleConnection = (stepId: string) => {
    setConnections((prev) =>
      prev.includes(stepId)
        ? prev.filter((id) => id !== stepId)
        : [...prev, stepId]
    );
  };

  if (!step) return null;

  return (
    <Modal visible={visible} animationType="slide" transparent={false}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Configure Step</Text>
          <TouchableOpacity onPress={onClose}>
            <Text style={styles.closeButton}>×</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content}>
          <View style={styles.formGroup}>
            <Text style={styles.label}>Step Label *</Text>
            <Input
              value={label}
              onChangeText={setLabel}
              placeholder="Enter step label"
            />
          </View>

          <View style={styles.formGroup}>
            <Text style={styles.label}>Description</Text>
            <Input
              value={description}
              onChangeText={setDescription}
              placeholder="Enter step description (optional)"
            />
          </View>

          {(isTriggerNode(step) || isActionNode(step)) && (
            <>
              {loadingCatalog ? (
                <View style={{ padding: 20, alignItems: 'center' }}>
                  <ActivityIndicator size="large" color={Colors.primary} />
                  <Text style={[styles.label, { marginTop: 8 }]}>Loading services...</Text>
                </View>
              ) : (
                <>
                  <View style={styles.formGroup}>
                    <Text style={styles.label}>
                      Service * ({isTriggerNode(step) ? servicesWithActions.length : servicesWithReactions.length} available)
                    </Text>
                    {(isTriggerNode(step) ? servicesWithActions : servicesWithReactions).length === 0 ? (
                      <Text style={styles.smallText}>No services available. Please check your server connection.</Text>
                    ) : (
                      <ScrollView style={{ maxHeight: 200 }} nestedScrollEnabled={true}>
                        <View style={styles.buttonGroup}>
                          {(isTriggerNode(step) ? servicesWithActions : servicesWithReactions).map((service) => (
                          <TouchableOpacity
                            key={service.slug}
                            style={[
                              styles.optionButton,
                              serviceId === service.slug && styles.optionButtonSelected,
                            ]}
                            onPress={() => {
                              setServiceId(service.slug);
                              setActionId(''); // Reset action when service changes
                            }}
                          >
                            <Text
                              style={[
                                styles.optionButtonText,
                                serviceId === service.slug && styles.optionButtonTextSelected,
                              ]}
                            >
                              {service.name}
                            </Text>
                            {service.description && (
                              <Text
                                style={[
                                  styles.smallText,
                                  serviceId === service.slug && { color: 'rgba(255, 255, 255, 0.8)' },
                                ]}
                              >
                                {service.description}
                              </Text>
                            )}
                          </TouchableOpacity>
                        ))}
                        </View>
                      </ScrollView>
                    )}
                  </View>

                  {serviceId && availableOptions.length > 0 && (
                    <View style={styles.formGroup}>
                      <Text style={styles.label}>
                        {isTriggerNode(step) ? 'Trigger' : 'Action'} * ({availableOptions.length} available)
                      </Text>
                      <ScrollView style={{ maxHeight: 200 }} nestedScrollEnabled={true}>
                        <View style={styles.buttonGroup}>
                          {availableOptions.map((option) => (
                            <TouchableOpacity
                              key={option.key}
                              style={[
                                styles.optionButton,
                                actionId === option.key && styles.optionButtonSelected,
                              ]}
                              onPress={() => setActionId(option.key)}
                            >
                              <Text
                                style={[
                                  styles.optionButtonText,
                                  actionId === option.key && styles.optionButtonTextSelected,
                                ]}
                              >
                                {option.name}
                              </Text>
                              {option.description && (
                                <Text
                                  style={[
                                    styles.smallText,
                                    actionId === option.key && { color: 'rgba(255, 255, 255, 0.8)' },
                                  ]}
                                >
                                  {option.description}
                                </Text>
                              )}
                            </TouchableOpacity>
                          ))}
                        </View>
                      </ScrollView>
                    </View>
                  )}

                  {/* Parameter inputs for actions and triggers */}
                  {serviceId && actionId && (
                    <View style={styles.formGroup}>
                      <Text style={[styles.label, { marginBottom: 12, fontSize: 16, fontWeight: 'bold' }]}>
                        Parameters
                      </Text>

                      {/* Time - Every Interval */}
                      {serviceId === 'time' && actionId === 'every_interval' && (
                        <View>
                          <Text style={styles.label}>Interval (seconds) *</Text>
                          <Input
                            value={params.interval_seconds?.toString() || '60'}
                            onChangeText={(value) => setParams({...params, interval_seconds: parseInt(value) || 60})}
                            placeholder="60"
                            keyboardType="numeric"
                          />
                          <Text style={styles.smallText}>How often to trigger (in seconds). Minimum: 1 second.</Text>
                        </View>
                      )}

                      {/* Weather - Get Current Weather */}
                      {serviceId === 'weather' && actionId === 'get_current_weather' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Location (City)</Text>
                            <Input
                              value={params.location || ''}
                              onChangeText={(value) => setParams({...params, location: value, lat: undefined, lon: undefined})}
                              placeholder="e.g., Paris,FR or London,UK"
                            />
                            <Text style={styles.smallText}>City name with country code or leave empty to use coordinates below</Text>
                          </View>
                          <View style={{ flexDirection: 'row', gap: 8 }}>
                            <View style={{ flex: 1 }}>
                              <Text style={styles.label}>Latitude</Text>
                              <Input
                                value={params.lat?.toString() || ''}
                                onChangeText={(value) => setParams({...params, lat: parseFloat(value) || undefined, location: undefined})}
                                placeholder="e.g., 48.8566"
                                keyboardType="decimal-pad"
                              />
                            </View>
                            <View style={{ flex: 1 }}>
                              <Text style={styles.label}>Longitude</Text>
                              <Input
                                value={params.lon?.toString() || ''}
                                onChangeText={(value) => setParams({...params, lon: parseFloat(value) || undefined, location: undefined})}
                                placeholder="e.g., 2.3522"
                                keyboardType="decimal-pad"
                              />
                            </View>
                          </View>
                          <Text style={styles.smallText}>Use either city name OR coordinates (not both)</Text>
                        </View>
                      )}

                      {/* Gmail - Send Email */}
                      {serviceId === 'gmail' && actionId === 'send_email' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>To *</Text>
                            <Input
                              value={params.to || ''}
                              onChangeText={(value) => setParams({...params, to: value})}
                              placeholder="recipient@example.com"
                              keyboardType="email-address"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Subject *</Text>
                            <Input
                              value={params.subject || ''}
                              onChangeText={(value) => setParams({...params, subject: value})}
                              placeholder="Email subject"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Body *</Text>
                            <Input
                              value={params.body || ''}
                              onChangeText={(value) => setParams({...params, body: value})}
                              placeholder="Message body (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                          </View>
                        </View>
                      )}

                      {/* Gmail - New Email from Sender */}
                      {serviceId === 'gmail' && actionId === 'new_email_from_sender' && (
                        <View>
                          <Text style={styles.label}>Sender Email *</Text>
                          <Input
                            value={params.sender_email || ''}
                            onChangeText={(value) => setParams({...params, sender_email: value})}
                            placeholder="name@example.com"
                            keyboardType="email-address"
                          />
                          <Text style={styles.smallText}>Only trigger for emails from this sender</Text>
                        </View>
                      )}

                      {/* Outlook - New Email from Sender */}
                      {serviceId === 'outlook' && actionId === 'new_email_from_sender' && (
                        <View>
                          <Text style={styles.label}>Sender Email *</Text>
                          <Input
                            value={params.sender_email || ''}
                            onChangeText={(value) => setParams({...params, sender_email: value})}
                            placeholder="name@example.com"
                            keyboardType="email-address"
                          />
                          <Text style={styles.smallText}>Only trigger for emails from this sender</Text>
                        </View>
                      )}

                      {/* Discord - New Message in Channel */}
                      {serviceId === 'discord' && actionId === 'new_message_in_channel' && (
                        <View>
                          <Text style={styles.label}>Channel ID *</Text>
                          <Input
                            value={params.channel_id || ''}
                            onChangeText={(value) => setParams({...params, channel_id: value})}
                            placeholder="123456789012345678"
                          />
                          <Text style={styles.smallText}>The Discord channel ID to monitor for new messages</Text>
                        </View>
                      )}

                      {/* Discord - Reaction Added */}
                      {serviceId === 'discord' && actionId === 'reaction_added' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Channel ID *</Text>
                            <Input
                              value={params.channel_id || ''}
                              onChangeText={(value) => setParams({...params, channel_id: value})}
                              placeholder="123456789012345678"
                            />
                            <Text style={styles.smallText}>The Discord channel ID where the message is located</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Message ID *</Text>
                            <Input
                              value={params.message_id || ''}
                              onChangeText={(value) => setParams({...params, message_id: value})}
                              placeholder="987654321098765432"
                            />
                            <Text style={styles.smallText}>The specific message ID to monitor for reactions. Enable Discord Developer Mode to copy message IDs.</Text>
                          </View>
                        </View>
                      )}

                      {/* Weather - Temperature Threshold */}
                      {serviceId === 'weather' && actionId === 'temperature_threshold' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Location *</Text>
                            <Input
                              value={params.location || ''}
                              onChangeText={(value) => setParams({...params, location: value})}
                              placeholder="London,UK or Paris,FR"
                            />
                            <Text style={styles.smallText}>City name (e.g., "London,UK")</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Temperature Threshold (°C) *</Text>
                            <Input
                              value={params.threshold?.toString() || ''}
                              onChangeText={(value) => setParams({...params, threshold: parseFloat(value) || undefined})}
                              placeholder="25"
                              keyboardType="decimal-pad"
                            />
                            <Text style={styles.smallText}>Temperature in Celsius</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Condition *</Text>
                            <View style={styles.buttonGroup}>
                              {['above', 'below'].map((op) => (
                                <TouchableOpacity
                                  key={op}
                                  style={[
                                    styles.optionButton,
                                    params.operator === op && styles.optionButtonSelected,
                                  ]}
                                  onPress={() => setParams({...params, operator: op})}
                                >
                                  <Text
                                    style={[
                                      styles.optionButtonText,
                                      params.operator === op && styles.optionButtonTextSelected,
                                    ]}
                                  >
                                    {op === 'above' ? 'Goes above threshold' : 'Goes below threshold'}
                                  </Text>
                                </TouchableOpacity>
                              ))}
                            </View>
                          </View>
                        </View>
                      )}

                      {/* Weather - Weather Condition */}
                      {serviceId === 'weather' && actionId === 'weather_condition' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Location *</Text>
                            <Input
                              value={params.location || ''}
                              onChangeText={(value) => setParams({...params, location: value})}
                              placeholder="London,UK or Paris,FR"
                            />
                            <Text style={styles.smallText}>City name (e.g., "London,UK")</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Weather Condition *</Text>
                            <ScrollView style={{ maxHeight: 200 }} nestedScrollEnabled={true}>
                              <View style={styles.buttonGroup}>
                                {['clear', 'clouds', 'rain', 'drizzle', 'thunderstorm', 'snow', 'mist', 'fog'].map((cond) => (
                                  <TouchableOpacity
                                    key={cond}
                                    style={[
                                      styles.optionButton,
                                      params.condition === cond && styles.optionButtonSelected,
                                    ]}
                                    onPress={() => setParams({...params, condition: cond})}
                                  >
                                    <Text
                                      style={[
                                        styles.optionButtonText,
                                        params.condition === cond && styles.optionButtonTextSelected,
                                      ]}
                                    >
                                      {cond.charAt(0).toUpperCase() + cond.slice(1)}
                                    </Text>
                                  </TouchableOpacity>
                                ))}
                              </View>
                            </ScrollView>
                          </View>
                        </View>
                      )}

                      {/* OpenAI - Generate Text */}
                      {serviceId === 'openai' && actionId === 'generate_text' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Prompt *</Text>
                            <Input
                              value={params.prompt || ''}
                              onChangeText={(value) => setParams({...params, prompt: value})}
                              placeholder="Enter your prompt (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                            <Text style={styles.smallText}>You can use variables like {`{{weather.temperature}}`}</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Max Tokens</Text>
                            <Input
                              value={params.max_tokens?.toString() || ''}
                              onChangeText={(value) => setParams({...params, max_tokens: parseInt(value) || undefined})}
                              placeholder="e.g., 100"
                              keyboardType="numeric"
                            />
                            <Text style={styles.smallText}>Maximum length of the response (default: 100)</Text>
                          </View>
                        </View>
                      )}

                      {/* GitHub - Create Issue */}
                      {serviceId === 'github' && actionId === 'create_issue' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Issue Title *</Text>
                            <Input
                              value={params.title || ''}
                              onChangeText={(value) => setParams({...params, title: value})}
                              placeholder="Issue title"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Issue Body</Text>
                            <Input
                              value={params.body || ''}
                              onChangeText={(value) => setParams({...params, body: value})}
                              placeholder="Issue description (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                          </View>
                        </View>
                      )}

                      {/* GitHub - Triggers (new_issue, pull_request_opened, etc.) */}
                      {serviceId === 'github' && ['new_issue', 'pull_request_opened', 'push_to_repository', 'release_published'].includes(actionId) && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                            <Text style={styles.smallText}>GitHub username or organization name</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                            <Text style={styles.smallText}>Name of the repository to monitor</Text>
                          </View>
                        </View>
                      )}

                      {/* Google Calendar - Event Starting Soon */}
                      {serviceId === 'google_calendar' && actionId === 'event_starting_soon' && (
                        <View>
                          <Text style={styles.label}>Minutes Before Event</Text>
                          <Input
                            value={params.minutes_before?.toString() || '15'}
                            onChangeText={(value) => setParams({...params, minutes_before: parseInt(value) || 15})}
                            placeholder="15"
                            keyboardType="numeric"
                          />
                          <Text style={styles.smallText}>Trigger X minutes before the event starts (default: 15)</Text>
                        </View>
                      )}

                      {/* Google Calendar - Create Event */}
                      {serviceId === 'google_calendar' && actionId === 'create_event' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Event Title *</Text>
                            <Input
                              value={params.summary || ''}
                              onChangeText={(value) => setParams({...params, summary: value})}
                              placeholder="Meeting with team"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Description</Text>
                            <Input
                              value={params.description || ''}
                              onChangeText={(value) => setParams({...params, description: value})}
                              placeholder="Event description (supports variables)"
                              multiline
                              numberOfLines={3}
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Start Time *</Text>
                            <Input
                              value={params.start_time || ''}
                              onChangeText={(value) => setParams({...params, start_time: value})}
                              placeholder="2024-01-15T10:00:00"
                            />
                            <Text style={styles.smallText}>ISO 8601 format or use a variable</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>End Time *</Text>
                            <Input
                              value={params.end_time || ''}
                              onChangeText={(value) => setParams({...params, end_time: value})}
                              placeholder="2024-01-15T11:00:00"
                            />
                            <Text style={styles.smallText}>ISO 8601 format or use a variable</Text>
                          </View>
                        </View>
                      )}

                      {/* Outlook - Send Email */}
                      {serviceId === 'outlook' && actionId === 'send_email' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>To *</Text>
                            <Input
                              value={params.to || ''}
                              onChangeText={(value) => setParams({...params, to: value})}
                              placeholder="recipient@example.com"
                              keyboardType="email-address"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Subject *</Text>
                            <Input
                              value={params.subject || ''}
                              onChangeText={(value) => setParams({...params, subject: value})}
                              placeholder="Email subject"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Body *</Text>
                            <Input
                              value={params.body || ''}
                              onChangeText={(value) => setParams({...params, body: value})}
                              placeholder="Message body (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                          </View>
                        </View>
                      )}

                      {/* Outlook - Mark as Read */}
                      {serviceId === 'outlook' && actionId === 'mark_as_read' && (
                        <View>
                          <Text style={styles.label}>Message ID *</Text>
                          <Input
                            value={params.message_id || ''}
                            onChangeText={(value) => setParams({...params, message_id: value})}
                            placeholder="e.g., {{outlook.message_id}}"
                          />
                          <Text style={styles.smallText}>Use a variable from a previous step</Text>
                        </View>
                      )}

                      {/* Outlook - Forward Email */}
                      {serviceId === 'outlook' && actionId === 'forward_email' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Message ID *</Text>
                            <Input
                              value={params.message_id || ''}
                              onChangeText={(value) => setParams({...params, message_id: value})}
                              placeholder="e.g., {{outlook.message_id}}"
                            />
                            <Text style={styles.smallText}>Use a variable from a previous step</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>To *</Text>
                            <Input
                              value={params.to || ''}
                              onChangeText={(value) => setParams({...params, to: value})}
                              placeholder="recipient@example.com"
                              keyboardType="email-address"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Comment (optional)</Text>
                            <Input
                              value={params.comment || ''}
                              onChangeText={(value) => setParams({...params, comment: value})}
                              placeholder="Add a comment when forwarding"
                              multiline
                              numberOfLines={3}
                            />
                          </View>
                        </View>
                      )}

                      {/* Gmail - Mark as Read */}
                      {serviceId === 'gmail' && actionId === 'mark_as_read' && (
                        <View>
                          <Text style={styles.label}>Message ID *</Text>
                          <Input
                            value={params.message_id || ''}
                            onChangeText={(value) => setParams({...params, message_id: value})}
                            placeholder="e.g., {{gmail.message_id}}"
                          />
                          <Text style={styles.smallText}>Use a variable from a previous step</Text>
                        </View>
                      )}

                      {/* Gmail - Forward Email */}
                      {serviceId === 'gmail' && actionId === 'forward_email' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Message ID *</Text>
                            <Input
                              value={params.message_id || ''}
                              onChangeText={(value) => setParams({...params, message_id: value})}
                              placeholder="e.g., {{gmail.message_id}}"
                            />
                            <Text style={styles.smallText}>Use a variable from a previous step</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>To *</Text>
                            <Input
                              value={params.to || ''}
                              onChangeText={(value) => setParams({...params, to: value})}
                              placeholder="recipient@example.com"
                              keyboardType="email-address"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Comment (optional)</Text>
                            <Input
                              value={params.comment || ''}
                              onChangeText={(value) => setParams({...params, comment: value})}
                              placeholder="Add a comment when forwarding"
                              multiline
                              numberOfLines={3}
                            />
                          </View>
                        </View>
                      )}

                      {/* GitHub - Add Comment */}
                      {serviceId === 'github' && actionId === 'add_comment' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Issue Number *</Text>
                            <Input
                              value={params.issue_number?.toString() || ''}
                              onChangeText={(value) => setParams({...params, issue_number: parseInt(value) || undefined})}
                              placeholder="e.g., 42 or {{github.issue_number}}"
                              keyboardType="numeric"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Comment Body *</Text>
                            <Input
                              value={params.body || ''}
                              onChangeText={(value) => setParams({...params, body: value})}
                              placeholder="Comment text (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                          </View>
                        </View>
                      )}

                      {/* GitHub - Close Issue */}
                      {serviceId === 'github' && actionId === 'close_issue' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Issue Number *</Text>
                            <Input
                              value={params.issue_number?.toString() || ''}
                              onChangeText={(value) => setParams({...params, issue_number: parseInt(value) || undefined})}
                              placeholder="e.g., 42 or {{github.issue_number}}"
                              keyboardType="numeric"
                            />
                          </View>
                        </View>
                      )}

                      {/* GitHub - Add Label */}
                      {serviceId === 'github' && actionId === 'add_label' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Issue Number *</Text>
                            <Input
                              value={params.issue_number?.toString() || ''}
                              onChangeText={(value) => setParams({...params, issue_number: parseInt(value) || undefined})}
                              placeholder="e.g., 42 or {{github.issue_number}}"
                              keyboardType="numeric"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Labels *</Text>
                            <Input
                              value={params.labels || ''}
                              onChangeText={(value) => setParams({...params, labels: value})}
                              placeholder="bug,enhancement"
                            />
                            <Text style={styles.smallText}>Comma-separated list of labels</Text>
                          </View>
                        </View>
                      )}

                      {/* GitHub - Create Branch */}
                      {serviceId === 'github' && actionId === 'create_branch' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Repository Owner *</Text>
                            <Input
                              value={params.repo_owner || ''}
                              onChangeText={(value) => setParams({...params, repo_owner: value})}
                              placeholder="e.g., octocat"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Repository Name *</Text>
                            <Input
                              value={params.repo_name || ''}
                              onChangeText={(value) => setParams({...params, repo_name: value})}
                              placeholder="e.g., Hello-World"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Branch Name *</Text>
                            <Input
                              value={params.branch_name || ''}
                              onChangeText={(value) => setParams({...params, branch_name: value})}
                              placeholder="feature/new-feature"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Source Branch</Text>
                            <Input
                              value={params.source_branch || ''}
                              onChangeText={(value) => setParams({...params, source_branch: value})}
                              placeholder="main (default)"
                            />
                            <Text style={styles.smallText}>Branch to create from (default: main)</Text>
                          </View>
                        </View>
                      )}

                      {/* Weather - Get Forecast */}
                      {serviceId === 'weather' && actionId === 'get_forecast' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Location (City)</Text>
                            <Input
                              value={params.location || ''}
                              onChangeText={(value) => setParams({...params, location: value, lat: undefined, lon: undefined})}
                              placeholder="e.g., Paris,FR or London,UK"
                            />
                            <Text style={styles.smallText}>City name with country code or leave empty to use coordinates below</Text>
                          </View>
                          <View style={{ flexDirection: 'row', gap: 8 }}>
                            <View style={{ flex: 1 }}>
                              <Text style={styles.label}>Latitude</Text>
                              <Input
                                value={params.lat?.toString() || ''}
                                onChangeText={(value) => setParams({...params, lat: parseFloat(value) || undefined, location: undefined})}
                                placeholder="e.g., 48.8566"
                                keyboardType="decimal-pad"
                              />
                            </View>
                            <View style={{ flex: 1 }}>
                              <Text style={styles.label}>Longitude</Text>
                              <Input
                                value={params.lon?.toString() || ''}
                                onChangeText={(value) => setParams({...params, lon: parseFloat(value) || undefined, location: undefined})}
                                placeholder="e.g., 2.3522"
                                keyboardType="decimal-pad"
                              />
                            </View>
                          </View>
                          <View>
                            <Text style={styles.label}>Count (optional)</Text>
                            <Input
                              value={params.cnt?.toString() || ''}
                              onChangeText={(value) => setParams({...params, cnt: parseInt(value) || undefined})}
                              placeholder="e.g., 40"
                              keyboardType="numeric"
                            />
                            <Text style={styles.smallText}>Max 40 entries (3-hour intervals). Leave empty for all.</Text>
                          </View>
                          <Text style={styles.smallText}>Use either city name OR coordinates (not both)</Text>
                        </View>
                      )}

                      {/* Delay - Wait (as action) */}
                      {serviceId === 'delay' && actionId === 'wait' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Duration *</Text>
                            <Input
                              value={params.duration?.toString() || '1'}
                              onChangeText={(value) => setParams({...params, duration: parseInt(value) || 1})}
                              placeholder="e.g., 30"
                              keyboardType="numeric"
                            />
                          </View>
                          <View>
                            <Text style={styles.label}>Unit *</Text>
                            <View style={styles.buttonGroup}>
                              {['seconds', 'minutes', 'hours', 'days'].map((u) => (
                                <TouchableOpacity
                                  key={u}
                                  style={[
                                    styles.optionButton,
                                    params.unit === u && styles.optionButtonSelected,
                                  ]}
                                  onPress={() => setParams({...params, unit: u})}
                                >
                                  <Text
                                    style={[
                                      styles.optionButtonText,
                                      params.unit === u && styles.optionButtonTextSelected,
                                    ]}
                                  >
                                    {u.charAt(0).toUpperCase() + u.slice(1)}
                                  </Text>
                                </TouchableOpacity>
                              ))}
                            </View>
                          </View>
                        </View>
                      )}

                      {/* Discord - Send Message */}
                      {serviceId === 'discord' && actionId === 'send_message' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Channel ID *</Text>
                            <Input
                              value={params.channel_id || ''}
                              onChangeText={(value) => setParams({...params, channel_id: value})}
                              placeholder="e.g., 123456789012345678"
                            />
                            <Text style={styles.smallText}>The ID of the Discord channel to send the message to</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Message *</Text>
                            <Input
                              value={params.message || ''}
                              onChangeText={(value) => setParams({...params, message: value})}
                              placeholder="Enter message (supports variables like {{gmail.subject}})"
                              multiline
                              numberOfLines={4}
                            />
                            <Text style={styles.smallText}>Message content to send to the channel</Text>
                          </View>
                        </View>
                      )}

                      {/* Discord - Send DM */}
                      {serviceId === 'discord' && actionId === 'send_dm' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>User ID *</Text>
                            <Input
                              value={params.user_id || ''}
                              onChangeText={(value) => setParams({...params, user_id: value})}
                              placeholder="e.g., 123456789012345678"
                            />
                            <Text style={styles.smallText}>The ID of the Discord user to send a direct message to</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Message *</Text>
                            <Input
                              value={params.message || ''}
                              onChangeText={(value) => setParams({...params, message: value})}
                              placeholder="Enter message (supports variables)"
                              multiline
                              numberOfLines={4}
                            />
                          </View>
                        </View>
                      )}

                      {/* OpenAI - Chat Completion */}
                      {serviceId === 'openai' && actionId === 'chat' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Prompt *</Text>
                            <Input
                              value={params.prompt || ''}
                              onChangeText={(value) => setParams({...params, prompt: value})}
                              placeholder="Enter your prompt (supports variables like {{gmail.subject}})"
                              multiline
                              numberOfLines={4}
                            />
                            <Text style={styles.smallText}>The message or question to send to ChatGPT</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Model (optional)</Text>
                            <View style={styles.buttonGroup}>
                              {['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview'].map((model) => (
                                <TouchableOpacity
                                  key={model}
                                  style={[
                                    styles.optionButton,
                                    params.model === model && styles.optionButtonSelected,
                                  ]}
                                  onPress={() => setParams({...params, model})}
                                >
                                  <Text
                                    style={[
                                      styles.optionButtonText,
                                      params.model === model && styles.optionButtonTextSelected,
                                    ]}
                                  >
                                    {model === 'gpt-3.5-turbo' ? 'GPT-3.5 Turbo' : model === 'gpt-4' ? 'GPT-4' : 'GPT-4 Turbo'}
                                  </Text>
                                </TouchableOpacity>
                              ))}
                            </View>
                            <Text style={styles.smallText}>Default: gpt-3.5-turbo</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Max Tokens (optional)</Text>
                            <Input
                              value={params.max_tokens?.toString() || ''}
                              onChangeText={(value) => setParams({...params, max_tokens: parseInt(value) || undefined})}
                              placeholder="500"
                              keyboardType="numeric"
                            />
                            <Text style={styles.smallText}>Maximum length of the response (1-4000)</Text>
                          </View>
                        </View>
                      )}

                      {/* DeepL - Translate */}
                      {serviceId === 'deepl' && actionId === 'translate' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Source Language *</Text>
                            <Input
                              value={params.source_lang || ''}
                              onChangeText={(value) => setParams({...params, source_lang: value.toUpperCase()})}
                              placeholder="EN"
                            />
                            <Text style={styles.smallText}>Source language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Target Language *</Text>
                            <Input
                              value={params.target_lang || ''}
                              onChangeText={(value) => setParams({...params, target_lang: value.toUpperCase()})}
                              placeholder="FR"
                            />
                            <Text style={styles.smallText}>Target language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Text to Translate *</Text>
                            <Input
                              value={params.text || ''}
                              onChangeText={(value) => setParams({...params, text: value})}
                              placeholder="Enter text or use variables like {{gmail.body}}"
                              multiline
                              numberOfLines={3}
                            />
                            <Text style={styles.smallText}>The text to translate. You can use variables from previous steps.</Text>
                          </View>
                        </View>
                      )}

                      {/* DeepL - Auto Translate */}
                      {serviceId === 'deepl' && actionId === 'auto_translate' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Target Language *</Text>
                            <Input
                              value={params.target_lang || ''}
                              onChangeText={(value) => setParams({...params, target_lang: value.toUpperCase()})}
                              placeholder="FR"
                            />
                            <Text style={styles.smallText}>Target language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Text to Translate *</Text>
                            <Input
                              value={params.text || ''}
                              onChangeText={(value) => setParams({...params, text: value})}
                              placeholder="Enter text or use variables like {{gmail.body}}"
                              multiline
                              numberOfLines={3}
                            />
                            <Text style={styles.smallText}>The text to translate. Source language will be detected automatically.</Text>
                          </View>
                        </View>
                      )}

                      {/* DeepL - Detect Language */}
                      {serviceId === 'deepl' && actionId === 'detect_language' && (
                        <View style={{ gap: 12 }}>
                          <View>
                            <Text style={styles.label}>Text to Analyze *</Text>
                            <Input
                              value={params.text || ''}
                              onChangeText={(value) => setParams({...params, text: value})}
                              placeholder="Enter text or use variables like {{gmail.body}}"
                              multiline
                              numberOfLines={3}
                            />
                            <Text style={styles.smallText}>The text to detect the language from.</Text>
                          </View>
                          <View>
                            <Text style={styles.label}>Sample Length (optional)</Text>
                            <Input
                              value={params.sample_length?.toString() || ''}
                              onChangeText={(value) => setParams({...params, sample_length: parseInt(value) || undefined})}
                              placeholder="e.g., 100"
                              keyboardType="numeric"
                            />
                            <Text style={styles.smallText}>Number of characters to analyze (default: 100). Helps save API quota.</Text>
                          </View>
                        </View>
                      )}

                      {/* Debug - Log Message */}
                      {serviceId === 'debug' && actionId === 'log' && (
                        <View>
                          <Text style={styles.label}>Log Message *</Text>
                          <Input
                            value={params.message || ''}
                            onChangeText={(value) => setParams({...params, message: value})}
                            placeholder="e.g., Weather: {{weather.temperature}}°C"
                            multiline
                            numberOfLines={4}
                          />
                          <Text style={styles.smallText}>Use variables like {`{{service.variable}}`}</Text>
                        </View>
                      )}
                    </View>
                  )}
                </>
              )}
            </>
          )}

          {isConditionNode(step) && (
            <>
              <View style={styles.formGroup}>
                <Text style={styles.label}>Condition Type *</Text>
                <View style={styles.buttonGroup}>
                  {['simple', 'expression'].map((type) => (
                    <TouchableOpacity
                      key={type}
                      style={[
                        styles.optionButton,
                        conditionType === type && styles.optionButtonSelected,
                      ]}
                      onPress={() => setConditionType(type as 'simple' | 'expression')}
                    >
                      <Text
                        style={[
                          styles.optionButtonText,
                          conditionType === type && styles.optionButtonTextSelected,
                        ]}
                      >
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Condition Value *</Text>
                <Input
                  value={conditionValue}
                  onChangeText={setConditionValue}
                  placeholder="Enter condition value"
                />
              </View>
            </>
          )}

          {isDelayNode(step) && (
            <>
              <View style={styles.formGroup}>
                <Text style={styles.label}>Duration *</Text>
                <Input
                  value={duration}
                  onChangeText={setDuration}
                  placeholder="Enter duration"
                  keyboardType="numeric"
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.label}>Unit *</Text>
                <View style={styles.buttonGroup}>
                  {['seconds', 'minutes', 'hours'].map((u) => (
                    <TouchableOpacity
                      key={u}
                      style={[
                        styles.optionButton,
                        unit === u && styles.optionButtonSelected,
                      ]}
                      onPress={() => setUnit(u as 'seconds' | 'minutes' | 'hours')}
                    >
                      <Text
                        style={[
                          styles.optionButtonText,
                          unit === u && styles.optionButtonTextSelected,
                        ]}
                      >
                        {u.charAt(0).toUpperCase() + u.slice(1)}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            </>
          )}

          {/* Connections Section */}
          <View style={styles.formGroup}>
            <Text style={styles.label}>Connect to Next Steps</Text>
            <Text style={[styles.label, { fontSize: 12, fontWeight: 'normal', color: Colors.mutedForeground }]}>
              Select which steps should run after this one
            </Text>
            {availableSteps.filter(s => s.id !== step.id).length === 0 ? (
              <Text style={[styles.label, { fontSize: 12, fontWeight: 'normal', color: Colors.mutedForeground }]}>
                No other steps available. Add more steps first.
              </Text>
            ) : (
              <View style={styles.buttonGroup}>
                {availableSteps
                  .filter(s => s.id !== step.id)
                  .map((s) => (
                    <TouchableOpacity
                      key={s.id}
                      style={[
                        styles.connectionButton,
                        connections.includes(s.id) && styles.connectionButtonSelected,
                      ]}
                      onPress={() => toggleConnection(s.id)}
                    >
                      <View style={styles.connectionButtonContent}>
                        <Text
                          style={[
                            styles.optionButtonText,
                            connections.includes(s.id) && styles.optionButtonTextSelected,
                          ]}
                        >
                          {s.label}
                        </Text>
                        <Text
                          style={[
                            styles.smallText,
                            connections.includes(s.id) && { color: Colors.backgroundLight },
                          ]}
                        >
                          ({s.type})
                        </Text>
                      </View>
                      {connections.includes(s.id) && (
                        <Text style={{ color: Colors.backgroundLight, marginLeft: 8 }}>✓</Text>
                      )}
                    </TouchableOpacity>
                  ))}
              </View>
            )}
          </View>
        </ScrollView>

        <View style={styles.footer}>
          <CustomButton
            title="Save"
            onPress={handleSave}
            variant="default"
            style={{ flex: 1, marginRight: 8 }}
          />
          <CustomButton
            title="Cancel"
            onPress={onClose}
            variant="outline"
            style={{ flex: 1 }}
          />
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.backgroundLight,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Colors.textDark,
    fontFamily: FontFamilies.heading,
  },
  closeButton: {
    fontSize: 32,
    color: Colors.textDark,
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.textDark,
    marginBottom: 8,
    fontFamily: FontFamilies.body,
  },
  buttonGroup: {
    gap: 8,
  },
  optionButton: {
    padding: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.backgroundLight,
    marginBottom: 8,
  },
  optionButtonSelected: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  optionButtonText: {
    fontSize: 14,
    color: Colors.textDark,
    textAlign: 'center',
    fontFamily: FontFamilies.body,
  },
  optionButtonTextSelected: {
    color: Colors.backgroundLight,
    fontWeight: 'bold',
  },
  connectionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.backgroundLight,
    marginBottom: 8,
  },
  connectionButtonSelected: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  connectionButtonContent: {
    flex: 1,
  },
  smallText: {
    fontSize: 12,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  footer: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    gap: 8,
  },
});

export default StepConfigModal;
