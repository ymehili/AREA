"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "sonner";
import { searchTemplatesAdmin, updateTemplateAdmin } from "@/lib/api";
import type { Template, AdminTemplateSearchParams } from "@/lib/types/marketplace";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, RefreshCw, Eye, EyeOff, Lock } from "lucide-react";

export default function AdminTemplatesContent() {
  const auth = useAuth();
  
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [visibilityFilter, setVisibilityFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const loadTemplates = useCallback(async () => {
    if (!auth.token) return;
    
    setLoading(true);
    try {
      const params: AdminTemplateSearchParams = {
        page,
        size: pageSize,
        sort_by: "created_at",
        order: "desc",
      };
      
      if (searchQuery) params.q = searchQuery;
      if (statusFilter) params.status_filter = statusFilter as "pending" | "approved" | "rejected" | "archived";
      if (visibilityFilter) params.visibility_filter = visibilityFilter as "public" | "private" | "unlisted";
      
      const result = await searchTemplatesAdmin(auth.token, params);
      setTemplates(result.items);
      setTotal(result.total);
      setTotalPages(result.pages);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, [auth.token, page, searchQuery, statusFilter, visibilityFilter]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleUpdateTemplate = async (
    templateId: string,
    updates: { status?: "pending" | "approved" | "rejected" | "archived"; visibility?: "public" | "private" | "unlisted" }
  ) => {
    if (!auth.token) return;
    
    try {
      await updateTemplateAdmin(auth.token, templateId, updates);
      toast.success("Template updated successfully");
      loadTemplates();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update template");
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      approved: "default",
      pending: "secondary",
      rejected: "destructive",
      archived: "outline",
    };
    return (
      <Badge variant={variants[status] || "outline"}>
        {status}
      </Badge>
    );
  };

  const getVisibilityBadge = (visibility: string) => {
    const icons = {
      public: <Eye className="h-3 w-3 mr-1" />,
      private: <Lock className="h-3 w-3 mr-1" />,
      unlisted: <EyeOff className="h-3 w-3 mr-1" />,
    };
    return (
      <Badge variant="outline" className="flex items-center">
        {icons[visibility as keyof typeof icons]}
        {visibility}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search and filter marketplace templates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search templates..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? undefined : v)}>
                <SelectTrigger id="status">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="visibility">Visibility</Label>
              <Select value={visibilityFilter || "all"} onValueChange={(v) => setVisibilityFilter(v === "all" ? undefined : v)}>
                <SelectTrigger id="visibility">
                  <SelectValue placeholder="All visibilities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All visibilities</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="unlisted">Unlisted</SelectItem>
                  <SelectItem value="private">Private</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button onClick={loadTemplates} variant="outline" className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Templates Table */}
      <Card>
        <CardHeader>
          <CardTitle>Templates ({total})</CardTitle>
          <CardDescription>
            Manage all marketplace templates regardless of status or visibility
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No templates found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Visibility</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {templates.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell className="font-medium max-w-xs truncate">
                          {template.title}
                        </TableCell>
                        <TableCell>{template.category}</TableCell>
                        <TableCell>{getStatusBadge(template.status)}</TableCell>
                        <TableCell>{getVisibilityBadge(template.visibility)}</TableCell>
                        <TableCell>{template.usage_count} uses</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(template.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex gap-2 justify-end">
                            <Select
                              value={template.status}
                              onValueChange={(status) => 
                                handleUpdateTemplate(template.id, { status: status as "pending" | "approved" | "rejected" | "archived" })
                              }
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="pending">Pending</SelectItem>
                                <SelectItem value="approved">Approved</SelectItem>
                                <SelectItem value="rejected">Rejected</SelectItem>
                                <SelectItem value="archived">Archived</SelectItem>
                              </SelectContent>
                            </Select>
                            
                            <Select
                              value={template.visibility}
                              onValueChange={(visibility) => 
                                handleUpdateTemplate(template.id, { visibility: visibility as "public" | "private" | "unlisted" })
                              }
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="public">Public</SelectItem>
                                <SelectItem value="unlisted">Unlisted</SelectItem>
                                <SelectItem value="private">Private</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
