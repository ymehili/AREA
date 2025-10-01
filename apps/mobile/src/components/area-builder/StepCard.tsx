import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { NodeData, isTriggerNode, isActionNode, isConditionNode, isDelayNode } from '../../types/area-builder';
import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';
import CustomButton from '../ui/Button';

interface StepCardProps {
  step: NodeData;
  index: number;
  onEdit: () => void;
  onDelete: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
}

const StepCard: React.FC<StepCardProps> = ({
  step,
  index,
  onEdit,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}) => {
  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'trigger':
        return { backgroundColor: '#DBEAFE', color: '#1E40AF' }; // Blue
      case 'action':
        return { backgroundColor: '#D1FAE5', color: '#065F46' }; // Green
      case 'condition':
        return { backgroundColor: '#FEF3C7', color: '#92400E' }; // Yellow
      case 'delay':
        return { backgroundColor: '#E9D5FF', color: '#6B21A8' }; // Purple
      default:
        return { backgroundColor: Colors.muted, color: Colors.textDark };
    }
  };

  const badgeStyle = getBadgeStyle(step.type);

  const getStepDetails = () => {
    if (isTriggerNode(step)) {
      return `Service: ${step.serviceId || 'Not set'}, Action: ${step.actionId || 'Not set'}`;
    }
    if (isActionNode(step)) {
      return `Service: ${step.serviceId || 'Not set'}, Action: ${step.actionId || 'Not set'}`;
    }
    if (isConditionNode(step)) {
      return `Type: ${step.conditionType}, Value: ${step.conditionValue || 'Not set'}`;
    }
    if (isDelayNode(step)) {
      return `Duration: ${step.duration} ${step.unit}`;
    }
    return '';
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.leftSection}>
          <View style={[styles.badge, { backgroundColor: badgeStyle.backgroundColor }]}>
            <Text style={[styles.badgeText, { color: badgeStyle.color }]}>
              {step.type.toUpperCase()}
            </Text>
          </View>
          <Text style={styles.stepNumber}>#{index + 1}</Text>
        </View>
        <View style={styles.reorderButtons}>
          {canMoveUp && (
            <TouchableOpacity
              style={styles.reorderButton}
              onPress={onMoveUp}
              disabled={!canMoveUp}
            >
              <Text style={styles.reorderButtonText}>↑</Text>
            </TouchableOpacity>
          )}
          {canMoveDown && (
            <TouchableOpacity
              style={styles.reorderButton}
              onPress={onMoveDown}
              disabled={!canMoveDown}
            >
              <Text style={styles.reorderButtonText}>↓</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <View style={styles.content}>
        <Text style={styles.label}>{step.label}</Text>
        {step.description && (
          <Text style={styles.description}>{step.description}</Text>
        )}
        <Text style={styles.details}>{getStepDetails()}</Text>
        {step.connections && step.connections.length > 0 && (
          <View style={styles.connectionsContainer}>
            <Text style={styles.connectionsLabel}>→ Connects to {step.connections.length} step{step.connections.length > 1 ? 's' : ''}</Text>
          </View>
        )}
      </View>

      <View style={styles.actions}>
        <CustomButton
          title="Edit"
          onPress={onEdit}
          variant="outline"
          style={{ flex: 1, marginRight: 8 }}
        />
        <CustomButton
          title="Delete"
          onPress={onDelete}
          variant="destructive"
          style={{ flex: 1 }}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    backgroundColor: Colors.cardLight,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  leftSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    fontFamily: FontFamilies.body,
  },
  stepNumber: {
    fontSize: 12,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  reorderButtons: {
    flexDirection: 'row',
    gap: 4,
  },
  reorderButton: {
    width: 32,
    height: 32,
    borderRadius: 4,
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  reorderButtonText: {
    fontSize: 18,
    color: Colors.textDark,
  },
  content: {
    marginBottom: 12,
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 4,
    fontFamily: FontFamilies.body,
  },
  description: {
    fontSize: 14,
    color: Colors.mutedForeground,
    marginBottom: 4,
    fontFamily: FontFamilies.body,
  },
  details: {
    fontSize: 12,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
  },
  connectionsContainer: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  connectionsLabel: {
    fontSize: 12,
    color: Colors.primary,
    fontFamily: FontFamilies.body,
    fontWeight: '600',
  },
});

export default StepCard;
