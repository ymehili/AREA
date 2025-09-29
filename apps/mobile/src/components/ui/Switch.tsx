import React from 'react';
import { Switch as RNSwitch, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';

interface SwitchProps {
  value: boolean;
  onValueChange: (value: boolean) => void;
  disabled?: boolean;
}

const Switch: React.FC<SwitchProps> = ({ value, onValueChange, disabled = false }) => {
  return (
    <RNSwitch
      style={styles.switch}
      value={value}
      onValueChange={onValueChange}
      disabled={disabled}
      thumbColor={Colors.backgroundLight}
      trackColor={{ 
        false: Colors.muted, 
        true: value ? Colors.primary : Colors.muted 
      }}
    />
  );
};

const styles = StyleSheet.create({
  switch: {
    transform: [{ scaleX: 0.9 }, { scaleY: 0.9 }], // Slightly smaller than default
  },
});

export default Switch;