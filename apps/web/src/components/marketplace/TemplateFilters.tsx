"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import type { TemplateCategory, TemplateTag } from "@/lib/types/marketplace";

interface TemplateFiltersProps {
  categories: TemplateCategory[];
  availableTags: TemplateTag[];
  selectedCategory?: string;
  selectedTags: string[];
  onCategoryChange: (category: string | undefined) => void;
  onTagsChange: (tags: string[]) => void;
  sortBy: string;
  order: string;
  onSortChange: (sortBy: string, order: string) => void;
}

export function TemplateFilters({
  categories,
  availableTags,
  selectedCategory,
  selectedTags,
  onCategoryChange,
  onTagsChange,
  sortBy,
  order,
  onSortChange,
}: TemplateFiltersProps) {
  const [tagInput, setTagInput] = useState("");
  const [filteredTags, setFilteredTags] = useState<TemplateTag[]>(availableTags);

  useEffect(() => {
    if (tagInput) {
      setFilteredTags(
        availableTags.filter(tag =>
          tag.name.toLowerCase().includes(tagInput.toLowerCase()) &&
          !selectedTags.includes(tag.name)
        )
      );
    } else {
      setFilteredTags(availableTags.filter(tag => !selectedTags.includes(tag.name)));
    }
  }, [tagInput, availableTags, selectedTags]);

  const addTag = (tagName: string) => {
    if (!selectedTags.includes(tagName)) {
      onTagsChange([...selectedTags, tagName]);
    }
    setTagInput("");
  };

  const removeTag = (tagName: string) => {
    onTagsChange(selectedTags.filter(t => t !== tagName));
  };

  return (
    <div className="space-y-6 rounded-lg border p-6 bg-card">
      <h3 className="font-semibold">Filters</h3>

      {/* Category Filter */}
      <div className="space-y-2">
        <Label>Category</Label>
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          value={selectedCategory || ""}
          onChange={(e) => onCategoryChange(e.target.value || undefined)}
        >
          <option value="">All Categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.slug}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      {/* Tag Filter */}
      <div className="space-y-2">
        <Label>Tags</Label>
        
        {/* Selected Tags */}
        {selectedTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {selectedTags.map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1">
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  className="ml-1 hover:text-destructive"
                  aria-label={`Remove ${tag} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        {/* Tag Search */}
        <input
          type="text"
          placeholder="Search tags..."
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />

        {/* Available Tags */}
        {tagInput && filteredTags.length > 0 && (
          <div className="max-h-40 overflow-y-auto space-y-1 border rounded-md p-2">
            {filteredTags.slice(0, 10).map((tag) => (
              <button
                key={tag.id}
                onClick={() => addTag(tag.name)}
                className="w-full text-left px-2 py-1.5 text-sm rounded hover:bg-accent transition-colors"
              >
                <span className="font-medium">{tag.name}</span>
                <span className="text-xs text-muted-foreground ml-2">
                  ({tag.usage_count})
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Sort Options */}
      <div className="space-y-2">
        <Label>Sort By</Label>
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          value={`${sortBy}-${order}`}
          onChange={(e) => {
            const [newSortBy, newOrder] = e.target.value.split("-");
            onSortChange(newSortBy, newOrder);
          }}
        >
          <option value="usage_count-desc">Most Popular</option>
          <option value="created_at-desc">Newest First</option>
          <option value="rating_average-desc">Highest Rated</option>
          <option value="title-asc">Title (A-Z)</option>
          <option value="title-desc">Title (Z-A)</option>
        </select>
      </div>
    </div>
  );
}
