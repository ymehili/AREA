"use client";

import React, { useState, useRef, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import AreaFlow, { type AreaFlowHandles } from '@/components/area-builder/AreaFlow';
import { Node, Edge } from 'reactflow';
import { NodeData, DelayNodeData } from '@/components/area-builder/node-types';
import { getAreaWithSteps, updateArea, updateAreaStep } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { cn, headingClasses } from '@/lib/utils';
import type { AreaWithStepsResponse } from '@/lib/api';

export default function EditAreaPage() {
  const router = useRouter();
  const params = useParams();
  const areaId = params.id as string;
  const auth = useAuth();

  const [loading, setLoading] = useState(true);
  const [areaName, setAreaName] = useState('');
  const [areaDescription, setAreaDescription] = useState('');
  const [hasSelectedNode, setHasSelectedNode] = useState(false);
  const [initialNodes, setInitialNodes] = useState<Node<NodeData>[]>([]);
  const [initialEdges, setInitialEdges] = useState<Edge[]>([]);
  const areaFlowRef = useRef<AreaFlowHandles>(null);

  useEffect(() => {
    const loadArea = async () => {
      if (!auth.token || !areaId) {
        return;
      }

      try {
        setLoading(true);
        const area: AreaWithStepsResponse = await getAreaWithSteps(auth.token, areaId);

        // Set area metadata
        setAreaName(area.name);
        setAreaDescription(area.description || '');

        // Convert steps to nodes
        if (area.steps && area.steps.length > 0) {
          const nodes: Node<NodeData>[] = area.steps.map((step, index) => {
            // Prepare base node data
            let nodeData: NodeData;
            
            if (step.step_type === 'delay') {
              // For delay nodes, extract duration and unit from config if available
              // Validate unit to ensure it's one of the allowed values
              const rawUnit = step.config?.unit;
              const validUnits = ['seconds', 'minutes', 'hours', 'days'] as const;
              const unit = (validUnits as readonly string[]).includes(rawUnit as string) 
                ? (rawUnit as 'seconds' | 'minutes' | 'hours' | 'days') 
                : 'seconds';

              const delayData: DelayNodeData = {
                label: `${step.step_type}: ${step.service || 'custom'}/${step.action || 'action'}`,
                description: '',
                type: 'delay',
                duration: typeof step.config?.duration === 'number' ? step.config.duration : 1,
                unit,
                config: step.config || {},
              };
              nodeData = delayData;
            } else {
              // For other node types, use generic data
              // Extract params from config (params were saved merged into config)
              const config = step.config || {};
              const { clientId, position, targets, ...params } = config;

              nodeData = {
                label: `${step.step_type}: ${step.service || 'custom'}/${step.action || 'action'}`,
                description: '',
                config: step.config || {},
                type: step.step_type as 'trigger' | 'action' | 'condition',
                serviceId: step.service || '',
                actionId: step.action || '',
                params: params as Record<string, unknown>,
              } as NodeData;
            }
            
            return {
              id: step.id,
              type: step.step_type,
              // Use saved position if available, otherwise calculate based on index
              position: (step.config?.position as { x: number; y: number }) || { x: 250, y: index * 150 + 50 },
              data: nodeData,
            };
          });

          // Restore edges from saved targets
          const edges: Edge[] = [];
          area.steps.forEach((step) => {
            const targets = (step.config?.targets as string[]) || [];
            targets.forEach((targetId) => {
              edges.push({
                id: `e${step.id}-${targetId}`,
                source: step.id,
                target: targetId,
              });
            });
          });

          setInitialNodes(nodes);
          setInitialEdges(edges);
        }
      } catch (error) {
        console.error('Error loading area:', error);
        toast.error('Failed to load area. Redirecting to dashboard...');
        setTimeout(() => router.push('/dashboard'), 2000);
      } finally {
        setLoading(false);
      }
    };

    void loadArea();
  }, [auth.token, areaId, router]);

  const handleDelete = () => {
    if (areaFlowRef.current) {
      areaFlowRef.current.deleteSelectedNode();
      setHasSelectedNode(false);
    }
  };

  const handleSave = async () => {
    if (!areaName) {
      toast.error('Please enter an area name');
      return;
    }

    try {
      if (!auth.token) {
        throw new Error('User not authenticated');
      }

      // Get the current nodes and edges from the flow
      const currentNodes = areaFlowRef.current?.getCurrentNodes() || initialNodes;
      const currentEdges = areaFlowRef.current?.getCurrentEdges() || initialEdges;

      // Find the trigger node
      const triggerNode = currentNodes.find(node => node.type === 'trigger');
      if (!triggerNode) {
        toast.error('Please add a trigger to your area');
        return;
      }

      // Prepare update payload
      const castedTriggerNodeData = triggerNode.data as NodeData;
      const firstActionNode = currentNodes.find(node => node.type === 'action');
      const firstActionData = firstActionNode?.data as NodeData | undefined;

      const updatePayload = {
        name: areaName,
        trigger_service: castedTriggerNodeData.type === 'trigger' && 'serviceId' in castedTriggerNodeData ? castedTriggerNodeData.serviceId || 'manual' : 'manual',
        trigger_action: castedTriggerNodeData.type === 'trigger' && 'actionId' in castedTriggerNodeData ? castedTriggerNodeData.actionId || 'trigger' : 'trigger',
        trigger_params: castedTriggerNodeData.type === 'trigger' && ('params' in castedTriggerNodeData) && castedTriggerNodeData.params ? castedTriggerNodeData.params : undefined,
        reaction_service: firstActionData && ('serviceId' in firstActionData) ? firstActionData.serviceId || 'manual' : 'manual',
        reaction_action: firstActionData && ('actionId' in firstActionData) ? firstActionData.actionId || 'reaction' : 'reaction',
        reaction_params: firstActionData && ('params' in firstActionData) && firstActionData.params ? firstActionData.params : undefined,
      };

      // Update the area metadata
      await updateArea(auth.token, areaId, updatePayload);

      // Update each step's position and edges
      const updateStepPromises = currentNodes.map(async (node) => {
        if (!auth.token || !node.id) return;

        const nodeData = node.data as NodeData;
        const targetEdges = currentEdges.filter(edge => edge.source === node.id).map(edge => edge.target);

        // Prepare the config to save, including delay-specific properties if it's a delay node
        let configToSave: Record<string, unknown> = {
          ...(nodeData.config || {}),
          // Include params in config so they're available during execution
          ...(('params' in nodeData && nodeData.params) ? nodeData.params : {}),
          clientId: node.id,
          position: node.position,
          targets: targetEdges,
        };

        // If this is a delay node, include duration and unit in the config
        if (node.type === 'delay') {
          const delayNodeData = nodeData as DelayNodeData;
          configToSave = {
            ...configToSave,
            duration: delayNodeData.duration,
            unit: delayNodeData.unit,
          };
        }

        // Update step with new position and targets
        await updateAreaStep(auth.token, node.id, {
          config: configToSave,
        });
      });

      await Promise.all(updateStepPromises);

      toast.success('Area updated successfully!');
      router.push('/dashboard');
    } catch (error) {
      console.error('Error updating area:', error);
      toast.error('Failed to update area. Please try again.');
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="container mx-auto py-8">
        <div className="mb-8">
          <h1 className={cn(headingClasses(1), "text-foreground")}>Edit AREA</h1>
          <p className="text-muted-foreground mt-2">
            Modify your automation flow
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
              initialNodes={initialNodes}
              initialEdges={initialEdges}
              onNodeSelect={(nodeId) => setHasSelectedNode(!!nodeId)}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button
            variant="default"
            onClick={handleSave}
          >
            Update AREA
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
            variant="destructive"
            onClick={() => router.push('/dashboard')}
          >
            Cancel
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
