import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { DelayNodeData } from './node-types';

const DelayNode: React.FC<NodeProps<DelayNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <Card className={`w-64 ${selected ? 'border-2 border-primary shadow-lg ring-2 ring-ring' : 'border-2 border-purple-500'} bg-purple-50 dark:bg-purple-950/30`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="secondary" className="bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-200">
            Delay
          </Badge>
        </div>
        <h3 className="font-semibold text-lg break-words">{data.label}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 break-words">
          {data.description || `${data.duration} ${data.unit}`}
        </p>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 break-words">
          Duration: {data.duration} {data.unit}
        </div>
      </CardContent>
      {/* Input handle positioned at the left side */}
      <Handle
        type="target"
        position={Position.Left}
        id="delay-input"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-purple-500"
      />
      {/* Output handle positioned at the right side */}
      <Handle
        type="source"
        position={Position.Right}
        id="delay-output"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-purple-500"
      />
    </Card>
  );
};

export default DelayNode;