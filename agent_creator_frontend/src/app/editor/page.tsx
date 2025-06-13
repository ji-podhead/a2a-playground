'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  Node,
  Edge,
  Connection,
  useReactFlow,
  NodeMouseHandler,
  MarkerType,
  DefaultEdgeOptions,
  NodeOrigin,
} from 'reactflow';
import 'reactflow/dist/style.css';

import DraggableNode from '@/components/DraggableNode';
import DetailPanel, { NodeConfigData } from '@/components/DetailPanel';
import { Button } from '@/components/ui/button';
import { travelPlannerPreset } from './presets'; // Assuming this is still relevant or can be adapted
import * as apiService from '@/lib/apiService'; // Import our API service
import { AgentType, Agent } from '@/types/api'; // Import types

let idCounter = 0; // Changed from just id to avoid conflict with potential global id
const getLocalId = () => `localnode_${idCounter++}`;

const defaultNodeStyle = {
  border: '1px solid #1a192b',
  borderRadius: '8px',
  padding: '0px',
  backgroundColor: '#ffffff',
  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
};

const nodeOrigin: NodeOrigin = [0.5, 0.5];

const defaultEdgeOptions: DefaultEdgeOptions = {
  animated: false,
  style: { stroke: '#7b68ee', strokeWidth: 2.5 },
  markerEnd: { type: MarkerType.ArrowClosed, color: '#7b68ee', width: 20, height: 20 },
};

// Extended Node type to ensure data compatibility with NodeConfigData
type AgentFlowNode = Node<NodeConfigData>;

const EditorPage = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<AgentFlowNode[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);
  const { screenToFlowPosition, getNodes, getEdges, fitView, setViewport } = useReactFlow(); // Added setViewport
  const [selectedNode, setSelectedNode] = useState<AgentFlowNode | null>(null);

  // Fetch existing agents on mount
  useEffect(() => {
    const fetchAndLoadAgents = async () => {
      try {
        console.log("Fetching existing agents...");
        const existingAgents: Agent[] = await apiService.listAgents();
        console.log('Fetched existing agents:', existingAgents);

        // For now, just log. Future: Convert to AgentFlowNode[] and setNodes.
        // This requires careful handling of positions to avoid overlap.
        // Example of converting (without layouting):
        /*
        const flowNodes: AgentFlowNode[] = existingAgents.map((agent, index) => ({
          id: agent.agent_id, // Use backend ID as React Flow ID
          type: 'default', // Or determine from agent.agent_type if mapping exists
          position: { x: Math.random() * 400, y: Math.random() * 400 + index * 100 }, // Random initial position
          data: {
            label: agent.name,
            agent_id: agent.agent_id,
            agent_type: agent.agent_type,
            generic_config: JSON.stringify(agent.config || {}),
            // ... map other NodeConfigData fields if necessary
          },
          style: defaultNodeStyle,
        }));
        // setNodes(flowNodes); // This would replace current nodes
        // setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 100);
        */
      } catch (error) {
        console.error('Failed to fetch existing agents:', error);
        // alert('Failed to load existing agents. See console for details.');
      }
    };
    fetchAndLoadAgents();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount


  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge({ ...params, ...defaultEdgeOptions }, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    async (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      if (!reactFlowWrapper.current) return;

      const nodeType = event.dataTransfer.getData('application/reactflow-type') || 'default';
      const label = event.dataTransfer.getData('application/reactflow-label') || 'New Agent';
      const agentTypeString = event.dataTransfer.getData('application/reactflow-agent-type');

      if (!agentTypeString || !Object.values(AgentType).includes(agentTypeString as AgentType)) {
        console.error('Invalid or missing agent type on drop:', agentTypeString);
        alert('Could not create agent: Invalid agent type.');
        return;
      }
      const agentType = agentTypeString as AgentType;

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const initialGenericConfig = '{}'; // Empty JSON object

      try {
        console.log(`Creating agent: ${label}, type: ${agentType}`);
        const newAgentFromApi = await apiService.createAgent({
          name: label,
          agent_type: agentType,
          config: JSON.parse(initialGenericConfig),
        });
        console.log('Agent created via API:', newAgentFromApi);

        const newNode: AgentFlowNode = {
          id: newAgentFromApi.agent_id, // Use backend ID
          type: nodeType,
          position,
          data: {
            label: newAgentFromApi.name,
            agent_id: newAgentFromApi.agent_id,
            agent_type: newAgentFromApi.agent_type,
            generic_config: JSON.stringify(newAgentFromApi.config || {}),
          },
          style: defaultNodeStyle,
        };
        setNodes((nds) => [...nds, newNode]);
        setSelectedNode(newNode);
      } catch (error) {
        console.error('Failed to create agent via API:', error);
        alert(`Failed to create agent: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    },
    [screenToFlowPosition, setNodes]
  );

  const onNodeClick: NodeMouseHandler = useCallback((event, node) => {
    setSelectedNode(node as AgentFlowNode);
  }, []);

  const onNodeDataChange = useCallback(
    async (nodeId: string, newData: Partial<NodeConfigData>) => {
      // Update local React Flow state immediately for responsiveness
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? { ...node, data: { ...node.data, ...newData } as NodeConfigData }
            : node
        )
      );
      if (selectedNode && selectedNode.id === nodeId) {
        setSelectedNode((sn) =>
          sn ? { ...sn, data: { ...sn.data, ...newData } as NodeConfigData } : null
        );
      }

      // Persist changes to backend if agent_id exists (i.e., it's a backend-managed agent)
      const targetNode = nodes.find(n => n.id === nodeId); // Use current nodes state
      if (targetNode?.data?.agent_id) {
        try {
          let updatePayload: apiService.AgentUpdatePayload = {};
          if (newData.label !== undefined) {
            updatePayload.name = newData.label;
          }
          if (newData.generic_config !== undefined) {
            try {
              updatePayload.config = JSON.parse(newData.generic_config);
            } catch (parseError) {
              console.error('Invalid JSON in generic_config, not updating config:', parseError);
              // alert('Error: Generic Config contains invalid JSON. Config not saved.');
              // Optionally revert generic_config in UI or provide specific feedback
              return; // Stop update if JSON is bad
            }
          }

          if (Object.keys(updatePayload).length > 0) {
            console.log(`Updating agent ${targetNode.data.agent_id} with payload:`, updatePayload);
            await apiService.updateAgent(targetNode.data.agent_id, updatePayload);
            console.log(`Agent ${targetNode.data.agent_id} updated successfully.`);
            // alert('Agent updated successfully.'); // Optional: provide user feedback
          }
        } catch (error) {
          console.error(`Failed to update agent ${targetNode.data.agent_id}:`, error);
          // alert(`Failed to update agent: ${error instanceof Error ? error.message : 'Unknown error'}`);
          // Optionally, revert optimistic UI update here
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setNodes, selectedNode, nodes] // nodes is needed here
  );

  const onRunClick = useCallback(async () => {
    const currentNodes = getNodes();
    console.log('Pipeline Data for Execution:', { nodes: currentNodes, edges: getEdges() });
    alert(`Starting execution for ${currentNodes.length} agent(s) if applicable. Check console for details.`);

    for (const node of currentNodes) {
      if (node.data?.agent_id) {
        try {
          let params = {};
          if (node.data.generic_config) {
            try {
              params = JSON.parse(node.data.generic_config);
            } catch (e) {
              console.warn(`Node ${node.id} (${node.data.label}) has invalid JSON in generic_config. Executing with empty params. Error: ${e}`);
            }
          }

          console.log(`Executing agent ${node.data.label} (ID: ${node.data.agent_id}) with params:`, params);
          const executionResult = await apiService.executeAgent(node.data.agent_id, { parameters: params });
          console.log(`Execution result for ${node.data.label}:`, executionResult);
          // Update node data or display status based on executionResult.status
          // For example, you could change node color or add a status badge.
          // This part can be expanded significantly.
           onNodeDataChange(node.id, { ...node.data, last_execution_status: executionResult.status });


        } catch (error) {
          console.error(`Failed to execute agent ${node.data.label} (ID: ${node.data.agent_id}):`, error);
          // alert(`Error executing agent ${node.data.label}. See console.`);
          onNodeDataChange(node.id, { ...node.data, last_execution_status: 'failed_to_start' });

        }
      } else {
        console.log(`Node ${node.id} (${node.data.label}) is not a backend agent, skipping execution.`);
      }
    }
  }, [getNodes, getEdges, onNodeDataChange]);

  const onLoadTravelPlannerPreset = useCallback(() => {
    // This preset loading logic needs to be adapted if it's to create backend agents.
    // For now, it will create local React Flow nodes.
    // Or, it could be a sequence of API calls to create these agents.
    const presetFlowNodes: AgentFlowNode[] = travelPlannerPreset.nodes.map(node => ({
      ...node,
      id: node.data?.agent_id || getLocalId(), // Use agent_id if preset provides it, else local
      style: defaultNodeStyle,
      data: node.data as NodeConfigData, // Ensure data matches NodeConfigData
    }));
    setNodes(presetFlowNodes);
    setEdges(travelPlannerPreset.edges);
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 100);
    alert("Travel Planner Preset Loaded. Note: These might be local nodes unless the preset is updated to create backend agents.");
  }, [setNodes, setEdges, fitView]);

  return (
    <div className="flex h-screen bg-gray-200 text-gray-800">
      <div className="w-72 p-4 bg-white border-r border-gray-300 shadow-lg flex flex-col space-y-2">
        <h2 className="text-xl font-bold mb-4 text-indigo-700">Agent Palette</h2>
        <div className="flex-grow space-y-1">
          {/* Update DraggableNode to pass the correct AgentType */}
          <DraggableNode nodeType="default" label="MCP Agent" agentType={AgentType.MCP} />
          <DraggableNode nodeType="default" label="A2A Agent" agentType={AgentType.A2A} />
          <DraggableNode nodeType="input" label="Custom Input Agent" agentType={AgentType.CUSTOM} />
          {/* Add more agent types as needed */}
        </div>
        <Button onClick={onLoadTravelPlannerPreset} className="mt-2 w-full bg-indigo-600 hover:bg-indigo-700">
          Load Travel Preset
        </Button>
        <Button onClick={onRunClick} className="mt-2 w-full bg-green-600 hover:bg-green-700">
          Run Pipeline
        </Button>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onNodeClick={onNodeClick}
            fitView
            defaultEdgeOptions={defaultEdgeOptions}
            nodeOrigin={nodeOrigin}
            className="bg-gray-50"
          >
            <Controls className="[&>button]:bg-white [&>button]:border-gray-300 [&>button_svg]:fill-gray-700 hover:[&>button]:bg-gray-100" />
            <Background color="#aaa" gap={20} />
          </ReactFlow>
        </div>

        {selectedNode && (
          <div
            className="h-1/3 max-h-[40vh] bg-white border-t-2 border-gray-300 shadow-xl overflow-y-auto transition-all duration-300 ease-in-out"
          >
            <DetailPanel selectedNode={selectedNode} onNodeDataChange={onNodeDataChange} />
          </div>
        )}
      </div>
    </div>
  );
};

const EditorPageWrapper = () => (
  <ReactFlowProvider>
    <EditorPage />
  </ReactFlowProvider>
);

export default EditorPageWrapper;
