import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { TriggerNodeData } from './node-types';

const TriggerNode: React.FC<NodeProps<TriggerNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <Card className={`w-64 ${selected ? 'border-2 border-primary shadow-lg ring-2 ring-ring' : 'border-2 border-blue-500'} bg-blue-50 dark:bg-blue-950/30`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
            Trigger
          </Badge>
        </div>
        <h3 className="font-semibold text-lg break-words">{data.label}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 break-words">{data.description || data.serviceId}</p>
      </CardContent>
      {/* Output handle positioned at the right side */}
      <Handle
        type="source"
        position={Position.Right}
        id="trigger-output"
        isConnectable={isConnectable}
        className="w-3 h-3 bg-blue-500"
      />
    </Card>
  );
};

export default TriggerNode;