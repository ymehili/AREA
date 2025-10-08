import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { Colors } from '../../constants/colors';
import { TextStyles } from '../../constants/typography';

type ButtonVariant = 'default' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'link';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  style?: ViewStyle;
  size?: 'default' | 'sm' | 'lg';
  textStyle?: TextStyle;
}

const getButtonStyles = (variant: ButtonVariant, disabled: boolean): ViewStyle => {
  const baseStyle: ViewStyle = {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
    paddingVertical: 12,
    paddingHorizontal: 16,
    minWidth: 48,
    minHeight: 48,
    borderWidth: 1,
    borderColor: 'transparent',
  };

  let variantStyle: ViewStyle = {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  };

  if (variant === 'secondary') {
    variantStyle = {
      backgroundColor: Colors.secondary,
      borderColor: Colors.secondary,
    };
  } else if (variant === 'destructive') {
    variantStyle = {
      backgroundColor: Colors.error,
      borderColor: Colors.error,
    };
  } else if (variant === 'outline') {
    variantStyle = {
      backgroundColor: 'transparent',
      borderColor: Colors.border,
    };
  } else if (variant === 'ghost') {
    variantStyle = {
      backgroundColor: 'transparent',
      borderColor: 'transparent',
    };
  } else if (variant === 'link') {
    variantStyle = {
      backgroundColor: 'transparent',
      borderColor: 'transparent',
    };
  }

  if (disabled) {
    variantStyle.backgroundColor = Colors.muted;
    variantStyle.borderColor = Colors.muted;
  }

  return {
    ...baseStyle,
    ...variantStyle,
  };
};

const getTextStyles = (variant: ButtonVariant, disabled: boolean): TextStyle => {
  const baseStyle: TextStyle = {
    ...TextStyles['body-bold'],
    textAlign: 'center',
  };

  if (variant === 'outline' || variant === 'ghost' || variant === 'link') {
    baseStyle.color = Colors.primary;
  } else {
    baseStyle.color = Colors.primaryForeground;
  }

  if (variant === 'destructive') {
    baseStyle.color = Colors.errorForeground;
  }

  if (disabled) {
    baseStyle.color = Colors.mutedForeground;
  }

  return baseStyle;
};

const getButtonSizeStyles = (size: 'default' | 'sm' | 'lg'): ViewStyle => {
  if (size === 'sm') {
    return {
      paddingVertical: 10,
      paddingHorizontal: 12,
      minHeight: 44, // Accessibility: minimum 44x44px touch target
    };
  } else if (size === 'lg') {
    return {
      paddingVertical: 16,
      paddingHorizontal: 24,
      minHeight: 56,
    };
  }
  // Default size already handled in base style
  return {};
};

export const Button: React.FC<ButtonProps> = ({ 
  title, 
  onPress, 
  variant = 'default', 
  disabled = false, 
  style, 
  size = 'default',
  textStyle 
}) => {
  const buttonStyle = getButtonStyles(variant, disabled);
  const textStyleFromVariant = getTextStyles(variant, disabled);
  const sizeStyle = getButtonSizeStyles(size);

  return (
    <TouchableOpacity
      style={[buttonStyle, sizeStyle, style, disabled && { opacity: 0.5 }]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={[textStyleFromVariant, textStyle]}>
        {title}
      </Text>
    </TouchableOpacity>
  );
};

export default Button;