/**
 * Marketplace types for workflow template sharing
 */

export interface Template {
  id: string;
  original_area_id: string | null;
  publisher_user_id: string;
  title: string;
  description: string;
  long_description: string | null;
  category: string;
  tags: string[];
  template_json: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "archived";
  visibility: "public" | "private" | "unlisted";
  usage_count: number;
  clone_count: number;
  rating_average: number | null;
  rating_count: number;
  created_at: string;
  published_at: string | null;
  approved_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TemplateSearchParams {
  q?: string;
  category?: string;
  tags?: string[];
  min_rating?: number;
  sort_by?: "created_at" | "usage_count" | "rating_average" | "title";
  order?: "asc" | "desc";
  page?: number;
  size?: number;
}

export interface AdminTemplateSearchParams extends TemplateSearchParams {
  status_filter?: "pending" | "approved" | "rejected" | "archived";
  visibility_filter?: "public" | "private" | "unlisted";
}

export interface AdminTemplateUpdateRequest {
  status?: "pending" | "approved" | "rejected" | "archived";
  visibility?: "public" | "private" | "unlisted";
}

export interface TemplatePublishRequest {
  area_id: string;
  title: string;
  description: string;
  long_description?: string;
  category: string;
  tags?: string[];
  visibility?: "public" | "private" | "unlisted";
}

export interface TemplateCloneRequest {
  area_name: string;
  parameter_overrides?: Record<string, unknown>;
}

export interface TemplateCloneResponse {
  created_area_id: string;
  message: string;
}

export interface TemplateCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
}

export interface TemplateTag {
  id: string;
  name: string;
  slug: string;
  usage_count: number;
  created_at: string;
}
