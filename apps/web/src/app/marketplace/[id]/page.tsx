"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Copy, Star, Users, Calendar, Tag } from "lucide-react";
import { toast } from "sonner";
import AppShell from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { getTemplateById, cloneTemplate } from "@/lib/api";
import { loadStoredSession } from "@/lib/api";
import type { Template } from "@/lib/types/marketplace";
import { headingClasses } from "@/lib/utils";

interface TemplateJsonStructure {
  trigger?: {
    service?: string;
    action?: string;
  };
  reaction?: {
    service?: string;
    action?: string;
  };
  steps?: Array<{
    service?: string;
    action?: string;
  }>;
}

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const templateId = params.id as string;
  
  const [template, setTemplate] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Clone dialog state
  const [showCloneDialog, setShowCloneDialog] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [areaName, setAreaName] = useState("");

  useEffect(() => {
    const loadTemplate = async () => {
      try {
        setLoading(true);
        const data = await getTemplateById(templateId);
        setTemplate(data);
        setAreaName(`Clone of ${data.title}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load template");
      } finally {
        setLoading(false);
      }
    };

    loadTemplate();
  }, [templateId]);

  const handleClone = async () => {
    const session = loadStoredSession();
    if (!session?.token) {
      toast.error("Please sign in to clone templates");
      router.push("/auth/signin");
      return;
    }

    if (!template) return;

    try {
      setCloning(true);
      await cloneTemplate(session.token, template.id, {
        area_name: areaName,
        parameter_overrides: {},
      });
      
      toast.success("Template cloned successfully!");
      router.push(`/dashboard`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to clone template");
    } finally {
      setCloning(false);
      setShowCloneDialog(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 space-y-6 max-w-4xl">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  if (error || !template) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 max-w-4xl">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-destructive">
            <p className="font-medium">Failed to load template</p>
            <p className="text-sm mt-1">{error || "Template not found"}</p>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="container mx-auto py-8 space-y-6 max-w-4xl">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => router.back()}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Marketplace
        </Button>

        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <h1 className={headingClasses(1)}>{template.title}</h1>
              <p className="text-lg text-muted-foreground">{template.description}</p>
            </div>
            <Button size="lg" onClick={() => setShowCloneDialog(true)}>
              <Copy className="h-4 w-4 mr-2" />
              Clone Template
            </Button>
          </div>

          {/* Metadata */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <Badge variant="secondary" className="text-sm">
              {template.category}
            </Badge>
            
            <div className="flex items-center gap-1.5">
              <Users className="h-4 w-4" />
              <span>{template.usage_count.toLocaleString()} uses</span>
            </div>
            
            <div className="flex items-center gap-1.5">
              <Copy className="h-4 w-4" />
              <span>{template.clone_count.toLocaleString()} clones</span>
            </div>
            
            {template.rating_average !== null && (
              <div className="flex items-center gap-1.5">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                <span>{template.rating_average.toFixed(1)}</span>
                <span className="text-xs">({template.rating_count} ratings)</span>
              </div>
            )}
            
            <div className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              <span>{new Date(template.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Tags */}
          {template.tags && template.tags.length > 0 && (
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <div className="flex flex-wrap gap-1.5">
                {template.tags.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Long Description */}
        {template.long_description && (
          <Card>
            <CardHeader>
              <CardTitle>About this Template</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-muted-foreground">
                {template.long_description}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Workflow Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Workflow Structure</CardTitle>
            <CardDescription>
              This template contains the following automation workflow
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {template.template_json && typeof template.template_json === 'object' && (() => {
                const json = template.template_json as TemplateJsonStructure;
                return (
                  <>
                    {/* Trigger */}
                    {json.trigger && (
                      <div className="p-4 rounded-lg border bg-card">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="default">Trigger</Badge>
                          <span className="text-sm font-medium">
                            {json.trigger.service || 'Unknown'} - {json.trigger.action || 'Unknown'}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Starts the automation when this event occurs
                        </p>
                      </div>
                    )}

                    {/* Reaction */}
                    {json.reaction && (
                      <div className="p-4 rounded-lg border bg-card">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="secondary">Action</Badge>
                          <span className="text-sm font-medium">
                            {json.reaction.service || 'Unknown'} - {json.reaction.action || 'Unknown'}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Performs this action when triggered
                        </p>
                      </div>
                    )}

                    {/* Steps */}
                    {json.steps && json.steps.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium">Additional Steps:</p>
                        {json.steps.map((step, index) => (
                          <div key={index} className="p-3 rounded-lg border bg-card">
                            <span className="text-sm">
                              {step.service || 'Unknown'} - {step.action || 'Unknown'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </CardContent>
        </Card>

        {/* Clone Dialog */}
        <Dialog open={showCloneDialog} onOpenChange={setShowCloneDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Clone Template</DialogTitle>
              <DialogDescription>
                Give your new automation a name. You can customize it later.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="area-name">Automation Name</Label>
                <Input
                  id="area-name"
                  value={areaName}
                  onChange={(e) => setAreaName(e.target.value)}
                  placeholder="My Automation"
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowCloneDialog(false)}
                disabled={cloning}
              >
                Cancel
              </Button>
              <Button
                onClick={handleClone}
                disabled={cloning || !areaName.trim()}
              >
                {cloning ? "Cloning..." : "Clone Template"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
