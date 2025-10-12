"use client";

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createAreaWithSteps } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { cn, headingClasses } from '@/lib/utils';

// Service and action options matching mobile wizard
const SERVICES = ["Gmail", "Google Drive", "Slack", "GitHub"] as const;
const TRIGGERS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ["New Email", "New Email w/ Attachment"],
  "Google Drive": ["New File in Folder"],
  Slack: ["New Message in Channel"],
  GitHub: ["New Pull Request"],
};
const ACTIONS_BY_SERVICE: Record<string, string[]> = {
  Gmail: ["Send Email"],
  "Google Drive": ["Upload File", "Create Folder"],
  Slack: ["Send Message"],
  GitHub: ["Create Issue"],
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
      toast.error("Failed to create AREA. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }, [auth, triggerService, trigger, actionService, action, router]);

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
                  <p className="text-sm text-muted-foreground">When this happens...</p>
                  <div className="grid grid-cols-2 gap-3">
                    {SERVICES.map((s) => (
                      <Button
                        key={s}
                        variant={triggerService === s ? "default" : "outline"}
                        onClick={() => setTriggerService(s)}
                        className="w-full"
                      >
                        {s}
                      </Button>
                    ))}
                  </div>
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
                  <p className="text-sm text-muted-foreground">From {triggerService}</p>
                  <div className="grid grid-cols-1 gap-3">
                    {(TRIGGERS_BY_SERVICE[triggerService] || []).map((t) => (
                      <Button
                        key={t}
                        variant={trigger === t ? "default" : "outline"}
                        onClick={() => setTrigger(t)}
                        className="w-full"
                      >
                        {t}
                      </Button>
                    ))}
                  </div>
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
                  <p className="text-sm text-muted-foreground">Then do this...</p>
                  <div className="grid grid-cols-2 gap-3">
                    {SERVICES.map((s) => (
                      <Button
                        key={s}
                        variant={actionService === s ? "default" : "outline"}
                        onClick={() => setActionService(s)}
                        className="w-full"
                      >
                        {s}
                      </Button>
                    ))}
                  </div>
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
                  <p className="text-sm text-muted-foreground">In {actionService}</p>
                  <div className="grid grid-cols-1 gap-3">
                    {(ACTIONS_BY_SERVICE[actionService] || []).map((a) => (
                      <Button
                        key={a}
                        variant={action === a ? "default" : "outline"}
                        onClick={() => setAction(a)}
                        className="w-full"
                      >
                        {a}
                      </Button>
                    ))}
                  </div>
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
                        <span className="font-semibold">When</span> &ldquo;{trigger}&rdquo; happens in{" "}
                        <span className="font-semibold">{triggerService}</span>
                      </p>
                      <p className="text-base mt-2">
                        <span className="font-semibold">Then</span> &ldquo;{action}&rdquo; in{" "}
                        <span className="font-semibold">{actionService}</span>
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
