import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

import { NodeData, isDelayNode } from './node-types';

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
              {/* Configuration UI would be implemented here based on the selected node type */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {nodeConfig ? 'Configuration options for selected node' : 'Select a node to configure'}
              </div>
              
              {/* Placeholder configuration fields - these would be dynamic based on node type */}
              {nodeConfig && (
                <div className="mt-4 space-y-3">
                  <div>
                    <label className="text-sm font-medium">Step Label</label>
                    <input
                      type="text"
                      className="w-full p-2 border rounded mt-1"
                      value={nodeConfig.label || ''}
                      onChange={(e) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, label: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Description</label>
                    <textarea
                      className="w-full p-2 border rounded mt-1"
                      value={nodeConfig.description || ''}
                      onChange={(e) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, description: e.target.value })}
                    />
                  </div>

                  {/* Delay-specific configuration */}
                  {isDelayNode(nodeConfig) && (
                    <>
                      <div>
                        <label className="text-sm font-medium">Duration</label>
                        <input
                          type="number"
                          min="1"
                          className="w-full p-2 border rounded mt-1"
                          value={nodeConfig.duration || 1}
                          onChange={(e) => {
                            const newDuration = parseInt(e.target.value, 10) || 1;
                            onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, duration: newDuration });
                          }}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Unit</label>
                        <select
                          className="w-full p-2 border rounded mt-1"
                          value={nodeConfig.unit || 'seconds'}
                          onChange={(e) => onNodeConfigChange?.(selectedNodeId, { ...nodeConfig, unit: e.target.value as 'seconds' | 'minutes' | 'hours' | 'days' })}
                        >
                          <option value="seconds">Seconds</option>
                          <option value="minutes">Minutes</option>
                          <option value="hours">Hours</option>
                          <option value="days">Days</option>
                        </select>
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