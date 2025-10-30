"use client";

import { useState, useEffect, useCallback } from "react";
import { searchTemplates, getTemplateCategories, getTemplateTags } from "@/lib/api";
import type {
  Template,
  TemplateCategory,
  TemplateTag,
  TemplateSearchParams,
  PaginatedResponse,
} from "@/lib/types/marketplace";

interface UseMarketplaceSearchState {
  templates: Template[];
  categories: TemplateCategory[];
  availableTags: TemplateTag[];
  loading: boolean;
  error: string | null;
  pagination: {
    total: number;
    page: number;
    size: number;
    pages: number;
  };
}

interface UseMarketplaceSearchActions {
  setSearchQuery: (query: string) => void;
  setCategory: (category: string | undefined) => void;
  setTags: (tags: string[]) => void;
  setSort: (sortBy: string, order: string) => void;
  setPage: (page: number) => void;
  refresh: () => void;
}

const DEBOUNCE_DELAY = 500;

export function useMarketplaceSearch(initialPageSize = 12): [
  UseMarketplaceSearchState,
  UseMarketplaceSearchActions
] {
  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [category, setCategory] = useState<string | undefined>();
  const [tags, setTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("usage_count");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(initialPageSize);

  // Data state
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [availableTags, setAvailableTags] = useState<TemplateTag[]>([]);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    size: initialPageSize,
    pages: 0,
  });
  
  // Loading & error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      // Reset to page 1 when search changes
      if (searchQuery !== debouncedQuery) {
        setPage(1);
      }
    }, DEBOUNCE_DELAY);

    return () => {
      clearTimeout(handler);
    };
  }, [searchQuery, debouncedQuery]);

  // Load categories and tags on mount
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const [categoriesData, tagsData] = await Promise.all([
          getTemplateCategories(),
          getTemplateTags(50),
        ]);
        setCategories(categoriesData);
        setAvailableTags(tagsData);
      } catch (err) {
        console.error("Failed to load marketplace metadata:", err);
      }
    };

    loadMetadata();
  }, []);

  // Search templates when filters change
  useEffect(() => {
    const performSearch = async () => {
      setLoading(true);
      setError(null);

      try {
        const params: TemplateSearchParams = {
          page,
          size: pageSize,
          sort_by: sortBy as TemplateSearchParams["sort_by"],
          order: order as "asc" | "desc",
        };

        if (debouncedQuery) params.q = debouncedQuery;
        if (category) params.category = category;
        if (tags.length > 0) params.tags = tags;

        const result: PaginatedResponse<Template> = await searchTemplates(params);
        
        setTemplates(result.items);
        setPagination({
          total: result.total,
          page: result.page,
          size: result.size,
          pages: result.pages,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load templates");
        setTemplates([]);
      } finally {
        setLoading(false);
      }
    };

    performSearch();
  }, [debouncedQuery, category, tags, sortBy, order, page, pageSize]);

  const setSort = useCallback((newSortBy: string, newOrder: string) => {
    setSortBy(newSortBy);
    setOrder(newOrder);
    setPage(1); // Reset to first page when sorting changes
  }, []);

  const refresh = useCallback(() => {
    // Trigger re-fetch by updating a dependency
    setPage(p => p);
  }, []);

  return [
    {
      templates,
      categories,
      availableTags,
      loading,
      error,
      pagination,
    },
    {
      setSearchQuery,
      setCategory,
      setTags,
      setSort,
      setPage,
      refresh,
    },
  ];
}
