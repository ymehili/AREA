import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { NodeData, isTriggerNode, isActionNode, isConditionNode, isDelayNode } from '../../types/area-builder';
import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';
import CustomButton from '../ui/Button';
import Input from '../ui/Input';

interface StepConfigModalProps {
  visible: boolean;
  step: NodeData | null;
  availableSteps: NodeData[]; // All steps to allow connection selection
  onClose: () => void;
  onSave: (updatedStep: NodeData) => void;
}

const SERVICES = ['Gmail', 'Google Drive', 'Slack', 'GitHub'];
const TRIGGERS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ['New Email', 'New Email w/ Attachment'],
  'Google Drive': ['New File in Folder'],
  Slack: ['New Message in Channel'],
  GitHub: ['New Pull Request'],
};
const ACTIONS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ['Send Email'],
  'Google Drive': ['Upload File', 'Create Folder'],
  Slack: ['Send Message'],
  GitHub: ['Create Issue'],
};

const StepConfigModal: React.FC<StepConfigModalProps> = ({
  visible,
  step,
  availableSteps,
  onClose,
  onSave,
}) => {
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [actionId, setActionId] = useState('');
  const [conditionType, setConditionType] = useState<'simple' | 'expression'>('simple');
  const [conditionValue, setConditionValue] = useState('');
  const [duration, setDuration] = useState('1');
  const [unit, setUnit] = useState<'seconds' | 'minutes' | 'hours'>('seconds');
  const [connections, setConnections] = useState<string[]>([]);

  useEffect(() => {
    if (step) {
      setLabel(step.label || '');
      setDescription(step.description || '');
      setConnections(step.connections || []);

      if (isTriggerNode(step) || isActionNode(step)) {
        setServiceId(step.serviceId || '');
        setActionId(step.actionId || '');
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
              <View style={styles.formGroup}>
                <Text style={styles.label}>Service *</Text>
                <View style={styles.buttonGroup}>
                  {SERVICES.map((service) => (
                    <TouchableOpacity
                      key={service}
                      style={[
                        styles.optionButton,
                        serviceId === service && styles.optionButtonSelected,
                      ]}
                      onPress={() => {
                        setServiceId(service);
                        setActionId(''); // Reset action when service changes
                      }}
                    >
                      <Text
                        style={[
                          styles.optionButtonText,
                          serviceId === service && styles.optionButtonTextSelected,
                        ]}
                      >
                        {service}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              {serviceId && (
                <View style={styles.formGroup}>
                  <Text style={styles.label}>
                    {isTriggerNode(step) ? 'Trigger' : 'Action'} *
                  </Text>
                  <View style={styles.buttonGroup}>
                    {(isTriggerNode(step)
                      ? TRIGGERS_BY_SERVICE[serviceId] || []
                      : ACTIONS_BY_SERVICE[serviceId] || []
                    ).map((action) => (
                      <TouchableOpacity
                        key={action}
                        style={[
                          styles.optionButton,
                          actionId === action && styles.optionButtonSelected,
                        ]}
                        onPress={() => setActionId(action)}
                      >
                        <Text
                          style={[
                            styles.optionButtonText,
                            actionId === action && styles.optionButtonTextSelected,
                          ]}
                        >
                          {action}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
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
