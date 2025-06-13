'use client';

import React, { useCallback, useRef, useState } from 'react';
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
  MarkerType, // For edge markers
  DefaultEdgeOptions, // Type for defaultEdgeOptions
  NodeOrigin, // For nodeOrigin
} from 'reactflow';
import 'reactflow/dist/style.css';

import DraggableNode from '@/components/DraggableNode';
import DetailPanel, { NodeConfigData } from '@/components/DetailPanel';
import { Button } from '@/components/ui/button';
import { travelPlannerPreset } from './presets';

let id = 0;
const getId = () => `dndnode_${id++}`;

// n8n-like styling options
const defaultNodeStyle = {
  border: '1px solid #1a192b', // n8n uses a dark border
  borderRadius: '8px',
  padding: '0px', // Internal padding will be handled by custom node structure if any, or content
  backgroundColor: '#ffffff', // Nodes are typically white
  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)', // Subtle shadow
};

const nodeOrigin: NodeOrigin = [0.5, 0.5]; // Center node origin

const defaultEdgeOptions: DefaultEdgeOptions = {
  animated: false, // n8n edges are not typically animated by default unless running
  style: { stroke: '#7b68ee', strokeWidth: 2.5 }, // A purple-ish color, slightly thicker
  markerEnd: { type: MarkerType.ArrowClosed, color: '#7b68ee', width: 20, height: 20 },
};


const EditorPage = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeConfigData>[]>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge[]>([]);
  const { screenToFlowPosition, getNodes, getEdges, fitView } = useReactFlow();
  const [selectedNode, setSelectedNode] = useState<Node<NodeConfigData> | null>(null);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge({ ...params, ...defaultEdgeOptions }, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      if (!reactFlowWrapper.current) return;
      const type = event.dataTransfer.getData('application/reactflow-type') || 'default';
      const labelFromDrop = event.dataTransfer.getData('application/reactflow-label') || 'New Node';

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const newNodeData: NodeConfigData = { label: labelFromDrop };
      const newNode: Node<NodeConfigData> = {
        id: getId(),
        type,
        position,
        data: newNodeData,
        style: defaultNodeStyle, // Apply default style to new nodes
      };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setNodes((nds) => [...nds, newNode as any]);
      setSelectedNode(newNode);
    },
    [screenToFlowPosition, nodes, setNodes]
  );

  const onNodeClick: NodeMouseHandler = useCallback((event, node) => {
    setSelectedNode(node as Node<NodeConfigData>);
  }, []);

  const onNodeDataChange = useCallback(
    (nodeId: string, newData: Partial<NodeConfigData>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ? { ...node, data: { ...node.data, ...newData } as NodeConfigData } as any
            : node
        )
      );
      if (selectedNode && selectedNode.id === nodeId) {
        setSelectedNode((sn) =>
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          sn ? { ...sn, data: { ...sn.data, ...newData } as NodeConfigData } as any : null
        );
      }
    },
    [setNodes, selectedNode]
  );

  const onRunClick = useCallback(() => {
    const pipelineData = { nodes: getNodes(), edges: getEdges() };
    console.log('Pipeline Data:', JSON.stringify(pipelineData, null, 2));
    alert('Pipeline data logged to console.');
  }, [getNodes, getEdges]);

  const onLoadTravelPlannerPreset = useCallback(() => {
    const presetNodes: Node<NodeConfigData>[] = travelPlannerPreset.nodes.map(node => ({
      ...node,
      style: defaultNodeStyle, // Apply default style to preset nodes
      data: node.data as NodeConfigData,
    }));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setNodes(presetNodes as any);
    setEdges(travelPlannerPreset.edges); // Edges from preset can use defaultEdgeOptions via onConnect or direct merge
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 100);
  }, [setNodes, setEdges, fitView]);

  return (
    <div className="flex h-screen bg-gray-200 text-gray-800"> {/* Overall background */}
      {/* Sidebar */}
      <div className="w-72 p-4 bg-white border-r border-gray-300 shadow-lg flex flex-col space-y-2">
        <h2 className="text-xl font-bold mb-4 text-indigo-700">Node Palette</h2>
        <div className="flex-grow space-y-1">
          <DraggableNode nodeType="default" label="Master Agent" />
          <DraggableNode nodeType="default" label="Specialist Agent" />
          <DraggableNode nodeType="input" label="Input Node" /> {/* Changed type for variety */}
          <DraggableNode nodeType="output" label="Output Node" /> {/* Changed type for variety */}
        </div>
        <Button onClick={onLoadTravelPlannerPreset} className="mt-2 w-full bg-indigo-600 hover:bg-indigo-700">
          Load Travel Preset
        </Button>
        <Button onClick={onRunClick} className="mt-2 w-full bg-green-600 hover:bg-green-700">
          Run Pipeline
        </Button>
      </div>

      {/* Main Flow Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Canvas */}
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
            defaultEdgeOptions={defaultEdgeOptions} // Apply default edge styling
            nodeOrigin={nodeOrigin} // Center origin for all nodes
            className="bg-gray-50" // Canvas background
          >
            <Controls className="[&>button]:bg-white [&>button]:border-gray-300 [&>button_svg]:fill-gray-700 hover:[&>button]:bg-gray-100" />
            <Background color="#aaa" gap={20} />
          </ReactFlow>
        </div>

        {/* Detail Panel - Conditionally render or animate in/out */}
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
