import React, { useRef, useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import VariablePicker from '@/components/VariablePicker';
import { AreaStepNodeData, NodeData, ConditionNodeData, TriggerNodeData, ActionNodeData, isDelayNode, isActionNode, isTriggerNode } from './node-types';
import { requestJson } from '@/lib/api';
import { useRequireAuth } from '@/hooks/use-auth';

interface ControlsPanelProps {
  onAddNode: (type: 'trigger' | 'action' | 'condition' | 'delay') => void;
  selectedNodeId?: string;
  onNodeConfigChange?: (id: string, config: Partial<NodeData>) => void;
  nodeConfig?: Partial<NodeData>;
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
  nodeConfig
}) => {
  // Auth hook to get token
  const auth = useRequireAuth();

  // Refs for tracking currently focused input fields
  const focusedInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  // State for available services
  const [services, setServices] = useState<ServiceCatalog[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  const [connectedServices, setConnectedServices] = useState<string[]>([]);

  // Fetch services and user connections on mount
  useEffect(() => {
    const fetchData = async () => {
      if (!auth.token) return;

      setLoadingServices(true);
      try {
        // Fetch both services catalog and user connections
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

  // Function to handle input focus
  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    focusedInputRef.current = e.target;
  };

  // Function to insert variable at cursor position in focused input
  const handleInsertVariable = (variableId: string) => {
    if (focusedInputRef.current) {
      const input = focusedInputRef.current;
      const start = input.selectionStart || 0;
      const end = input.selectionEnd || 0;
      const currentValue = input.value;
      const variableTemplate = `{{${variableId}}}`;
      
      // Insert the variable template at cursor position
      const newValue = 
        currentValue.substring(0, start) + 
        variableTemplate + 
        currentValue.substring(end);
      
      // Update the input value
      input.value = newValue;
      
      // Set cursor position after the inserted variable (only for text inputs)
      // Note: setSelectionRange() doesn't work on number inputs
      const inputElement = input as HTMLInputElement;
      if (inputElement.type !== 'number') {
        const newCursorPosition = start + variableTemplate.length;
        input.setSelectionRange(newCursorPosition, newCursorPosition);
      }
      
      // Trigger change event to update React state
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };

  return (
    <div className="w-80 h-full bg-card border-l overflow-y-auto px-3 py-4 flex flex-col gap-3">
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
                              {services.map((service) => (
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
                            {/* Built-in services and services with shared API keys do not require per-user connection */}
                            {!['debug', 'time', 'delay', 'weather'].includes(nodeConfig.serviceId) && !connectedServices.includes(nodeConfig.serviceId) && (
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

                            {/* Trigger params: Gmail new_email_from_sender requires sender_email */}
                            {nodeConfig.serviceId === 'gmail' && nodeConfig.actionId === 'new_email_from_sender' && (
                              <div>
                                <Label htmlFor="gmail_sender_email">Sender Email</Label>
                                <Input
                                  id="gmail_sender_email"
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
                          </>
                        )}
                      </div>
                    </>
                  )}

                  {/* Condition-specific fields */}
                  {nodeConfig.type === 'condition' && (() => {
                    const conditionData = nodeConfig as Partial<ConditionNodeData>;
                    const conditionType = conditionData.conditionType || 'simple';
                    const conditionConfig = conditionData.config || {};

                    return (
                      <>
                        <Separator className="my-3" />
                        <div className="space-y-3">
                          <div>
                            <Label htmlFor="conditionType">Condition Type</Label>
                            <Select
                              value={conditionType}
                              onValueChange={(value: 'simple' | 'expression') =>
                                onNodeConfigChange(selectedNodeId, {
                                  ...conditionData,
                                  conditionType: value,
                                  config: { ...conditionConfig }
                                } as AreaStepNodeData)
                              }
                            >
                              <SelectTrigger id="conditionType">
                                <SelectValue placeholder="Select condition type" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="simple">Simple Comparison</SelectItem>
                                <SelectItem value="expression">Expression</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {conditionType === 'simple' ? (
                            <>
                              <div>
                                <Label htmlFor="field">Field / Variable</Label>
                                <Input
                                  id="field"
                                  type="text"
                                  placeholder="e.g., trigger.minute"
                                  value={(conditionConfig.field as string) || ''}
                                  onChange={(e) =>
                                    onNodeConfigChange(selectedNodeId, {
                                      ...conditionData,
                                      config: { ...conditionConfig, field: e.target.value }
                                    } as AreaStepNodeData)
                                  }
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Use dot notation for nested values</p>
                              </div>

                              <div>
                                <Label htmlFor="operator">Operator</Label>
                                <Select
                                  value={(conditionConfig.operator as string) || 'eq'}
                                  onValueChange={(value) =>
                                    onNodeConfigChange(selectedNodeId, {
                                      ...conditionData,
                                      config: { ...conditionConfig, operator: value }
                                    } as AreaStepNodeData)
                                  }
                                >
                                  <SelectTrigger id="operator">
                                    <SelectValue placeholder="Select operator" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="eq">== (equals)</SelectItem>
                                    <SelectItem value="ne">!= (not equals)</SelectItem>
                                    <SelectItem value="gt">&gt; (greater than)</SelectItem>
                                    <SelectItem value="lt">&lt; (less than)</SelectItem>
                                    <SelectItem value="gte">&gt;= (greater or equal)</SelectItem>
                                    <SelectItem value="lte">&lt;= (less or equal)</SelectItem>
                                    <SelectItem value="contains">contains</SelectItem>
                                    <SelectItem value="startswith">starts with</SelectItem>
                                    <SelectItem value="endswith">ends with</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>

                              <div>
                                <Label htmlFor="value">Expected Value</Label>
                                <Input
                                  id="value"
                                  type="text"
                                  placeholder="e.g., 0"
                                  value={(conditionConfig.value as string) || ''}
                                  onChange={(e) =>
                                    onNodeConfigChange(selectedNodeId, {
                                      ...conditionData,
                                      config: { ...conditionConfig, value: e.target.value }
                                    } as AreaStepNodeData)
                                  }
                                  onFocus={handleInputFocus}
                                />
                                <p className="text-xs text-gray-500 mt-1">Numbers will be auto-converted</p>
                              </div>
                            </>
                          ) : (
                            <div>
                              <Label htmlFor="expression">Expression</Label>
                              <textarea
                                id="expression"
                                className="w-full p-2 border rounded mt-1 min-h-[80px] font-mono text-sm"
                                placeholder="e.g., trigger.minute % 2 == 0"
                                value={(conditionConfig.expression as string) || ''}
                                onChange={(e) =>
                                  onNodeConfigChange(selectedNodeId, {
                                    ...conditionData,
                                    config: { ...conditionConfig, expression: e.target.value }
                                  } as AreaStepNodeData)
                                }
                                onFocus={handleInputFocus}
                              />
                              <p className="text-xs text-gray-500 mt-1">
                                Write a Python-like expression that evaluates to True/False
                              </p>
                            </div>
                          )}
                        </div>
                      </>
                    );
                  })()}

                  {/* Delay-specific configuration */}
                  {isDelayNode(nodeConfig) && (
                    <>
                      <Separator className="my-3" />
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="duration">Duration</Label>
                          <Input
                            id="duration"
                            type="number"
                            min="1"
                            value={nodeConfig.duration || 1}
                            onChange={(e) => {
                              const newDuration = parseInt(e.target.value, 10) || 1;
                              onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, duration: newDuration });
                            }}
                            onFocus={handleInputFocus}
                          />
                        </div>
                        <div>
                          <Label htmlFor="unit">Unit</Label>
                          <Select
                            value={nodeConfig.unit || 'seconds'}
                            onValueChange={(value) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, unit: value as 'seconds' | 'minutes' | 'hours' | 'days' })}
                          >
                            <SelectTrigger id="unit">
                              <SelectValue placeholder="Select time unit" />
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
                    </>
                  )}

                  {/* Action-specific configuration with VariablePicker */}
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
                              } as AreaStepNodeData);
                            }}
                            disabled={loadingServices}
                          >
                            <SelectTrigger id="actionService">
                              <SelectValue placeholder={loadingServices ? "Loading..." : "Select a service"} />
                            </SelectTrigger>
                            <SelectContent>
                              {services.map((service) => (
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
                            {/* Built-in services and services with shared API keys do not require per-user connection */}
                            {!['debug', 'time', 'delay', 'weather'].includes(nodeConfig.serviceId) && !connectedServices.includes(nodeConfig.serviceId) && (
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

                            <VariablePicker
                              availableVariables={[
                                { id: 'now', name: 'Current Time', description: 'The time when the trigger fired', category: 'Trigger', type: 'text' as const },
                                { id: 'user_id', name: 'User ID', description: 'The ID of the user who triggered the action', category: 'Trigger', type: 'text' as const },
                                { id: 'area_id', name: 'Area ID', description: 'The ID of the automation area', category: 'Trigger', type: 'text' as const },
                                // Add more based on the service
                                ...(nodeConfig.serviceId === 'gmail' ? [
                                  { id: 'gmail.sender', name: 'Email Sender', description: 'The sender of the email', category: 'Gmail', type: 'text' as const },
                                  { id: 'gmail.subject', name: 'Email Subject', description: 'The subject of the email', category: 'Gmail', type: 'text' as const },
                                  { id: 'gmail.body', name: 'Email Body', description: 'The body content of the email', category: 'Gmail', type: 'text' as const },
                                  { id: 'gmail.message_id', name: 'Message ID', description: 'The Gmail message ID', category: 'Gmail', type: 'text' as const },
                                  { id: 'gmail.thread_id', name: 'Thread ID', description: 'The Gmail thread ID', category: 'Gmail', type: 'text' as const },
                                  { id: 'gmail.snippet', name: 'Snippet', description: 'A short preview of the email', category: 'Gmail', type: 'text' as const },
                                ] : []),
                                ...(nodeConfig.serviceId === 'openai' ? [
                                  { id: 'openai.response', name: 'AI Response', description: 'The generated text from OpenAI', category: 'OpenAI', type: 'text' as const },
                                  { id: 'openai.image_urls', name: 'Image URLs', description: 'Generated image URLs (DALL-E)', category: 'OpenAI', type: 'text' as const },
                                  { id: 'openai.moderation.flagged', name: 'Content Flagged', description: 'Whether content was flagged', category: 'OpenAI', type: 'text' as const },
                                  { id: 'openai.input_tokens', name: 'Input Tokens', description: 'Number of tokens in prompt', category: 'OpenAI', type: 'text' as const },
                                  { id: 'openai.output_tokens', name: 'Output Tokens', description: 'Number of tokens in response', category: 'OpenAI', type: 'text' as const },
                                ] : []),
                              ]}
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
