'use client';

import React, { ChangeEvent, useEffect, useState } from 'react';
import { Node } from 'reactflow';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { AgentType } from '@/types/api'; // Import AgentType
import { Button } from '@/components/ui/button'; // For a potential save/update button

// Define a type for the node's data object
export interface NodeConfigData {
  label: string; // Will map to agent's name
  agent_id?: string | null; // Store backend agent ID
  agent_type?: AgentType | null; // Store backend agent type

  // Existing fields - can be part of the generic_config or mapped if needed
  name?: string; // Internal name, if different from label
  apiEndpoint?: string;
  pydanticModel?: string;
  jsonResponseConfig?: string;
  destination?: string;
  date?: string;
  duration?: number;
  task?: string;

  // New field for generic JSON configuration
  generic_config?: string; // JSON string for agent's config property
}

interface DetailPanelProps {
  selectedNode: Node<NodeConfigData> | null;
  onNodeDataChange: (nodeId: string, newData: Partial<NodeConfigData>) => void;
  // Add a new prop for explicit save/update if DetailPanel manages its own state for API calls
  // onSaveChanges?: (nodeId: string, dataToSave: Partial<NodeConfigData>) => void;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ selectedNode, onNodeDataChange }) => {
  const [currentConfig, setCurrentConfig] = useState<string>('');

  useEffect(() => {
     // Initialize textarea with current node's generic_config or default
     if (selectedNode?.data?.generic_config) {
         setCurrentConfig(selectedNode.data.generic_config);
     } else {
         setCurrentConfig('{}'); // Default to empty JSON object
     }
  }, [selectedNode]);

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
      if (name === 'duration' && processedValue < 0) processedValue = 0;
    }
    const updatedField = { [name]: processedValue };
    onNodeDataChange(selectedNode.id, updatedField as Partial<NodeConfigData>);
  };

  const handleGenericConfigChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
     setCurrentConfig(event.target.value);
  };

  // This function would be called when the user blurs the textarea or clicks a "save config" button
  const persistGenericConfig = () => {
     try {
         JSON.parse(currentConfig); // Validate JSON
         onNodeDataChange(selectedNode.id, { generic_config: currentConfig });
         // Optionally, trigger onSaveChanges here if DetailPanel is to directly call API
         // if (onSaveChanges && selectedNode.data?.agent_id) {
         //   onSaveChanges(selectedNode.id, { name: selectedNode.data.label, config: JSON.parse(currentConfig) });
         // }
     } catch (error) {
         alert("Invalid JSON in Generic Configuration.");
     }
  };

  const nodeData = selectedNode.data || { label: 'N/A' };

  return (
    <div className="p-4 bg-white h-full overflow-y-auto shadow-sm border-l border-gray-200">
      <h3 className="text-lg font-semibold mb-1 text-gray-800">Agent Configuration</h3>
      <p className="text-xs text-gray-500 mb-1">Node ID: {selectedNode.id}</p>
      {nodeData.agent_id && <p className="text-xs text-gray-500 mb-1">Agent ID: {nodeData.agent_id}</p>}
      {nodeData.agent_type && <p className="text-xs text-gray-500 mb-4">Agent Type: {nodeData.agent_type}</p>}


      <div className="space-y-4">
        <div>
          <Label htmlFor={`node-type-${selectedNode.id}`} className="text-xs text-gray-600">ReactFlow Type</Label>
          <Input id={`node-type-${selectedNode.id}`} type="text" value={selectedNode.type || 'N/A'} readOnly className="mt-1 bg-gray-100 cursor-not-allowed" />
        </div>

        <div>
          <Label htmlFor={`node-label-${selectedNode.id}`}>Name (Agent Label)</Label>
          <Input id={`node-label-${selectedNode.id}`} type="text" name="label" placeholder="Enter agent name" value={nodeData.label} onChange={handleInputChange} className="mt-1" />
        </div>

        <Separator className="my-4" />
        <h4 className="text-md font-medium text-gray-700 mb-1">Agent Backend Configuration (JSON)</h4>
         <div>
             <Label htmlFor={`generic-config-${selectedNode.id}`}>Generic Config (JSON)</Label>
             <Textarea
                 id={`generic-config-${selectedNode.id}`}
                 name="generic_config"
                 rows={8}
                 placeholder='{ "key": "value" }'
                 value={currentConfig}
                 onChange={handleGenericConfigChange}
                 onBlur={persistGenericConfig} // Save when focus leaves textarea
                 className="mt-1 font-mono text-xs"
             />
             <p className="text-xs text-gray-500 mt-1">Edit the JSON configuration for this agent. This will be sent to the backend.</p>
         </div>

        {/* Existing fields can be kept for UI convenience or gradually phased out / mapped to generic_config */}
        {/* For simplicity, primary focus is now on 'label' (for name) and 'generic_config' (for config) */}

        {/* <Separator className="my-4" />
        <h4 className="text-md font-medium text-gray-700 mb-1">Additional Parameters (UI only or map to config)</h4>
         {nodeData.task !== undefined && ( ... )}
        */}
      </div>
    </div>
  );
};

export default DetailPanel;
