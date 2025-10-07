"use client";

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import AreaFlow, { type AreaFlowHandles } from '@/components/area-builder/AreaFlow';
import { Node, Edge } from 'reactflow';
import { NodeData, isTriggerNode, isActionNode } from '@/components/area-builder/node-types';
import { createAreaWithSteps } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { cn, headingClasses } from '@/lib/utils';

export default function WizardPage() {
  const router = useRouter();
  const auth = useAuth();
  const [nodes] = useState<Node<NodeData>[]>([]);
  const [edges] = useState<Edge[]>([]);
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');
  const [hasSelectedNode, setHasSelectedNode] = useState(false);
  const areaFlowRef = useRef<AreaFlowHandles>(null);

  const handleDelete = () => {
    if (areaFlowRef.current) {
      areaFlowRef.current.deleteSelectedNode();
      setHasSelectedNode(false); // Reset selection state
    }
  };



  const handleSave = async () => {
    if (!areaName) {
      toast.error('Please enter an area name');
      return;
    }

    try {
      // Get the token from the stored session
      if (!auth.token) {
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

      const triggerNodeData = triggerNode.data as NodeData;
      const firstActionNode = currentNodes.find(node => node.type === 'action');
      const firstActionData = firstActionNode?.data as NodeData | undefined;

      // Convert the flow nodes/edges to the appropriate format for the API
      // The first node should be a trigger, and we'll use it to create the area
      const areaData = {
        name: areaName,
        description: areaDescription,
        is_active: true,
        trigger_service: isTriggerNode(triggerNodeData) ? triggerNodeData.serviceId || 'manual' : 'manual',
        trigger_action: isTriggerNode(triggerNodeData) ? triggerNodeData.actionId || 'trigger' : 'trigger',
        reaction_service: firstActionData && isActionNode(firstActionData) ? firstActionData.serviceId || 'manual' : 'manual',
        reaction_action: firstActionData && isActionNode(firstActionData) ? firstActionData.actionId || 'reaction' : 'reaction',
        steps: currentNodes.map((node, index) => {
          const nodeData = node.data as NodeData;
          // Find edges connected to this node
          const targetEdges = currentEdges.filter(edge => edge.source === node.id).map(edge => edge.target);
          
          // Prepare the base config with common properties
          let stepConfig: Record<string, unknown> = {
            ...(nodeData.config || {}),
            clientId: node.id,
            position: node.position,
            targets: targetEdges,
          };
          
          // Add delay-specific configuration if this is a delay node
          if (node.type === 'delay' && 'duration' in nodeData && 'unit' in nodeData) {
            stepConfig = {
              ...stepConfig,
              duration: (nodeData as { duration?: number }).duration,
              unit: (nodeData as { unit?: string }).unit,
            };
          }
          
          return {
            step_type: node.type as 'trigger' | 'action' | 'condition' | 'delay',
            order: index,
            service: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.serviceId : null,
            action: (isTriggerNode(nodeData) || isActionNode(nodeData)) ? nodeData.actionId : null,
            config: stepConfig,
          };
        }),
      };

      // Call the API to create the area with steps
      const result = await createAreaWithSteps(auth.token, areaData);
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
    <AppShell>
      <div className="container mx-auto py-8">
        <div className="mb-8">
          <h1 className={cn(headingClasses(1), "text-foreground")}>Advanced AREA Builder</h1>
          <p className="text-muted-foreground mt-2">
            Create multi-step automations with the visual flow editor
          </p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Area Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Area Name *</label>
              <input
                type="text"
                value={areaName}
                onChange={(e) => setAreaName(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter area name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <textarea
                value={areaDescription}
                onChange={(e) => setAreaDescription(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter area description"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="h-[600px] mb-6">
          <CardHeader>
            <CardTitle>Automation Flow</CardTitle>
          </CardHeader>
          <CardContent className="p-0 h-[calc(100%-60px)]">
            <AreaFlow
              ref={areaFlowRef}
              initialNodes={nodes}
              initialEdges={edges}
              onNodeSelect={(nodeId) => setHasSelectedNode(!!nodeId)}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button
            variant="default"
            onClick={handleSave}
          >
            Save AREA
          </Button>
          {hasSelectedNode && (
            <Button
              variant="destructive"
              onClick={handleDelete}
            >
              Delete Selected
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => router.push('/dashboard')}
          >
            Cancel
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
