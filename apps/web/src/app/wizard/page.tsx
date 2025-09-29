"use client";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useMemo, useState } from "react";
import { createArea, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { cn, headingClasses } from "@/lib/utils";
import { toast } from "sonner";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter 
} from "@/components/ui/dialog";

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
  const [showDuplicateNameDialog, setShowDuplicateNameDialog] = useState(false);
  const [duplicateAreaData, setDuplicateAreaData] = useState<{
    name: string;
    uniqueName: string;
    payload: any;
  } | null>(null);

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
      <Card className="p-6">
        <CardHeader className="p-0 mb-4">
          <CardTitle className={cn(headingClasses(1), "text-foreground")}>AREA Creation Wizard</CardTitle>
        </CardHeader>
        <CardContent className="p-0 space-y-6">
          <div className="text-sm text-muted-foreground mb-4">Step {step} of 5</div>

          {/* Step progress indicator */}
          <div className="flex items-center justify-between mb-6">
            {([1, 2, 3, 4, 5] as Step[]).map((s) => (
              <div key={s} className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  s === step 
                    ? 'bg-primary text-primary-foreground' 
                    : s < step 
                      ? 'bg-success text-success-foreground' 
                      : 'bg-muted text-muted-foreground'
                }`}>
                  {s}
                </div>
                <div className="text-xs mt-2 text-center">
                  {s === 1 && 'Trigger Service'}
                  {s === 2 && 'Trigger'}
                  {s === 3 && 'Action Service'}
                  {s === 4 && 'Action'}
                  {s === 5 && 'Review'}
                </div>
              </div>
            ))}
          </div>

          {step === 1 && (
            <div className="space-y-4">
              <div className="text-xl font-medium text-foreground">Step 1: Choose Trigger Service</div>
              <div className="text-sm text-muted-foreground mb-4">Select the service that will trigger the action</div>
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
            <div className="space-y-4">
              <div className="text-xl font-medium text-foreground">Step 2: Choose Trigger</div>
              <div className="text-sm text-muted-foreground mb-4">Select the specific trigger event</div>
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
            <div className="space-y-4">
              <div className="text-xl font-medium text-foreground">Step 3: Choose REAction Service</div>
              <div className="text-sm text-muted-foreground mb-4">Select the service that will react to the trigger</div>
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
            <div className="space-y-4">
              <div className="text-xl font-medium text-foreground">Step 4: Choose REAction</div>
              <div className="text-sm text-muted-foreground mb-4">Select the specific reaction action</div>
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
            <div className="space-y-4">
              <div className="text-xl font-medium text-foreground">Step 5: Review & Confirm</div>
              <div className="text-sm text-muted-foreground mb-4">Confirm your AREA configuration</div>
              <div className="bg-muted p-4 rounded-md">
                <div className="text-sm text-muted-foreground">
                  If new &quot;{trigger}&quot; in {triggerService}, then &quot;{action}&quot; in {actionService}.
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-6 border-t">
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
                  } catch (error) {
                    if (error instanceof ApiError && error.status === 409) {
                      // Handle duplicate area name error by showing a dialog
                      const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                      const uniqueName = `${triggerService} → ${actionService} (${timestamp})`;
                      
                      setDuplicateAreaData({
                        name: `${triggerService} → ${actionService}`,
                        uniqueName,
                        payload: {
                          name: uniqueName,
                          trigger_service: triggerService,
                          trigger_action: trigger,
                          reaction_service: actionService,
                          reaction_action: action,
                        }
                      });
                      setShowDuplicateNameDialog(true);
                    } else {
                      // For other errors, display a toast notification
                      toast.error(error instanceof Error ? error.message : "An error occurred while creating the area");
                    }
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
      
      {/* Dialog for duplicate area name */}
      <Dialog open={showDuplicateNameDialog} onOpenChange={setShowDuplicateNameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Duplicate Area Name</DialogTitle>
            <DialogDescription>
              An area with the name "{duplicateAreaData?.name}" already exists.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <p className="text-sm text-muted-foreground">
              Would you like to create it with a unique name: <strong>"{duplicateAreaData?.uniqueName}"</strong>?
            </p>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowDuplicateNameDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={async () => {
                if (!auth.token || !duplicateAreaData) return;
                
                try {
                  await createArea(auth.token, duplicateAreaData.payload);
                  window.location.href = "/dashboard";
                } catch (error) {
                  toast.error(error instanceof Error ? error.message : "An error occurred while creating the area");
                } finally {
                  setShowDuplicateNameDialog(false);
                }
              }}
            >
              Create with New Name
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
