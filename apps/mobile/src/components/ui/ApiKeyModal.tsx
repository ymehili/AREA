import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';

import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';

interface ApiKeyModalProps {
  visible: boolean;
  serviceName: string;
  onClose: () => void;
  onConfirm: (apiKey: string) => void;
}

const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ 
  visible, 
  serviceName, 
  onClose, 
  onConfirm 
}) => {
  const [apiKey, setApiKey] = useState('');

  const handleConfirm = () => {
    onConfirm(apiKey);
    setApiKey('');
  };

  const handleCancel = () => {
    setApiKey('');
    onClose();
  };

  return (
    <Modal
      animationType="slide"
      transparent={true}
      visible={visible}
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView 
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.container}
      >
        <View style={styles.modalContainer}>
          <View style={styles.contentContainer}>
            <Text style={styles.title}>
              Connect {serviceName}
            </Text>
            <Text style={styles.message}>
              Enter your {serviceName === 'openai' ? 'OpenAI' : serviceName === 'weather' ? 'OpenWeatherMap' : serviceName} API key:
            </Text>
            
            <TextInput
              style={styles.input}
              value={apiKey}
              onChangeText={setApiKey}
              placeholder={`Enter ${serviceName} API key`}
              secureTextEntry={true}
              autoFocus={true}
            />
            
            <View style={styles.buttonContainer}>
              <TouchableOpacity 
                style={[styles.button, styles.cancelButton]} 
                onPress={handleCancel}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={[styles.button, styles.confirmButton]} 
                onPress={handleConfirm}
                disabled={!apiKey.trim()}
              >
                <Text style={styles.confirmButtonText}>Connect</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
    padding: 20,
  },
  contentContainer: {
    width: '100%',
    backgroundColor: Colors.backgroundLight,
    borderRadius: 8,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: Colors.textDark,
    marginBottom: 10,
    textAlign: 'center',
    fontFamily: FontFamilies.heading,
  },
  message: {
    fontSize: 16,
    color: Colors.textDark,
    marginBottom: 20,
    textAlign: 'center',
    fontFamily: FontFamilies.body,
  },
  input: {
    width: '100%',
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 6,
    padding: 12,
    marginBottom: 20,
    backgroundColor: Colors.inputBackground,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
  },
  button: {
    flex: 1,
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    marginHorizontal: 5,
  },
  cancelButton: {
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.muted,
  },
  confirmButton: {
    backgroundColor: Colors.primary,
  },
  cancelButtonText: {
    color: Colors.textDark,
    fontWeight: 'bold',
    fontFamily: FontFamilies.body,
  },
  confirmButtonText: {
    color: Colors.backgroundLight,
    fontWeight: 'bold',
    fontFamily: FontFamilies.body,
  },
});

export default ApiKeyModal;