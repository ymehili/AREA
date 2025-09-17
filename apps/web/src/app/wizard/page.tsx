"use client";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useMemo, useState } from "react";
import { createArea } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

type Step = 1 | 2 | 3 | 4 | 5;

const services = ["Gmail", "Google Drive", "Slack", "GitHub"] as const;
const triggersByService: Record<string, string[]> = {
  Gmail: ["New Email", "New Email w/ Attachment"],
  "Google Drive": ["New File in Folder"],
  Slack: ["New Message in Channel"],
  GitHub: ["New Pull Request"],
};
const actionsByService: Record<string, string[]> = {
  Gmail: ["Send Email"],
  "Google Drive": ["Upload File", "Create Folder"],
  Slack: ["Send Message"],
  GitHub: ["Create Issue"],
};

export default function WizardPage() {
  const auth = useAuth();
  const [step, setStep] = useState<Step>(1);
  const [triggerService, setTriggerService] = useState<string>("");
  const [trigger, setTrigger] = useState<string>("");
  const [actionService, setActionService] = useState<string>("");
  const [action, setAction] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const next = () => setStep((s) => Math.min(s + 1, 5) as Step);
  const back = () => setStep((s) => Math.max(s - 1, 1) as Step);

  const canNext = useMemo(() => {
    if (step === 1) return !!triggerService;
    if (step === 2) return !!trigger;
    if (step === 3) return !!actionService;
    if (step === 4) return !!action;
    return true;
  }, [step, triggerService, trigger, actionService, action]);

  return (
    <AppShell>
      <Card>
        <CardHeader>
          <CardTitle>AREA Creation Wizard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-sm text-muted-foreground">Step {step} of 5</div>

          {step === 1 && (
            <div className="space-y-2">
              <div className="font-medium">Step 1: Choose Trigger Service</div>
              <Select onValueChange={setTriggerService} value={triggerService}>
                <SelectTrigger className="w-full md:w-80">
                  <SelectValue placeholder="Select a service" />
                </SelectTrigger>
                <SelectContent>
                  {services.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-2">
              <div className="font-medium">Step 2: Choose Trigger</div>
              <Select onValueChange={setTrigger} value={trigger}>
                <SelectTrigger className="w-full md:w-80">
                  <SelectValue placeholder="Select a trigger" />
                </SelectTrigger>
                <SelectContent>
                  {(triggersByService[triggerService] ?? []).map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-2">
              <div className="font-medium">Step 3: Choose REAction Service</div>
              <Select onValueChange={setActionService} value={actionService}>
                <SelectTrigger className="w-full md:w-80">
                  <SelectValue placeholder="Select a service" />
                </SelectTrigger>
                <SelectContent>
                  {services.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-2">
              <div className="font-medium">Step 4: Choose REAction</div>
              <Select onValueChange={setAction} value={action}>
                <SelectTrigger className="w-full md:w-80">
                  <SelectValue placeholder="Select an action" />
                </SelectTrigger>
                <SelectContent>
                  {(actionsByService[actionService] ?? []).map((a) => (
                    <SelectItem key={a} value={a}>
                      {a}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-2">
              <div className="font-medium">Step 5: Review & Confirm</div>
              <div className="text-sm text-muted-foreground">
                If new &quot;{trigger}&quot; in {triggerService}, then &quot;{action}&quot; in {actionService}.
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <Button variant="outline" onClick={back} disabled={step === 1}>
              Back
            </Button>
            {step < 5 ? (
              <Button onClick={next} disabled={!canNext}>
                Next
              </Button>
            ) : (
              <Button
                disabled={submitting}
                onClick={async () => {
                  if (!auth.token) return;
                  setSubmitting(true);
                  try {
                    await createArea(auth.token, {
                      name: `${triggerService} → ${actionService}`,
                      trigger_service: triggerService,
                      trigger_action: trigger,
                      reaction_service: actionService,
                      reaction_action: action,
                    });
                    window.location.href = "/dashboard";
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                {submitting ? "Saving..." : "Finish"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
