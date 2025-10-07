"use client";

import { cn, headingClasses } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/use-auth";
import { UnauthorizedError } from "@/lib/api";
import { toast } from "sonner";

interface UserActivityLog {
  id: string;
  timestamp: string;
  action_type: string;
  service_name: string | null;
  details: string | null;
  status: "success" | "failed" | "pending";
  created_at: string;
}

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
        // API call to fetch user's activity logs
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/user-activities`, {
          headers: {
            Authorization: `Bearer ${auth.token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401) {
            throw new UnauthorizedError();
          }
          throw new Error(`Failed to fetch activity logs: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        
        // Transform backend data to match frontend Activity type
        const transformedActivities: Activity[] = data.map((item: UserActivityLog) => ({
          id: item.id,
          timestamp: item.timestamp,
          action: item.action_type,
          service: item.service_name || "User Account", // Use service_name from backend or default
          status: item.status, // Use the explicit status from backend
          details: item.details || "Activity details not available",
        }));
        
        setActivities(transformedActivities);
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
      case "success": 
        return "!bg-success !border-success !text-white";
      case "failed": 
        return "!bg-destructive !border-destructive !text-white";
      case "processing": 
        return "!bg-warning !border-warning !text-white";
      default: 
        return "!bg-muted !border-muted !text-white";
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
                      <Badge className={`${getStatusColor(activity.status)}`}>
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