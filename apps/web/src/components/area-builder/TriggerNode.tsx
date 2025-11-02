import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { TriggerNodeData } from './node-types';

const TriggerNode: React.FC<NodeProps<TriggerNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <div className="relative">
      <Card className={`w-72 ${selected ? 'ring-2 ring-primary shadow-xl' : 'shadow-md'} border-2 border-blue-500 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/40 dark:to-blue-900/30 overflow-visible`}>
        <CardContent className="p-4 pr-8">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="secondary" className="bg-blue-500 text-white">
              Trigger
            </Badge>
          </div>
          <h3 className="font-semibold text-lg break-words text-blue-900 dark:text-blue-100">{data.label}</h3>
          <p className="text-sm text-blue-700 dark:text-blue-300 mt-1 break-words">{data.description || data.serviceId}</p>
        </CardContent>
        
        {/* Output handle - integrated into the card edge */}
        <div className="absolute -right-3 top-1/2 -translate-y-1/2 z-10">
          <div className="relative w-10 h-10 flex items-center justify-center">
            {/* Glow ring effect */}
            <div className="absolute inset-0 bg-blue-500/30 rounded-full blur-sm"></div>
            <Handle
              type="source"
              position={Position.Right}
              id="trigger-output"
              isConnectable={isConnectable}
              className="!w-8 !h-8 !bg-blue-500 !border-4 !border-white dark:!border-gray-800 hover:!bg-blue-600 hover:scale-110 transition-all cursor-crosshair !static !transform-none shadow-lg"
            />
          </div>
        </div>
      </Card>
    </div>
  );
};

export default TriggerNode;