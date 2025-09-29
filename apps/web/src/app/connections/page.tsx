"use client";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { UnauthorizedError, requestJson } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";
import { cn, headingClasses } from "@/lib/utils";

type Service = {
  id: string;
  name: string;
  description: string;
  connected: boolean;
};

type ServiceFromAPI = {
  slug: string;
  name: string;
  description: string;
};

type ServiceListResponse = {
  services: ServiceFromAPI[];
};

export default function ConnectionsPage() {
  const auth = useRequireAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadServices = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await requestJson<ServiceListResponse>(
        "/services/services",
        { method: "GET" },
        auth.token,
      );
      const transformed = data.services.map((service) => ({
        id: service.slug,
        name: service.name,
        description: service.description,
        connected: false,
      }));
      setServices(transformed);
      setError(null);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Unable to load services.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    void loadServices();
  }, [loadServices]);

  const toggle = (id: string, state: boolean) => {
    setServices((prev) => prev.map((s) => (s.id === id ? { ...s, connected: state } : s)));
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className={cn(headingClasses(1), "text-foreground")}>Service Connection Hub</h1>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      ) : error ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-destructive text-center">
            <p className="font-semibold">Error loading services</p>
            <p>{error}</p>
            <Button onClick={() => void loadServices()} className="mt-4">
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <Card key={s.id} className="p-4">
              <CardHeader className="p-0 mb-4">
                <div className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-lg text-foreground">{s.name}</CardTitle>
                  <Badge variant={s.connected ? "default" : "secondary"}>
                    {s.connected ? "Connected" : "Not connected"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <p className="text-sm text-muted-foreground mb-4">{s.description}</p>
                <div className="flex justify-end">
                  {s.connected ? (
                    <Button variant="outline" onClick={() => toggle(s.id, false)}>
                      Disconnect
                    </Button>
                  ) : (
                    <Button onClick={() => toggle(s.id, true)}>Connect</Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
