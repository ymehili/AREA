import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
  Alert,
  TextInput,
  Modal,
  Platform,
  StatusBar,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import CustomButton from './ui/Button';
import Card from './ui/Card';
import { Colors } from '../constants/colors';
import { TextStyles, FontFamilies } from '../constants/typography';
import { getTemplateById, cloneTemplate, deleteTemplate } from '../utils/marketplace';
import type { Template } from '../types/marketplace';

interface TemplateDetailScreenProps {
  apiBaseUrl: string;
  token: string | null;
}

interface TemplateJsonStructure {
  trigger?: {
    service?: string;
    action?: string;
  };
  reaction?: {
    service?: string;
    action?: string;
  };
}

export default function TemplateDetailScreen({
  apiBaseUrl,
  token,
}: TemplateDetailScreenProps) {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { templateId } = route.params || {};

  const [template, setTemplate] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cloning, setCloning] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showCloneModal, setShowCloneModal] = useState(false);
  const [areaName, setAreaName] = useState('');
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  // Fetch current user ID
  useEffect(() => {
    const fetchCurrentUser = async () => {
      if (!token) return;
      
      try {
        const response = await fetch(`${apiBaseUrl}/users/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const userData = await response.json();
          setCurrentUserId(userData.id);
        }
      } catch (err) {
        console.error('Failed to fetch current user:', err);
      }
    };

    fetchCurrentUser();
  }, [apiBaseUrl, token]);

  const loadTemplate = useCallback(async () => {
    if (!templateId) {
      setError('No template ID provided');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getTemplateById(apiBaseUrl, templateId);
      setTemplate(data);
      setAreaName(data.title);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load template');
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, templateId]);

  useEffect(() => {
    loadTemplate();
  }, [loadTemplate]);

  const handleClone = async () => {
    if (!token) {
      Alert.alert('Authentication Required', 'Please log in to clone this template.');
      return;
    }

    if (!template) return;

    if (!areaName.trim()) {
      Alert.alert('Name Required', 'Please enter a name for your new automation.');
      return;
    }

    setCloning(true);

    try {
      const response = await cloneTemplate(apiBaseUrl, token, template.id, {
        area_name: areaName.trim(),
      });

      setShowCloneModal(false);
      Alert.alert(
        'Success',
        'Template cloned successfully! You can now view and edit it in your dashboard.',
        [
          {
            text: 'OK',
            onPress: () => navigation.navigate('MainTabs', { screen: 'Dashboard' }),
          },
        ]
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to clone template';
      Alert.alert('Clone Failed', message);
    } finally {
      setCloning(false);
    }
  };

  const handleDelete = async () => {
    if (!token) {
      Alert.alert('Authentication Required', 'Please log in to delete this template.');
      return;
    }

    if (!template) return;

    Alert.alert(
      'Delete Template',
      'Are you sure you want to delete this template from the marketplace? This action cannot be undone.',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            setDeleting(true);
            try {
              await deleteTemplate(apiBaseUrl, token, template.id);
              Alert.alert(
                'Success',
                'Template deleted successfully.',
                [
                  {
                    text: 'OK',
                    onPress: () => navigation.navigate('MainTabs', { screen: 'Marketplace' }),
                  },
                ]
              );
            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to delete template';
              Alert.alert('Delete Failed', message);
              setDeleting(false);
            }
          },
        },
      ]
    );
  };

  // Check if current user is the template owner
  const isOwner = template && currentUserId && template.publisher_user_id === currentUserId;

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading template...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !template) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.header}>
          <View style={styles.backButtonContainer}>
            <CustomButton
              title="← Back"
              onPress={() => navigation.goBack()}
              variant="outline"
              style={styles.backButton}
            />
          </View>
        </View>
        <Card style={styles.errorCard}>
          <Text style={styles.errorTitle}>Failed to load template</Text>
          <Text style={styles.errorText}>{error || 'Template not found'}</Text>
          <CustomButton title="Try Again" onPress={loadTemplate} variant="outline" />
        </Card>
      </SafeAreaView>
    );
  }

  const templateJson = template.template_json as TemplateJsonStructure;

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <View style={styles.backButtonContainer}>
          <CustomButton
            title="← Back"
            onPress={() => navigation.goBack()}
            variant="outline"
            style={styles.backButton}
          />
        </View>
        <View style={styles.headerActions}>
          {isOwner && (
            <TouchableOpacity
              onPress={handleDelete}
              disabled={deleting}
              style={styles.deleteButton}
            >
              <Ionicons
                name="trash-outline"
                size={20}
                color={deleting ? Colors.mutedForeground : Colors.error}
              />
            </TouchableOpacity>
          )}
          <CustomButton
            title="Clone Template"
            onPress={() => setShowCloneModal(true)}
            variant="default"
            style={styles.cloneButton}
          />
        </View>
      </View>

      <ScrollView style={styles.content}>
        {/* Template Header */}
        <View style={styles.titleSection}>
          <Text style={styles.title}>{template.title}</Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{template.category}</Text>
          </View>
        </View>

        {/* Stats */}
        <View style={styles.stats}>
          <View style={styles.stat}>
            <Ionicons name="people-outline" size={20} color={Colors.mutedForeground} />
            <Text style={styles.statText}>
              {template.usage_count.toLocaleString()} uses
            </Text>
          </View>
          <View style={styles.stat}>
            <Ionicons name="copy-outline" size={20} color={Colors.mutedForeground} />
            <Text style={styles.statText}>
              {template.clone_count.toLocaleString()} clones
            </Text>
          </View>
          {template.rating_average !== null && (
            <View style={styles.stat}>
              <Ionicons name="star" size={20} color="#facc15" />
              <Text style={styles.statText}>
                {template.rating_average.toFixed(1)} ({template.rating_count})
              </Text>
            </View>
          )}
        </View>

        {/* Description */}
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.description}>{template.description}</Text>
          {template.long_description && (
            <Text style={[styles.description, styles.longDescription]}>
              {template.long_description}
            </Text>
          )}
        </Card>

        {/* Tags */}
        {template.tags && template.tags.length > 0 && (
          <Card style={styles.section}>
            <Text style={styles.sectionTitle}>Tags *</Text>
            <View style={styles.tagsContainer}>
              {template.tags.map((tag, index) => (
                <View key={index} style={styles.tag}>
                  <Text style={styles.tagText}>{tag}</Text>
                </View>
              ))}
            </View>
          </Card>
        )}

        {/* Workflow Structure */}
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Workflow Structure</Text>
          <Text style={styles.sectionSubtitle}>
            This template contains the following automation workflow
          </Text>

          {/* Trigger */}
          {templateJson.trigger && (
            <View style={styles.workflowCard}>
              <View style={styles.workflowBadge}>
                <Text style={styles.workflowBadgeText}>Trigger</Text>
              </View>
              <Text style={styles.workflowTitle}>
                {templateJson.trigger.service || 'Unknown'} -{' '}
                {templateJson.trigger.action || 'Unknown'}
              </Text>
              <Text style={styles.workflowDescription}>
                Starts the automation when this event occurs
              </Text>
            </View>
          )}

          {/* Reaction */}
          {templateJson.reaction && (
            <View style={styles.workflowCard}>
              <View style={[styles.workflowBadge, styles.workflowBadgeReaction]}>
                <Text style={styles.workflowBadgeText}>Reaction</Text>
              </View>
              <Text style={styles.workflowTitle}>
                {templateJson.reaction.service || 'Unknown'} -{' '}
                {templateJson.reaction.action || 'Unknown'}
              </Text>
              <Text style={styles.workflowDescription}>
                Performs this action when the trigger fires
              </Text>
            </View>
          )}
        </Card>

        <View style={{ height: 24 }} />
      </ScrollView>

      {/* Clone Modal */}
      <Modal
        visible={showCloneModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowCloneModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Clone Template</Text>
            <Text style={styles.modalDescription}>
              Give your new automation a name. You can customize it after cloning.
            </Text>

            <View style={styles.modalInput}>
              <Text style={styles.inputLabel}>Automation Name</Text>
              <TextInput
                style={styles.input}
                value={areaName}
                onChangeText={setAreaName}
                placeholder="My Automation"
                placeholderTextColor={Colors.mutedForeground}
              />
            </View>

            <View style={styles.modalButtons}>
              <CustomButton
                title="Cancel"
                onPress={() => setShowCloneModal(false)}
                variant="outline"
                style={styles.modalButton}
                disabled={cloning}
              />
              <CustomButton
                title={cloning ? 'Cloning...' : 'Clone'}
                onPress={handleClone}
                variant="default"
                style={styles.modalButton}
                disabled={cloning || !areaName.trim()}
              />
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: Colors.backgroundLight,
    paddingTop: Platform.OS === 'ios' ? 0 : StatusBar.currentHeight,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingTop: Platform.OS === 'ios' ? 8 : 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: 8,
  },
  backButtonContainer: {
    alignItems: 'flex-start',
  },
  backButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    minWidth: 80,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  deleteButton: {
    padding: 8,
    borderRadius: 6,
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cloneButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  titleSection: {
    marginBottom: 16,
  },
  title: {
    ...TextStyles.h2,
    color: Colors.textDark,
    fontFamily: FontFamilies.heading,
    marginBottom: 8,
  },
  categoryBadge: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.muted,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  categoryText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  stats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
    marginBottom: 16,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    ...TextStyles.h3,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 8,
  },
  sectionSubtitle: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginBottom: 12,
  },
  description: {
    ...TextStyles.body,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    lineHeight: 22,
  },
  longDescription: {
    marginTop: 12,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  tagText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  workflowCard: {
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  workflowBadge: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.primary,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginBottom: 8,
  },
  workflowBadgeReaction: {
    backgroundColor: Colors.success,
  },
  workflowBadgeText: {
    fontSize: 12,
    color: Colors.backgroundLight,
    fontFamily: FontFamilies.body,
    fontWeight: '600',
  },
  workflowTitle: {
    ...TextStyles['body-bold'],
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 4,
  },
  workflowDescription: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  errorCard: {
    margin: 16,
  },
  errorTitle: {
    ...TextStyles['body-bold'],
    color: Colors.error,
    fontFamily: FontFamilies.body,
    marginBottom: 4,
  },
  errorText: {
    ...TextStyles.small,
    color: Colors.error,
    fontFamily: FontFamilies.body,
    marginBottom: 12,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  loadingText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginTop: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  modalContent: {
    backgroundColor: Colors.cardLight,
    borderRadius: 12,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    ...TextStyles.h2,
    color: Colors.textDark,
    fontFamily: FontFamilies.heading,
    marginBottom: 8,
  },
  modalDescription: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginBottom: 16,
  },
  modalInput: {
    marginBottom: 16,
  },
  inputLabel: {
    ...TextStyles['body-bold'],
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: Colors.input,
    padding: 12,
    borderRadius: 6,
    backgroundColor: Colors.backgroundLight,
    color: Colors.textDark,
    ...TextStyles.body,
    fontFamily: FontFamilies.body,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  modalButton: {
    flex: 1,
  },
});
