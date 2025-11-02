import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

import { ActionNodeData } from './node-types';

const ActionNode: React.FC<NodeProps<ActionNodeData>> = ({ data, isConnectable, selected }) => {
  return (
    <div className="relative">
      <Card className={`w-72 ${selected ? 'ring-2 ring-primary shadow-xl' : 'shadow-md'} border-2 border-green-500 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/40 dark:to-green-900/30 overflow-visible`}>
        <CardContent className="p-4 px-8">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="secondary" className="bg-green-500 text-white">
              Action
            </Badge>
          </div>
          <h3 className="font-semibold text-lg break-words text-green-900 dark:text-green-100">{data.label}</h3>
          <p className="text-sm text-green-700 dark:text-green-300 mt-1 break-words">{data.description || data.serviceId}</p>
        </CardContent>
        
        {/* Input handle - integrated into the card edge */}
        <div className="absolute -left-3 top-1/2 -translate-y-1/2 z-10">
          <div className="relative w-10 h-10 flex items-center justify-center">
            {/* Glow ring effect */}
            <div className="absolute inset-0 bg-green-500/30 rounded-full blur-sm"></div>
            <Handle
              type="target"
              position={Position.Left}
              id="action-input"
              isConnectable={isConnectable}
              className="!w-8 !h-8 !bg-green-500 !border-4 !border-white dark:!border-gray-800 hover:!bg-green-600 hover:scale-110 transition-all cursor-crosshair !static !transform-none shadow-lg"
            />
          </div>
        </div>
        
        {/* Output handle - integrated into the card edge */}
        <div className="absolute -right-3 top-1/2 -translate-y-1/2 z-10">
          <div className="relative w-10 h-10 flex items-center justify-center">
            {/* Glow ring effect */}
            <div className="absolute inset-0 bg-green-500/30 rounded-full blur-sm"></div>
            <Handle
              type="source"
              position={Position.Right}
              id="action-output"
              isConnectable={isConnectable}
              className="!w-8 !h-8 !bg-green-500 !border-4 !border-white dark:!border-gray-800 hover:!bg-green-600 hover:scale-110 transition-all cursor-crosshair !static !transform-none shadow-lg"
            />
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ActionNode;