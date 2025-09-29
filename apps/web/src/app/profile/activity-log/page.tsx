"use client";

import { cn, headingClasses } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/use-auth";
import { UnauthorizedError, requestJson } from "@/lib/api";
import { toast } from "sonner";

type Activity = {
  id: string;
  timestamp: string;
  action: string;
  service: string;
  status: "success" | "failed" | "processing";
  details: string;
};

export default function ActivityLogPage() {
  const auth = useRequireAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadActivities = async () => {
      if (!auth.token) {
        return;
      }
      setLoading(true);
      try {
        // Mock data for now - in a real implementation, this would come from the API
        const mockActivities: Activity[] = [
          {
            id: "1",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            action: "AREA executed",
            service: "Gmail → Google Drive",
            status: "success",
            details: "New email processed, attachment uploaded",
          },
          {
            id: "2",
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            action: "Connection established",
            service: "Slack",
            status: "success",
            details: "Successfully connected to Slack workspace",
          },
          {
            id: "3",
            timestamp: new Date(Date.now() - 10800000).toISOString(),
            action: "AREA failed",
            service: "GitHub → Email",
            status: "failed",
            details: "Failed to send email due to authentication error",
          },
          {
            id: "4",
            timestamp: new Date(Date.now() - 14400000).toISOString(),
            action: "AREA created",
            service: "Gmail → Dropbox",
            status: "success",
            details: "Created new automation between services",
          },
          {
            id: "5",
            timestamp: new Date(Date.now() - 21600000).toISOString(),
            action: "Profile updated",
            service: "User Account",
            status: "success",
            details: "Updated email address and profile details",
          },
        ];
        setActivities(mockActivities);
        setError(null);
      } catch (err) {
        if (err instanceof UnauthorizedError) {
          toast.error("Session expired. Please sign in again.");
          auth.logout();
          return;
        }
        const message = err instanceof Error ? err.message : "Unable to load activity log.";
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };

    void loadActivities();
  }, [auth]);

  const getStatusColor = (status: Activity["status"]) => {
    switch (status) {
      case "success": return "bg-success";
      case "failed": return "bg-destructive";
      case "processing": return "bg-warning";
      default: return "bg-muted";
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col space-y-4">
        <h1 className={cn(headingClasses(2), "text-foreground")}>Activity Log</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col space-y-4">
        <h1 className={cn(headingClasses(2), "text-foreground")}>Activity Log</h1>
        <div className="flex justify-center items-center h-64">
          <div className="text-destructive text-center">
            <p className="font-semibold">Error loading activity log</p>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className={cn(headingClasses(2), "text-foreground")}>Activity Log</h1>
      <Card>
        <CardHeader className="p-4">
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Your account activity history</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {activities.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">
              No recent activity found.
            </div>
          ) : (
            <div className="divide-y">
              {activities.map((activity) => (
                <div key={activity.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">{activity.action}</p>
                      <p className="text-sm text-muted-foreground truncate">{activity.service}</p>
                      <p className="text-xs text-muted-foreground mt-1">{activity.details}</p>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <Badge variant="secondary" className={`${getStatusColor(activity.status)}`}>
                        {activity.status.charAt(0).toUpperCase() + activity.status.slice(1)}
                      </Badge>
                      <p className="text-xs text-muted-foreground">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
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