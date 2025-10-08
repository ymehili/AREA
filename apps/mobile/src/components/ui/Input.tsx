import React, { useState, useRef, useEffect } from 'react';
import { View, TextInput, Text, StyleSheet, TextInputProps, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants/colors';
import { TextStyles } from '../../constants/typography';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerStyle?: object;
}

const Input: React.FC<InputProps> = ({ 
  label, 
  error, 
  containerStyle, 
  style, 
  ...props 
}) => {
  return (
    <View style={[styles.container, containerStyle]}>
      {label ? (
        <Text style={styles.label}>{label}</Text>
      ) : null}
      <TextInput
        style={[
          styles.input,
          error && styles.inputError,
          style
        ]}
        placeholderTextColor={Colors.mutedForeground}
        {...props}
      />
      {error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : null}
    </View>
  );
};

interface PasswordInputProps extends InputProps {
  // No auto-hide delay - just simple toggle
}

export const PasswordInput: React.FC<PasswordInputProps> = ({
  label,
  error,
  containerStyle,
  style,
  ...props
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <View style={[styles.container, containerStyle]}>
      {label ? (
        <Text style={styles.label}>{label}</Text>
      ) : null}
      <View style={styles.passwordContainer}>
        <TextInput
          {...props}
          secureTextEntry={!showPassword}
          style={[
            styles.input,
            styles.passwordInput,
            error && styles.inputError,
            style
          ]}
          placeholderTextColor={Colors.mutedForeground}
        />
        <TouchableOpacity
          onPress={() => setShowPassword(!showPassword)}
          style={styles.eyeButton}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons
            name={showPassword ? 'eye-off' : 'eye'}
            size={20}
            color={Colors.mutedForeground}
          />
        </TouchableOpacity>
      </View>
      {error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    marginBottom: 16,
  },
  label: {
    ...TextStyles.small,
    color: Colors.textDark,
    marginBottom: 8,
  },
  input: {
    ...TextStyles.body,
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 6,
    paddingVertical: 12,
    paddingHorizontal: 12,
    backgroundColor: 'transparent',
    color: Colors.textDark,
  },
  passwordContainer: {
    position: 'relative',
  },
  passwordInput: {
    paddingRight: 48,
  },
  eyeButton: {
    position: 'absolute',
    right: 12,
    top: 12,
    padding: 4,
  },
  inputError: {
    borderColor: Colors.error,
  },
  errorText: {
    ...TextStyles.small,
    color: Colors.error,
    marginTop: 4,
  },
});

export default Input;