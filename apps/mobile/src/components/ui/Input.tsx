import React from 'react';
import { View, TextInput, Text, StyleSheet, TextInputProps, TextStyle } from 'react-native';
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