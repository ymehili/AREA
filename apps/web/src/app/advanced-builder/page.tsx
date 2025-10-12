'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import AreaFlow, { type AreaFlowHandles } from '@/components/area-builder/AreaFlow';
import { Node, Edge } from 'reactflow';
import { NodeData, isTriggerNode, isActionNode } from '@/components/area-builder/node-types';
import { createAreaWithSteps, loadStoredSession, UnauthorizedError } from '@/lib/api';

const AdvancedBuilderPage = () => {
  const router = useRouter();
  const [nodes] = useState<Node<NodeData>[]>([]);
  const [edges] = useState<Edge[]>([]);
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');
  const areaFlowRef = useRef<AreaFlowHandles>(null);

  // Helper function to remove undefined values from an object
  const cleanParams = (params: Record<string, unknown> | undefined): Record<string, unknown> | undefined => {
    if (!params) return undefined;
    const cleaned: Record<string, unknown> = {};
    Object.keys(params).forEach(key => {
      const value = params[key];
      if (value !== undefined && value !== null && !(typeof value === 'number' && isNaN(value))) {
        cleaned[key] = value;
      }
    });
    return Object.keys(cleaned).length > 0 ? cleaned : undefined;
  };

  const handleSave = async () => {
    if (!areaName) {
      toast.error('Please enter an area name');
      return;
    }

    try {
      // Get the token from the stored session
      const storedSession = loadStoredSession();
      if (!storedSession || !storedSession.token) {
        toast.error('You must be logged in to create an area');
        router.push('/');
        return;
      }

      // Get the current nodes and edges directly from the flow ref to ensure we have the latest
      const currentNodes = areaFlowRef.current?.getCurrentNodes() || nodes;
      const currentEdges = areaFlowRef.current?.getCurrentEdges() || edges;

      // Find the trigger node to use as the initial trigger
      const triggerNode = currentNodes.find(node => node.type === 'trigger');
      if (!triggerNode) {
        toast.error('Please add a trigger to your area');
        return;
      }

      // Convert the flow nodes/edges to the appropriate format for the API
      // The first node should be a trigger, and we'll use it to create the area
      const triggerNodeData = triggerNode.data as NodeData;
      const firstActionNode = currentNodes.find(node => node.type === 'action');
      const firstActionData = firstActionNode?.data as NodeData | undefined;

      const areaData = {
        name: areaName,
        description: areaDescription,
        is_active: true,
        trigger_service: isTriggerNode(triggerNodeData) ? triggerNodeData.serviceId || 'manual' : 'manual',
        trigger_action: isTriggerNode(triggerNodeData) ? triggerNodeData.actionId || 'trigger' : 'trigger',
        trigger_params: isTriggerNode(triggerNodeData) ? cleanParams(triggerNodeData.params) : undefined,
        reaction_service: firstActionData && isActionNode(firstActionData) ? firstActionData.serviceId || 'manual' : 'manual',
        reaction_action: firstActionData && isActionNode(firstActionData) ? firstActionData.actionId || 'reaction' : 'reaction',
        reaction_params: firstActionData && isActionNode(firstActionData) ? cleanParams(firstActionData.params) : undefined,
        steps: currentNodes.map((node, index) => {
          const nodeData = node.data as NodeData;
          // Find edges connected to this node
          const targetEdges = currentEdges.filter(edge => edge.source === node.id).map(edge => edge.target);
          
          // Get clean params without undefined/null/NaN values
          const params = ('params' in nodeData && nodeData.params) ? cleanParams(nodeData.params as Record<string, unknown>) : undefined;
          
          return {
            step_type: node.type as 'trigger' | 'action' | 'condition' | 'delay',
            order: index,
            service: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.serviceId : null,
            action: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.actionId : null,
            config: {
              ...(nodeData.config || {}),
              // Include params in config so they're available during execution
              ...(params || {}),
              clientId: node.id,
              position: node.position,
              targets: targetEdges,
            },
          };
        }),
      };

      // Call the API to create the area with steps
      const result = await createAreaWithSteps(storedSession.token, areaData);
      console.log('Area created:', result);
      
      // Redirect to dashboard or show success message
      toast.success('Area created successfully!');
      router.push('/dashboard');
    } catch (error) {
      // Handle authentication errors specifically
      if (error instanceof UnauthorizedError) {
        toast.error('Your session has expired. Please log in again.');
        // Clear the stored session
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem('area_auth_session');
        }
        router.push('/');
        return;
      }
      
      console.error('Error creating area:', error);
      
      // Show specific error message from the API
      if (error instanceof Error) {
        toast.error(error.message);
      } else {
        toast.error('Failed to create area. Please try again.');
      }
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Advanced AREA Builder</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          Create multi-step automations with the visual flow editor
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Area Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Area Name *</label>
            <input
              type="text"
              value={areaName}
              onChange={(e) => setAreaName(e.target.value)}
              className="w-full p-2 border rounded"
              placeholder="Enter area name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={areaDescription}
              onChange={(e) => setAreaDescription(e.target.value)}
              className="w-full p-2 border rounded"
              placeholder="Enter area description"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle>Automation Flow</CardTitle>
        </CardHeader>
        <CardContent className="p-0 h-[calc(100%-60px)]">
          <AreaFlow
            ref={areaFlowRef}
            initialNodes={nodes}
            initialEdges={edges}
          />
        </CardContent>
      </Card>

      <div className="mt-6 flex justify-end space-x-4">
        <Button
          variant="outline"
          onClick={() => router.push('/dashboard')}
        >
          Cancel
        </Button>
        <Button
          onClick={handleSave}
        >
          Save AREA
        </Button>
      </div>
    </div>
  );
};

export default AdvancedBuilderPage;