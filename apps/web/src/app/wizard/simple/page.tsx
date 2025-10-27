"use client";

import React, { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createAreaWithSteps, requestJson } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { cn, headingClasses } from '@/lib/utils';

interface AutomationOption {
  key: string;
  name: string;
  description: string;
  params?: Record<string, { type: string; label?: string; options?: string[]; placeholder?: string }>;
}

interface Service {
  slug: string;
  name: string;
  description: string;
  actions: AutomationOption[];
  reactions: AutomationOption[];
}

interface ParamDefinition {
  type: string;
  label?: string;
  options?: string[];
  placeholder?: string;
}

export default function SimpleWizardPage() {
  // Helper to render custom fields
  // Fallback param definitions for demo/testing if backend does not provide them
  const mockParams: Record<string, Record<string, ParamDefinition>> = {
    'temperature_threshold': {
      location: { type: 'text', label: 'Location', placeholder: 'City or coordinates' },
      threshold: { type: 'number', label: 'Temperature Threshold', placeholder: 'e.g. 20' },
      condition: { type: 'select', label: 'Condition', options: ['above', 'below'] },
    },
    'weather_condition': {
      location: { type: 'text', label: 'Location', placeholder: 'City or coordinates' },
      condition: { type: 'select', label: 'Condition', options: ['clear', 'clouds', 'rain', 'drizzle', 'thunderstorm', 'snow', 'mist', 'fog'] },
    },
    'new_email_from_sender': {
      sender: { type: 'text', label: 'Sender Email', placeholder: 'example@gmail.com' },
    },
    'send_email': {
      to: { type: 'text', label: 'Recipient(s)', placeholder: 'user@example.com' },
      subject: { type: 'text', label: 'Subject', placeholder: 'Email subject' },
      body: { type: 'text', label: 'Body', placeholder: 'Email body' },
    },
    'every_interval': {
      interval: { type: 'number', label: 'Interval (seconds)', placeholder: 'e.g. 60' },
    },
  };

  function getParamsDef(type: 'trigger' | 'action', key: string, params: Record<string, ParamDefinition> | undefined) {
    // First, use the params from the API if they exist and have fields
    if (params && typeof params === 'object' && Object.keys(params).length > 0) return params;
    // Then, try the mock params as fallback
    if (mockParams[key]) return mockParams[key];
    // If no params defined anywhere, return null
    return null;
  }

  function renderParamsFields(
    paramsDef: Record<string, ParamDefinition> | null, 
    values: Record<string, string | number>, 
    setValues: (v: Record<string, string | number>) => void
  ) {
    if (!paramsDef || typeof paramsDef !== 'object') return null;
    return Object.entries(paramsDef).map(([key, def]) => {
      const d = def;
      return (
        <div key={key} className="mb-3">
          <label className="block text-xs font-medium mb-1 text-foreground">{d.label || key}</label>
          {d.type === 'number' ? (
            <input
              type="number"
              value={values[key] ?? ''}
              onChange={e => setValues({ ...values, [key]: e.target.value !== '' ? Number(e.target.value) : '' })}
              className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
              placeholder={d.placeholder || ''}
            />
          ) : d.type === 'select' && Array.isArray(d.options) ? (
            <select
              value={values[key] ?? ''}
              onChange={e => setValues({ ...values, [key]: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
            >
              <option value="">Select...</option>
              {d.options.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={values[key] ?? ''}
              onChange={e => setValues({ ...values, [key]: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background"
              placeholder={d.placeholder || ''}
            />
          )}
        </div>
      );
    });
  }
  const router = useRouter();
  const auth = useAuth();
  const [step, setStep] = useState(1);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggerService, setTriggerService] = useState("");
  const [trigger, setTrigger] = useState("");
  const [actionService, setActionService] = useState("");
  const [action, setAction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // Params for trigger/action
  const [triggerParams, setTriggerParams] = useState<Record<string, string | number>>({});
  const [actionParams, setActionParams] = useState<Record<string, string | number>>({});
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');

  // Fetch services from API
  useEffect(() => {
    const fetchServices = async () => {
      if (!auth.token) return;
      
      try {
        const data = await requestJson<{ services: Service[] }>('/services/actions-reactions', {
          headers: {
            Authorization: `Bearer ${auth.token}`,
          },
        });
        setServices(data.services || []);
      } catch (error) {
        console.error('Failed to fetch services:', error);
        toast.error('Failed to load services');
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, [auth.token]);

  const triggerServices = services.filter(s => s.actions.length > 0);
  const reactionServices = services.filter(s => s.reactions.length > 0);
  
  const selectedTriggerService = services.find(s => s.slug === triggerService);
  const selectedActionService = services.find(s => s.slug === actionService);

  function areParamsFilled(paramsDef: Record<string, ParamDefinition> | null | undefined, values: Record<string, string | number>) {
    if (!paramsDef || !Object.keys(paramsDef).length) return true;
    return Object.entries(paramsDef).every(([key]) => {
      return values[key] !== undefined && values[key] !== '';
    });
  }

  const canNext = React.useMemo(() => {
    if (step === 1) return !!triggerService && !!areaName;
    if (step === 2) {
      if (!trigger) return false;
      const paramsDef = selectedTriggerService?.actions.find(a => a.key === trigger)?.params;
      return areParamsFilled(paramsDef, triggerParams);
    }
    if (step === 3) return !!actionService;
    if (step === 4) {
      if (!action) return false;
      const paramsDef = selectedActionService?.reactions.find(a => a.key === action)?.params;
      return areParamsFilled(paramsDef, actionParams);
    }
    return true;
  }, [step, triggerService, trigger, actionService, action, triggerParams, actionParams, selectedTriggerService, selectedActionService, areaName]);

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
        name: areaName,
        description: areaDescription,
        is_active: true,
        trigger_service: triggerService,
        trigger_action: trigger,
        trigger_params: Object.keys(triggerParams).length ? triggerParams : undefined,
        reaction_service: actionService,
        reaction_action: action,
        reaction_params: Object.keys(actionParams).length ? actionParams : undefined,
        steps: [
          {
            step_type: "trigger" as const,
            order: 0,
            service: triggerService,
            action: trigger,
            config: { position: { x: 250, y: 50 }, ...triggerParams },
          },
          {
            step_type: "action" as const,
            order: 1,
            service: actionService,
            action: action,
            config: { position: { x: 250, y: 200 }, ...actionParams },
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
  }, [auth, triggerService, trigger, actionService, action, router, areaName, areaDescription, triggerParams, actionParams]);

  if (loading) {
    return (
      <AppShell>
        <div className="container mx-auto py-8 max-w-3xl">
          <div className="text-center">Loading services...</div>
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
            <div className="relative min-h-[200px]">
              {/* Step 1 */}
              <div
                className={cn(
                  "transition-all duration-300 ease-in-out",
                  step === 1
                    ? "translate-x-0 opacity-100"
                    : step > 1
                    ? "hidden"
                    : "hidden"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Area Details</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium mb-2 text-foreground">
                        Area Name <span className="text-destructive"> *</span>
                      </label>
                      <input
                        type="text"
                        value={areaName}
                        onChange={(e) => setAreaName(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-[box-shadow] duration-150 bg-background"
                        placeholder="My Automation"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium mb-2 text-foreground">Description</label>
                      <textarea
                        value={areaDescription}
                        onChange={(e) => setAreaDescription(e.target.value)}
                        rows={3}
                        className="w-full px-3 py-2 text-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-[box-shadow] duration-150 bg-background resize-none"
                        placeholder="Describe what this automation does..."
                      />
                    </div>
                  </div>
                  
                  <h3 className={cn(headingClasses(3))}>Choose Trigger Service</h3>
                  <p className="text-sm text-muted-foreground">When this happens...</p>
                  <div className="grid grid-cols-2 gap-3">
                    {triggerServices.map((s) => (
                      <Button
                        key={s.slug}
                        variant={triggerService === s.slug ? "default" : "outline"}
                        onClick={() => {
                          setTriggerService(s.slug);
                          setTrigger(""); // Reset trigger when service changes
                        }}
                        className="w-full"
                      >
                        {s.name}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div
                className={cn(
                  "transition-all duration-300 ease-in-out",
                  step === 2
                    ? "translate-x-0 opacity-100"
                    : step > 2
                    ? "hidden"
                    : "hidden"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Trigger Action</h3>
                  <p className="text-sm text-muted-foreground">From {selectedTriggerService?.name}</p>
                  <div className="grid grid-cols-1 gap-3 mb-4">
                    {(selectedTriggerService?.actions || []).map((t) => (
                      <Button
                        key={t.key}
                        variant={trigger === t.key ? "default" : "outline"}
                        onClick={() => {
                          setTrigger(t.key);
                          setTriggerParams({});
                        }}
                        className={cn(
                          "w-full text-left justify-start h-auto py-4 px-4",
                          trigger === t.key && "text-white"
                        )}
                      >
                        <div className="w-full">
                          <div className="font-medium text-base">{t.name}</div>
                          <div className={cn(
                            "text-xs mt-1.5",
                            trigger === t.key ? "text-white/80" : "text-muted-foreground"
                          )}>
                            {t.description}
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                  {/* Custom fields for trigger - only show if trigger has parameters */}
                  {trigger && (() => {
                    const selectedAction = selectedTriggerService?.actions.find(a => a.key === trigger);
                    const paramsDef = getParamsDef('trigger', trigger, selectedAction?.params);
                    return paramsDef && Object.keys(paramsDef).length > 0 ? (
                      <div className="mt-2">
                        <h4 className="font-semibold text-sm mb-2">Trigger Parameters</h4>
                        {renderParamsFields(paramsDef, triggerParams, setTriggerParams)}
                      </div>
                    ) : null;
                  })()}
                </div>
              </div>

              {/* Step 3 */}
              <div
                className={cn(
                  "transition-all duration-300 ease-in-out",
                  step === 3
                    ? "translate-x-0 opacity-100"
                    : step > 3
                    ? "hidden"
                    : "hidden"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Reaction Service</h3>
                  <p className="text-sm text-muted-foreground">Then do this...</p>
                  <div className="grid grid-cols-2 gap-3">
                    {reactionServices.map((s) => (
                      <Button
                        key={s.slug}
                        variant={actionService === s.slug ? "default" : "outline"}
                        onClick={() => {
                          setActionService(s.slug);
                          setAction(""); // Reset action when service changes
                        }}
                        className="w-full"
                      >
                        {s.name}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Step 4 */}
              <div
                className={cn(
                  "transition-all duration-300 ease-in-out",
                  step === 4
                    ? "translate-x-0 opacity-100"
                    : step > 4
                    ? "hidden"
                    : "hidden"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Choose Reaction Action</h3>
                  <p className="text-sm text-muted-foreground">In {selectedActionService?.name}</p>
                  <div className="grid grid-cols-1 gap-3 mb-4">
                    {(selectedActionService?.reactions || []).map((a) => (
                      <Button
                        key={a.key}
                        variant={action === a.key ? "default" : "outline"}
                        onClick={() => {
                          setAction(a.key);
                          setActionParams({});
                        }}
                        className={cn(
                          "w-full text-left justify-start h-auto py-4 px-4",
                          action === a.key && "text-white"
                        )}
                      >
                        <div className="w-full">
                          <div className="font-medium text-base">{a.name}</div>
                          <div className={cn(
                            "text-xs mt-1.5",
                            action === a.key ? "text-white/80" : "text-muted-foreground"
                          )}>
                            {a.description}
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                  {/* Custom fields for action - only show if action has parameters */}
                  {action && (() => {
                    const selectedReaction = selectedActionService?.reactions.find(a => a.key === action);
                    const paramsDef = getParamsDef('action', action, selectedReaction?.params);
                    return paramsDef && Object.keys(paramsDef).length > 0 ? (
                      <div className="mt-2">
                        <h4 className="font-semibold text-sm mb-2">Action Parameters</h4>
                        {renderParamsFields(paramsDef, actionParams, setActionParams)}
                      </div>
                    ) : null;
                  })()}
                </div>
              </div>

              {/* Step 5 - Review */}
              <div
                className={cn(
                  "transition-all duration-300 ease-in-out",
                  step === 5
                    ? "translate-x-0 opacity-100"
                    : "hidden"
                )}
              >
                <div className="space-y-4">
                  <h3 className={cn(headingClasses(3))}>Review & Confirm</h3>
                  <Card className="bg-muted/50 border-2">
                    <CardContent className="pt-6">
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-medium text-foreground mb-1">Area Name</h4>
                          <p className="text-base">{areaName}</p>
                        </div>
                        
                        {areaDescription && (
                          <div>
                            <h4 className="font-medium text-foreground mb-1">Description</h4>
                            <p className="text-sm text-muted-foreground">{areaDescription}</p>
                          </div>
                        )}
                        
                        <div>
                          <h4 className="font-medium text-foreground mb-1">Your Automation</h4>
                          <p className="text-base">
                            <span className="font-semibold">When</span> &ldquo;{selectedTriggerService?.actions.find(a => a.key === trigger)?.name}&rdquo; happens in{" "}
                            <span className="font-semibold">{selectedTriggerService?.name}</span>
                          </p>
                          
                          {/* Show trigger parameters if they exist */}
                          {(() => {
                            const selectedAction = selectedTriggerService?.actions.find(a => a.key === trigger);
                            return trigger && selectedAction?.params && Object.keys(selectedAction.params).length > 0 ? (
                              <div className="mt-2">
                                <h5 className="text-sm font-medium text-foreground">Trigger Parameters:</h5>
                                <ul className="text-sm list-disc list-inside">
                                  {Object.entries(triggerParams).map(([paramKey, paramValue]) => (
                                    <li key={paramKey}>
                                      <span className="font-medium">{paramKey}:</span> {String(paramValue)}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ) : null;
                          })()}
                          
                          <p className="text-base mt-2">
                            <span className="font-semibold">Then</span> &ldquo;{selectedActionService?.reactions.find(r => r.key === action)?.name}&rdquo; in{" "}
                            <span className="font-semibold">{selectedActionService?.name}</span>
                          </p>
                          
                          {/* Show action parameters if they exist */}
                          {(() => {
                            const selectedReaction = selectedActionService?.reactions.find(a => a.key === action);
                            return action && selectedReaction?.params && Object.keys(selectedReaction.params).length > 0 ? (
                              <div className="mt-2">
                                <h5 className="text-sm font-medium text-foreground">Action Parameters:</h5>
                                <ul className="text-sm list-disc list-inside">
                                  {Object.entries(actionParams).map(([paramKey, paramValue]) => (
                                    <li key={paramKey}>
                                      <span className="font-medium">{paramKey}:</span> {String(paramValue)}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ) : null;
                          })()}
                        </div>
                      </div>
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
            onClick={() => router.push('/dashboard')}
            disabled={submitting}
          >
            Cancel
          </Button>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={step === 1 || submitting}
            >
              Back
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
