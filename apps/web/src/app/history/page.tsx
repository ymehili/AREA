"use client";
import AppShell from "@/components/app-shell";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCallback, useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/use-auth";
import {
  UnauthorizedError,
  getExecutionLogsForUser,
  ExecutionLog,
} from "@/lib/api";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  RotateCcw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  PlayCircle,
} from "lucide-react";
import { cn, headingClasses } from "@/lib/utils";

export default function HistoryPage() {
  const auth = useRequireAuth();
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<ExecutionLog | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const loadExecutionLogs = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const logs = await getExecutionLogsForUser(auth.token);
      // Sort logs by timestamp, newest first (chronological order as per requirements)
      const sortedLogs = logs.sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
      setExecutionLogs(sortedLogs);
      setError(null);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message =
        err instanceof Error ? err.message : "Unable to load execution logs.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    void loadExecutionLogs();
  }, [loadExecutionLogs]);

  const getStatusConfig = (status: string) => {
    const lowerStatus = status.toLowerCase();
    switch (lowerStatus) {
      case "success":
        return {
          color: "bg-success border-success text-white",
          icon: CheckCircle,
          label: "Success",
          bg: "bg-green-500",
        };
      case "failed":
        return {
          color: "bg-destructive border-destructive text-white",
          icon: XCircle,
          label: "Failed",
          bg: "bg-red-500",
        };
      case "running":
        return {
          color: "bg-warning border-warning text-foreground",
          icon: PlayCircle,
          label: "Running",
          bg: "bg-yellow-500",
        };
      case "pending":
        return {
          color: "bg-muted border-muted-foreground text-foreground",
          icon: Clock,
          label: "Pending",
          bg: "bg-gray-500",
        };
      default:
        return {
          color: "bg-secondary border-border text-foreground",
          icon: AlertCircle,
          label: status.charAt(0).toUpperCase() + status.slice(1),
          bg: "bg-gray-300",
        };
    }
  };

  const handleLogClick = (log: ExecutionLog) => {
    setSelectedLog(log);
    setIsDialogOpen(true);
  };

  if (loading) {
    return (
      <AppShell>
        <div className="space-y-4">
          <div>
            <h1 className={cn(headingClasses(2), "text-foreground")}>
              Execution History
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Loading your automation execution logs...
            </p>
          </div>

          <Card>
            <CardContent className="flex justify-center items-center h-64">
              <div className="flex flex-col items-center space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                <p className="text-muted-foreground">
                  Loading execution logs...
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="space-y-4">
          <div>
            <h1 className={cn(headingClasses(2), "text-foreground")}>
              Execution History
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Error loading automation execution logs
            </p>
          </div>

          <Card>
            <CardContent className="flex flex-col items-center justify-center h-64">
              <div className="text-center space-y-4 max-w-md">
                <XCircle className="mx-auto h-12 w-12 text-destructive" />
                <div>
                  <h3 className="text-lg font-medium text-foreground">
                    Error loading execution history
                  </h3>
                  <p className="text-sm text-muted-foreground mt-2">{error}</p>
                </div>
                <Button
                  onClick={() => void loadExecutionLogs()}
                  variant="default"
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
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
      <div className="space-y-6">
        <div>
          <h1 className={cn(headingClasses(2), "text-foreground")}>
            Execution History
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Detailed logs of your AREA executions
          </p>
        </div>

        {executionLogs.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="flex justify-center mb-4">
                <div className="bg-muted rounded-full p-3">
                  <Clock className="h-8 w-8 text-muted-foreground" />
                </div>
              </div>
              <h3 className="text-lg font-medium text-foreground mb-1">
                No execution logs yet
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Your AREA executions will appear here once they run
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            <Card>
              <CardHeader className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      Automation Execution Logs
                    </CardTitle>
                    <CardDescription className="text-sm">
                      History of your AREA executions
                    </CardDescription>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {executionLogs.length}{" "}
                    {executionLogs.length === 1 ? "log" : "logs"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y">
                  {executionLogs.map((log) => {
                    const statusConfig = getStatusConfig(log.status);
                    const StatusIcon = statusConfig.icon;

                    return (
                      <div
                        key={log.id}
                        className="p-4 hover:bg-accent cursor-pointer transition-colors duration-150"
                        onClick={() => handleLogClick(log)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <StatusIcon className="h-4 w-4" />
                              <p className="font-medium text-foreground truncate">
                                Execution #{log.id.substring(0, 8)}
                              </p>
                            </div>

                            <div className="flex items-center gap-4 text-sm">
                              <div className="flex items-center gap-1 text-muted-foreground">
                                <span className="text-xs">AREA:</span>
                                <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                                  {log.area_id.substring(0, 6)}...
                                </span>
                              </div>

                              <div className="flex items-center gap-1 text-muted-foreground">
                                <span className="text-xs">Status:</span>
                                <span className="text-xs font-medium">
                                  {log.status}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-col items-end space-y-2">
                            <Badge
                              className={`${statusConfig.color} capitalize`}
                            >
                              {statusConfig.label}
                            </Badge>

                            <div className="flex items-center text-xs text-muted-foreground">
                              <Clock className="h-3 w-3 mr-1" />
                              <span>
                                {new Date(log.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Detailed View Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <PlayCircle className="h-5 w-5" />
                Execution Details
              </DialogTitle>
              <DialogDescription>
                Detailed information about this execution
              </DialogDescription>
            </DialogHeader>

            {selectedLog && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                      Execution ID
                    </h3>
                    <p className="text-sm font-mono bg-muted rounded px-2 py-1 break-all">
                      {selectedLog.id}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                      Area ID
                    </h3>
                    <p className="text-sm font-mono bg-muted rounded px-2 py-1 break-all">
                      {selectedLog.area_id}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                      Status
                    </h3>
                    <div className="flex items-center gap-2">
                      <Badge
                        className={`${getStatusConfig(selectedLog.status).color} capitalize`}
                      >
                        {getStatusConfig(selectedLog.status).label}
                      </Badge>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                      Timestamp
                    </h3>
                    <p className="text-sm">
                      {new Date(selectedLog.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>

                {selectedLog.step_details && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-primary"></div>
                      Step Details
                    </h3>
                    <div className="bg-muted rounded-md p-4 overflow-x-auto text-sm">
                      <pre className="whitespace-pre-wrap break-words">
                        {JSON.stringify(selectedLog.step_details, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {selectedLog.output && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-green-500"></div>
                      Output
                    </h3>
                    <div className="bg-muted rounded-md p-4 whitespace-pre-wrap break-words text-sm">
                      {selectedLog.output}
                    </div>
                  </div>
                )}

                {selectedLog.error_message && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-red-500"></div>
                      Error Message
                    </h3>
                    <div className="bg-destructive/10 border border-destructive/30 rounded-md p-4 whitespace-pre-wrap break-words text-sm text-destructive">
                      {selectedLog.error_message}
                    </div>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
