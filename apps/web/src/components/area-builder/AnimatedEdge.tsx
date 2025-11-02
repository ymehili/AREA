import React from 'react';
import { BaseEdge, EdgeProps, getSmoothStepPath } from 'reactflow';

const AnimatedEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 8,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {/* Animated particle moving along the path */}
      <circle r="3" fill="#3b82f6">
        <animateMotion dur="2s" repeatCount="indefinite" path={edgePath} />
      </circle>
      {/* Second particle with delay for staggered effect */}
      <circle r="3" fill="#3b82f6" opacity="0.6">
        <animateMotion dur="2s" repeatCount="indefinite" path={edgePath} begin="0.5s" />
      </circle>
    </>
  );
};

export default AnimatedEdge;
