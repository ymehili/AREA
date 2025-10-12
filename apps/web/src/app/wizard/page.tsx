"use client";

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import AppShell from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import AreaFlow, { type AreaFlowHandles } from '@/components/area-builder/AreaFlow';
import { Node, Edge } from 'reactflow';
import { NodeData, isTriggerNode, isActionNode } from '@/components/area-builder/node-types';
import { createAreaWithSteps, UnauthorizedError } from '@/lib/api';
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

    // Check if user is authenticated
    if (!auth.token) {
      toast.error('You must be logged in to create an area');
      router.push('/');
      return;
    }

    try {
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
          
          // Prepare the base config with common properties
          let stepConfig: Record<string, unknown> = {
            ...(nodeData.config || {}),
            // Include params in config so they're available during execution
            ...(params || {}),
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
      // Handle authentication errors specifically
      if (error instanceof UnauthorizedError) {
        toast.error('Your session has expired. Please log in again.');
        auth.logout();
        router.push('/');
        return;
      }
      
      // Show specific error message from the API
      if (error instanceof Error) {
        toast.error(error.message);
        
        // Only log unexpected errors to console
        if (!error.message.includes('already exists')) {
          console.error('Unexpected error creating area:', error);
        }
      } else {
        console.error('Error creating area:', error);
        toast.error('Failed to create area. Please try again.');
      }
    }
  };

  return (
    <AppShell>
      <div className="h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="border-b bg-card px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={cn(headingClasses(2), "text-foreground")}>Advanced AREA Builder</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Create multi-step automations with the visual flow editor
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => router.push('/dashboard')}
              >
                Cancel
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
                variant="default"
                onClick={handleSave}
              >
                Save AREA
              </Button>
            </div>
          </div>
        </div>

        {/* Main content area with sidebar */}
        <div className="flex h-[calc(100%-80px)]">
          {/* Left sidebar for area details */}
          <div className="w-80 border-r bg-card overflow-y-auto">
            <div className="p-6 space-y-4">
              <div>
                <h3 className="font-semibold text-sm mb-4 text-foreground">Area Details</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium mb-2 text-foreground">
                      Area Name <span className="text-destructive">*</span>
                    </label>
                    <input
                      type="text"
                      value={areaName}
                      onChange={(e) => setAreaName(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-[box-shadow] duration-150 bg-background"
                      placeholder="My Automation"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs font-medium mb-2 text-foreground">Description</label>
                    <textarea
                      value={areaDescription}
                      onChange={(e) => setAreaDescription(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 text-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-[box-shadow] duration-150 bg-background resize-none"
                      placeholder="Describe what this automation does..."
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t">
                <h3 className="font-semibold text-xs mb-3 text-muted-foreground uppercase tracking-wide">
                  Instructions
                </h3>
                <ul className="space-y-2 text-xs text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">1.</span>
                    <span>Use the toolbar on the right to add nodes</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">2.</span>
                    <span>Start with a trigger (blue) node</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">3.</span>
                    <span>Connect nodes by dragging from handles</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">4.</span>
                    <span>Click nodes to configure their settings</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">5.</span>
                    <span>Save when your flow is complete</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Main flow editor - full height */}
          <div className="flex-1 bg-muted/30">
            <AreaFlow
              ref={areaFlowRef}
              initialNodes={nodes}
              initialEdges={edges}
              onNodeSelect={(nodeId) => setHasSelectedNode(!!nodeId)}
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
