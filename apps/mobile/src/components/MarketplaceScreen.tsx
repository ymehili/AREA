import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Platform,
  StatusBar,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import TemplateCard from './marketplace/TemplateCard';
import CustomButton from './ui/Button';
import Card from './ui/Card';
import { Colors } from '../constants/colors';
import { TextStyles, FontFamilies } from '../constants/typography';
import {
  searchTemplates,
  getTemplateCategories,
  getTemplateTags,
} from '../utils/marketplace';
import type {
  Template,
  TemplateCategory,
  TemplateTag,
  TemplateSearchParams,
} from '../types/marketplace';

interface MarketplaceScreenProps {
  apiBaseUrl: string;
}

export default function MarketplaceScreen({ apiBaseUrl }: MarketplaceScreenProps) {
  const navigation = useNavigation<any>();
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState<'usage_count' | 'created_at' | 'rating_average' | 'title'>('usage_count');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Data state
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    size: pageSize,
    pages: 0,
  });

  // Loading & error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      if (searchQuery !== debouncedQuery) {
        setPage(1);
      }
    }, 500);

    return () => clearTimeout(handler);
  }, [searchQuery, debouncedQuery]);

  // Load categories on mount
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const categoriesData = await getTemplateCategories(apiBaseUrl);
        setCategories(categoriesData);
      } catch (err) {
        console.error('Failed to load marketplace metadata:', err);
      }
    };

    loadMetadata();
  }, [apiBaseUrl]);

  // Search templates when filters change
  const performSearch = useCallback(async () => {
    const shouldShowLoading = templates.length === 0;
    if (shouldShowLoading) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const params: TemplateSearchParams = {
        page,
        size: pageSize,
        sort_by: sortBy,
        order,
      };

      if (debouncedQuery) params.q = debouncedQuery;
      if (selectedCategory) params.category = selectedCategory;

      const result = await searchTemplates(apiBaseUrl, params);

      setTemplates(result.items);
      setPagination({
        total: result.total,
        page: result.page,
        size: result.size,
        pages: result.pages,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
      setTemplates([]);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [apiBaseUrl, debouncedQuery, selectedCategory, sortBy, order, page, templates.length]);

  useEffect(() => {
    performSearch();
  }, [performSearch]);

  const handleRefresh = () => {
    setPage(1);
    performSearch();
  };

  const handleNextPage = () => {
    if (page < pagination.pages) {
      setPage(page + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1);
    }
  };

  const handleTemplatePress = (templateId: string) => {
    navigation.navigate('TemplateDetail', { templateId });
  };

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.h1}>Workflow Marketplace</Text>
        <Text style={styles.subtitle}>
          Discover and clone automation workflows created by the community
        </Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchInputWrapper}>
          <Ionicons
            name="search"
            size={20}
            color={Colors.mutedForeground}
            style={styles.searchIcon}
          />
          <TextInput
            style={styles.searchInput}
            placeholder="Search workflows..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholderTextColor={Colors.mutedForeground}
          />
        </View>
        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => setShowFilters(!showFilters)}
        >
          <Ionicons
            name="options-outline"
            size={24}
            color={Colors.primary}
          />
        </TouchableOpacity>
      </View>

      {/* Filters */}
      {showFilters && (
        <Card style={styles.filtersCard}>
          <Text style={styles.filterTitle}>Filters</Text>
          
          {/* Category Filter */}
          <View style={styles.filterSection}>
            <Text style={styles.filterLabel}>Category</Text>
            <View style={styles.categoryButtons}>
              <TouchableOpacity
                style={[
                  styles.categoryButton,
                  !selectedCategory && styles.categoryButtonActive,
                ]}
                onPress={() => {
                  setSelectedCategory(undefined);
                  setPage(1);
                }}
              >
                <Text
                  style={[
                    styles.categoryButtonText,
                    !selectedCategory && styles.categoryButtonTextActive,
                  ]}
                >
                  All
                </Text>
              </TouchableOpacity>
              {categories.map((category) => (
                <TouchableOpacity
                  key={category.id}
                  style={[
                    styles.categoryButton,
                    selectedCategory === category.slug && styles.categoryButtonActive,
                  ]}
                  onPress={() => {
                    setSelectedCategory(category.slug);
                    setPage(1);
                  }}
                >
                  <Text
                    style={[
                      styles.categoryButtonText,
                      selectedCategory === category.slug && styles.categoryButtonTextActive,
                    ]}
                  >
                    {category.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Sort Options */}
          <View style={styles.filterSection}>
            <Text style={styles.filterLabel}>Sort By</Text>
            <View style={styles.sortButtons}>
              {[
                { label: 'Most Popular', value: 'usage_count', order: 'desc' as const },
                { label: 'Newest First', value: 'created_at', order: 'desc' as const },
                { label: 'Highest Rated', value: 'rating_average', order: 'desc' as const },
              ].map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.sortButton,
                    sortBy === option.value && order === option.order && styles.sortButtonActive,
                  ]}
                  onPress={() => {
                    setSortBy(option.value as typeof sortBy);
                    setOrder(option.order);
                    setPage(1);
                  }}
                >
                  <Text
                    style={[
                      styles.sortButtonText,
                      sortBy === option.value && order === option.order && styles.sortButtonTextActive,
                    ]}
                  >
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </Card>
      )}

      {/* Results Summary */}
      {!loading && templates.length > 0 && (
        <View style={styles.resultsInfo}>
          <Text style={styles.resultsText}>
            Showing {(pagination.page - 1) * pagination.size + 1} -{' '}
            {Math.min(pagination.page * pagination.size, pagination.total)} of{' '}
            {pagination.total} templates
          </Text>
        </View>
      )}

      {/* Error State */}
      {error && (
        <Card style={styles.errorCard}>
          <Text style={styles.errorTitle}>Failed to load templates</Text>
          <Text style={styles.errorText}>{error}</Text>
          <CustomButton
            title="Try Again"
            onPress={handleRefresh}
            variant="outline"
            style={styles.errorButton}
          />
        </Card>
      )}

      {/* Loading State */}
      {loading && templates.length === 0 && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading templates...</Text>
        </View>
      )}

      {/* Templates List */}
      {!loading && !error && (
        <ScrollView
          style={styles.templatesList}
          refreshControl={
            <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />
          }
        >
          {templates.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="folder-open-outline" size={64} color={Colors.mutedForeground} />
              <Text style={styles.emptyTitle}>No templates found</Text>
              <Text style={styles.emptyText}>
                Try adjusting your filters or search query
              </Text>
            </View>
          ) : (
            <>
              {templates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onPress={() => handleTemplatePress(template.id)}
                />
              ))}

              {/* Pagination */}
              {pagination.pages > 1 && (
                <View style={styles.pagination}>
                  <CustomButton
                    title="Previous"
                    onPress={handlePrevPage}
                    disabled={page === 1}
                    variant="outline"
                    style={styles.paginationButton}
                  />
                  <Text style={styles.paginationText}>
                    Page {pagination.page} of {pagination.pages}
                  </Text>
                  <CustomButton
                    title="Next"
                    onPress={handleNextPage}
                    disabled={page >= pagination.pages}
                    variant="outline"
                    style={styles.paginationButton}
                  />
                </View>
              )}
            </>
          )}
        </ScrollView>
      )}
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
    padding: 16,
    paddingTop: Platform.OS === 'ios' ? 8 : 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  h1: {
    ...TextStyles.h2,
    color: Colors.textDark,
    fontFamily: FontFamilies.heading,
    marginBottom: 4,
  },
  subtitle: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 8,
  },
  searchInputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 8,
    paddingHorizontal: 12,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    ...TextStyles.body,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  filterButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 8,
  },
  filtersCard: {
    marginHorizontal: 16,
    marginBottom: 16,
  },
  filterTitle: {
    ...TextStyles.h3,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 12,
  },
  filterSection: {
    marginBottom: 16,
  },
  filterLabel: {
    ...TextStyles['body-bold'],
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginBottom: 8,
  },
  categoryButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  categoryButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 6,
  },
  categoryButtonActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  categoryButtonText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  categoryButtonTextActive: {
    color: Colors.backgroundLight,
  },
  sortButtons: {
    gap: 8,
  },
  sortButton: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: Colors.backgroundLight,
    borderWidth: 1,
    borderColor: Colors.input,
    borderRadius: 6,
  },
  sortButtonActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  sortButtonText: {
    fontSize: 14,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
  },
  sortButtonTextActive: {
    color: Colors.backgroundLight,
  },
  resultsInfo: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  resultsText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
  },
  templatesList: {
    flex: 1,
    paddingHorizontal: 16,
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
  errorButton: {
    marginTop: 8,
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
  emptyState: {
    alignItems: 'center',
    padding: 48,
  },
  emptyTitle: {
    ...TextStyles.h3,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginTop: 16,
    marginBottom: 8,
  },
  emptyText: {
    ...TextStyles.small,
    color: Colors.mutedForeground,
    fontFamily: FontFamilies.body,
    textAlign: 'center',
  },
  pagination: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    marginTop: 8,
  },
  paginationButton: {
    flex: 1,
    marginHorizontal: 4,
  },
  paginationText: {
    ...TextStyles.small,
    color: Colors.textDark,
    fontFamily: FontFamilies.body,
    marginHorizontal: 8,
  },
});
