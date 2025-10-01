import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { ConditionNodeData } from './node-types';

const ConditionNode: React.FC<NodeProps<ConditionNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <Card className={`w-64 ${selected ? 'border-2 border-primary shadow-lg ring-2 ring-ring' : 'border-2 border-yellow-500'} bg-yellow-50 dark:bg-yellow-950/30`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-200">
            Condition
          </Badge>
        </div>
        <h3 className="font-semibold text-lg">{data.label}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{data.description || data.conditionValue}</p>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Type: {data.conditionType}
        </div>
      </CardContent>
      {/* Input handle positioned at the left side */}
      <Handle
        type="target"
        position={Position.Left}
        id="condition-input"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-yellow-500"
      />
      {/* Output handle positioned at the right side */}
      <Handle
        type="source"
        position={Position.Right}
        id="condition-output"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-yellow-500"
      />
    </Card>
  );
};

export default ConditionNode;