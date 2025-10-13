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

interface WeatherForecast {
  main?: {
    temp?: number;
    feels_like?: number;
    humidity?: number;
  };
  weather?: Array<{
    main?: string;
    description?: string;
  }>;
  wind?: {
    speed?: number;
  };
  dt_txt?: string;
  pop?: number;
}

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
          color: "bg-green-500 border-green-600 text-white",
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
          color: "bg-blue-500 border-blue-600 text-white",
          icon: PlayCircle,
          label: "Running",
          bg: "bg-blue-500",
        };
      case "pending":
        return {
          color: "bg-yellow-500 border-yellow-600 text-white",
          icon: Clock,
          label: "Pending",
          bg: "bg-yellow-500",
        };
      default:
        return {
          color: "bg-gray-500 border-gray-600 text-white",
          icon: AlertCircle,
          label: status.charAt(0).toUpperCase() + status.slice(1),
          bg: "bg-gray-500",
        };
    }
  };

  const handleLogClick = (log: ExecutionLog) => {
    setSelectedLog(log);
    setIsDialogOpen(true);
  };

  // Extract weather data from step_details if available
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const getWeatherData = (log: ExecutionLog | null) => {
    if (!log || !log.step_details) return null;
    
    try {
      const stepDetails = typeof log.step_details === 'string' 
        ? JSON.parse(log.step_details) 
        : log.step_details;
      
      const executionLog = stepDetails.execution_log || [];
      const weatherStep = executionLog.find((step: { service?: string; status?: string }) => 
        step.service === 'weather' && step.status === 'success'
      );
      
      if (!weatherStep) return null;
      
      // Extract weather data from the event context (stored in backend logs)
      // This will be populated once we update the backend to include it
      return weatherStep.weather_data || null;
    } catch {
      return null;
    }
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
                  <Badge variant="secondary" className="text-xs text-white bg-primary">
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
          <DialogContent className="!max-w-[95vw] !w-[95vw] max-h-[95vh] h-[95vh] overflow-hidden flex flex-col p-0">
            <DialogHeader className="flex-shrink-0 px-6 pt-6 pb-4 border-b">
              <DialogTitle className="flex items-center gap-2 text-xl">
                <PlayCircle className="h-6 w-6" />
                Execution Details
              </DialogTitle>
              <DialogDescription>
                Detailed information about this execution
              </DialogDescription>
            </DialogHeader>

            {selectedLog && (
              <div className="flex flex-row gap-6 overflow-y-auto flex-1 px-6 pb-6 pt-4 min-h-0">
                {/* Left Column - Metadata */}
                <div className="w-96 flex-shrink-0 space-y-4 self-start">
                  <Card className="border-2">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Execution Info</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-1.5">
                        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Execution ID
                        </h3>
                        <p className="text-xs font-mono bg-muted rounded px-2 py-1.5 break-all">
                          {selectedLog.id}
                        </p>
                      </div>

                      <div className="space-y-1.5">
                        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Area ID
                        </h3>
                        <p className="text-xs font-mono bg-muted rounded px-2 py-1.5 break-all">
                          {selectedLog.area_id}
                        </p>
                      </div>

                      <div className="space-y-1.5">
                        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Status
                        </h3>
                        <Badge
                          className={`${getStatusConfig(selectedLog.status).color} capitalize w-fit`}
                        >
                          {getStatusConfig(selectedLog.status).label}
                        </Badge>
                      </div>

                      <div className="space-y-1.5">
                        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Timestamp
                        </h3>
                        <p className="text-sm">
                          {new Date(selectedLog.timestamp).toLocaleString()}
                        </p>
                      </div>

                      {selectedLog.output && (
                        <div className="space-y-1.5 pt-3 border-t">
                          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Summary
                          </h3>
                          <div className="bg-muted rounded-md px-3 py-2 text-xs">
                            {selectedLog.output}
                          </div>
                        </div>
                      )}

                      {selectedLog.error_message && (
                        <div className="space-y-1.5 pt-3 border-t">
                          <h3 className="text-xs font-medium text-destructive uppercase tracking-wide">
                            Error
                          </h3>
                          <div className="bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2 text-xs text-destructive">
                            {selectedLog.error_message}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Right Column - Detailed Data */}
                <div className="flex-1 space-y-4 min-w-0">
                  {/* Weather Data Display */}
                  {selectedLog.step_details && (() => {
                    try {
                      const stepDetails = typeof selectedLog.step_details === 'string' 
                        ? JSON.parse(selectedLog.step_details) 
                        : selectedLog.step_details;
                      
                      const executionLog = stepDetails.execution_log || [];
                      const weatherStep = executionLog.find((step: { service?: string; status?: string; weather_data?: unknown; params_used?: { location?: string; lat?: number; lon?: number }; action?: string }) => 
                        step.service === 'weather' && step.status === 'success'
                      );
                      
                      if (!weatherStep) return null;
                      
                      const location = weatherStep.params_used?.location || 
                        (weatherStep.params_used?.lat && weatherStep.params_used?.lon 
                          ? `${weatherStep.params_used.lat}, ${weatherStep.params_used.lon}` 
                          : 'Unknown');
                      
                      const getWeatherEmoji = (condition: string) => {
                        const cond = condition?.toLowerCase() || '';
                        if (cond.includes('clear')) return '☀️';
                        if (cond.includes('cloud')) return '☁️';
                        if (cond.includes('rain')) return '🌧️';
                        if (cond.includes('snow')) return '❄️';
                        if (cond.includes('storm') || cond.includes('thunder')) return '⛈️';
                        if (cond.includes('mist') || cond.includes('fog')) return '🌫️';
                        return '🌤️';
                      };
                      
                      // Check if it's current weather or forecast
                      const isCurrentWeather = weatherStep.action === 'get_current_weather';
                      const isForecast = weatherStep.action === 'get_forecast';
                      
                      // Current Weather Display
                      if (isCurrentWeather && weatherStep.weather_data) {
                        const weatherData = weatherStep.weather_data;
                        const unitSymbol = weatherData.units === 'imperial' ? '°F' : weatherData.units === 'standard' ? 'K' : '°C';
                        const speedUnit = weatherData.units === 'imperial' ? 'mph' : 'm/s';
                        
                        return (
                          <Card className="border-2 border-blue-200 dark:border-blue-800">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                🌤️ Current Weather Information
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Header with main weather info */}
                              <div className="flex items-center justify-between bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-950 dark:to-cyan-950 rounded-lg p-4">
                                <div className="flex items-center gap-4">
                                  <span className="text-5xl">{getWeatherEmoji(weatherData.condition)}</span>
                                  <div>
                                    <p className="font-bold text-3xl">
                                      {weatherData.temperature}{unitSymbol}
                                    </p>
                                    <p className="text-sm text-muted-foreground capitalize font-medium">
                                      {weatherData.description}
                                    </p>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className="text-sm font-semibold">📍 {location}</p>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Current Weather
                                  </p>
                                </div>
                              </div>
                              
                              {/* Weather Details Grid */}
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Feels Like</p>
                                  <p className="text-lg font-semibold">
                                    {weatherData.feels_like}{unitSymbol}
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Humidity</p>
                                  <p className="text-lg font-semibold">
                                    💧 {weatherData.humidity}%
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Wind Speed</p>
                                  <p className="text-lg font-semibold">
                                    💨 {weatherData.wind_speed} {speedUnit}
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Pressure</p>
                                  <p className="text-lg font-semibold">
                                    🌡️ {weatherData.pressure} hPa
                                  </p>
                                </div>
                              </div>
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Data Retrieved Successfully
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenWeatherMap API
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      // Weather Forecast Display
                      if (isForecast && weatherStep.weather_data) {
                        const weatherData = weatherStep.weather_data;
                        
                        // Check if this is forecast type data
                        if (weatherData.type !== 'forecast' || !weatherData.forecast_data) return null;
                        
                        const forecastData = weatherData.forecast_data;
                        const forecasts = forecastData.list || [];
                        const city = forecastData.city || {};
                        const units = weatherData.units || 'metric';
                        const unitSymbol = units === 'imperial' ? '°F' : units === 'standard' ? 'K' : '°C';
                        const speedUnit = units === 'imperial' ? 'mph' : 'm/s';
                        
                        return (
                          <Card className="border-2 border-purple-200 dark:border-purple-800">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                📅 Weather Forecast
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Header */}
                              <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 rounded-lg p-4">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <p className="text-sm font-semibold">📍 {city.name || location}</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      5-Day Forecast ({forecasts.length} entries)
                                    </p>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-xs text-muted-foreground">Country</p>
                                    <p className="text-sm font-semibold">{city.country || 'N/A'}</p>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Forecast Entries */}
                              <div className="space-y-3 max-h-96 overflow-y-auto">
                                {forecasts.slice(0, 10).map((forecast: WeatherForecast, index: number) => {
                                  const temp = forecast.main?.temp;
                                  const feelsLike = forecast.main?.feels_like;
                                  const condition = forecast.weather?.[0]?.main || 'Unknown';
                                  const description = forecast.weather?.[0]?.description || '';
                                  const humidity = forecast.main?.humidity;
                                  const windSpeed = forecast.wind?.speed;
                                  const dateTime = forecast.dt_txt;
                                  const pop = forecast.pop ? Math.round(forecast.pop * 100) : 0; // Probability of precipitation
                                  
                                  return (
                                    <div key={index} className="bg-muted/30 border rounded-lg p-3 hover:bg-muted/50 transition-colors">
                                      <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-center gap-3 flex-1">
                                          <span className="text-3xl">{getWeatherEmoji(condition)}</span>
                                          <div className="flex-1">
                                            <div className="flex items-baseline gap-2">
                                              <p className="font-bold text-xl">
                                                {temp}{unitSymbol}
                                              </p>
                                              <p className="text-xs text-muted-foreground">
                                                Feels {feelsLike}{unitSymbol}
                                              </p>
                                            </div>
                                            <p className="text-xs text-muted-foreground capitalize mt-0.5">
                                              {description}
                                            </p>
                                            <p className="text-xs font-medium text-foreground mt-1">
                                              🕐 {dateTime}
                                            </p>
                                          </div>
                                        </div>
                                        
                                        <div className="flex flex-col gap-1.5 text-right">
                                          <div className="text-xs">
                                            <span className="text-muted-foreground">💧 </span>
                                            <span className="font-medium">{humidity}%</span>
                                          </div>
                                          <div className="text-xs">
                                            <span className="text-muted-foreground">💨 </span>
                                            <span className="font-medium">{windSpeed} {speedUnit}</span>
                                          </div>
                                          {pop > 0 && (
                                            <div className="text-xs">
                                              <span className="text-muted-foreground">🌧️ </span>
                                              <span className="font-medium">{pop}%</span>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                              
                              {forecasts.length > 10 && (
                                <p className="text-xs text-center text-muted-foreground pt-2 border-t">
                                  Showing first 10 of {forecasts.length} forecast entries
                                </p>
                              )}
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Forecast Retrieved Successfully
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenWeatherMap API
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      return null;
                    } catch {
                      return null;
                    }
                  })()}

                  {/* OpenAI Data Display */}
                  {selectedLog.step_details && (() => {
                    try {
                      const stepDetails = typeof selectedLog.step_details === 'string' 
                        ? JSON.parse(selectedLog.step_details) 
                        : selectedLog.step_details;
                      
                      const executionLog = stepDetails.execution_log || [];
                      const openaiStep = executionLog.find((step: { service?: string; status?: string; openai_data?: unknown; action?: string }) => 
                        step.service === 'openai' && step.status === 'success' && step.openai_data
                      );
                      
                      if (!openaiStep || !openaiStep.openai_data) return null;
                      
                      const openaiData = openaiStep.openai_data;
                      const action = openaiStep.action;
                      
                      // Get action emoji and title
                      const getActionEmoji = (action: string) => {
                        if (action === 'complete_text') return '✍️';
                        if (action === 'chat_completion') return '💬';
                        if (action === 'image_generation') return '🖼️';
                        if (action === 'content_moderation') return '🛡️';
                        return '🤖';
                      };
                      
                      const getActionTitle = (action: string) => {
                        if (action === 'complete_text') return 'Text Completion';
                        if (action === 'chat_completion') return 'Chat Completion';
                        if (action === 'image_generation') return 'Image Generation';
                        if (action === 'content_moderation') return 'Content Moderation';
                        return 'OpenAI Response';
                      };
                      
                      // Text Completion Display
                      if (action === 'complete_text' && openaiData.response) {
                        return (
                          <Card className="border-2 border-green-200 dark:border-green-800">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                {getActionEmoji(action)} OpenAI {getActionTitle(action)}
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Response Display */}
                              <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950 dark:to-emerald-950 rounded-lg p-4 border border-green-200 dark:border-green-800">
                                <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">Generated Response</p>
                                <div className="text-sm leading-relaxed whitespace-pre-wrap bg-white dark:bg-gray-900 rounded p-3 border">
                                  {openaiData.response}
                                </div>
                              </div>
                              
                              {/* Model & Token Info Grid */}
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Model</p>
                                  <p className="text-sm font-semibold font-mono">
                                    🤖 {openaiData.model || 'N/A'}
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Finish Reason</p>
                                  <p className="text-sm font-semibold capitalize">
                                    ✓ {openaiData.finish_reason || 'stop'}
                                  </p>
                                </div>
                                {openaiData.usage && (
                                  <>
                                    <div className="bg-muted/50 border rounded-lg p-3">
                                      <p className="text-xs text-muted-foreground mb-1.5 font-medium">Tokens Used</p>
                                      <p className="text-sm font-semibold">
                                        📊 {openaiData.usage.total_tokens || 0}
                                      </p>
                                    </div>
                                    <div className="bg-muted/50 border rounded-lg p-3">
                                      <p className="text-xs text-muted-foreground mb-1.5 font-medium">Completion Tokens</p>
                                      <p className="text-sm font-semibold">
                                        ✨ {openaiData.usage.completion_tokens || 0}
                                      </p>
                                    </div>
                                  </>
                                )}
                              </div>
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Generated Successfully
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenAI API
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      // Chat Completion Display
                      if (action === 'chat_completion' && openaiData.response) {
                        return (
                          <Card className="border-2 border-blue-200 dark:border-blue-800">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                {getActionEmoji(action)} OpenAI {getActionTitle(action)}
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Response Display */}
                              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-950 dark:to-cyan-950 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                                <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">AI Response</p>
                                <div className="text-sm leading-relaxed whitespace-pre-wrap bg-white dark:bg-gray-900 rounded p-3 border">
                                  {openaiData.response}
                                </div>
                              </div>
                              
                              {/* Model & Token Info Grid */}
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Model</p>
                                  <p className="text-sm font-semibold font-mono">
                                    🤖 {openaiData.model || 'N/A'}
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Finish Reason</p>
                                  <p className="text-sm font-semibold capitalize">
                                    ✓ {openaiData.finish_reason || 'stop'}
                                  </p>
                                </div>
                                {openaiData.usage && (
                                  <>
                                    <div className="bg-muted/50 border rounded-lg p-3">
                                      <p className="text-xs text-muted-foreground mb-1.5 font-medium">Tokens Used</p>
                                      <p className="text-sm font-semibold">
                                        📊 {openaiData.usage.total_tokens || 0}
                                      </p>
                                    </div>
                                    <div className="bg-muted/50 border rounded-lg p-3">
                                      <p className="text-xs text-muted-foreground mb-1.5 font-medium">Completion Tokens</p>
                                      <p className="text-sm font-semibold">
                                        ✨ {openaiData.usage.completion_tokens || 0}
                                      </p>
                                    </div>
                                  </>
                                )}
                              </div>
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Response Generated Successfully
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenAI API
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      // Image Generation Display
                      if (action === 'image_generation' && openaiData.image_urls) {
                        return (
                          <Card className="border-2 border-purple-200 dark:border-purple-800">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                {getActionEmoji(action)} OpenAI {getActionTitle(action)}
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Images Display */}
                              <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
                                <p className="text-xs text-muted-foreground mb-3 font-medium uppercase tracking-wide">Generated Images</p>
                                <div className="grid grid-cols-2 gap-3">
                                  {openaiData.image_urls.map((url: string, index: number) => (
                                    <div key={index} className="bg-white dark:bg-gray-900 rounded-lg overflow-hidden border">
                                      {/* eslint-disable-next-line @next/next/no-img-element */}
                                      <img 
                                        src={url} 
                                        alt={`Generated image ${index + 1}`}
                                        className="w-full h-auto"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>
                              
                              {/* Model Info */}
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Model</p>
                                  <p className="text-sm font-semibold font-mono">
                                    🎨 {openaiData.model || 'dall-e-3'}
                                  </p>
                                </div>
                                <div className="bg-muted/50 border rounded-lg p-3">
                                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Images Generated</p>
                                  <p className="text-sm font-semibold">
                                    🖼️ {openaiData.image_urls.length}
                                  </p>
                                </div>
                              </div>
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Images Generated Successfully
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenAI DALL-E
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      // Content Moderation Display
                      if (action === 'content_moderation' && openaiData.moderation_result) {
                        const moderation = openaiData.moderation_result;
                        const isFlagged = moderation.flagged;
                        
                        return (
                          <Card className={cn(
                            "border-2",
                            isFlagged ? "border-red-200 dark:border-red-800" : "border-green-200 dark:border-green-800"
                          )}>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-base flex items-center gap-2">
                                {getActionEmoji(action)} OpenAI {getActionTitle(action)}
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              {/* Moderation Status */}
                              <div className={cn(
                                "rounded-lg p-4 border",
                                isFlagged 
                                  ? "bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-950 dark:to-orange-950 border-red-200 dark:border-red-800"
                                  : "bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950 dark:to-emerald-950 border-green-200 dark:border-green-800"
                              )}>
                                <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">Moderation Status</p>
                                <div className="flex items-center gap-2">
                                  <span className="text-2xl">{isFlagged ? '⚠️' : '✅'}</span>
                                  <p className="text-lg font-semibold">
                                    {isFlagged ? 'Content Flagged' : 'Content Safe'}
                                  </p>
                                </div>
                              </div>
                              
                              {/* Category Scores */}
                              {moderation.categories && (
                                <div className="space-y-2">
                                  <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Flagged Categories</p>
                                  <div className="grid grid-cols-2 gap-2">
                                    {Object.entries(moderation.categories)
                                      .filter(([, flagged]) => flagged)
                                      .map(([category]) => (
                                        <div key={category} className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded p-2">
                                          <p className="text-xs font-medium text-red-700 dark:text-red-300 capitalize">
                                            {category.replace(/[_-]/g, ' ')}
                                          </p>
                                        </div>
                                      ))}
                                  </div>
                                  {!Object.values(moderation.categories).some((v) => v) && (
                                    <p className="text-xs text-muted-foreground italic">No categories flagged</p>
                                  )}
                                </div>
                              )}
                              
                              {/* Model Info */}
                              <div className="bg-muted/50 border rounded-lg p-3">
                                <p className="text-xs text-muted-foreground mb-1.5 font-medium">Model</p>
                                <p className="text-sm font-semibold font-mono">
                                  🛡️ {openaiData.model || 'text-moderation-latest'}
                                </p>
                              </div>
                              
                              {/* Status Badge */}
                              <div className="flex items-center justify-between pt-3 border-t">
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-300">
                                  ✓ Moderation Complete
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  via OpenAI Moderation API
                                </span>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      }
                      
                      return null;
                    } catch {
                      return null;
                    }
                  })()}

                  {/* Step Details */}
                  {selectedLog.step_details && (
                    <Card className="border-2">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full bg-primary"></div>
                          Step Execution Log
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="bg-muted rounded-lg p-4 overflow-x-auto">
                          <pre className="text-xs whitespace-pre-wrap break-words font-mono">
                            {JSON.stringify(selectedLog.step_details, null, 2)}
                          </pre>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  );
}
