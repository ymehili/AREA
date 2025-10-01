import { NodeProps } from 'reactflow';

// Base type for all area step node data
export interface AreaStepNodeData {
  id?: string;
  label: string;
  type: 'trigger' | 'action' | 'condition' | 'delay';
  description?: string;
  config?: Record<string, unknown>;
}

// Specific data types for each node type
export interface TriggerNodeData extends AreaStepNodeData {
  type: 'trigger';
  serviceId: string;
  actionId: string;
  config?: Record<string, unknown>;
}

export interface ActionNodeData extends AreaStepNodeData {
  type: 'action';
  serviceId: string;
  actionId: string;
  config?: Record<string, unknown>;
}

export interface ConditionNodeData extends AreaStepNodeData {
  type: 'condition';
  conditionType: 'simple' | 'expression';
  conditionValue: string;
  config?: {
    operator?: string;
    value?: unknown;
    expression?: string;
  };
}

export interface DelayNodeData extends AreaStepNodeData {
  type: 'delay';
  duration: number;
  unit: 'seconds' | 'minutes' | 'hours';
  config?: Record<string, unknown>;
}

// Union type for all possible node data types
export type NodeData = TriggerNodeData | ActionNodeData | ConditionNodeData | DelayNodeData;

// NodeProps with our custom data types
export type AreaStepNodeProps<T extends NodeData = NodeData> = Omit<NodeProps<T>, 'data'> & { data: T };

// Type guard functions to check node types
export const isTriggerNode = (data: NodeData): data is TriggerNodeData => {
  return data.type === 'trigger';
};

export const isActionNode = (data: NodeData): data is ActionNodeData => {
  return data.type === 'action';
};

export const isConditionNode = (data: NodeData): data is ConditionNodeData => {
  return data.type === 'condition';
};

export const isDelayNode = (data: NodeData): data is DelayNodeData => {
  return data.type === 'delay';
};

// Define the node types for React Flow
export const nodeTypes = {
  trigger: 'trigger',
  action: 'action',
  condition: 'condition',
  delay: 'delay',
} as const;

export type NodeType = keyof typeof nodeTypes;