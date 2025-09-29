"use client";

import { cn, headingClasses } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/use-auth";
import { UnauthorizedError } from "@/lib/api";
import { toast } from "sonner";

type AutomationEvent = {
  id: string;
  timestamp: string;
  areaName: string;
  trigger: string;
  action: string;
  status: "success" | "failed" | "skipped";
  duration?: number; // in milliseconds
};

export default function AutomationHistoryPage() {
  const auth = useRequireAuth();
  const [events, setEvents] = useState<AutomationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadEvents = async () => {
      if (!auth.token) {
        return;
      }
      setLoading(true);
      try {
        // Mock data for now - in a real implementation, this would come from the API
        const mockEvents: AutomationEvent[] = [
          {
            id: "1",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            areaName: "Email to Drive Backup",
            trigger: "Gmail: New Email",
            action: "Google Drive: Upload Attachment",
            status: "success",
            duration: 1250,
          },
          {
            id: "2",
            timestamp: new Date(Date.now() - 3605000).toISOString(),
            areaName: "Slack Notification",
            trigger: "GitHub: New Pull Request",
            action: "Slack: Send Message",
            status: "success",
            duration: 850,
          },
          {
            id: "3",
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            areaName: "File Sync",
            trigger: "Dropbox: New File",
            action: "Google Drive: Upload File",
            status: "failed",
            duration: 200,
          },
          {
            id: "4",
            timestamp: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
            areaName: "Daily Report",
            trigger: "Scheduler: Daily",
            action: "Email: Send Report",
            status: "success",
            duration: 3200,
          },
          {
            id: "5",
            timestamp: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
            areaName: "Issue Tracker",
            trigger: "Jira: New Issue",
            action: "Email: Send Notification",
            status: "success",
            duration: 980,
          },
        ];
        setEvents(mockEvents);
        setError(null);
      } catch (err) {
        if (err instanceof UnauthorizedError) {
          toast.error("Session expired. Please sign in again.");
          auth.logout();
          return;
        }
        const message = err instanceof Error ? err.message : "Unable to load automation history.";
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };

    void loadEvents();
  }, [auth]);

  const getStatusColor = (status: AutomationEvent["status"]) => {
    switch (status) {
      case "success": return "!bg-success !border-success !text-white";
      case "failed": return "!bg-destructive !border-destructive !text-white";
      case "skipped": return "!bg-warning !border-warning !text-white";
      default: return "!bg-muted !border-muted !text-white";
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col space-y-4">
        <h1 className={cn(headingClasses(2), "text-foreground")}>Automation History</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col space-y-4">
        <h1 className={cn(headingClasses(2), "text-foreground")}>Automation History</h1>
        <div className="flex justify-center items-center h-64">
          <div className="text-destructive text-center">
            <p className="font-semibold">Error loading automation history</p>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className={cn(headingClasses(2), "text-foreground")}>Automation History</h1>
      <Card>
        <CardHeader className="p-4">
          <CardTitle>Automation Execution Logs</CardTitle>
          <CardDescription>History of your AREA executions</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {events.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">
              No automation history found.
            </div>
          ) : (
            <div className="divide-y">
              {events.map((event) => (
                <div key={event.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">{event.areaName}</p>
                      <div className="flex space-x-4 mt-1 text-sm">
                        <div>
                          <span className="text-muted-foreground">Trigger:</span> {event.trigger}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Action:</span> {event.action}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <Badge className={`${getStatusColor(event.status)}`}>
                        {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
                      </Badge>
                      <p className="text-xs text-muted-foreground">
                        {new Date(event.timestamp).toLocaleString()}
                      </p>
                      {event.duration && (
                        <p className="text-xs text-muted-foreground">
                          Duration: {event.duration}ms
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}