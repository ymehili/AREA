import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { AreaStepNodeData, NodeData, ConditionNodeData } from './node-types';

interface ControlsPanelProps {
  onAddNode: (type: 'trigger' | 'action' | 'condition' | 'delay') => void;
  selectedNodeId?: string;
  onNodeConfigChange?: (id: string, config: Partial<AreaStepNodeData>) => void;
  nodeConfig?: Partial<NodeData>;
}

const ControlsPanel: React.FC<ControlsPanelProps> = ({
  onAddNode,
  selectedNodeId,
  onNodeConfigChange,
  nodeConfig
}) => {
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
                  <div>
                    <Label htmlFor="label">Step Label</Label>
                    <Input
                      id="label"
                      type="text"
                      value={nodeConfig.label || ''}
                      onChange={(e) => onNodeConfigChange(selectedNodeId, { ...nodeConfig, label: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <textarea
                      id="description"
                      className="w-full p-2 border rounded mt-1 min-h-[60px]"
                      value={nodeConfig.description || ''}
                      onChange={(e) => onNodeConfigChange(selectedNodeId, { ...nodeConfig, description: e.target.value })}
                    />
                  </div>

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