"use client";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn, headingClasses } from "@/lib/utils";
import { UnauthorizedError, requestJson, deleteArea as apiDeleteArea } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";

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
          <Button onClick={() => (window.location.href = "/wizard")}>Create AREA</Button>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex items-center justify-between mb-6">
          <h1 className={cn(headingClasses(1), "text-foreground")}>Dashboard</h1>
          <Button onClick={() => (window.location.href = "/wizard")}>Create AREA</Button>
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
        <Button onClick={() => (window.location.href = "/wizard")}>Create AREA</Button>
      </div>
      {areas.length === 0 ? (
        <Card className="p-6">
          <CardHeader className="p-0 pb-4">
            <CardTitle className={cn(headingClasses(3), "text-foreground")}>Get started</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <p className="text-sm text-muted-foreground mb-6">You have no AREAs yet.</p>
            <Button onClick={() => (window.location.href = "/wizard")}>Create your first AREA</Button>
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
                <div className="flex items-center justify-between pt-4">
                  <Switch
                    checked={area.enabled}
                    onCheckedChange={(v) => void toggleArea(area.id, v)}
                  />
                  <Button variant="destructive" size="sm" onClick={() => void removeArea(area.id)}>
                    Delete
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

