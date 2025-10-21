"use client";

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createAreaWithSteps } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { cn, headingClasses } from '@/lib/utils';

type CatalogService = {
  slug: string;
  name: string;
  description: string;
  actions: Array<{ key: string; name: string; description: string }>;
  reactions: Array<{ key: string; name: string; description: string }>;
};

export default function SimpleWizardPage() {
  const router = useRouter();
  const auth = useAuth();
  const [step, setStep] = useState(1);
  const [triggerService, setTriggerService] = useState("");
  const [trigger, setTrigger] = useState("");
  const [actionService, setActionService] = useState("");
  const [action, setAction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [catalogServices, setCatalogServices] = useState<CatalogService[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  // Load catalog services on mount
  useEffect(() => {
    const loadCatalog = async () => {
      if (!auth.token) {
        setCatalogError("Not authenticated");
        setLoadingCatalog(false);
        return;
      }
      setLoadingCatalog(true);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/services/actions-reactions`,
          {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${auth.token}`,
            },
          }
        );
        
        if (!response.ok) {
          throw new Error('Failed to load services catalog');
        }
        
        const data = await response.json();
        console.log(`[SimpleWizard] Loaded ${data.services.length} services from catalog`);
        setCatalogServices(data.services);
        setCatalogError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load services catalog.";
        setCatalogError(message);
        console.error("[SimpleWizard] Failed to load catalog:", message);
        toast.error("Failed to load services catalog");
      } finally {
        setLoadingCatalog(false);
      }
    };
    void loadCatalog();
  }, [auth.token]);

  // Get services that have actions (triggers)
  const servicesWithActions = React.useMemo(() => {
    return catalogServices.filter((service) => service.actions.length > 0);
  }, [catalogServices]);

  // Get services that have reactions
  const servicesWithReactions = React.useMemo(() => {
    return catalogServices.filter((service) => service.reactions.length > 0);
  }, [catalogServices]);

  // Get actions for selected trigger service
  const availableActions = React.useMemo(() => {
    const service = catalogServices.find((s) => s.slug === triggerService);
    return service?.actions ?? [];
  }, [catalogServices, triggerService]);

  // Get reactions for selected action service
  const availableReactions = React.useMemo(() => {
    const service = catalogServices.find((s) => s.slug === actionService);
    return service?.reactions ?? [];
  }, [catalogServices, actionService]);

  const canNext = React.useMemo(() => {
    if (step === 1) return !!triggerService;
    if (step === 2) return !!trigger;
    if (step === 3) return !!actionService;
    if (step === 4) return !!action;
    return true;
  }, [step, triggerService, trigger, actionService, action]);

  const handleNext = () => {
    setStep(Math.min(step + 1, 5));
  };

  const handleBack = () => {
    setStep(Math.max(step - 1, 1));
  };

  const submit = useCallback(async () => {
    if (!auth.token) {
      toast.error("Not signed in. Please log in first.");
      return;
    }
    if (!(triggerService && trigger && actionService && action)) {
      toast.error("Complete all steps before creating the AREA.");
      return;
    }
    setSubmitting(true);
    try {
      const areaData = {
        name: `${triggerService} → ${actionService}`,
        description: `If ${trigger} in ${triggerService}, then ${action} in ${actionService}`,
        is_active: true,
        trigger_service: triggerService,
        trigger_action: trigger,
        reaction_service: actionService,
        reaction_action: action,
        steps: [
          {
            step_type: "trigger" as const,
            order: 0,
            service: triggerService,
            action: trigger,
            config: { position: { x: 250, y: 50 } },
          },
          {
            step_type: "action" as const,
            order: 1,
            service: actionService,
            action: action,
            config: { position: { x: 250, y: 200 } },
          },
        ],
      };

      const result = await createAreaWithSteps(auth.token, areaData);
      
      // Link the steps
      if (result.steps && result.steps.length >= 2) {
        const triggerStep = result.steps.find((s: { step_type: string }) => s.step_type === "trigger");
        const actionStep = result.steps.find((s: { step_type: string }) => s.step_type === "action");
        
        if (triggerStep && actionStep) {
          await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/areas/steps/${triggerStep.id}`, {
            method: "PATCH",
            headers: {
              "Authorization": `Bearer ${auth.token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              config: {
                ...triggerStep.config,
                targets: [actionStep.id],
              },
            }),
          });
        }
      }

      toast.success("AREA created successfully!");
      router.push('/dashboard');
    } catch (error) {
      console.error('Error creating area:', error);
      
      // Show specific error message from the API
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error("Failed to create AREA. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }, [auth, triggerService, trigger, actionService, action, router]);

  if (loadingCatalog) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 max-w-3xl">
          <Card>
            <CardContent className="py-12 text-center">
              <div className="flex flex-col items-center gap-4">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
                <p className="text-muted-foreground">Loading services...</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  if (catalogError) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle>Error Loading Services</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-destructive mb-4">{catalogError}</p>
              <div className="flex gap-2">
                <Button onClick={() => router.push('/dashboard')} variant="outline">
                  Back to Dashboard
                </Button>
                <Button onClick={() => window.location.reload()}>
                  Retry
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="container mx-auto py-8 max-w-3xl">
        <div className="mb-8">
          <h1 className={cn(headingClasses(1), "text-foreground")}>AREA Creation Wizard</h1>
          <p className="text-muted-foreground mt-2">
            Create a simple automation in 5 easy steps
          </p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Step {step} of 5</CardTitle>
            {/* Progress indicator */}
            <div className="flex gap-2 mt-4">
              {[1, 2, 3, 4, 5].map((s) => (
                <div
                  key={s}
                  className={cn(
                    "h-2 flex-1 rounded-full transition-all duration-200",
                    s <= step ? "bg-primary" : "bg-muted"
                  )}
                />
              ))}
            </div>
          </CardHeader>
          <CardContent className="relative overflow-hidden">
            {/* Step content container with slide animation */}
            <div className="relative" style={{ minHeight: '300px' }}>
              {/* Step 1 */}
              <div
                className={cn(
                  "absolute inset-0 transition-all duration-300 ease-in-out",
                  step === 1
                    ? "translate-x-0 opacity-100"
                    : step > 1
                    ? "-translate-x-full opacity-0 pointer-events-none"
                    : "translate-x-full opacity-0 pointer-events-none"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Trigger Service</h3>
                  <p className="text-sm text-muted-foreground">
                    When this happens... ({servicesWithActions.length} available)
                  </p>
                  {servicesWithActions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No services with triggers available. Please check your server connection.
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 gap-3">
                      {servicesWithActions.map((service) => (
                        <Button
                          key={service.slug}
                          variant={triggerService === service.slug ? "default" : "outline"}
                          onClick={() => {
                            setTriggerService(service.slug);
                            setTrigger(""); // Reset trigger when service changes
                          }}
                          className="w-full"
                        >
                          {service.name}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Step 2 */}
              <div
                className={cn(
                  "absolute inset-0 transition-all duration-300 ease-in-out",
                  step === 2
                    ? "translate-x-0 opacity-100"
                    : step > 2
                    ? "-translate-x-full opacity-0 pointer-events-none"
                    : "translate-x-full opacity-0 pointer-events-none"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Trigger Action</h3>
                  <p className="text-sm text-muted-foreground">
                    From {catalogServices.find(s => s.slug === triggerService)?.name || triggerService} ({availableActions.length} available)
                  </p>
                  {availableActions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No triggers available for this service.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {availableActions.map((action) => (
                        <Button
                          key={action.key}
                          variant={trigger === action.key ? "default" : "outline"}
                          onClick={() => setTrigger(action.key)}
                          className="w-full flex flex-col items-start h-auto py-3"
                        >
                          <span className="font-semibold">{action.name}</span>
                          {action.description && (
                            <span className="text-xs text-muted-foreground font-normal mt-1">
                              {action.description}
                            </span>
                          )}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Step 3 */}
              <div
                className={cn(
                  "absolute inset-0 transition-all duration-300 ease-in-out",
                  step === 3
                    ? "translate-x-0 opacity-100"
                    : step > 3
                    ? "-translate-x-full opacity-0 pointer-events-none"
                    : "translate-x-full opacity-0 pointer-events-none"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Reaction Service</h3>
                  <p className="text-sm text-muted-foreground">
                    Then do this... ({servicesWithReactions.length} available)
                  </p>
                  {servicesWithReactions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No services with reactions available. Please check your server connection.
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 gap-3">
                      {servicesWithReactions.map((service) => (
                        <Button
                          key={service.slug}
                          variant={actionService === service.slug ? "default" : "outline"}
                          onClick={() => {
                            setActionService(service.slug);
                            setAction(""); // Reset action when service changes
                          }}
                          className="w-full"
                        >
                          {service.name}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Step 4 */}
              <div
                className={cn(
                  "absolute inset-0 transition-all duration-300 ease-in-out",
                  step === 4
                    ? "translate-x-0 opacity-100"
                    : step > 4
                    ? "-translate-x-full opacity-0 pointer-events-none"
                    : "translate-x-full opacity-0 pointer-events-none"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Reaction Action</h3>
                  <p className="text-sm text-muted-foreground">
                    In {catalogServices.find(s => s.slug === actionService)?.name || actionService} ({availableReactions.length} available)
                  </p>
                  {availableReactions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No reactions available for this service.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {availableReactions.map((reaction) => (
                        <Button
                          key={reaction.key}
                          variant={action === reaction.key ? "default" : "outline"}
                          onClick={() => setAction(reaction.key)}
                          className="w-full flex flex-col items-start h-auto py-3"
                        >
                          <span className="font-semibold">{reaction.name}</span>
                          {reaction.description && (
                            <span className="text-xs text-muted-foreground font-normal mt-1">
                              {reaction.description}
                            </span>
                          )}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Step 5 - Review */}
              <div
                className={cn(
                  "absolute inset-0 transition-all duration-300 ease-in-out",
                  step === 5
                    ? "translate-x-0 opacity-100"
                    : "translate-x-full opacity-0 pointer-events-none"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Review & Confirm</h3>
                  <Card className="bg-muted/50 border-2">
                    <CardContent className="pt-6">
                      <p className="text-sm font-medium mb-2">Your automation:</p>
                      <p className="text-base">
                        <span className="font-semibold">When</span> &ldquo;{availableActions.find(a => a.key === trigger)?.name || trigger}&rdquo; happens in{" "}
                        <span className="font-semibold">{catalogServices.find(s => s.slug === triggerService)?.name || triggerService}</span>
                      </p>
                      <p className="text-base mt-2">
                        <span className="font-semibold">Then</span> &ldquo;{availableReactions.find(r => r.key === action)?.name || action}&rdquo; in{" "}
                        <span className="font-semibold">{catalogServices.find(s => s.slug === actionService)?.name || actionService}</span>
                      </p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Navigation buttons */}
        <div className="flex justify-between gap-4">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={step === 1 || submitting}
          >
            Back
          </Button>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => router.push('/dashboard')}
              disabled={submitting}
            >
              Cancel
            </Button>
            
            {step < 5 ? (
              <Button
                onClick={handleNext}
                disabled={!canNext || submitting}
              >
                Next
              </Button>
            ) : (
              <Button
                onClick={submit}
                disabled={submitting}
              >
                {submitting ? "Creating..." : "Create AREA"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
