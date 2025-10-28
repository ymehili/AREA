import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { ActionNodeData } from './node-types';

const ActionNode: React.FC<NodeProps<ActionNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <Card className={`w-64 ${selected ? 'border-2 border-primary shadow-lg ring-2 ring-ring' : 'border-2 border-green-500'} bg-green-50 dark:bg-green-950/30`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200">
            Action
          </Badge>
        </div>
        <h3 className="font-semibold text-lg break-words">{data.label}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 break-words">{data.description || data.serviceId}</p>
      </CardContent>
      {/* Input handle positioned at the left side */}
      <Handle
        type="target"
        position={Position.Left}
        id="action-input"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-green-500"
      />
      {/* Output handle positioned at the right side */}
      <Handle
        type="source"
        position={Position.Right}
        id="action-output"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-green-500"
      />
    </Card>
  );
};

export default ActionNode;