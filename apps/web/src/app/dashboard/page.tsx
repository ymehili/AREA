"use client";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn, headingClasses } from "@/lib/utils";
import { UnauthorizedError, requestJson, deleteArea as apiDeleteArea } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";
import { Share2 } from "lucide-react";

type AreaFromAPI = {
  id: string;
  name: string;
  trigger_service: string;
  trigger_action: string;
  reaction_service: string;
  reaction_action: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

type Area = {
  id: string;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
};

export default function DashboardPage() {
  const auth = useRequireAuth();
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAreas = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await requestJson<AreaFromAPI[]>(
        "/areas",
        { method: "GET" },
        auth.token,
      );
      const transformed = data.map(area => ({
        id: area.id,
        name: area.name,
        trigger: `${area.trigger_service}: ${area.trigger_action}`,
        action: `${area.reaction_service}: ${area.reaction_action}`,
        enabled: area.enabled,
      }));
      setAreas(transformed);
      setError(null);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Unable to load areas.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    void loadAreas();
  }, [loadAreas]);

  const toggleArea = async (id: string, enabled: boolean) => {
    try {
      const endpoint = enabled ? `/areas/${id}/enable` : `/areas/${id}/disable`;
      await requestJson<AreaFromAPI>(
        endpoint,
        { method: "POST" },
        auth.token,
      );
      setAreas((prev) => prev.map((a) => (a.id === id ? { ...a, enabled } : a)));
      toast.success(`Area ${enabled ? "enabled" : "disabled"}`);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : `Failed to ${enabled ? "enable" : "disable"} area.`;
      toast.error(message);
    }
  };

  const removeArea = async (id: string) => {
    try {
      await apiDeleteArea(auth.token!, id);
      setAreas((prev) => prev.filter((a) => a.id !== id));
      toast.success("Area deleted");
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Failed to delete area.";
      toast.error(message);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-between mb-6">
          <h1 className={cn(headingClasses(1), "text-foreground")}>Dashboard</h1>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>Create AREA</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => (window.location.href = "/wizard/simple")}>
                Simple Wizard
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => (window.location.href = "/wizard")}>
                Advanced Builder
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <CardHeader className="p-0 pb-4">
                <div className="flex flex-row items-center justify-between">
                  <Skeleton className="h-6 w-32" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="space-y-2 mb-6">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                </div>
                <div className="flex items-center justify-between pt-4">
                  <Skeleton className="h-6 w-12" />
                  <div className="flex gap-2">
                    <Skeleton className="h-8 w-16" />
                    <Skeleton className="h-8 w-16" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex items-center justify-between mb-6">
          <h1 className={cn(headingClasses(1), "text-foreground")}>Dashboard</h1>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>Create AREA</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => (window.location.href = "/wizard/simple")}>
                Simple Wizard
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => (window.location.href = "/wizard")}>
                Advanced Builder
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="text-destructive text-center">
            <p className="font-semibold">Error loading areas</p>
            <p>{error}</p>
            <Button onClick={() => void loadAreas()} className="mt-4">
              Retry
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className={cn(headingClasses(1), "text-foreground")}>Dashboard</h1>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button>Create AREA</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => (window.location.href = "/wizard/simple")}>
              Simple Wizard
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => (window.location.href = "/wizard")}>
              Advanced Builder
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {areas.length === 0 ? (
        <Card className="p-6">
          <CardHeader className="p-0 pb-4">
            <CardTitle className={cn(headingClasses(3), "text-foreground")}>Get started</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <p className="text-sm text-muted-foreground mb-6">You have no AREAs yet. Create your first automation:</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Button onClick={() => (window.location.href = "/wizard/simple")} className="flex-1">
                Simple Wizard
              </Button>
              <Button onClick={() => (window.location.href = "/wizard")} variant="outline" className="flex-1">
                Advanced Builder
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {areas.map((area) => (
            <Card key={area.id} className="p-6 flex flex-col">
              <CardHeader className="p-0 pb-4">
                <div className="flex flex-row items-center justify-between">
                  <CardTitle className="text-lg font-medium text-foreground">{area.name}</CardTitle>
                  <Badge variant={area.enabled ? "default" : "secondary"} className={area.enabled ? "" : "text-white"}>
                    {area.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0 flex-grow">
                <div className="text-sm text-muted-foreground mb-6">
                  <div className="mb-2">When: {area.trigger}</div>
                  <div>Then: {area.action}</div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Switch
                      checked={area.enabled}
                      onCheckedChange={(v) => void toggleArea(area.id, v)}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.location.href = `/wizard/${area.id}`}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => void removeArea(area.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={() => window.location.href = `/marketplace/publish?area_id=${area.id}`}
                  >
                    <Share2 className="h-4 w-4 mr-2" />
                    Publish to Marketplace
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
