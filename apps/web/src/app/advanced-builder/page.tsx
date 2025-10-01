'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import AreaFlow, { type AreaFlowHandles } from '@/components/area-builder/AreaFlow';
import { Node, Edge } from 'reactflow';
import { NodeData, isTriggerNode, isActionNode } from '@/components/area-builder/node-types';
import { createAreaWithSteps, loadStoredSession } from '@/lib/api';

const AdvancedBuilderPage = () => {
  const router = useRouter();
  const [nodes, setNodes] = useState<Node<NodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');
  const areaFlowRef = useRef<AreaFlowHandles>(null);

  const handleSave = async () => {
    if (!areaName) {
      toast.error('Please enter an area name');
      return;
    }

    try {
      // Get the token from the stored session
      const storedSession = loadStoredSession();
      if (!storedSession || !storedSession.token) {
        throw new Error('User not authenticated');
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
      const areaData = {
        name: areaName,
        description: areaDescription,
        is_active: true,
        trigger_service: (() => {
          const data = triggerNode.data as NodeData;
          return isTriggerNode(data) ? data.serviceId || 'manual' : 'manual';
        })(),
        trigger_action: (() => {
          const data = triggerNode.data as NodeData;
          return isTriggerNode(data) ? data.actionId || 'trigger' : 'trigger';
        })(),
        reaction_service: 'manual',  // We'll update this based on the last node or first action if no other reaction is found
        reaction_action: 'reaction',
        steps: currentNodes.map((node, index) => {
          const nodeData = node.data as NodeData;
          // Find edges connected to this node
          const targetEdges = currentEdges.filter(edge => edge.source === node.id).map(edge => edge.target);
          return {
            step_type: node.type as 'trigger' | 'action' | 'condition' | 'delay',
            order: index,
            service: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.serviceId : null,
            action: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.actionId : null,
            config: {
              ...(nodeData.config || {}),
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
      console.error('Error creating area:', error);
      toast.error('Failed to create area. Please try again.');
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
        <button
          onClick={() => router.push('/dashboard')}
          className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Save AREA
        </button>
      </div>
    </div>
  );
};

export default AdvancedBuilderPage;