"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { requestJson, UnauthorizedError } from "@/lib/api";
import { useAuthContext } from "@/components/auth-provider";

interface ApiKeyConnectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  service: {
    id: string;
    name: string;
  };
  onConnect: () => void;
}

export default function ApiKeyConnectionDialog({ 
  open, 
  onOpenChange, 
  service, 
  onConnect 
}: ApiKeyConnectionDialogProps) {
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const auth = useAuthContext();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!auth.token) {
        toast.error("Authentication required. Please log in.");
        return;
      }

      // Clean the API key by removing any leading/trailing whitespace
      const cleanedApiKey = apiKey.trim();
      
      // Call the API to add the API key connection
      const response = await requestJson<{ message: string }>(
        `/service-connections/api-key/${service.id}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ api_key: cleanedApiKey }),
        },
        auth.token
      );

      if (response.message) {
        toast.success(`${service.name} connected successfully!`);
        onConnect();
        onOpenChange(false);
      }
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Failed to connect service.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  // Validate API key format based on service
  const getApiKeyValidation = () => {
    if (service.id === 'openai') {
      // OpenAI API keys start with "sk-", "sk-proj-", or "sk-svcacct-"
      return {
        isValid: (apiKey.startsWith("sk-") || apiKey.startsWith("sk-proj-") || apiKey.startsWith("sk-svcacct-")) && apiKey.length > 10,
        helpText: 'For OpenAI, API keys start with "sk-".'
      };
    } else if (service.id === 'weather') {
      // Weather API keys are alphanumeric (OpenWeatherMap format)
      return {
        isValid: apiKey.length >= 32, // OpenWeatherMap API keys are 32 characters
        helpText: 'Get your API key from OpenWeatherMap (https://openweathermap.org/api).'
      };
    }
    // Default validation for other services
    return {
      isValid: apiKey.trim().length > 0,
      helpText: 'Your API key will be encrypted and stored securely.'
    };
  };

  const { isValid: isValidApiKey, helpText } = getApiKeyValidation();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add API Key for {service.name}</DialogTitle>
          <DialogDescription>
            Enter your {service.name} API key to connect your account.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="service-name">Service</Label>
            <Input 
              id="service-name" 
              value={service.name} 
              readOnly 
              disabled
              className="bg-muted cursor-not-allowed opacity-60" 
            />
          </div>
          <div>
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder={`Enter your ${service.name} API key`}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground mt-2">
              Your API key will be encrypted and stored securely. {helpText}
            </p>
          </div>
          
          {error && (
            <div className="text-sm text-red-500">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-2">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => {
                onOpenChange(false);
                setApiKey("");
                setError("");
              }}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={!isValidApiKey || loading}
            >
              {loading ? "Connecting..." : "Connect"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}