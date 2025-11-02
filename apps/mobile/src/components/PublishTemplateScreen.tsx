import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TextInput,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import CustomButton from './ui/Button';
import Card from './ui/Card';
import { Colors } from '../constants/colors';
import { TextStyles, FontFamilies } from '../constants/typography';
import {
  publishTemplate,
  getTemplateCategories,
  getTemplateTags,
} from '../utils/marketplace';
import type {
  TemplateCategory,
  TemplateTag,
  TemplatePublishRequest,
} from '../types/marketplace';

interface Area {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
}

interface PublishTemplateScreenProps {
  apiBaseUrl: string;
  token: string | null;
}

export default function PublishTemplateScreen({
  apiBaseUrl,
  token,
}: PublishTemplateScreenProps) {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { areaId: preselectedAreaId } = route.params || {};

  const [areas, setAreas] = useState<Area[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [availableTags, setAvailableTags] = useState<TemplateTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);

  // Form state
  const [selectedAreaId, setSelectedAreaId] = useState<string>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [longDescription, setLongDescription] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [visibility, setVisibility] = useState<'public' | 'private' | 'unlisted'>('public');
  const [tagSearch, setTagSearch] = useState('');
  const [showTagPicker, setShowTagPicker] = useState(false);
  const [showAreaPicker, setShowAreaPicker] = useState(false);
  const [showCategoryPicker, setShowCategoryPicker] = useState(false);

  useEffect(() => {
    if (!token) {
      Alert.alert('Authentication Required', 'Please log in to publish templates.');
      navigation.goBack();
      return;
    }

    const loadData = async () => {
      try {
        setLoading(true);

        // Fetch user's areas
        const areasResponse = await fetch(`${apiBaseUrl}/areas`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!areasResponse.ok) {
          throw new Error('Failed to fetch areas');
        }

        const areasData = await areasResponse.json();

        const [categoriesData, tagsData] = await Promise.all([
          getTemplateCategories(apiBaseUrl),
          getTemplateTags(apiBaseUrl, 50),
        ]);

        setAreas(areasData);
        setCategories(categoriesData);
        setAvailableTags(tagsData);

        // Preselect area if provided
        if (preselectedAreaId && areasData.some((a: Area) => a.id === preselectedAreaId)) {
          setSelectedAreaId(preselectedAreaId);
          const area = areasData.find((a: Area) => a.id === preselectedAreaId);
          if (area) {
            setTitle(area.name);
          }
        }
      } catch (err) {
        Alert.alert('Error', 'Failed to load data. Please try again.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token, apiBaseUrl, preselectedAreaId, navigation]);

  const handlePublish = async () => {
    if (!token) {
      Alert.alert('Authentication Required', 'Please log in to publish templates.');
      return;
    }

    if (!selectedAreaId) {
      Alert.alert('Missing Information', 'Please select an automation to publish.');
      return;
    }

    if (!title.trim() || !description.trim() || !selectedCategory) {
      Alert.alert('Missing Information', 'Please fill in all required fields.');
      return;
    }

    try {
      setPublishing(true);

      const request: TemplatePublishRequest = {
        area_id: selectedAreaId,
        title: title.trim(),
        description: description.trim(),
        long_description: longDescription.trim() || undefined,
        category: selectedCategory,
        tags: selectedTags,
        visibility,
      };

      const result = await publishTemplate(apiBaseUrl, token, request);

      Alert.alert(
        'Success',
        'Template published successfully!',
        [
          {
            text: 'View Template',
            onPress: () => {
              navigation.navigate('TemplateDetail', { templateId: result.id });
            },
          },
          {
            text: 'Go to Marketplace',
            onPress: () => {
              navigation.navigate('MainTabs', { screen: 'Marketplace' });
            },
          },
        ]
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to publish template';
      Alert.alert('Publish Failed', message);
    } finally {
      setPublishing(false);
    }
  };

  const handleAddTag = (tagName: string) => {
    if (!selectedTags.includes(tagName)) {
      setSelectedTags([...selectedTags, tagName]);
      setTagSearch('');
      setShowTagPicker(false);
    }
  };

  const handleRemoveTag = (tagName: string) => {
    setSelectedTags(selectedTags.filter((t) => t !== tagName));
  };

  const filteredTags = availableTags
    .filter(
      (tag) =>
        !selectedTags.includes(tag.name) &&
        tag.name.toLowerCase().includes(tagSearch.toLowerCase())
    )
    .slice(0, 10);

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <CustomButton
          title="← Back"
          onPress={() => navigation.goBack()}
          variant="outline"
        />
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.titleSection}>
          <Text style={styles.title}>Publish Template</Text>
          <Text style={styles.subtitle}>Share your automation with the community</Text>
        </View>

        {/* Select Area */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Automation to Publish *</Text>
          <TouchableOpacity
            style={styles.selectButton}
            onPress={() => setShowAreaPicker(true)}
          >
            <Text style={[styles.selectButtonText, !selectedAreaId && styles.selectButtonPlaceholder]}>
              {selectedAreaId
                ? areas.find((a) => a.id === selectedAreaId)?.name || 'Select an automation'
                : 'Select an automation'}
            </Text>
            <Ionicons name="chevron-down" size={20} color={Colors.mutedForeground} />
          </TouchableOpacity>
          {areas.length === 0 && (
            <Text style={styles.helpText}>
              You don't have any automations yet. Create one first!
            </Text>
          )}
        </View>

        {/* Title */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Template Title *</Text>
          <TextInput
            style={styles.input}
            value={title}
            onChangeText={setTitle}
            placeholder="My Awesome Automation"
            placeholderTextColor={Colors.mutedForeground}
            maxLength={255}
          />
          <Text style={styles.charCount}>{title.length}/255 characters</Text>
        </View>

        {/* Description */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Short Description *</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            value={description}
            onChangeText={setDescription}
            placeholder="A brief description of what this automation does..."
            placeholderTextColor={Colors.mutedForeground}
            maxLength={500}
            multiline
            numberOfLines={3}
          />
          <Text style={styles.charCount}>{description.length}/500 characters</Text>
        </View>

        {/* Long Description */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Detailed Description (Optional)</Text>
          <TextInput
            style={[styles.input, styles.textArea, styles.textAreaLarge]}
            value={longDescription}
            onChangeText={setLongDescription}
            placeholder="Provide more details about how to use this template, what it's useful for, configuration tips, etc."
            placeholderTextColor={Colors.mutedForeground}
            multiline
            numberOfLines={6}
          />
        </View>

        {/* Category */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Category *</Text>
          <TouchableOpacity
            style={styles.selectButton}
            onPress={() => setShowCategoryPicker(true)}
          >
            <Text style={[styles.selectButtonText, !selectedCategory && styles.selectButtonPlaceholder]}>
              {selectedCategory || 'Select a category'}
            </Text>
            <Ionicons name="chevron-down" size={20} color={Colors.mutedForeground} />
          </TouchableOpacity>
        </View>

        {/* Tags */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Tags *</Text>
          
          {/* Selected Tags */}
          {selectedTags.length > 0 && (
            <View style={styles.tagsContainer}>
              {selectedTags.map((tag) => (
                <View key={tag} style={styles.selectedTag}>
                  <Text style={styles.selectedTagText}>{tag}</Text>
                  <TouchableOpacity onPress={() => handleRemoveTag(tag)}>
                    <Ionicons name="close-circle" size={20} color={Colors.mutedForeground} />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          )}

          {/* Tag Search */}
          <TextInput
            style={styles.input}
            value={tagSearch}
            onChangeText={(text) => {
              setTagSearch(text);
              setShowTagPicker(text.length > 0);
            }}
            placeholder="Search tags..."
            placeholderTextColor={Colors.mutedForeground}
            onFocus={() => setShowTagPicker(tagSearch.length > 0)}
          />

          {/* Available Tags */}
          {showTagPicker && filteredTags.length > 0 && (
            <Card style={styles.tagPickerCard}>
              {filteredTags.map((tag) => (
                <TouchableOpacity
                  key={tag.id}
                  style={styles.tagOption}
                  onPress={() => handleAddTag(tag.name)}
                >
                  <Text style={styles.tagOptionText}>{tag.name}</Text>
                  <Text style={styles.tagUsageCount}>({tag.usage_count})</Text>
                </TouchableOpacity>
              ))}
            </Card>
          )}
        </View>

        {/* Visibility */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Visibility</Text>
          <View style={styles.visibilityOptions}>
            {[
              { value: 'public', label: 'Public', description: 'Visible to everyone' },
              { value: 'private', label: 'Private', description: 'Only visible to you' },
              { value: 'unlisted', label: 'Unlisted', description: 'Only accessible via direct link' },
            ].map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.visibilityOption,
                  visibility === option.value && styles.visibilityOptionActive,
                ]}
                onPress={() => setVisibility(option.value as typeof visibility)}
              >
                <View style={styles.radioButton}>
                  {visibility === option.value && <View style={styles.radioButtonInner} />}
                </View>
                <View style={styles.visibilityOptionText}>
                  <Text style={styles.visibilityOptionLabel}>{option.label}</Text>
                  <Text style={styles.visibilityOptionDescription}>{option.description}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Publish Button */}
        <View style={styles.publishButtonContainer}>
          <CustomButton
            title={publishing ? 'Publishing...' : 'Publish Template'}
            onPress={handlePublish}
            disabled={
              publishing ||
              !selectedAreaId ||
              !title.trim() ||
              !description.trim() ||
              !selectedCategory
            }
            variant="default"
          />
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>

      {/* Area Picker Modal */}
      <Modal
        visible={showAreaPicker}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowAreaPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Select Automation</Text>
            <ScrollView style={styles.modalScroll}>
              {areas.map((area) => (
                <TouchableOpacity
                  key={area.id}
                  style={[
                    styles.modalOption,
                    selectedAreaId === area.id && styles.modalOptionSelected,
                  ]}
                  onPress={() => {
                    setSelectedAreaId(area.id);
                    if (!title) {
                      setTitle(area.name);
                    }
                    setShowAreaPicker(false);
                  }}
                >
                  <Text style={styles.modalOptionText}>{area.name}</Text>
                  {selectedAreaId === area.id && (
                    <Ionicons name="checkmark" size={24} color={Colors.primary} />
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
            <CustomButton
              title="Cancel"
              onPress={() => setShowAreaPicker(false)}
              variant="outline"
            />
          </View>
        </View>
      </Modal>

      {/* Category Picker Modal */}
      <Modal
        visible={showCategoryPicker}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowCategoryPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Select Category</Text>
            <ScrollView style={styles.modalScroll}>
              {categories.map((category) => (
                <TouchableOpacity
                  key={category.id}
                  style={[
                    styles.modalOption,
                    selectedCategory === category.name && styles.modalOptionSelected,
                  ]}
                  onPress={() => {
                    setSelectedCategory(category.name);
                    setShowCategoryPicker(false);
                  }}
                >
                  <Text style={styles.modalOptionText}>{category.name}</Text>
                  {selectedCategory === category.name && (
                    <Ionicons name="checkmark" size={24} color={Colors.primary} />
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
            <CustomButton
              title="Cancel"
              onPress={() => setShowCategoryPicker(false)}
              variant="outline"
            />
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
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  content: {
    flex: 1,
    padding: 16,
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
  titleSection: {
    marginBottom: 24,
  },
  title: {
    ...TextStyles.h2,
    color: Colors.textDark,
    fontFamily: FontFamilies.heading,
    marginBottom: 4,
  },
  subtitle: {
    ...TextStyles.body,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
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
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  textAreaLarge: {
    minHeight: 120,
  },
  charCount: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginTop: 4,
    textAlign: 'right',
  },
  helpText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginTop: 4,
  },
  selectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: Colors.input,
    padding: 12,
    borderRadius: 6,
    backgroundColor: Colors.backgroundLight,
  },
  selectButtonText: {
    ...TextStyles.body,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  selectButtonPlaceholder: {
    color: Colors.mutedForeground,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 8,
  },
  selectedTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.muted,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    gap: 6,
  },
  selectedTagText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  tagPickerCard: {
    marginTop: 8,
    maxHeight: 200,
  },
  tagOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: 4,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  tagOptionText: {
    ...TextStyles.body,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  tagUsageCount: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  visibilityOptions: {
    gap: 8,
  },
  visibilityOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 6,
    backgroundColor: Colors.backgroundLight,
    gap: 12,
  },
  visibilityOptionActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.cardLight,
  },
  radioButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: Colors.input,
    justifyContent: 'center',
    alignItems: 'center',
  },
  radioButtonInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Colors.primary,
  },
  visibilityOptionText: {
    flex: 1,
  },
  visibilityOptionLabel: {
    ...TextStyles['body-bold'],
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  visibilityOptionDescription: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    marginTop: 2,
  },
  publishButtonContainer: {
    marginTop: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: Colors.cardLight,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 16,
    maxHeight: '80%',
  },
  modalTitle: {
    ...TextStyles.h3,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 16,
  },
  modalScroll: {
    maxHeight: 400,
    marginBottom: 16,
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  modalOptionSelected: {
    backgroundColor: Colors.cardLight,
  },
  modalOptionText: {
    ...TextStyles.body,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    flex: 1,
  },
});
