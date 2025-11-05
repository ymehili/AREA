import React from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';

interface WizardSelectionModalProps {
  visible: boolean;
  onClose: () => void;
  onSelectSimple: () => void;
  onSelectAdvanced: () => void;
}

const WizardSelectionModal: React.FC<WizardSelectionModalProps> = ({ 
  visible, 
  onClose, 
  onSelectSimple,
  onSelectAdvanced,
}) => {
  return (
    <Modal
      animationType="slide"
      transparent={true}
      visible={visible}
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.container}>
        <View style={styles.overlay} />
        <View style={styles.modalContainer}>
          <View style={styles.contentContainer}>
            <View style={styles.header}>
              <Text style={styles.title}>Create New AREA</Text>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Ionicons name="close" size={24} color={Colors.primary} />
              </TouchableOpacity>
            </View>
            
            <Text style={styles.message}>
              Choose how you'd like to create your automation:
            </Text>
            
            <TouchableOpacity 
              style={styles.optionCard}
              onPress={onSelectSimple}
              activeOpacity={0.7}
            >
              <View style={styles.iconContainer}>
                <Ionicons name="flash-outline" size={32} color={Colors.primary} />
              </View>
              <View style={styles.optionContent}>
                <Text style={styles.optionTitle}>Simple Wizard</Text>
                <Text style={styles.optionDescription}>
                  Quick and easy setup with guided steps. Perfect for creating basic automations.
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={Colors.primary} />
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.optionCard}
              onPress={onSelectAdvanced}
              activeOpacity={0.7}
            >
              <View style={styles.iconContainer}>
                <Ionicons name="git-network-outline" size={32} color={Colors.primary} />
              </View>
              <View style={styles.optionContent}>
                <Text style={styles.optionTitle}>Advanced Builder</Text>
                <Text style={styles.optionDescription}>
                  Full control with complex workflows, conditions, and multiple actions.
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={Colors.primary} />
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContainer: {
    backgroundColor: Colors.backgroundLight,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: -2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  contentContainer: {
    padding: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    ...TextStyles.h2,
    fontSize: 24,
    fontFamily: FontFamilies.heading,
    color: Colors.primary,
    fontWeight: '600',
  },
  closeButton: {
    padding: 4,
  },
  message: {
    ...TextStyles.body,
    fontFamily: FontFamilies.body,
    color: Colors.textDark,
    marginBottom: 24,
    fontSize: 16,
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardLight,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colors.primary + '15',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  optionContent: {
    flex: 1,
  },
  optionTitle: {
    ...TextStyles.h3,
    fontSize: 18,
    fontFamily: FontFamilies.heading,
    color: Colors.primary,
    fontWeight: '600',
    marginBottom: 4,
  },
  optionDescription: {
    ...TextStyles.body,
    fontFamily: FontFamilies.body,
    color: Colors.textDark,
    fontSize: 14,
    lineHeight: 20,
  },
});

export default WizardSelectionModal;
