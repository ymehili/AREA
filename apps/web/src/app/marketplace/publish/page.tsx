"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import AppShell from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useRequireAuth } from "@/hooks/use-auth";
import { publishTemplate, getTemplateCategories, getTemplateTags } from "@/lib/api";
import type { TemplateCategory, TemplateTag, TemplatePublishRequest } from "@/lib/types/marketplace";
import { headingClasses } from "@/lib/utils";

// Mock API function to get user's areas - you'll need to implement this
async function getUserAreas(token: string): Promise<Array<{ id: string; name: string; template_json: Record<string, unknown> }>> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/areas`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error("Failed to fetch areas");
  }
  return response.json();
}

function PublishTemplateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAreaId = searchParams.get("area_id");
  
  const auth = useRequireAuth();
  const { token, initializing: authLoading } = auth;
  
  const [areas, setAreas] = useState<Array<{ id: string; name: string; template_json: Record<string, unknown> }>>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [availableTags, setAvailableTags] = useState<TemplateTag[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Form state
  const [selectedAreaId, setSelectedAreaId] = useState<string>("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [longDescription, setLongDescription] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [visibility, setVisibility] = useState<"public" | "private" | "unlisted">("public");
  const [tagSearch, setTagSearch] = useState("");
  
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (!token) return;

    const loadData = async () => {
      try {
        setLoading(true);
        const [areasData, categoriesData, tagsData] = await Promise.all([
          getUserAreas(token),
          getTemplateCategories(),
          getTemplateTags(50),
        ]);
        
        setAreas(areasData);
        setCategories(categoriesData);
        setAvailableTags(tagsData);
        
        // Preselect area if provided
        if (preselectedAreaId && areasData.some(a => a.id === preselectedAreaId)) {
          setSelectedAreaId(preselectedAreaId);
          const area = areasData.find(a => a.id === preselectedAreaId);
          if (area) {
            setTitle(area.name);
          }
        }
      } catch (err) {
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token, preselectedAreaId]);

  const handlePublish = async () => {
    if (!token) {
      toast.error("Please sign in to publish templates");
      return;
    }

    if (!selectedAreaId) {
      toast.error("Please select an automation to publish");
      return;
    }

    if (!title.trim() || !description.trim() || !selectedCategory) {
      toast.error("Please fill in all required fields");
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

      const result = await publishTemplate(token, request);
      
      toast.success("Template published successfully!");
      router.push(`/marketplace/${result.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to publish template");
    } finally {
      setPublishing(false);
    }
  };

  const handleAddTag = (tag: string) => {
    if (!selectedTags.includes(tag)) {
      setSelectedTags([...selectedTags, tag]);
      setTagSearch("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setSelectedTags(selectedTags.filter(t => t !== tag));
  };

  const filteredTags = availableTags
    .filter(tag => 
      !selectedTags.includes(tag.name) && 
      tag.name.toLowerCase().includes(tagSearch.toLowerCase())
    )
    .slice(0, 10);

  if (authLoading || loading) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 max-w-2xl">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </AppShell>
    );
  }

  const selectedArea = areas.find(a => a.id === selectedAreaId);

  return (
    <AppShell>
      <div className="container mx-auto py-8 space-y-6 max-w-2xl">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => router.back()}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>

        {/* Header */}
        <div className="space-y-2">
          <h1 className={headingClasses(1)}>Publish Template</h1>
          <p className="text-lg text-muted-foreground">
            Share your automation with the community
          </p>
        </div>

        {/* Form */}
        <div className="space-y-6">
          {/* Select Area */}
          <div className="space-y-2">
            <Label htmlFor="area">Automation to Publish *</Label>
            <Select value={selectedAreaId} onValueChange={setSelectedAreaId}>
              <SelectTrigger id="area">
                <SelectValue placeholder="Select an automation" />
              </SelectTrigger>
              <SelectContent>
                {areas.map((area) => (
                  <SelectItem key={area.id} value={area.id}>
                    {area.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {areas.length === 0 && (
              <p className="text-sm text-muted-foreground">
                You don&apos;t have any automations yet. Create one first!
              </p>
            )}
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Template Title *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="My Awesome Automation"
              maxLength={255}
            />
            <p className="text-xs text-muted-foreground">
              {title.length}/255 characters
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Short Description *</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A brief description of what this automation does..."
              maxLength={500}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              {description.length}/500 characters
            </p>
          </div>

          {/* Long Description */}
          <div className="space-y-2">
            <Label htmlFor="long-description">Detailed Description (Optional)</Label>
            <Textarea
              id="long-description"
              value={longDescription}
              onChange={(e) => setLongDescription(e.target.value)}
              placeholder="Provide more details about how to use this template, what it's useful for, configuration tips, etc."
              rows={6}
            />
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="category">Category *</Label>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger id="category">
                <SelectValue placeholder="Select a category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((category) => (
                  <SelectItem key={category.name} value={category.name}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <div className="space-y-2">
              {/* Selected Tags */}
              {selectedTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedTags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-1.5 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              {/* Tag Search */}
              <Input
                id="tags"
                value={tagSearch}
                onChange={(e) => setTagSearch(e.target.value)}
                placeholder="Search tags..."
              />

              {/* Tag Suggestions */}
              {tagSearch && filteredTags.length > 0 && (
                <div className="rounded-md border p-2 space-y-1 max-h-48 overflow-y-auto">
                  {filteredTags.map((tag) => (
                    <button
                      key={tag.name}
                      onClick={() => handleAddTag(tag.name)}
                      className="w-full text-left px-2 py-1.5 text-sm hover:bg-accent rounded-sm flex items-center justify-between"
                    >
                      <span>{tag.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {tag.usage_count} uses
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Visibility */}
          <div className="space-y-2">
            <Label>Visibility *</Label>
            <RadioGroup value={visibility} onValueChange={(v: string) => setVisibility(v as typeof visibility)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="public" id="public" />
                <Label htmlFor="public" className="font-normal cursor-pointer">
                  <span className="font-medium">Public</span> - Anyone can discover and use this template
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="unlisted" id="unlisted" />
                <Label htmlFor="unlisted" className="font-normal cursor-pointer">
                  <span className="font-medium">Unlisted</span> - Only people with the link can access
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="private" id="private" />
                <Label htmlFor="private" className="font-normal cursor-pointer">
                  <span className="font-medium">Private</span> - Only you can see this template
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Preview */}
          {selectedArea && (
            <Card>
              <CardHeader>
                <CardTitle>Workflow Preview</CardTitle>
                <CardDescription>
                  This is what will be shared with the template
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-4 rounded-md overflow-x-auto max-h-64">
                  {JSON.stringify(selectedArea.template_json, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}

          {/* Submit */}
          <div className="flex gap-4">
            <Button
              variant="outline"
              onClick={() => router.back()}
              disabled={publishing}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handlePublish}
              disabled={publishing || !selectedAreaId || !title.trim() || !description.trim() || !selectedCategory}
              className="flex-1"
            >
              {publishing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Publishing...
                </>
              ) : (
                "Publish Template"
              )}
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function PublishTemplatePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PublishTemplateContent />
    </Suspense>
  );
}
