"use client";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState, useEffect } from "react";

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
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadServices = async () => {
      try {
        setLoading(true);
        // Use the correct port for the API
        const response = await fetch('http://localhost:8080/api/v1/services/services');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch services: ${response.status} ${response.statusText}`);
        }
        
        const data: ServiceListResponse = await response.json();
        
        // Transform the API response to match our UI needs
        const transformedServices: Service[] = data.services.map(service => ({
          id: service.slug,
          name: service.name,
          description: service.description,
          connected: false // Default to not connected
        }));
        
        setServices(transformedServices);
        setError(null);
      } catch (err) {
        console.error('Error fetching services:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        // Fallback to hardcoded services
        setServices([
          { id: "google", name: "Google Drive", description: "Cloud storage service", connected: true },
          { id: "gmail", name: "Gmail", description: "Email service", connected: true },
          { id: "slack", name: "Slack", description: "Team communication platform", connected: false },
          { id: "github", name: "GitHub", description: "Code hosting platform", connected: false },
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadServices();
  }, []);

  const toggle = (id: string, state: boolean) => {
    setServices((prev) => prev.map((s) => (s.id === id ? { ...s, connected: state } : s)));
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Service Connection Hub</h1>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        </div>
      ) : error ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-red-500 text-center">
            <p className="font-semibold">Error loading services</p>
            <p>{error}</p>
            <Button onClick={() => window.location.reload()} className="mt-4">
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <Card key={s.id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-base">{s.name}</CardTitle>
                <Badge variant={s.connected ? "default" : "secondary"}>
                  {s.connected ? "Connected" : "Not connected"}
                </Badge>
              </CardHeader>
              <CardContent className="flex gap-2 justify-end">
                {s.connected ? (
                  <Button variant="outline" onClick={() => toggle(s.id, false)}>
                    Disconnect
                  </Button>
                ) : (
                  <Button onClick={() => toggle(s.id, true)}>Connect</Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}

