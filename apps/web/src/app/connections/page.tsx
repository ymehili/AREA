"use client";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { UnauthorizedError, requestJson } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";
import { cn, headingClasses } from "@/lib/utils";
import ApiKeyConnectionDialog from "@/components/api-key-connection-dialog";

// Define API-key services - these services use API keys instead of OAuth
const API_KEY_SERVICES = ["openai"];

type Service = {
  id: string;
  name: string;
  description: string;
  connected: boolean;
  connection_id?: string;
  is_api_key_service: boolean; // New field to distinguish between OAuth and API-key services
};

type ServiceFromAPI = {
  slug: string;
  name: string;
  description: string;
};

type ServiceListResponse = {
  services: ServiceFromAPI[];
};

type ServiceConnection = {
  id: string;
  service_name: string;
  oauth_metadata?: {
    provider: string;
    user_info: {
      login?: string;
      name?: string;
    };
  };
};

type ServiceConnectionsResponse = ServiceConnection[];

type OAuthProvidersResponse = {
  providers: string[];
};

type ServiceConnectionTestResponse = {
  success: boolean;
  [key: string]: unknown;
};

export default function ConnectionsPage() {
  const auth = useRequireAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApiKeyService, setSelectedApiKeyService] = useState<Service | null>(null);

  const loadServices = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      // Load available services from catalog
      const servicesData = await requestJson<ServiceListResponse>(
        "/services/services",
        { method: "GET" },
        auth.token,
      );

      // Load OAuth providers
      const providersData = await requestJson<OAuthProvidersResponse>(
        "/service-connections/providers",
        { method: "GET" },
        auth.token,
      );

      // Load existing connections
      const connectionsData = await requestJson<ServiceConnectionsResponse>(
        "/users/me/connections",
        { method: "GET" },
        auth.token,
      );

      // Combine OAuth providers and API-key services to determine which to show
      const allSupportedServices = [...providersData.providers, ...API_KEY_SERVICES];

      // Filter services to only show those with either OAuth or API-key implementations
      // and merge with connection status
      const transformed = servicesData.services
        .filter((service) => allSupportedServices.includes(service.slug))
        .map((service) => {
          const connection = connectionsData.find(
            (conn) => conn.service_name === service.slug
          );
          return {
            id: service.slug,
            name: service.name,
            description: service.description,
            connected: !!connection,
            connection_id: connection?.id,
            is_api_key_service: API_KEY_SERVICES.includes(service.slug),
          };
        });

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

  // Handle OAuth2 callback messages from URL parameters
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const error = urlParams.get('error');
    const service = urlParams.get('service');

    if (success === 'connected' && service) {
      toast.success(`Successfully connected to ${service}!`);
      // Clean up URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
      // Reload services to show new connection
      void loadServices();
    } else if (error) {
      let errorMessage = 'Failed to connect to service.';
      switch (error) {
        case 'invalid_state':
          errorMessage = 'Security check failed. Please try again.';
          break;
        case 'session_expired':
          errorMessage = 'Session expired. Please try connecting again.';
          break;
        case 'connection_failed':
          errorMessage = 'Failed to establish connection. Please try again.';
          break;
        case 'access_denied':
          errorMessage = 'Access was denied. Please authorize the application.';
          break;
        case 'already_connected':
          errorMessage = `You are already connected to ${service || 'this service'}.`;
          break;
      }
      toast.error(errorMessage);
      // Clean up URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [loadServices]);

  const connectService = async (serviceId: string) => {
    if (!auth.token) {
      toast.error("Authentication required. Please log in again.");
      return;
    }

    try {
      const data = await requestJson<{ authorization_url: string }>(
        `/service-connections/connect/${serviceId}`,
        { method: "POST", credentials: "include" },
        auth.token,
      );

      if (!data.authorization_url) {
        toast.error("Unable to start OAuth flow. Please try again.");
        return;
      }

      window.location.href = data.authorization_url;
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }

      const message =
        err instanceof Error ? err.message : "Unable to initiate service connection.";
      toast.error(message);
    }
  };

  const disconnectService = async (serviceId: string, connectionId: string) => {
    if (!auth.token) {
      return;
    }

    try {
      await requestJson(
        `/service-connections/connections/${connectionId}`,
        { method: "DELETE" },
        auth.token,
      );

      toast.success(`${serviceId} disconnected successfully.`);
      // Reload services to update connection status
      void loadServices();
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Unable to disconnect service.";
      toast.error(message);
    }
  };

  const testConnection = async (serviceId: string, connectionId: string) => {
    if (!auth.token) {
      return;
    }

    try {
      const testResult = await requestJson<ServiceConnectionTestResponse>(
        `/service-connections/test/${serviceId}/${connectionId}`,
        { method: "GET" },
        auth.token,
      );

      if (testResult.success) {
        toast.success(`${serviceId} connection test successful!`);
      } else {
        toast.error(`${serviceId} connection test failed.`);
      }
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Unable to test connection.";
      toast.error(message);
    }
  };

  const handleApiKeyConnect = (service: Service) => {
    setSelectedApiKeyService(service);
  };

  const handleApiKeyDialogClose = () => {
    setSelectedApiKeyService(null);
    void loadServices(); // Reload to ensure the connection status is updated
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className={cn(headingClasses(1), "text-foreground")}>Service Connection Hub</h1>
      </div>

      {loading ? (
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-4">
              <CardHeader className="p-0 mb-4">
                <div className="flex flex-row items-center justify-between space-y-0">
                  <Skeleton className="h-6 w-32" />
                  <Skeleton className="h-5 w-24 rounded-full" />
                </div>
              </CardHeader>
              <CardContent className="flex gap-2 justify-end">
                <Skeleton className="h-9 w-20" />
              </CardContent>
            </Card>
          ))}
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
                  <Badge variant={s.connected ? "default" : "secondary"} className={s.connected ? "" : "text-white"}>
                    {s.connected ? "Connected" : "Not connected"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex gap-2 justify-end">
                {s.connected ? (
                  <>
                    {s.connection_id && (
                      <Button
                        className="cursor-pointer"
                        variant="secondary"
                        size="sm"
                        onClick={() => testConnection(s.id, s.connection_id!)}
                      >
                        Test
                      </Button>
                    )}
                    <Button
                      className="cursor-pointer"
                      variant="destructive"
                      onClick={() => s.connection_id && disconnectService(s.id, s.connection_id)}
                    >
                      Disconnect
                    </Button>
                  </>
                ) : s.is_api_key_service ? (
                  <Button onClick={() => handleApiKeyConnect(s)}>Add API Key</Button>
                ) : (
                  <Button onClick={() => void connectService(s.id)}>Connect</Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* API Key Connection Dialog */}
      {selectedApiKeyService && (
        <ApiKeyConnectionDialog
          open={!!selectedApiKeyService}
          onOpenChange={() => setSelectedApiKeyService(null)}
          service={selectedApiKeyService}
          onConnect={handleApiKeyDialogClose}
        />
      )}
    </AppShell>
  );
}
