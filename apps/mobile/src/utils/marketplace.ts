/**
 * Marketplace API utilities for workflow template sharing
 */

import type {
  Template,
  PaginatedResponse,
  TemplateSearchParams,
  TemplatePublishRequest,
  TemplateCloneRequest,
  TemplateCloneResponse,
  TemplateCategory,
  TemplateTag,
} from '../types/marketplace';

// Use the same API base URL resolver from App.tsx
// This will be imported from the main API utility module

/**
 * Search and filter marketplace templates (PUBLIC - no auth required)
 */
export async function searchTemplates(
  apiBaseUrl: string,
  params?: TemplateSearchParams,
): Promise<PaginatedResponse<Template>> {
  const searchParams = new URLSearchParams();
  
  if (params?.q) searchParams.set("q", params.q);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.tags) params.tags.forEach(tag => searchParams.append("tags", tag));
  if (params?.min_rating !== undefined) searchParams.set("min_rating", params.min_rating.toString());
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params?.order) searchParams.set("order", params.order);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.size) searchParams.set("size", params.size.toString());
  
  const queryString = searchParams.toString();
  const url = queryString 
    ? `${apiBaseUrl}/marketplace/templates?${queryString}` 
    : `${apiBaseUrl}/marketplace/templates`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to search templates: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get a specific template by ID (PUBLIC - no auth required)
 */
export async function getTemplateById(
  apiBaseUrl: string,
  templateId: string
): Promise<Template> {
  const response = await fetch(`${apiBaseUrl}/marketplace/templates/${templateId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to get template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get all available template categories (PUBLIC)
 */
export async function getTemplateCategories(
  apiBaseUrl: string
): Promise<TemplateCategory[]> {
  const response = await fetch(`${apiBaseUrl}/marketplace/categories`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to get categories: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get popular template tags (PUBLIC)
 */
export async function getTemplateTags(
  apiBaseUrl: string,
  limit = 50
): Promise<TemplateTag[]> {
  const response = await fetch(`${apiBaseUrl}/marketplace/tags?limit=${limit}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to get tags: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Publish an area as a marketplace template (requires auth)
 */
export async function publishTemplate(
  apiBaseUrl: string,
  token: string,
  request: TemplatePublishRequest,
): Promise<Template> {
  const response = await fetch(`${apiBaseUrl}/marketplace/templates`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to publish template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Clone a marketplace template to create a new area (requires auth)
 */
export async function cloneTemplate(
  apiBaseUrl: string,
  token: string,
  templateId: string,
  request: TemplateCloneRequest,
): Promise<TemplateCloneResponse> {
  const response = await fetch(`${apiBaseUrl}/marketplace/templates/${templateId}/clone`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to clone template: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a marketplace template (requires auth, only owner can delete)
 */
export async function deleteTemplate(
  apiBaseUrl: string,
  token: string,
  templateId: string,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/marketplace/templates/${templateId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed to delete template: ${response.statusText}`);
  }
}
