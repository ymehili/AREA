import React, { useRef, useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import VariablePicker from '@/components/VariablePicker';
import { AreaStepNodeData, NodeData, TriggerNodeData, ActionNodeData, DelayNodeData, isActionNode, isTriggerNode } from './node-types';
import { requestJson } from '@/lib/api';
import { useRequireAuth } from '@/hooks/use-auth';

// Type for nodes and edges
type FlowNode = {
  id: string;
  data?: Partial<NodeData>;
};

type FlowEdge = {
  source: string;
  target: string;
};

interface ControlsPanelProps {
  onAddNode: (type: 'trigger' | 'action' | 'condition' | 'delay') => void;
  selectedNodeId?: string;
  onNodeConfigChange?: (id: string, config: Partial<NodeData>) => void;
  nodeConfig?: Partial<NodeData>;
  nodes?: FlowNode[];  // Add nodes to compute propagated variables
  edges?: FlowEdge[];  // Add edges to determine execution order
}

// Type for service catalog
type ServiceCatalog = {
  slug: string;
  name: string;
  description: string;
  actions: { key: string; name: string; description: string }[];
  reactions: { key: string; name: string; description: string }[];
};

// Response type for service catalog
type ServiceCatalogResponse = {
  services: ServiceCatalog[];
};

const ControlsPanel: React.FC<ControlsPanelProps> = ({
  onAddNode,
  selectedNodeId,
  onNodeConfigChange,
  nodeConfig,
  nodes = [],
  edges = []
}) => {
  const auth = useRequireAuth();

  const focusedInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const lastSelectionStartRef = useRef<number>(0);
  const lastSelectionEndRef = useRef<number>(0);

  // State for available services
  const [services, setServices] = useState<ServiceCatalog[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  const [connectedServices, setConnectedServices] = useState<string[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (!auth.token) return;

      setLoadingServices(true);
      try {
        const [catalogData, connectionsData] = await Promise.all([
          requestJson<ServiceCatalogResponse>(
            '/services/actions-reactions',
            { method: 'GET' },
            auth.token
          ),
          requestJson<{ connected_services: string[] }>(
            '/services/user-connections',
            { method: 'GET' },
            auth.token
          )
        ]);

        setServices(catalogData.services || []);
        setConnectedServices(connectionsData.connected_services || []);
      } catch (error) {
        console.error('Failed to fetch services:', error);
      } finally {
        setLoadingServices(false);
      }
    };
    fetchData();
  }, [auth.token]);

  // Type for variable object
  type VariableItem = {
    id: string;
    name: string;
    description: string;
    category: string;
    type: 'text' | 'number' | 'boolean';
  };

  // Helper function to get all variables available to a node (propagated from previous steps)
  const getPropagatedVariables = (currentNodeId: string | undefined) => {
    if (!currentNodeId || nodes.length === 0) {
      return [];
    }

    const variablesMap: Record<string, VariableItem> = {};

    // Add common variables always available
    variablesMap['now'] = { id: 'now', name: 'Current Time', description: 'The time when the trigger fired', category: 'Trigger', type: 'text' as const };
    variablesMap['user_id'] = { id: 'user_id', name: 'User ID', description: 'The ID of the user who triggered the action', category: 'Trigger', type: 'text' as const };
    variablesMap['area_id'] = { id: 'area_id', name: 'Area ID', description: 'The ID of the automation area', category: 'Trigger', type: 'text' as const };

    // Find all nodes that execute before the current node
    const getPrecedingNodes = (nodeId: string, visited = new Set<string>()): Set<string> => {
      if (visited.has(nodeId)) return visited;
      visited.add(nodeId);

      // Find edges that point TO this node
      const incomingEdges = edges.filter(edge => edge.target === nodeId);
      incomingEdges.forEach(edge => {
        getPrecedingNodes(edge.source, visited);
      });

      return visited;
    };

    const precedingNodeIds = getPrecedingNodes(currentNodeId);
    precedingNodeIds.delete(currentNodeId); // Remove current node from the list

    // Collect variables from all preceding nodes
    precedingNodeIds.forEach(nodeId => {
      const node = nodes.find(n => n.id === nodeId);
      if (!node || !node.data) return;

      // Only Trigger and Action nodes have serviceId
      if (!isTriggerNode(node.data) && !isActionNode(node.data)) return;

      const serviceId = node.data.serviceId;
      if (!serviceId) return;

      // Add service-specific variables based on the service type
      const serviceVariables = getVariablesForService(serviceId);
      serviceVariables.forEach(v => {
        variablesMap[v.id] = v;
      });
    });

    return Object.values(variablesMap);
  };

  // Helper function to get variables for a specific service
  const getVariablesForService = (serviceId: string): VariableItem[] => {
    const variables: VariableItem[] = [];

    if (serviceId === 'gmail') {
      variables.push(
        { id: 'gmail.sender', name: 'Email Sender', description: 'The sender of the email', category: 'Gmail', type: 'text' as const },
        { id: 'gmail.subject', name: 'Email Subject', description: 'The subject of the email', category: 'Gmail', type: 'text' as const },
        { id: 'gmail.body', name: 'Email Body', description: 'The body content of the email', category: 'Gmail', type: 'text' as const },
        { id: 'gmail.message_id', name: 'Message ID', description: 'The Gmail message ID', category: 'Gmail', type: 'text' as const },
        { id: 'gmail.thread_id', name: 'Thread ID', description: 'The Gmail thread ID', category: 'Gmail', type: 'text' as const },
        { id: 'gmail.snippet', name: 'Snippet', description: 'A short preview of the email', category: 'Gmail', type: 'text' as const }
      );
    } else if (serviceId === 'outlook') {
      variables.push(
        { id: 'outlook.sender', name: 'Email Sender', description: 'The sender email address', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.sender_email', name: 'Sender Email', description: 'The sender email address', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.sender_name', name: 'Sender Name', description: 'The sender display name', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.subject', name: 'Email Subject', description: 'The subject of the email', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.snippet', name: 'Body Preview', description: 'A short preview of the email body', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.body_preview', name: 'Body Preview', description: 'A short preview of the email body', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.message_id', name: 'Message ID', description: 'The Outlook message ID', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.conversation_id', name: 'Conversation ID', description: 'The Outlook conversation/thread ID', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.received_datetime', name: 'Received Date/Time', description: 'When the email was received', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.sent_datetime', name: 'Sent Date/Time', description: 'When the email was sent', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.timestamp', name: 'Timestamp', description: 'Email received timestamp', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.is_read', name: 'Is Read', description: 'Whether the email has been read', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.importance', name: 'Importance', description: 'Email importance level', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.has_attachments', name: 'Has Attachments', description: 'Whether the email has attachments', category: 'Outlook', type: 'text' as const },
        { id: 'outlook.web_link', name: 'Web Link', description: 'Link to view the email in Outlook web', category: 'Outlook', type: 'text' as const }
      );
    } else if (serviceId === 'openai') {
      variables.push(
        { id: 'openai.response', name: 'AI Response', description: 'The generated text from OpenAI', category: 'OpenAI', type: 'text' as const },
        { id: 'openai.image_urls', name: 'Image URLs', description: 'Generated image URLs (DALL-E)', category: 'OpenAI', type: 'text' as const },
        { id: 'openai.moderation.flagged', name: 'Content Flagged', description: 'Whether content was flagged', category: 'OpenAI', type: 'text' as const },
        { id: 'openai.input_tokens', name: 'Input Tokens', description: 'Number of tokens in prompt', category: 'OpenAI', type: 'text' as const },
        { id: 'openai.output_tokens', name: 'Output Tokens', description: 'Number of tokens in response', category: 'OpenAI', type: 'text' as const }
      );
    } else if (serviceId === 'google_calendar') {
      variables.push(
        { id: 'calendar.event_id', name: 'Event ID', description: 'The unique event identifier', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.title', name: 'Event Title', description: 'The event title/summary', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.description', name: 'Description', description: 'Event description/details', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.location', name: 'Location', description: 'Event location', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.start_time', name: 'Start Time', description: 'Event start time (ISO 8601)', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.end_time', name: 'End Time', description: 'Event end time (ISO 8601)', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.attendees', name: 'Attendees', description: 'Comma-separated attendee emails', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.organizer', name: 'Organizer', description: 'Event organizer email', category: 'Google Calendar', type: 'text' as const },
        { id: 'calendar.link', name: 'Event Link', description: 'Google Calendar web link', category: 'Google Calendar', type: 'text' as const }
      );
    } else if (serviceId === 'github') {
      variables.push(
        { id: 'github.repo', name: 'Repository Name', description: 'The name of the repository', category: 'GitHub', type: 'text' as const },
        { id: 'github.repo_full_name', name: 'Repository Full Name', description: 'The full name of the repository (owner/repo)', category: 'GitHub', type: 'text' as const },
        { id: 'github.repo_url', name: 'Repository URL', description: 'The HTML URL of the repository', category: 'GitHub', type: 'text' as const },
        { id: 'github.sender', name: 'Sender', description: 'The user who triggered the event', category: 'GitHub', type: 'text' as const },
        { id: 'github.issue_number', name: 'Issue Number', description: 'The issue number', category: 'GitHub', type: 'text' as const },
        { id: 'github.issue_title', name: 'Issue Title', description: 'The title of the issue', category: 'GitHub', type: 'text' as const },
        { id: 'github.issue_body', name: 'Issue Body', description: 'The body content of the issue', category: 'GitHub', type: 'text' as const },
        { id: 'github.issue_author', name: 'Issue Author', description: 'The author of the issue', category: 'GitHub', type: 'text' as const },
        { id: 'github.pull_request_number', name: 'PR Number', description: 'The pull request number', category: 'GitHub', type: 'text' as const },
        { id: 'github.pull_request_title', name: 'PR Title', description: 'The title of the pull request', category: 'GitHub', type: 'text' as const },
        { id: 'github.pull_request_body', name: 'PR Body', description: 'The body content of the pull request', category: 'GitHub', type: 'text' as const },
        { id: 'github.pull_request_author', name: 'PR Author', description: 'The author of the pull request', category: 'GitHub', type: 'text' as const },
        { id: 'github.branch', name: 'Branch', description: 'The branch name', category: 'GitHub', type: 'text' as const },
        { id: 'github.action', name: 'Action', description: 'The action that occurred (opened, closed, etc.)', category: 'GitHub', type: 'text' as const }
      );
    } else if (serviceId === 'weather') {
      variables.push(
        { id: 'weather.temperature', name: 'Temperature', description: 'Current temperature', category: 'Weather', type: 'number' as const },
        { id: 'weather.feels_like', name: 'Feels Like', description: 'Perceived temperature', category: 'Weather', type: 'number' as const },
        { id: 'weather.humidity', name: 'Humidity', description: 'Humidity percentage', category: 'Weather', type: 'number' as const },
        { id: 'weather.pressure', name: 'Pressure', description: 'Atmospheric pressure', category: 'Weather', type: 'number' as const },
        { id: 'weather.wind_speed', name: 'Wind Speed', description: 'Wind speed', category: 'Weather', type: 'number' as const },
        { id: 'weather.wind_deg', name: 'Wind Direction', description: 'Wind direction in degrees', category: 'Weather', type: 'number' as const },
        { id: 'weather.clouds', name: 'Cloudiness', description: 'Cloud coverage percentage', category: 'Weather', type: 'number' as const },
        { id: 'weather.description', name: 'Description', description: 'Weather description', category: 'Weather', type: 'text' as const },
        { id: 'weather.main', name: 'Main Condition', description: 'Main weather condition', category: 'Weather', type: 'text' as const },
        { id: 'weather.icon', name: 'Weather Icon', description: 'Weather icon code', category: 'Weather', type: 'text' as const },
        { id: 'weather.city', name: 'City', description: 'City name', category: 'Weather', type: 'text' as const },
        { id: 'weather.country', name: 'Country', description: 'Country code', category: 'Weather', type: 'text' as const },
        { id: 'weather.sunrise', name: 'Sunrise', description: 'Sunrise time', category: 'Weather', type: 'text' as const },
        { id: 'weather.sunset', name: 'Sunset', description: 'Sunset time', category: 'Weather', type: 'text' as const }
      );
    } else if (serviceId === 'deepl') {
      variables.push(
        { id: 'deepl.translated_text', name: 'Translated Text', description: 'The translated text output', category: 'DeepL', type: 'text' as const },
        { id: 'deepl.detected_language', name: 'Detected Language', description: 'The detected source language code (e.g., EN, FR, DE)', category: 'DeepL', type: 'text' as const },
        { id: 'deepl.detected_source_language', name: 'Detected Source Language', description: 'The automatically detected source language', category: 'DeepL', type: 'text' as const },
        { id: 'deepl.source_language', name: 'Source Language', description: 'The specified source language', category: 'DeepL', type: 'text' as const },
        { id: 'deepl.target_language', name: 'Target Language', description: 'The target language for translation', category: 'DeepL', type: 'text' as const },
        { id: 'deepl.original_text', name: 'Original Text', description: 'The original input text', category: 'DeepL', type: 'text' as const }
      );
    }

    return variables;
  };

  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    focusedInputRef.current = e.target;
  };

  const handleInputSelectCapture = (e: React.SyntheticEvent) => {
    const target = e.target as HTMLInputElement | HTMLTextAreaElement;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
      const value = (target as HTMLInputElement | HTMLTextAreaElement).value ?? '';
      const start = (target as HTMLInputElement | HTMLTextAreaElement).selectionStart ?? value.length;
      const end = (target as HTMLInputElement | HTMLTextAreaElement).selectionEnd ?? start;
      lastSelectionStartRef.current = start;
      lastSelectionEndRef.current = end;
    }
  };

  const handleInsertVariable = (variableId: string) => {
    if (!selectedNodeId || !focusedInputRef.current || !nodeConfig || !onNodeConfigChange) return;

    const input = focusedInputRef.current;
    const start = (input.selectionStart ?? lastSelectionStartRef.current) || 0;
    const end = (input.selectionEnd ?? lastSelectionEndRef.current) || start;
    const currentValue = input.value;
    const variableTemplate = `{{${variableId}}}`;

    const newValue =
      currentValue.substring(0, start) +
      variableTemplate +
      currentValue.substring(end);

    const inputId = input.id;

    if (inputId === 'label') {
      onNodeConfigChange(selectedNodeId, {
        ...nodeConfig,
        label: newValue
      } as AreaStepNodeData);

      input.value = newValue;
      const inputElement = input as HTMLInputElement;
      if (inputElement.type !== 'number') {
        const newCursorPosition = start + variableTemplate.length;
        input.setSelectionRange(newCursorPosition, newCursorPosition);
      }
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      return;
    }

    if (inputId === 'description') {
      onNodeConfigChange(selectedNodeId, {
        ...nodeConfig,
        description: newValue
      } as AreaStepNodeData);

      input.value = newValue;
      const inputElement = input as HTMLInputElement;
      if (inputElement.type !== 'number') {
        const newCursorPosition = start + variableTemplate.length;
        input.setSelectionRange(newCursorPosition, newCursorPosition);
      }
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      return;
    }

    let paramName = inputId;

    if (inputId === 'github_branch_name') {
      paramName = 'branch_name';
    }

    paramName = paramName.replace(/^github_issue_/, '');
    paramName = paramName.replace(/^github_comment_/, '');
    paramName = paramName.replace(/^github_close_/, '');
    paramName = paramName.replace(/^github_label_/, '');
    paramName = paramName.replace(/^github_branch_/, '');
    paramName = paramName.replace(/^github_/, '');
    paramName = paramName.replace(/^gmail_fwd_/, '');
    paramName = paramName.replace(/^gmail_/, '');
    paramName = paramName.replace(/^outlook_fwd_/, '');
    paramName = paramName.replace(/^outlook_/, '');
    paramName = paramName.replace(/^weather_/, '');
    paramName = paramName.replace(/^forecast_/, '');
    // OpenAI - more specific patterns first
    paramName = paramName.replace(/^openai_image_/, '');
    paramName = paramName.replace(/^openai_text_/, '');
    paramName = paramName.replace(/^openai_moderate_/, '');
    paramName = paramName.replace(/^openai_/, '');
    // Google Drive
    paramName = paramName.replace(/^drive_copy_/, '');
    paramName = paramName.replace(/^drive_move_/, '');
    paramName = paramName.replace(/^drive_delete_/, '');
    paramName = paramName.replace(/^drive_trigger_/, '');
    paramName = paramName.replace(/^drive_/, '');
    // Calendar
    paramName = paramName.replace(/^calendar_/, '');
    paramName = paramName.replace(/^calendar_create_/, '');
    paramName = paramName.replace(/^calendar_update_/, '');
    paramName = paramName.replace(/^calendar_delete_/, '');
    paramName = paramName.replace(/^calendar_quick_/, '');
    // DeepL
    paramName = paramName.replace(/^deepl_source_/, '');
    paramName = paramName.replace(/^deepl_target_/, '');
    paramName = paramName.replace(/^deepl_auto_/, '');
    paramName = paramName.replace(/^deepl_detect_/, '');
    paramName = paramName.replace(/^deepl_/, '');

    if (inputId === 'debugMessage') {
      paramName = 'message';
    }

    if (isActionNode(nodeConfig)) {
      const currentParams = (nodeConfig as ActionNodeData).params || {};
      onNodeConfigChange(selectedNodeId, {
        ...nodeConfig,
        params: { ...currentParams, [paramName]: newValue }
      } as ActionNodeData);
    } else if (isTriggerNode(nodeConfig)) {
      const currentParams = (nodeConfig as TriggerNodeData).params || {};
      onNodeConfigChange(selectedNodeId, {
        ...nodeConfig,
        params: { ...currentParams, [paramName]: newValue }
      } as TriggerNodeData);
    }

    input.value = newValue;

    const inputElement = input as HTMLInputElement;
    if (inputElement.type !== 'number') {
      const newCursorPosition = start + variableTemplate.length;
      input.setSelectionRange(newCursorPosition, newCursorPosition);
    }

    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
  };

  return (
    <div 
      className="w-80 h-full bg-card border-l overflow-y-auto px-3 py-4 flex flex-col gap-3"
      onSelectCapture={handleInputSelectCapture}
    >
      <Card className="border-0 shadow-none">
        <CardHeader className="px-0 pt-0">
          <CardTitle className="text-base font-semibold">Add Step</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 px-0 pb-0">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start h-9"
            onClick={() => onAddNode('trigger')}
          >
            <Badge variant="outline" className="mr-2 bg-blue-100 text-blue-800 text-xs">Trigger</Badge>
            <span className="text-sm">Add Event</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start h-9"
            onClick={() => onAddNode('action')}
          >
            <Badge variant="outline" className="mr-2 bg-green-100 text-green-800 text-xs">Action</Badge>
            <span className="text-sm">Add Action</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start h-9"
            onClick={() => onAddNode('condition')}
          >
            <Badge variant="outline" className="mr-2 bg-yellow-100 text-yellow-800 text-xs">Condition</Badge>
            <span className="text-sm">Add If</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start h-9"
            onClick={() => onAddNode('delay')}
          >
            <Badge variant="outline" className="mr-2 bg-purple-100 text-purple-800 text-xs">Delay</Badge>
            <span className="text-sm">Add Delay</span>
          </Button>
        </CardContent>
      </Card>

      {selectedNodeId && onNodeConfigChange && (
        <>
          <Separator />
          <Card className="border-0 shadow-none">
            <CardHeader className="px-0">
              <CardTitle className="text-base font-semibold">Configure Step</CardTitle>
            </CardHeader>
            <CardContent className="px-0 pb-0">
              {/* Configuration UI based on the selected node type */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {nodeConfig ? 'Configuration options for selected node' : 'Select a node to configure'}
              </div>

              {/* Configuration fields - dynamic based on node type */}
              {nodeConfig && (
                <div className="mt-4 space-y-3">
                  <div>
                    <Label htmlFor="label">Step Label</Label>
                    <Input
                      id="label"
                      type="text"
                      value={nodeConfig.label || ''}
                      onChange={(e) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, label: e.target.value })}
                      onFocus={handleInputFocus}
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <textarea
                      id="description"
                      className="w-full p-2 border rounded mt-1 min-h-[60px]"
                      value={nodeConfig.description || ''}
                      onChange={(e) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, description: e.target.value })}
                      onFocus={handleInputFocus}
                      placeholder="Enter a description for this step"
                    />
                  </div>

                  {/* Trigger-specific configuration */}
                  {isTriggerNode(nodeConfig) && (
                    <>
                      <Separator className="my-3" />
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="triggerService">Service</Label>
                          <Select
                            value={nodeConfig.serviceId || ''}
                            onValueChange={(value) => {
                              // Reset actionId when service changes
                              onNodeConfigChange(selectedNodeId, {
                                ...nodeConfig,
                                serviceId: value,
                                actionId: '',
                                label: services.find(s => s.slug === value)?.name || nodeConfig.label
                              } as TriggerNodeData);
                            }}
                            disabled={loadingServices}
                          >
                            <SelectTrigger id="triggerService">
                              <SelectValue placeholder={loadingServices ? "Loading..." : "Select a service"} />
                            </SelectTrigger>
                            <SelectContent>
                              {services
                                .filter((service) => service.actions.length > 0)
                                .map((service) => (
                                  <SelectItem key={service.slug} value={service.slug}>
                                    {service.name}
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-gray-500 mt-1">Choose the service that will trigger this automation</p>
                        </div>

                        {nodeConfig.serviceId && (
                          <>
                            {/* Built-in services do not require per-user connection */}
                            {!['debug', 'time', 'delay'].includes(nodeConfig.serviceId) && !connectedServices.includes(nodeConfig.serviceId) && (
                              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                                <p className="text-sm text-yellow-800">
                                  ⚠️ You need to connect your {services.find(s => s.slug === nodeConfig.serviceId)?.name} account.{' '}
                                  <a href="/connections" className="underline font-medium">Go to Connections</a>
                                </p>
                              </div>
                            )}
                            <div>
                              <Label htmlFor="triggerAction">Trigger Event</Label>
                              <Select
                                value={nodeConfig.actionId || ''}
                                onValueChange={(value) => {
                                  const selectedService = services.find(s => s.slug === nodeConfig.serviceId);
                                  const selectedAction = selectedService?.actions.find(a => a.key === value);
                                  console.log('[ControlsPanel] Changing trigger from', nodeConfig.actionId, 'to', value);
                                  console.log('[ControlsPanel] Clearing params, old params:', nodeConfig.params);
                                  onNodeConfigChange(selectedNodeId, {
                                    ...nodeConfig,
                                    actionId: value,
                                    label: selectedAction?.name || nodeConfig.label,
                                    description: selectedAction?.description || nodeConfig.description,
                                    params: {}, // Clear all params when changing trigger
                                    config: {} // Also clear config to remove any trigger-specific config
                                  } as TriggerNodeData);
                                }}
                              >
                                <SelectTrigger id="triggerAction">
                                  <SelectValue placeholder="Select a trigger event" />
                                </SelectTrigger>
                                <SelectContent>
                                  {services
                                    .find((s) => s.slug === nodeConfig.serviceId)
                                    ?.actions.map((action) => (
                                      <SelectItem key={action.key} value={action.key}>
                                        {action.name}
                                      </SelectItem>
                                    ))}
                                </SelectContent>
                              </Select>
                              <p className="text-xs text-gray-500 mt-1">
                                {services.find(s => s.slug === nodeConfig.serviceId)?.actions.find(a => a.key === nodeConfig.actionId)?.description || 'Select the event that will trigger this automation'}
                              </p>
                            </div>

                            {/* Trigger params: Time every_interval requires interval_seconds */}
                            {nodeConfig.serviceId === 'time' && nodeConfig.actionId === 'every_interval' && (
                              <div>
                                <Label htmlFor="time_interval_seconds">Interval (seconds)</Label>
                                <Input
                                  id="time_interval_seconds"
                                  type="number"
                                  min="1"
                                  placeholder="60"
                                  value={(nodeConfig as TriggerNodeData).params?.interval_seconds as number || 60}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, {
                                      ...nodeConfig,
                                      params: { ...currentParams, interval_seconds: parseInt(e.target.value) || 60 }
                                    } as TriggerNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">How often to trigger (in seconds). Minimum: 1 second.</p>
                              </div>
                            )}

                            {/* Trigger params: Gmail and Outlook new_email_from_sender requires sender_email */}
                            {(nodeConfig.serviceId === 'gmail' || nodeConfig.serviceId === 'outlook') && nodeConfig.actionId === 'new_email_from_sender' && (
                              <div>
                                <Label htmlFor={`${nodeConfig.serviceId}_sender_email`}>Sender Email</Label>
                                <Input
                                  id={`${nodeConfig.serviceId}_sender_email`}
                                  type="email"
                                  placeholder="name@example.com"
                                  value={(nodeConfig as TriggerNodeData).params?.sender_email as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, {
                                      ...nodeConfig,
                                      params: { ...currentParams, sender_email: e.target.value }
                                    } as TriggerNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Only trigger for emails from this sender.</p>
                              </div>
                            )}

                            {/* Trigger params: Discord new_message_in_channel requires channel_id */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'new_message_in_channel' && (
                              <div>
                                <Label htmlFor="discord_trigger_channel_id">Channel ID</Label>
                                <Input
                                  id="discord_trigger_channel_id"
                                  type="text"
                                  placeholder="123456789012345678"
                                  value={(nodeConfig as TriggerNodeData).params?.channel_id as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, {
                                      ...nodeConfig,
                                      params: { ...currentParams, channel_id: e.target.value }
                                    } as TriggerNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">The Discord channel ID to monitor for new messages.</p>
                              </div>
                            )}

                            {/* Trigger params: Discord reaction_added requires channel_id and message_id */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'reaction_added' && (
                              <>
                                <div>
                                  <Label htmlFor="discord_reaction_channel_id">Channel ID</Label>
                                  <Input
                                    id="discord_reaction_channel_id"
                                    type="text"
                                    placeholder="123456789012345678"
                                    value={(nodeConfig as TriggerNodeData).params?.channel_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, channel_id: e.target.value }
                                      } as TriggerNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The Discord channel ID where the message is located.</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_reaction_message_id">Message ID</Label>
                                  <Input
                                    id="discord_reaction_message_id"
                                    type="text"
                                    placeholder="987654321098765432"
                                    value={(nodeConfig as TriggerNodeData).params?.message_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, message_id: e.target.value }
                                      } as TriggerNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The specific message ID to monitor for reactions. Enable Discord Developer Mode to copy message IDs.</p>
                                </div>
                              </>
                            )}

                            {/* Trigger params: Weather temperature_threshold requires location, threshold, and operator */}
                            {nodeConfig.serviceId === 'weather' && nodeConfig.actionId === 'temperature_threshold' && (
                              <>
                                <div>
                                  <Label htmlFor="weather_location">Location</Label>
                                  <Input
                                    id="weather_location"
                                    type="text"
                                    placeholder="London,UK or Paris,FR"
                                    value={(nodeConfig as TriggerNodeData).params?.location as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, location: e.target.value }
                                      } as TriggerNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">City name (e.g., &quot;London,UK&quot;)</p>
                                </div>
                                <div>
                                  <Label htmlFor="weather_threshold">Temperature Threshold (°C)</Label>
                                  <Input
                                    id="weather_threshold"
                                    type="number"
                                    placeholder="25"
                                    value={(nodeConfig as TriggerNodeData).params?.threshold as number || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, threshold: parseFloat(e.target.value) }
                                      } as TriggerNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Temperature in Celsius</p>
                                </div>
                                <div>
                                  <Label htmlFor="weather_operator">Condition</Label>
                                  <Select
                                    value={(nodeConfig as TriggerNodeData).params?.operator as string || 'above'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, operator: value }
                                      } as TriggerNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="weather_operator">
                                      <SelectValue placeholder="Select condition" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="above">Goes above threshold</SelectItem>
                                      <SelectItem value="below">Goes below threshold</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <p className="text-xs text-gray-500 mt-1">Trigger when temperature crosses the threshold</p>
                                </div>
                              </>
                            )}

                            {/* Trigger params: Weather weather_condition requires location and condition */}
                            {nodeConfig.serviceId === 'weather' && nodeConfig.actionId === 'weather_condition' && (
                              <>
                                <div>
                                  <Label htmlFor="weather_condition_location">Location</Label>
                                  <Input
                                    id="weather_condition_location"
                                    type="text"
                                    placeholder="London,UK or Paris,FR"
                                    value={(nodeConfig as TriggerNodeData).params?.location as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, location: e.target.value }
                                      } as TriggerNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">City name (e.g., &quot;London,UK&quot;)</p>
                                </div>
                                <div>
                                  <Label htmlFor="weather_condition_type">Weather Condition</Label>
                                  <Select
                                    value={(nodeConfig as TriggerNodeData).params?.condition as string || ''}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as TriggerNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, condition: value }
                                      } as TriggerNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="weather_condition_type">
                                      <SelectValue placeholder="Select condition" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="clear">Clear</SelectItem>
                                      <SelectItem value="clouds">Cloudy</SelectItem>
                                      <SelectItem value="rain">Rain</SelectItem>
                                      <SelectItem value="drizzle">Drizzle</SelectItem>
                                      <SelectItem value="thunderstorm">Thunderstorm</SelectItem>
                                      <SelectItem value="snow">Snow</SelectItem>
                                      <SelectItem value="mist">Mist</SelectItem>
                                      <SelectItem value="fog">Fog</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <p className="text-xs text-gray-500 mt-1">Trigger when weather changes to this condition</p>
                                </div>
                              </>
                            )}

                          </>
                        )}
                      </div>
                    </>
                  )}

                  {/* Action-specific configuration */}
                  {isActionNode(nodeConfig) && (
                    <>
                      <Separator className="my-3" />
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="actionService">Service</Label>
                          <Select
                            value={nodeConfig.serviceId || ''}
                            onValueChange={(value) => {
                              // Reset actionId when service changes
                              onNodeConfigChange(selectedNodeId, {
                                ...nodeConfig,
                                serviceId: value,
                                actionId: '',
                                label: services.find(s => s.slug === value)?.name || nodeConfig.label
                              } as ActionNodeData);
                            }}
                            disabled={loadingServices}
                          >
                            <SelectTrigger id="actionService">
                              <SelectValue placeholder={loadingServices ? "Loading..." : "Select a service"} />
                            </SelectTrigger>
                            <SelectContent>
                              {services
                                .filter((service) => service.reactions.length > 0)
                                .map((service) => (
                                  <SelectItem key={service.slug} value={service.slug}>
                                    {service.name}
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-gray-500 mt-1">Choose the service to perform an action</p>
                        </div>

                        {nodeConfig.serviceId && (
                          <>
                            {/* Built-in services do not require per-user connection */}
                            {!['debug', 'time', 'delay'].includes(nodeConfig.serviceId) && !connectedServices.includes(nodeConfig.serviceId) && (
                              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                                <p className="text-sm text-yellow-800">
                                  ⚠️ You need to connect your {services.find(s => s.slug === nodeConfig.serviceId)?.name} account.{' '}
                                  <a href="/connections" className="underline font-medium">Go to Connections</a>
                                </p>
                              </div>
                            )}
                            <div>
                              <Label htmlFor="actionReaction">Action</Label>
                              <Select
                                value={nodeConfig.actionId || ''}
                                onValueChange={(value) => {
                                  const selectedService = services.find(s => s.slug === nodeConfig.serviceId);
                                  const selectedReaction = selectedService?.reactions.find(r => r.key === value);
                                  console.log('[ControlsPanel] Changing action from', nodeConfig.actionId, 'to', value);
                                  console.log('[ControlsPanel] Clearing params, old params:', nodeConfig.params);
                                  onNodeConfigChange(selectedNodeId, {
                                    ...nodeConfig,
                                    actionId: value,
                                    label: selectedReaction?.name || nodeConfig.label,
                                    description: selectedReaction?.description || nodeConfig.description,
                                    params: {}, // Clear all params when changing action
                                    config: {} // Also clear config to remove any action-specific config
                                  } as ActionNodeData);
                                }}
                              >
                                <SelectTrigger id="actionReaction">
                                  <SelectValue placeholder="Select an action" />
                                </SelectTrigger>
                                <SelectContent>
                                  {services
                                    .find((s) => s.slug === nodeConfig.serviceId)
                                    ?.reactions.map((reaction) => (
                                      <SelectItem key={reaction.key} value={reaction.key}>
                                        {reaction.name}
                                      </SelectItem>
                                    ))}
                                </SelectContent>
                              </Select>
                              <p className="text-xs text-gray-500 mt-1">
                                {services.find(s => s.slug === nodeConfig.serviceId)?.reactions.find(r => r.key === nodeConfig.actionId)?.description || 'Select the action to perform'}
                              </p>
                            </div>

                            {/* Action params: Debug log message */}
                            {nodeConfig.serviceId === 'debug' && nodeConfig.actionId === 'log' && (
                              <div>
                                <Label htmlFor="debugMessage">Log Message</Label>
                                <textarea
                                  id="debugMessage"
                                  className="w-full p-2 border rounded mt-1 min-h-[80px] font-mono text-sm"
                                  placeholder="e.g., Email from {{gmail.sender}}: {{gmail.subject}}"
                                  value={(nodeConfig as ActionNodeData).params?.message as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as ActionNodeData).params || {};
                                    onNodeConfigChange?.(selectedNodeId!, {
                                      ...nodeConfig,
                                      params: { ...currentParams, message: e.target.value }
                                    } as ActionNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">{`Use variables like {{gmail.subject}}, {{gmail.sender}}, etc.`}</p>
                              </div>
                            )}

                            {/* Action params: Gmail send_email */}
                            {nodeConfig.serviceId === 'gmail' && nodeConfig.actionId === 'send_email' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="gmail_to">To</Label>
                                  <Input
                                    id="gmail_to"
                                    type="text"
                                    placeholder="recipient@example.com"
                                    value={(nodeConfig as ActionNodeData).params?.to as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, to: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="gmail_subject">Subject</Label>
                                  <Input
                                    id="gmail_subject"
                                    type="text"
                                    placeholder="Subject"
                                    value={(nodeConfig as ActionNodeData).params?.subject as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, subject: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="gmail_body">Body</Label>
                                  <textarea
                                    id="gmail_body"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Message body (supports variables like {{gmail.snippet}})"
                                    value={(nodeConfig as ActionNodeData).params?.body as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, body: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: Outlook send_email */}
                            {nodeConfig.serviceId === 'outlook' && nodeConfig.actionId === 'send_email' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="outlook_to">To</Label>
                                  <Input
                                    id="outlook_to"
                                    type="text"
                                    placeholder="recipient@example.com"
                                    value={(nodeConfig as ActionNodeData).params?.to as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, to: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="outlook_subject">Subject</Label>
                                  <Input
                                    id="outlook_subject"
                                    type="text"
                                    placeholder="Subject"
                                    value={(nodeConfig as ActionNodeData).params?.subject as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, subject: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="outlook_body">Body</Label>
                                  <textarea
                                    id="outlook_body"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Message body (supports variables like {{outlook.subject}})"
                                    value={(nodeConfig as ActionNodeData).params?.body as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, body: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: Outlook mark_as_read needs message_id */}
                            {nodeConfig.serviceId === 'outlook' && nodeConfig.actionId === 'mark_as_read' && (
                              <div>
                                <Label htmlFor="outlook_message_id">Message ID</Label>
                                <Input
                                  id="outlook_message_id"
                                  type="text"
                                  placeholder="{{outlook.message_id}}"
                                  value={(nodeConfig as ActionNodeData).params?.message_id as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as ActionNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, message_id: e.target.value } } as ActionNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Provide a message ID or use a variable from the trigger.</p>
                              </div>
                            )}

                            {/* Action params: Outlook forward_email needs message_id, to, comment (optional) */}
                            {nodeConfig.serviceId === 'outlook' && nodeConfig.actionId === 'forward_email' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="outlook_fwd_message_id">Message ID</Label>
                                  <Input
                                    id="outlook_fwd_message_id"
                                    type="text"
                                    placeholder="{{outlook.message_id}}"
                                    value={(nodeConfig as ActionNodeData).params?.message_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, message_id: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="outlook_fwd_to">Forward To</Label>
                                  <Input
                                    id="outlook_fwd_to"
                                    type="text"
                                    placeholder="recipient@example.com"
                                    value={(nodeConfig as ActionNodeData).params?.to as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, to: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="outlook_fwd_comment">Comment (optional)</Label>
                                  <textarea
                                    id="outlook_fwd_comment"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px]"
                                    placeholder="Add a note before the forwarded content"
                                    value={(nodeConfig as ActionNodeData).params?.comment as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, comment: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: Gmail mark_as_read needs message_id */}
                            {nodeConfig.serviceId === 'gmail' && nodeConfig.actionId === 'mark_as_read' && (
                              <div>
                                <Label htmlFor="gmail_message_id">Message ID</Label>
                                <Input
                                  id="gmail_message_id"
                                  type="text"
                                  placeholder="{{gmail.message_id}}"
                                  value={(nodeConfig as ActionNodeData).params?.message_id as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as ActionNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, message_id: e.target.value } } as ActionNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Provide a message ID or use a variable from the trigger.</p>
                              </div>
                            )}

                            {/* Action params: Gmail forward_email needs message_id, to, comment (optional) */}
                            {nodeConfig.serviceId === 'gmail' && nodeConfig.actionId === 'forward_email' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="gmail_fwd_message_id">Message ID</Label>
                                  <Input
                                    id="gmail_fwd_message_id"
                                    type="text"
                                    placeholder="{{gmail.message_id}}"
                                    value={(nodeConfig as ActionNodeData).params?.message_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, message_id: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="gmail_fwd_to">Forward To</Label>
                                  <Input
                                    id="gmail_fwd_to"
                                    type="text"
                                    placeholder="recipient@example.com"
                                    value={(nodeConfig as ActionNodeData).params?.to as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, to: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="gmail_fwd_comment">Comment (optional)</Label>
                                  <textarea
                                    id="gmail_fwd_comment"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px]"
                                    placeholder="Add a note before the forwarded content"
                                    value={(nodeConfig as ActionNodeData).params?.comment as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, comment: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: GitHub create_issue */}
                            {nodeConfig.serviceId === 'github' && nodeConfig.actionId === 'create_issue' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="github_issue_repo_owner">Repository Owner</Label>
                                  <Input
                                    id="github_issue_repo_owner"
                                    type="text"
                                    placeholder="e.g., octocat"
                                    value={(nodeConfig as ActionNodeData).params?.repo_owner as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_owner: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_issue_repo_name">Repository Name</Label>
                                  <Input
                                    id="github_issue_repo_name"
                                    type="text"
                                    placeholder="e.g., Hello-World"
                                    value={(nodeConfig as ActionNodeData).params?.repo_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_issue_title">Issue Title</Label>
                                  <Input
                                    id="github_issue_title"
                                    type="text"
                                    placeholder="e.g., Bug in authentication"
                                    value={(nodeConfig as ActionNodeData).params?.title as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, title: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_issue_body">Issue Body</Label>
                                  <textarea
                                    id="github_issue_body"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Describe the issue... (supports variables)"
                                    value={(nodeConfig as ActionNodeData).params?.body as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, body: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_issue_labels">Labels (optional, comma-separated)</Label>
                                  <Input
                                    id="github_issue_labels"
                                    type="text"
                                    placeholder="bug, help wanted"
                                    value={(nodeConfig as ActionNodeData).params?.labels as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const labels = e.target.value ? e.target.value.split(',').map(l => l.trim()) : [];
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, labels } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: GitHub add_comment */}
                            {nodeConfig.serviceId === 'github' && nodeConfig.actionId === 'add_comment' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="github_comment_repo_owner">Repository Owner</Label>
                                  <Input
                                    id="github_comment_repo_owner"
                                    type="text"
                                    placeholder="e.g., octocat"
                                    value={(nodeConfig as ActionNodeData).params?.repo_owner as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_owner: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_comment_repo_name">Repository Name</Label>
                                  <Input
                                    id="github_comment_repo_name"
                                    type="text"
                                    placeholder="e.g., Hello-World"
                                    value={(nodeConfig as ActionNodeData).params?.repo_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_comment_issue_number">Issue/PR Number</Label>
                                  <Input
                                    id="github_comment_issue_number"
                                    type="text"
                                    placeholder="e.g., 42 or {{github.issue_number}}"
                                    value={(nodeConfig as ActionNodeData).params?.issue_number as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, issue_number: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Use issue/PR number or variable from trigger</p>
                                </div>
                                <div>
                                  <Label htmlFor="github_comment_body">Comment</Label>
                                  <textarea
                                    id="github_comment_body"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Your comment... (supports variables)"
                                    value={(nodeConfig as ActionNodeData).params?.body as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, body: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: GitHub close_issue */}
                            {nodeConfig.serviceId === 'github' && nodeConfig.actionId === 'close_issue' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="github_close_repo_owner">Repository Owner</Label>
                                  <Input
                                    id="github_close_repo_owner"
                                    type="text"
                                    placeholder="e.g., octocat"
                                    value={(nodeConfig as ActionNodeData).params?.repo_owner as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_owner: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_close_repo_name">Repository Name</Label>
                                  <Input
                                    id="github_close_repo_name"
                                    type="text"
                                    placeholder="e.g., Hello-World"
                                    value={(nodeConfig as ActionNodeData).params?.repo_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_close_issue_number">Issue Number</Label>
                                  <Input
                                    id="github_close_issue_number"
                                    type="text"
                                    placeholder="e.g., 42 or {{github.issue_number}}"
                                    value={(nodeConfig as ActionNodeData).params?.issue_number as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, issue_number: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Use issue number or variable from trigger</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: GitHub add_label */}
                            {nodeConfig.serviceId === 'github' && nodeConfig.actionId === 'add_label' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="github_label_repo_owner">Repository Owner</Label>
                                  <Input
                                    id="github_label_repo_owner"
                                    type="text"
                                    placeholder="e.g., octocat"
                                    value={(nodeConfig as ActionNodeData).params?.repo_owner as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_owner: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_label_repo_name">Repository Name</Label>
                                  <Input
                                    id="github_label_repo_name"
                                    type="text"
                                    placeholder="e.g., Hello-World"
                                    value={(nodeConfig as ActionNodeData).params?.repo_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_label_issue_number">Issue/PR Number</Label>
                                  <Input
                                    id="github_label_issue_number"
                                    type="text"
                                    placeholder="e.g., 42 or {{github.issue_number}}"
                                    value={(nodeConfig as ActionNodeData).params?.issue_number as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, issue_number: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Use issue/PR number or variable from trigger</p>
                                </div>
                                <div>
                                  <Label htmlFor="github_label_labels">Labels (comma-separated)</Label>
                                  <Input
                                    id="github_label_labels"
                                    type="text"
                                    placeholder="bug, enhancement"
                                    value={(nodeConfig as ActionNodeData).params?.labels as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const labels = e.target.value ? e.target.value.split(',').map(l => l.trim()) : [];
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, labels } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: GitHub create_branch */}
                            {nodeConfig.serviceId === 'github' && nodeConfig.actionId === 'create_branch' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="github_branch_repo_owner">Repository Owner</Label>
                                  <Input
                                    id="github_branch_repo_owner"
                                    type="text"
                                    placeholder="e.g., octocat"
                                    value={(nodeConfig as ActionNodeData).params?.repo_owner as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_owner: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_branch_repo_name">Repository Name</Label>
                                  <Input
                                    id="github_branch_repo_name"
                                    type="text"
                                    placeholder="e.g., Hello-World"
                                    value={(nodeConfig as ActionNodeData).params?.repo_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, repo_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_branch_name">New Branch Name</Label>
                                  <Input
                                    id="github_branch_name"
                                    type="text"
                                    placeholder="e.g., feature-123"
                                    value={(nodeConfig as ActionNodeData).params?.branch_name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, branch_name: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="github_from_branch">From Branch (optional)</Label>
                                  <Input
                                    id="github_from_branch"
                                    type="text"
                                    placeholder="main (default)"
                                    value={(nodeConfig as ActionNodeData).params?.from_branch as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, from_branch: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Default: main</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Weather get_current_weather */}
                            {nodeConfig.serviceId === 'weather' && nodeConfig.actionId === 'get_current_weather' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="weather_location">Location (City)</Label>
                                  <Input
                                    id="weather_location"
                                    type="text"
                                    placeholder="e.g., Paris,FR or London,UK"
                                    value={(nodeConfig as ActionNodeData).params?.location as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value;
                                      // Only clear lat/lon if a non-empty location is entered
                                      if (value && value.trim()) {
                                        onNodeConfigChange(selectedNodeId, { 
                                          ...nodeConfig, 
                                          params: { ...currentParams, location: value, lat: undefined, lon: undefined } 
                                        } as ActionNodeData);
                                      } else {
                                        onNodeConfigChange(selectedNodeId, { 
                                          ...nodeConfig, 
                                          params: { ...currentParams, location: value } 
                                        } as ActionNodeData);
                                      }
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">City name with country code (e.g., Paris,FR) or leave empty to use coordinates below</p>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                  <div>
                                    <Label htmlFor="weather_lat">Latitude (optional)</Label>
                                    <Input
                                      id="weather_lat"
                                      type="number"
                                      step="0.0001"
                                      placeholder="e.g., 48.8566"
                                      value={(nodeConfig as ActionNodeData).params?.lat as number || ''}
                                      onChange={(e) => {
                                        const currentParams = (nodeConfig as ActionNodeData).params || {};
                                        const value = e.target.value ? parseFloat(e.target.value) : undefined;
                                        // Only clear location if we have a valid latitude value
                                        if (value !== undefined && !isNaN(value)) {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lat: value, location: undefined } 
                                          } as ActionNodeData);
                                        } else {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lat: value } 
                                          } as ActionNodeData);
                                        }
                                      }}
                                      onFocus={handleInputFocus}
                                    />
                                  </div>
                                  <div>
                                    <Label htmlFor="weather_lon">Longitude (optional)</Label>
                                    <Input
                                      id="weather_lon"
                                      type="number"
                                      step="0.0001"
                                      placeholder="e.g., 2.3522"
                                      value={(nodeConfig as ActionNodeData).params?.lon as number || ''}
                                      onChange={(e) => {
                                        const currentParams = (nodeConfig as ActionNodeData).params || {};
                                        const value = e.target.value ? parseFloat(e.target.value) : undefined;
                                        // Only clear location if we have a valid longitude value
                                        if (value !== undefined && !isNaN(value)) {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lon: value, location: undefined } 
                                          } as ActionNodeData);
                                        } else {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lon: value } 
                                          } as ActionNodeData);
                                        }
                                      }}
                                      onFocus={handleInputFocus}
                                    />
                                  </div>
                                </div>
                                <div>
                                  <Label htmlFor="weather_units">Units</Label>
                                  <Select
                                    value={(nodeConfig as ActionNodeData).params?.units as string || 'metric'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, units: value } 
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="weather_units">
                                      <SelectValue placeholder="Select units" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="metric">Metric (°C, m/s)</SelectItem>
                                      <SelectItem value="imperial">Imperial (°F, mph)</SelectItem>
                                      <SelectItem value="standard">Standard (Kelvin)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <p className="text-xs text-gray-500 mt-1">Temperature and wind speed units</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Weather get_forecast */}
                            {nodeConfig.serviceId === 'weather' && nodeConfig.actionId === 'get_forecast' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="forecast_location">Location (City)</Label>
                                  <Input
                                    id="forecast_location"
                                    type="text"
                                    placeholder="e.g., Tokyo,JP or Berlin,DE"
                                    value={(nodeConfig as ActionNodeData).params?.location as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value;
                                      // Only clear lat/lon if a non-empty location is entered
                                      if (value && value.trim()) {
                                        onNodeConfigChange(selectedNodeId, { 
                                          ...nodeConfig, 
                                          params: { ...currentParams, location: value, lat: undefined, lon: undefined } 
                                        } as ActionNodeData);
                                      } else {
                                        onNodeConfigChange(selectedNodeId, { 
                                          ...nodeConfig, 
                                          params: { ...currentParams, location: value } 
                                        } as ActionNodeData);
                                      }
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">City name with country code or use coordinates below</p>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                  <div>
                                    <Label htmlFor="forecast_lat">Latitude (optional)</Label>
                                    <Input
                                      id="forecast_lat"
                                      type="number"
                                      step="0.0001"
                                      placeholder="e.g., 35.6762"
                                      value={(nodeConfig as ActionNodeData).params?.lat as number || ''}
                                      onChange={(e) => {
                                        const currentParams = (nodeConfig as ActionNodeData).params || {};
                                        const value = e.target.value ? parseFloat(e.target.value) : undefined;
                                        // Only clear location if we have a valid latitude value
                                        if (value !== undefined && !isNaN(value)) {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lat: value, location: undefined } 
                                          } as ActionNodeData);
                                        } else {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lat: value } 
                                          } as ActionNodeData);
                                        }
                                      }}
                                      onFocus={handleInputFocus}
                                    />
                                  </div>
                                  <div>
                                    <Label htmlFor="forecast_lon">Longitude (optional)</Label>
                                    <Input
                                      id="forecast_lon"
                                      type="number"
                                      step="0.0001"
                                      placeholder="e.g., 139.6503"
                                      value={(nodeConfig as ActionNodeData).params?.lon as number || ''}
                                      onChange={(e) => {
                                        const currentParams = (nodeConfig as ActionNodeData).params || {};
                                        const value = e.target.value ? parseFloat(e.target.value) : undefined;
                                        // Only clear location if we have a valid longitude value
                                        if (value !== undefined && !isNaN(value)) {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lon: value, location: undefined } 
                                          } as ActionNodeData);
                                        } else {
                                          onNodeConfigChange(selectedNodeId, { 
                                            ...nodeConfig, 
                                            params: { ...currentParams, lon: value } 
                                          } as ActionNodeData);
                                        }
                                      }}
                                      onFocus={handleInputFocus}
                                    />
                                  </div>
                                </div>
                                <div>
                                  <Label htmlFor="forecast_units">Units</Label>
                                  <Select
                                    value={(nodeConfig as ActionNodeData).params?.units as string || 'metric'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, units: value } 
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="forecast_units">
                                      <SelectValue placeholder="Select units" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="metric">Metric (°C, m/s)</SelectItem>
                                      <SelectItem value="imperial">Imperial (°F, mph)</SelectItem>
                                      <SelectItem value="standard">Standard (Kelvin)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                                <div>
                                  <Label htmlFor="forecast_cnt">Number of Forecasts (optional)</Label>
                                  <Input
                                    id="forecast_cnt"
                                    type="number"
                                    min="1"
                                    max="40"
                                    placeholder="e.g., 8 (default: all available)"
                                    value={(nodeConfig as ActionNodeData).params?.cnt as number || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value ? parseInt(e.target.value) : undefined;
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, cnt: value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Max 40 entries (3-hour intervals). Leave empty for all.</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: OpenAI chat completion */}
                            {nodeConfig.serviceId === 'openai' && nodeConfig.actionId === 'chat' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="openai_prompt">Prompt</Label>
                                  <textarea
                                    id="openai_prompt"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Enter your prompt (supports variables like {{gmail.subject}})"
                                    value={(nodeConfig as ActionNodeData).params?.prompt as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, prompt: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The message or question to send to ChatGPT</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_model">Model (optional)</Label>
                                  <Select
                                    value={(nodeConfig as ActionNodeData).params?.model as string || 'gpt-3.5-turbo'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, model: value } 
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="openai_model">
                                      <SelectValue placeholder="Select model" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                                      <SelectItem value="gpt-4">GPT-4</SelectItem>
                                      <SelectItem value="gpt-4-turbo-preview">GPT-4 Turbo</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <p className="text-xs text-gray-500 mt-1">Default: gpt-3.5-turbo</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_max_tokens">Max Tokens (optional)</Label>
                                  <Input
                                    id="openai_max_tokens"
                                    type="number"
                                    min="1"
                                    max="4000"
                                    placeholder="500"
                                    value={(nodeConfig as ActionNodeData).params?.max_tokens as number || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value ? parseInt(e.target.value) : undefined;
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, max_tokens: value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Maximum length of the response (default: 500)</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_temperature">Temperature (optional)</Label>
                                  <Input
                                    id="openai_temperature"
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="2"
                                    placeholder="0.7"
                                    value={(nodeConfig as ActionNodeData).params?.temperature as number || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value ? parseFloat(e.target.value) : undefined;
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, temperature: value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">0 = focused, 2 = creative (default: 0.7)</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_system_prompt">System Prompt (optional)</Label>
                                  <textarea
                                    id="openai_system_prompt"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px]"
                                    placeholder="You are a helpful assistant..."
                                    value={(nodeConfig as ActionNodeData).params?.system_prompt as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, system_prompt: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Set the AI&apos;s behavior and context</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: OpenAI text completion */}
                            {nodeConfig.serviceId === 'openai' && nodeConfig.actionId === 'complete_text' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="openai_text_prompt">Prompt</Label>
                                  <textarea
                                    id="openai_text_prompt"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Enter text to complete..."
                                    value={(nodeConfig as ActionNodeData).params?.prompt as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, prompt: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_text_model">Model (optional)</Label>
                                  <Input
                                    id="openai_text_model"
                                    type="text"
                                    placeholder="gpt-3.5-turbo-instruct"
                                    value={(nodeConfig as ActionNodeData).params?.model as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, model: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Default: gpt-3.5-turbo-instruct</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_text_max_tokens">Max Tokens (optional)</Label>
                                  <Input
                                    id="openai_text_max_tokens"
                                    type="number"
                                    min="1"
                                    placeholder="256"
                                    value={(nodeConfig as ActionNodeData).params?.max_tokens as number || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value ? parseInt(e.target.value) : undefined;
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, max_tokens: value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Action params: OpenAI image generation */}
                            {nodeConfig.serviceId === 'openai' && nodeConfig.actionId === 'generate_image' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="openai_image_prompt">Image Description</Label>
                                  <textarea
                                    id="openai_image_prompt"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="A cute cat playing with a ball of yarn..."
                                    value={(nodeConfig as ActionNodeData).params?.prompt as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, prompt: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Describe the image you want to generate</p>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_image_size">Image Size</Label>
                                  <Select
                                    value={(nodeConfig as ActionNodeData).params?.size as string || '1024x1024'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, size: value } 
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="openai_image_size">
                                      <SelectValue placeholder="Select size" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="256x256">256x256 (Small)</SelectItem>
                                      <SelectItem value="512x512">512x512 (Medium)</SelectItem>
                                      <SelectItem value="1024x1024">1024x1024 (Large)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                                
                                <div>
                                  <Label htmlFor="openai_image_n">Number of Images</Label>
                                  <Input
                                    id="openai_image_n"
                                    type="number"
                                    min="1"
                                    max="10"
                                    placeholder="1"
                                    value={(nodeConfig as ActionNodeData).params?.n as number || 1}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      const value = e.target.value ? parseInt(e.target.value) : 1;
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, n: value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Generate 1-10 images (default: 1)</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: OpenAI content moderation */}
                            {nodeConfig.serviceId === 'openai' && nodeConfig.actionId === 'analyze_text' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="openai_moderate_input">Content to Moderate</Label>
                                  <textarea
                                    id="openai_moderate_input"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Enter content to analyze (supports variables like {{gmail.body}})"
                                    value={(nodeConfig as ActionNodeData).params?.input as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, input: e.target.value }
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Text to check for policy violations</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Discord send_message */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'send_message' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="discord_channel_id">Channel ID</Label>
                                  <Input
                                    id="discord_channel_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.channel_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, channel_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the Discord channel to send the message to</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_message">Message</Label>
                                  <textarea
                                    id="discord_message"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Enter message (supports variables like {{gmail.subject}})"
                                    value={(nodeConfig as ActionNodeData).params?.message as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, message: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Message content to send to the channel</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Discord send_dm */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'send_dm' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="discord_dm_user_id">User ID</Label>
                                  <Input
                                    id="discord_dm_user_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.user_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, user_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the Discord user to send a direct message to</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_dm_message">Message</Label>
                                  <textarea
                                    id="discord_dm_message"
                                    className="w-full p-2 border rounded mt-1 min-h-[100px]"
                                    placeholder="Enter message (supports variables like {{gmail.subject}})"
                                    value={(nodeConfig as ActionNodeData).params?.message as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, message: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Direct message content to send to the user</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Discord add_role */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'add_role' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="discord_guild_id">Server (Guild) ID</Label>
                                  <Input
                                    id="discord_guild_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.guild_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, guild_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the Discord server (guild)</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_role_user_id">User ID</Label>
                                  <Input
                                    id="discord_role_user_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.user_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, user_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the user to assign the role to</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_role_id">Role ID</Label>
                                  <Input
                                    id="discord_role_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.role_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, role_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the role to assign</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Discord create_channel */}
                            {nodeConfig.serviceId === 'discord' && nodeConfig.actionId === 'create_channel' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="discord_create_guild_id">Server (Guild) ID</Label>
                                  <Input
                                    id="discord_create_guild_id"
                                    type="text"
                                    placeholder="e.g., 123456789012345678"
                                    value={(nodeConfig as ActionNodeData).params?.guild_id as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, guild_id: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The ID of the Discord server (guild) where the channel will be created</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_channel_name">Channel Name</Label>
                                  <Input
                                    id="discord_channel_name"
                                    type="text"
                                    placeholder="e.g., new-announcements (supports variables)"
                                    value={(nodeConfig as ActionNodeData).params?.name as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, name: e.target.value } 
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Name for the new channel (supports variable templates)</p>
                                </div>
                                <div>
                                  <Label htmlFor="discord_channel_type">Channel Type</Label>
                                  <Select
                                    value={String((nodeConfig as ActionNodeData).params?.type || '0')}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { 
                                        ...nodeConfig, 
                                        params: { ...currentParams, type: parseInt(value) } 
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="discord_channel_type">
                                      <SelectValue placeholder="Select channel type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="0">Text Channel</SelectItem>
                                      <SelectItem value="2">Voice Channel</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <p className="text-xs text-gray-500 mt-1">Type of channel to create</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: Google Calendar quick_add_event */}
                            {nodeConfig.serviceId === 'google_calendar' && nodeConfig.actionId === 'quick_add_event' && (
                              <div>
                                <Label htmlFor="calendar_quick_text">Natural Language Event</Label>
                                <Input
                                  id="calendar_quick_text"
                                  type="text"
                                  placeholder="Meeting tomorrow at 3pm"
                                  value={(nodeConfig as ActionNodeData).params?.text as string || ''}
                                  onChange={(e) => {
                                    const currentParams = (nodeConfig as ActionNodeData).params || {};
                                    onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, text: e.target.value } } as ActionNodeData);
                                  }}
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Use natural language like &ldquo;Lunch with John tomorrow at 12pm&rdquo;</p>
                              </div>
                            )}

                            {/* Action params: DeepL translate */}
                            {nodeConfig.serviceId === 'deepl' && nodeConfig.actionId === 'translate' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="deepl_source_lang">Source Language</Label>
                                  <Input
                                    id="deepl_source_lang"
                                    type="text"
                                    placeholder="EN"
                                    value={(nodeConfig as ActionNodeData).params?.source_lang as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, source_lang: e.target.value.toUpperCase() } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Source language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</p>
                                </div>
                                <div>
                                  <Label htmlFor="deepl_target_lang">Target Language</Label>
                                  <Input
                                    id="deepl_target_lang"
                                    type="text"
                                    placeholder="FR"
                                    value={(nodeConfig as ActionNodeData).params?.target_lang as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, target_lang: e.target.value.toUpperCase() } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Target language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</p>
                                </div>
                                <div>
                                  <Label htmlFor="deepl_text">Text to Translate</Label>
                                  <textarea
                                    id="deepl_text"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px] font-mono text-sm"
                                    placeholder="Enter text or use variables like {{gmail.body}}"
                                    value={(nodeConfig as ActionNodeData).params?.text as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, text: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The text to translate. You can use variables from previous steps.</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: DeepL auto_translate */}
                            {nodeConfig.serviceId === 'deepl' && nodeConfig.actionId === 'auto_translate' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="deepl_auto_target_lang">Target Language</Label>
                                  <Input
                                    id="deepl_auto_target_lang"
                                    type="text"
                                    placeholder="FR"
                                    value={(nodeConfig as ActionNodeData).params?.target_lang as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, target_lang: e.target.value.toUpperCase() } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Target language code (e.g., EN, FR, DE, ES, IT, JA, ZH)</p>
                                </div>
                                <div>
                                  <Label htmlFor="deepl_auto_text">Text to Translate</Label>
                                  <textarea
                                    id="deepl_auto_text"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px] font-mono text-sm"
                                    placeholder="Enter text or use variables like {{gmail.body}}"
                                    value={(nodeConfig as ActionNodeData).params?.text as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, text: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The text to translate. Source language will be detected automatically.</p>
                                </div>
                              </div>
                            )}

                            {/* Action params: DeepL detect_language */}
                            {nodeConfig.serviceId === 'deepl' && nodeConfig.actionId === 'detect_language' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="deepl_detect_text">Text to Analyze</Label>
                                  <textarea
                                    id="deepl_detect_text"
                                    className="w-full p-2 border rounded mt-1 min-h-[80px] font-mono text-sm"
                                    placeholder="Enter text or use variables like {{gmail.body}}"
                                    value={(nodeConfig as ActionNodeData).params?.text as string || ''}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, text: e.target.value } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">The text to detect the language from.</p>
                                </div>
                                <div>
                                  <Label htmlFor="deepl_sample_length">Sample Length (optional)</Label>
                                  <Input
                                    id="deepl_sample_length"
                                    type="number"
                                    min="10"
                                    max="500"
                                    placeholder="100"
                                    value={(nodeConfig as ActionNodeData).params?.sample_length as number || 100}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, { ...nodeConfig, params: { ...currentParams, sample_length: parseInt(e.target.value) || 100 } } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                  <p className="text-xs text-gray-500 mt-1">Number of characters to analyze (default: 100). Helps save API quota.</p>
                                </div>
                              </div>
                            )}

                            {/* Specific configuration for delay service when used as an action */}
                            {nodeConfig.serviceId === 'delay' && nodeConfig.actionId === 'wait' && (
                              <div className="space-y-3">
                                <div>
                                  <Label htmlFor="delay_duration">Duration</Label>
                                  <Input
                                    id="delay_duration"
                                    type="number"
                                    min="1"
                                    placeholder="e.g. 30"
                                    value={(nodeConfig as ActionNodeData).params?.duration as number || 1}
                                    onChange={(e) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, duration: parseInt(e.target.value) || 1 }
                                      } as ActionNodeData);
                                    }}
                                    onFocus={handleInputFocus}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="delay_unit">Unit</Label>
                                  <Select
                                    value={(nodeConfig as ActionNodeData).params?.unit as string || 'seconds'}
                                    onValueChange={(value) => {
                                      const currentParams = (nodeConfig as ActionNodeData).params || {};
                                      onNodeConfigChange(selectedNodeId, {
                                        ...nodeConfig,
                                        params: { ...currentParams, unit: value }
                                      } as ActionNodeData);
                                    }}
                                  >
                                    <SelectTrigger id="delay_unit">
                                      <SelectValue placeholder="Select unit" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="seconds">Seconds</SelectItem>
                                      <SelectItem value="minutes">Minutes</SelectItem>
                                      <SelectItem value="hours">Hours</SelectItem>
                                      <SelectItem value="days">Days</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>
                            )}
                            
                            <VariablePicker
                              availableVariables={getPropagatedVariables(selectedNodeId)}
                              onInsertVariable={handleInsertVariable}
                            />
                          </>
                        )}
                      </div>
                    </>
                  )}

                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default ControlsPanel;
