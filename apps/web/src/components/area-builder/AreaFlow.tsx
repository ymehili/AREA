import React, { useState, useCallback, useMemo, useImperativeHandle, forwardRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Connection,
  Edge,
  Node,
  NodeTypes,
  ConnectionLineType,
  OnSelectionChangeFunc,
} from 'reactflow';
import 'reactflow/dist/style.css';

import TriggerNode from './TriggerNode';
import ActionNode from './ActionNode';
import ConditionNode from './ConditionNode';
import DelayNode from './DelayNode';
import ControlsPanel from './ControlsPanel';
import { 
  AreaStepNodeData, 
  NodeData,
  TriggerNodeData, 
  ActionNodeData, 
  ConditionNodeData, 
  DelayNodeData,
  isTriggerNode,
  isActionNode
} from './node-types';

// Define custom node types
const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  condition: ConditionNode,
  delay: DelayNode,
};

export interface AreaFlowProps {
  initialNodes?: Node<NodeData>[];
  initialEdges?: Edge[];
  onNodeSelect?: (nodeId: string | null) => void;
  onDeleteNode?: () => void;
}

export interface AreaFlowHandles {
  deleteSelectedNode: () => void;
  getSelectedNodeId: () => string | null;
  getCurrentNodes: () => Node<NodeData>[];
  getCurrentEdges: () => Edge[];
}

const AreaFlow = forwardRef<AreaFlowHandles, AreaFlowProps>((props, ref) => {
  const { 
    initialNodes = [], 
    initialEdges = [], 
    onNodeSelect,
    onDeleteNode
  } = props;
  // Initialize nodes and edges state
  const [nodes, setNodes, onNodesChange] = useNodesState<NodeData>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Get selected node data for configuration
  const selectedNode = useMemo(() => {
    return nodes.find(node => node.id === selectedNodeId);
  }, [nodes, selectedNodeId]);

  // Function to add a new node
  const addNode = useCallback((type: 'trigger' | 'action' | 'condition' | 'delay') => {
    // For triggers, position them at the start; for others, position them to the right
    const position = { 
      x: nodes.length > 0 ? Math.max(...nodes.map(n => n.position.x)) + 300 : 100, 
      y: 100 
    };

    const newNodeId = `${type}-${Date.now()}`;
    let newNodeData: NodeData;

    switch (type) {
      case 'trigger':
        newNodeData = {
          label: 'New Trigger',
          type: 'trigger',
          serviceId: '',
          actionId: '',
        } as TriggerNodeData;
        break;
      case 'action':
        newNodeData = {
          label: 'New Action',
          type: 'action',
          serviceId: '',
          actionId: '',
        } as ActionNodeData;
        break;
      case 'condition':
        newNodeData = {
          label: 'New Condition',
          type: 'condition',
          conditionType: 'simple',
          conditionValue: '',
        } as ConditionNodeData;
        break;
      case 'delay':
        newNodeData = {
          label: 'New Delay',
          type: 'delay',
          duration: 1,
          unit: 'seconds',
        } as DelayNodeData;
        break;
      default:
        throw new Error(`Unknown node type: ${type}`);
    }

    const newNode: Node<NodeData> = {
      id: newNodeId,
      type,
      position,
      data: newNodeData,
    };

    setNodes((nds) => nds.concat(newNode));
    setSelectedNodeId(newNodeId);
  }, [nodes, setNodes]);

  // Handle connection between nodes
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        id: `edge-${Date.now()}`,
        type: 'smoothstep',
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  // Handle node selection
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    if (onNodeSelect) {
      onNodeSelect(node.id);
    }
  }, [onNodeSelect]);

  // Handle selection changes
  const onSelectionChange = useCallback<OnSelectionChangeFunc>((selection) => {
    if (selection?.nodes?.length === 1) {
      const nodeId = selection.nodes[0].id;
      setSelectedNodeId(nodeId);
      if (onNodeSelect) {
        onNodeSelect(nodeId);
      }
    } else if (selection?.nodes?.length === 0) {
      setSelectedNodeId(null);
      if (onNodeSelect) {
        onNodeSelect(null);
      }
    }
  }, [onNodeSelect]);

  // Update node configuration
  const updateNodeConfig = useCallback((id: string, config: Partial<AreaStepNodeData>) => {
    setNodes((nds) => 
      nds.map(node => {
        if (node.id === id) {
          // Create the new data with the updates
          let newData = { ...node.data, ...config } as NodeData;
          
          // If this is a trigger or action node and the serviceId or actionId has changed,
          // update the label and description based on the service and action
          if ((isTriggerNode(newData) || isActionNode(newData)) && (config.serviceId || config.actionId)) {
            // For now, we'll update the label to reflect the selected service and action
            // In a more complete implementation, we would fetch the service catalog to get
            // the proper names for the service and action, but for now we'll just use the IDs
            if (config.serviceId) {
              newData.label = `${newData.type === 'trigger' ? 'Trigger' : 'Action'}: ${config.serviceId}`;
            } else if (config.actionId) {
              newData.label = `${newData.type === 'trigger' ? 'Trigger' : 'Action'}: ${newData.serviceId || 'Unknown'} - ${config.actionId}`;
            }
          }
          
          return { 
            ...node, 
            data: { 
              ...newData,
              // Ensure the type field is preserved (in case config accidentally overwrites it)
              type: node.data.type 
            } as NodeData 
          };
        }
        return node;
      })
    );
  }, [setNodes]);


  // Delete selected node
  const handleDelete = useCallback(() => {
    if (selectedNodeId) {
      setNodes((nds) => nds.filter(node => node.id !== selectedNodeId));
      setEdges((eds) => 
        eds.filter(edge => 
          edge.source !== selectedNodeId && edge.target !== selectedNodeId
        )
      );
      setSelectedNodeId(null);
      if (onDeleteNode) {
        onDeleteNode();
      }
    }
  }, [selectedNodeId, setNodes, setEdges, onDeleteNode]);

  // Expose the functions to parent component
  useImperativeHandle(ref, () => ({
    deleteSelectedNode: handleDelete,
    getSelectedNodeId: () => selectedNodeId,
    getCurrentNodes: () => nodes,
    getCurrentEdges: () => edges
  }));

  return (
    <div className="flex h-full w-full">
      <ReactFlowProvider>
        <ControlsPanel 
          onAddNode={addNode}
          selectedNodeId={selectedNodeId || undefined}
          onNodeConfigChange={updateNodeConfig}
          nodeConfig={selectedNode?.data}
        />
        <div className="flex-1 h-full relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onNodeDoubleClick={() => {
              setSelectedNodeId(null);
              if (onNodeSelect) {
                onNodeSelect(null);
              }
            }}
            onPaneClick={() => {
              setSelectedNodeId(null);
              if (onNodeSelect) {
                onNodeSelect(null);
              }
            }}
            nodeTypes={nodeTypes}
            connectionLineType={ConnectionLineType.SmoothStep}
            fitView
            elementsSelectable={true}
            onSelectionChange={onSelectionChange}
            nodesDraggable={true}
            nodesConnectable={true}
            selectNodesOnDrag={false}
          >
            <Controls />
            <Background gap={12} size={1} />
          </ReactFlow>
        </div>
      </ReactFlowProvider>
    </div>
  );
});

AreaFlow.displayName = 'AreaFlow';

export default AreaFlow;