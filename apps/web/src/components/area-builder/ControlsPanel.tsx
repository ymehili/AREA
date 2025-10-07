import React, { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import VariablePicker from '@/components/VariablePicker';
import TriggerActionSelector from './TriggerActionSelector';
import { AreaStepNodeData, NodeData, ConditionNodeData, isDelayNode, isActionNode, isTriggerNode } from './node-types';

interface ControlsPanelProps {
  onAddNode: (type: 'trigger' | 'action' | 'condition' | 'delay') => void;
  selectedNodeId?: string;
  onNodeConfigChange?: (id: string, config: Partial<NodeData>) => void;
  nodeConfig?: Partial<NodeData>;
}

const ControlsPanel: React.FC<ControlsPanelProps> = ({
  onAddNode,
  selectedNodeId,
  onNodeConfigChange,
  nodeConfig
}) => {
  // Refs for tracking currently focused input fields
  const focusedInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  
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
      
      // Set cursor position after the inserted variable
      const newCursorPosition = start + variableTemplate.length;
      input.setSelectionRange(newCursorPosition, newCursorPosition);
      
      // Trigger change event to update React state
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };

  return (
    <div className="w-64 h-full bg-gray-50 dark:bg-gray-900/20 p-4 flex flex-col gap-4 overflow-y-auto">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Add Step</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => onAddNode('trigger')}
          >
            <Badge variant="outline" className="mr-2 bg-blue-100 text-blue-800">Trigger</Badge>
            Add Event
          </Button>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => onAddNode('action')}
          >
            <Badge variant="outline" className="mr-2 bg-green-100 text-green-800">Action</Badge>
            Add Action
          </Button>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => onAddNode('condition')}
          >
            <Badge variant="outline" className="mr-2 bg-yellow-100 text-yellow-800">Condition</Badge>
            Add If
          </Button>
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => onAddNode('delay')}
          >
            <Badge variant="outline" className="mr-2 bg-purple-100 text-purple-800">Delay</Badge>
            Add Delay
          </Button>
        </CardContent>
      </Card>

      {selectedNodeId && onNodeConfigChange && (
        <>
          <Separator />
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Configure Step</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Configuration UI based on the selected node type */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {nodeConfig ? 'Configuration options for selected node' : 'Select a node to configure'}
              </div>

              {/* Configuration fields - dynamic based on node type */}
              {nodeConfig && (
                <div className="mt-4 space-y-3">
                  {/* Trigger and Action Node Configuration - Service and Action Selection */}
                  {(isTriggerNode(nodeConfig) || isActionNode(nodeConfig)) && (
                    <TriggerActionSelector
                      nodeType={nodeConfig.type as 'trigger' | 'action'}
                      onServiceSelect={(serviceId) => {
                        onNodeConfigChange(selectedNodeId, { ...nodeConfig, serviceId, actionId: '' });
                      }}
                      onActionSelect={(actionId) => {
                        onNodeConfigChange(selectedNodeId, { ...nodeConfig, actionId });
                      }}
                      selectedServiceId={nodeConfig.serviceId}
                      selectedActionId={nodeConfig.actionId}
                      label={nodeConfig.type === 'trigger' ? 'Trigger Configuration' : 'Action Configuration'}
                      description={nodeConfig.type === 'trigger' ? 'Select the service and trigger event' : 'Select the service and action to perform'}
                    />
                  )}

                  {/* Skip Step Label and Description for Trigger/Action nodes - they will be auto-populated */}
                  {!isTriggerNode(nodeConfig) && !isActionNode(nodeConfig) && (
                    <>
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
                        <VariablePicker
                          availableVariables={[
                            { id: 'trigger.now', name: 'Current Time', description: 'The time when the trigger fired', category: 'Trigger', type: 'text' as const },
                            { id: 'trigger.user.id', name: 'User ID', description: 'The ID of the user who triggered the action', category: 'Trigger', type: 'text' as const },
                            { id: 'trigger.area.id', name: 'Area ID', description: 'The ID of the automation area', category: 'Trigger', type: 'text' as const },
                            // Add more based on the service
                            ...(nodeConfig.serviceId === 'gmail' ? [
                              { id: 'trigger.gmail.sender', name: 'Email Sender', description: 'The sender of the email', category: 'Gmail', type: 'text' as const },
                              { id: 'trigger.gmail.subject', name: 'Email Subject', description: 'The subject of the email', category: 'Gmail', type: 'text' as const },
                              { id: 'trigger.gmail.body', name: 'Email Body', description: 'The body content of the email', category: 'Gmail', type: 'text' as const },
                            ] : []),
                            ...(nodeConfig.serviceId === 'github' ? [
                              { id: 'trigger.github.repo', name: 'Repo Name', description: 'The name of the repository', category: 'GitHub', type: 'text' as const },
                              { id: 'trigger.github.issue_number', name: 'Issue Number', description: 'The number of the issue', category: 'GitHub', type: 'number' as const },
                              { id: 'trigger.github.issue_title', name: 'Issue Title', description: 'The title of the issue', category: 'GitHub', type: 'text' as const },
                            ] : []),
                          ]}
                          onInsertVariable={handleInsertVariable}
                        />
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
