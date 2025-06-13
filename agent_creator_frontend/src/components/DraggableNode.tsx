'use client';

import React from 'react';

interface DraggableNodeProps {
  nodeType: string;
  label: string;
}

const DraggableNode: React.FC<DraggableNodeProps> = ({ nodeType, label }) => {
  const onDragStart = (event: React.DragEvent<HTMLDivElement>) => {
    event.dataTransfer.setData('application/reactflow-type', nodeType);
    event.dataTransfer.setData('application/reactflow-label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className="px-3 py-2 mb-3 border border-gray-300 rounded-lg shadow-sm cursor-grab bg-white hover:bg-indigo-50 hover:shadow-md transition-all duration-150 ease-in-out flex items-center"
      onDragStart={onDragStart}
      draggable
    >
      {/* Placeholder for an icon - could use an SVG or a character */}
      <span className="mr-2 text-indigo-600">◈</span>
      <span className="text-sm font-medium text-gray-700">{label}</span>
    </div>
  );
};

export default DraggableNode;
