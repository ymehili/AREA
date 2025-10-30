"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import AppShell from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { TemplateCard, TemplateSearch, TemplateFilters } from "@/components/marketplace";
import { useMarketplaceSearch } from "@/hooks/useMarketplaceSearch";
import { headingClasses } from "@/lib/utils";

export default function MarketplacePage() {
  const [state, actions] = useMarketplaceSearch(12);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("usage_count");
  const [order, setOrder] = useState("desc");

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    actions.setSearchQuery(query);
  };

  const handleCategoryChange = (category: string | undefined) => {
    setSelectedCategory(category);
    actions.setCategory(category);
  };

  const handleTagsChange = (tags: string[]) => {
    setSelectedTags(tags);
    actions.setTags(tags);
  };

  const handleSortChange = (newSortBy: string, newOrder: string) => {
    setSortBy(newSortBy);
    setOrder(newOrder);
    actions.setSort(newSortBy, newOrder);
  };

  return (
    <AppShell>
      <div className="container mx-auto py-8 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className={headingClasses(1)}>
            Workflow Marketplace
          </h1>
          <p className="text-muted-foreground text-lg">
            Discover and clone automation workflows created by the community
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl">
          <TemplateSearch
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Search workflows by name, description, or tags..."
          />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <aside className="lg:col-span-1">
            <TemplateFilters
              categories={state.categories}
              availableTags={state.availableTags}
              selectedCategory={selectedCategory}
              selectedTags={selectedTags}
              onCategoryChange={handleCategoryChange}
              onTagsChange={handleTagsChange}
              sortBy={sortBy}
              order={order}
              onSortChange={handleSortChange}
            />
          </aside>

          {/* Templates Grid */}
          <div className="lg:col-span-3 space-y-6">
            {/* Results Summary */}
            {!state.loading && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {state.pagination.total === 0 ? (
                    "No templates found"
                  ) : (
                    <>
                      Showing{" "}
                      <span className="font-medium text-foreground">
                        {(state.pagination.page - 1) * state.pagination.size + 1}
                      </span>
                      {" - "}
                      <span className="font-medium text-foreground">
                        {Math.min(
                          state.pagination.page * state.pagination.size,
                          state.pagination.total
                        )}
                      </span>
                      {" of "}
                      <span className="font-medium text-foreground">
                        {state.pagination.total}
                      </span>
                      {" templates"}
                    </>
                  )}
                </p>
              </div>
            )}

            {/* Error State */}
            {state.error && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
                <p className="font-medium">Failed to load templates</p>
                <p className="text-sm mt-1">{state.error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={actions.refresh}
                  className="mt-3"
                >
                  Try Again
                </Button>
              </div>
            )}

            {/* Loading State */}
            {state.loading && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Card key={i} className="h-[240px]">
                    <CardHeader>
                      <Skeleton className="h-6 w-3/4" />
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-2/3" />
                    </CardHeader>
                    <CardContent>
                      <div className="flex gap-2">
                        <Skeleton className="h-6 w-16" />
                        <Skeleton className="h-6 w-16" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Templates Grid */}
            {!state.loading && !state.error && state.templates.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {state.templates.map((template) => (
                  <TemplateCard key={template.id} template={template} />
                ))}
              </div>
            )}

            {/* Empty State */}
            {!state.loading && !state.error && state.templates.length === 0 && (
              <div className="text-center py-12 space-y-3">
                <p className="text-lg font-medium">No templates found</p>
                <p className="text-muted-foreground">
                  Try adjusting your filters or search query
                </p>
              </div>
            )}

            {/* Pagination */}
            {!state.loading && state.pagination.pages > 1 && (
              <div className="flex items-center justify-between border-t pt-6">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => actions.setPage(state.pagination.page - 1)}
                  disabled={state.pagination.page === 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>

                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Page {state.pagination.page} of {state.pagination.pages}
                  </span>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => actions.setPage(state.pagination.page + 1)}
                  disabled={state.pagination.page >= state.pagination.pages}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
