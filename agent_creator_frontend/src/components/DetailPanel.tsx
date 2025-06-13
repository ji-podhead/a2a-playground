'use client';

import React, { ChangeEvent } from 'react';
import { Node } from 'reactflow';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator'; // Optional: if not added, will skip

// Define a type for the node's data object
export interface NodeConfigData {
  label: string;
  name?: string;
  apiEndpoint?: string;
  pydanticModel?: string;
  jsonResponseConfig?: string;
  destination?: string;
  date?: string;
  duration?: number;
  task?: string;
}

interface DetailPanelProps {
  selectedNode: Node<NodeConfigData> | null;
  onNodeDataChange: (nodeId: string, newData: Partial<NodeConfigData>) => void;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ selectedNode, onNodeDataChange }) => {
  if (!selectedNode) {
    return (
      <div className="p-6 bg-gray-50 h-full flex items-center justify-center">
        <p className="text-gray-500">Select a node to view its details.</p>
      </div>
    );
  }

  const handleInputChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = event.target;
    let processedValue: string | number = value;
    if (type === 'number') {
      processedValue = parseFloat(value) || 0;
      if (name === 'duration' && processedValue < 0) processedValue = 0; // Example validation
    }
    const updatedField = { [name]: processedValue };
    onNodeDataChange(selectedNode.id, updatedField as Partial<NodeConfigData>);
  };

  const nodeData = selectedNode.data || { label: 'N/A' };

  return (
    <div className="p-4 bg-white h-full overflow-y-auto shadow-sm border-l border-gray-200">
      <h3 className="text-lg font-semibold mb-1 text-gray-800">Node Configuration</h3>
      <p className="text-xs text-gray-500 mb-4">ID: {selectedNode.id}</p>

      <div className="space-y-4">
        {/* General Section */}
        <div>
          <Label htmlFor={`node-type-${selectedNode.id}`} className="text-xs text-gray-600">Type</Label>
          <Input
            id={`node-type-${selectedNode.id}`}
            type="text"
            value={selectedNode.type || 'N/A'}
            readOnly
            className="mt-1 bg-gray-100 cursor-not-allowed"
          />
        </div>

        <div>
          <Label htmlFor={`node-label-${selectedNode.id}`}>Label</Label>
          <Input
            id={`node-label-${selectedNode.id}`}
            type="text"
            name="label"
            placeholder="Enter node label"
            value={nodeData.label}
            onChange={handleInputChange}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor={`node-name-${selectedNode.id}`}>Name (Internal)</Label>
          <Input
            id={`node-name-${selectedNode.id}`}
            type="text"
            name="name"
            placeholder="Internal node name (optional)"
            value={nodeData.name || ''}
            onChange={handleInputChange}
            className="mt-1"
          />
        </div>

        {/* API/Task Specific Section - Conditionally render or make generic */}
        <Separator className="my-4" />
        <h4 className="text-md font-medium text-gray-700 mb-1">Parameters</h4>

        {nodeData.task !== undefined && (
          <div>
            <Label htmlFor={`node-task-${selectedNode.id}`}>Task</Label>
            <Input
              id={`node-task-${selectedNode.id}`}
              type="text" name="task" value={nodeData.task || ''} onChange={handleInputChange}
              className="mt-1" placeholder="e.g., find_flights"
            />
          </div>
        )}

        {nodeData.destination !== undefined && (
          <div>
            <Label htmlFor={`node-destination-${selectedNode.id}`}>Destination</Label>
            <Input
              id={`node-destination-${selectedNode.id}`}
              type="text" name="destination" value={nodeData.destination || ''} onChange={handleInputChange}
              className="mt-1" placeholder="e.g., Paris"
            />
          </div>
        )}

        {nodeData.date !== undefined && (
         <div>
            <Label htmlFor={`node-date-${selectedNode.id}`}>Date</Label>
            <Input
              id={`node-date-${selectedNode.id}`}
              type="text" name="date" value={nodeData.date || ''} onChange={handleInputChange}
              className="mt-1" placeholder="YYYY-MM-DD"
            />
          </div>
        )}

        {nodeData.duration !== undefined && (
          <div>
            <Label htmlFor={`node-duration-${selectedNode.id}`}>Duration (days)</Label>
            <Input
              id={`node-duration-${selectedNode.id}`}
              type="number" name="duration" value={nodeData.duration || 0} onChange={handleInputChange}
              className="mt-1"
            />
          </div>
        )}

        <Separator className="my-4" />
         <h4 className="text-md font-medium text-gray-700 mb-1">Advanced Configuration</h4>

        <div>
          <Label htmlFor={`node-api-${selectedNode.id}`}>API Endpoint</Label>
          <Input
            id={`node-api-${selectedNode.id}`}
            type="text"
            name="apiEndpoint"
            placeholder="e.g., /api/agent"
            value={nodeData.apiEndpoint || ''}
            onChange={handleInputChange}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor={`node-pydantic-${selectedNode.id}`}>Pydantic Model</Label>
          <Textarea
            id={`node-pydantic-${selectedNode.id}`}
            name="pydanticModel"
            rows={5}
            placeholder="Define Pydantic model schema..."
            value={nodeData.pydanticModel || ''}
            onChange={handleInputChange}
            className="mt-1 font-mono text-xs"
          />
        </div>

        <div>
          <Label htmlFor={`node-jsonresponse-${selectedNode.id}`}>JSONResponse Config</Label>
          <Textarea
            id={`node-jsonresponse-${selectedNode.id}`}
            name="jsonResponseConfig"
            rows={5}
            placeholder="Define JSONResponse configuration..."
            value={nodeData.jsonResponseConfig || ''}
            onChange={handleInputChange}
            className="mt-1 font-mono text-xs"
          />
        </div>
      </div>
    </div>
  );
};

export default DetailPanel;
