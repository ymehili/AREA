import React from 'react';
import { ConnectionLineComponentProps, getSmoothStepPath } from 'reactflow';

const CustomConnectionLine: React.FC<ConnectionLineComponentProps> = ({
  fromX,
  fromY,
  toX,
  toY,
  fromPosition,
  toPosition,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX: fromX,
    sourceY: fromY,
    sourcePosition: fromPosition,
    targetX: toX,
    targetY: toY,
    targetPosition: toPosition,
    borderRadius: 8,
  });

  return (
    <g>
      <path
        fill="none"
        stroke="#3b82f6"
        strokeWidth={2.5}
        strokeLinecap="round"
        className="animated"
        d={edgePath}
        style={{
          filter: 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1))',
        }}
      />
      <circle
        cx={toX}
        cy={toY}
        fill="#fff"
        r={4}
        stroke="#3b82f6"
        strokeWidth={2}
        style={{
          filter: 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2))',
        }}
      />
    </g>
  );
};

export default CustomConnectionLine;
