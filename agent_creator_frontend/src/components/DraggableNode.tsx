'use client';

import React from 'react';
import { AgentType } from '@/types/api'; // Import AgentType

interface DraggableNodeProps {
  nodeType: string; // React Flow's node type (e.g., 'default', 'input', 'output')
  label: string;    // Label displayed on the draggable item and default for new node
  agentType: AgentType; // Our backend's agent type
}

const DraggableNode: React.FC<DraggableNodeProps> = ({ nodeType, label, agentType }) => {
  const onDragStart = (event: React.DragEvent<HTMLDivElement>) => {
    event.dataTransfer.setData('application/reactflow-type', nodeType);
    event.dataTransfer.setData('application/reactflow-label', label);
    event.dataTransfer.setData('application/reactflow-agent-type', agentType); // Pass agentType
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className="px-3 py-2 mb-3 border border-gray-300 rounded-lg shadow-sm cursor-grab bg-white hover:bg-indigo-50 hover:shadow-md transition-all duration-150 ease-in-out flex items-center"
      onDragStart={onDragStart}
      draggable
    >
      <span className="mr-2 text-indigo-600">◈</span> {/* Consider making icon dynamic based on agentType */}
      <span className="text-sm font-medium text-gray-700">{label}</span>
    </div>
  );
};

export default DraggableNode;
