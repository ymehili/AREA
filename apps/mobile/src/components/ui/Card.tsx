import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Colors } from '../../constants/colors';
import { TextStyles } from '../../constants/typography';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

const Card: React.FC<CardProps> = ({ children, header, footer, style }) => {
  return (
    <View style={[styles.card, style]}>
      {header && <View style={styles.cardHeader}>{header}</View>}
      <View style={styles.cardContent}>{children}</View>
      {footer && <View style={styles.cardFooter}>{footer}</View>}
    </View>
  );
};

interface CardHeaderProps {
  children: React.ReactNode;
  title?: string;
}

const CardHeader: React.FC<CardHeaderProps> = ({ children, title }) => {
  if (title) {
    return (
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{title}</Text>
      </View>
    );
  }
  return <View style={styles.cardHeader}>{children}</View>;
};

interface CardContentProps {
  children: React.ReactNode;
}

const CardContent: React.FC<CardContentProps> = ({ children }) => {
  return <View style={styles.cardContent}>{children}</View>;
};

interface CardFooterProps {
  children: React.ReactNode;
}

const CardFooter: React.FC<CardFooterProps> = ({ children }) => {
  return <View style={styles.cardFooter}>{children}</View>;
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.cardLight, // Light mode default
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    overflow: 'hidden',
  },
  cardHeader: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 4,
  },
  cardTitle: {
    ...TextStyles.h3,
    color: Colors.textDark,
  },
  cardContent: {
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  cardFooter: {
    paddingHorizontal: 16,
    paddingTop: 4,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
});

export { Card, CardHeader, CardContent, CardFooter };
export default Card;