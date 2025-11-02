import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Card from '../ui/Card';
import { Colors } from '../../constants/colors';
import { TextStyles, FontFamilies } from '../../constants/typography';
import type { Template } from '../../types/marketplace';

interface TemplateCardProps {
  template: Template;
  onPress: () => void;
}

export default function TemplateCard({ template, onPress }: TemplateCardProps) {
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <Card style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.title} numberOfLines={2}>
            {template.title}
          </Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{template.category}</Text>
          </View>
        </View>
        
        <Text style={styles.description} numberOfLines={3}>
          {template.description}
        </Text>

        {/* Tags */}
        {template.tags && template.tags.length > 0 && (
          <View style={styles.tagsContainer}>
            {template.tags.slice(0, 3).map((tag, index) => (
              <View key={index} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
              </View>
            ))}
            {template.tags.length > 3 && (
              <View style={styles.tag}>
                <Text style={styles.tagText}>+{template.tags.length - 3}</Text>
              </View>
            )}
          </View>
        )}

        {/* Stats */}
        <View style={styles.stats}>
          <View style={styles.stat}>
            <Ionicons name="people-outline" size={16} color={Colors.mutedForeground} />
            <Text style={styles.statText}>{template.usage_count.toLocaleString()}</Text>
          </View>
          
          <View style={styles.stat}>
            <Ionicons name="copy-outline" size={16} color={Colors.mutedForeground} />
            <Text style={styles.statText}>{template.clone_count.toLocaleString()}</Text>
          </View>
          
          {template.rating_average !== null && (
            <View style={styles.stat}>
              <Ionicons name="star" size={16} color="#facc15" />
              <Text style={styles.statText}>
                {template.rating_average.toFixed(1)} ({template.rating_count})
              </Text>
            </View>
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
    gap: 8,
  },
  title: {
    ...TextStyles.h3,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    flex: 1,
  },
  categoryBadge: {
    backgroundColor: Colors.muted,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  categoryText: {
    fontSize: 12,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  description: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginBottom: 12,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 12,
  },
  tag: {
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  tagText: {
    fontSize: 12,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  stats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
});
