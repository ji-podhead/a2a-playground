'use client';

import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { Agent, AgentCreate, AgentType, Execution, ExecutionCreate } from '@/types/api'; // Ensure this path is correct
import DetailPanel, { NodeConfigData } from '@/components/DetailPanel'; // Assuming DetailPanel will be adapted or used as part of this page
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'; // Assuming you have these ShadCN UI components
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'; // Assuming ShadCN UI

const API_BASE_URL = 'http://localhost:8000/api'; // Adjust if your backend runs elsewhere

export default function AgentPlatformPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states for creating a new agent
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentType, setNewAgentType] = useState<AgentType>(AgentType.A2A);
  const [newAgentConfig, setNewAgentConfig] = useState('{}'); // JSON string

  // Execution states
  const [executionParams, setExecutionParams] = useState('{}'); // JSON string
  const [executionResult, setExecutionResult] = useState<Execution | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/agents`);
      if (!response.ok) throw new Error(`Failed to fetch agents: ${response.statusText}`);
      const data: Agent[] = await response.json();
      setAgents(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateAgent = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    let parsedConfig = {};
    try {
      parsedConfig = JSON.parse(newAgentConfig);
    } catch (jsonError) {
      setError("Invalid JSON in agent configuration.");
      setIsLoading(false);
      return;
    }

    const agentToCreate: AgentCreate = {
      name: newAgentName,
      agent_type: newAgentType,
      config: parsedConfig,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentToCreate),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create agent');
      }
      setNewAgentName('');
      setNewAgentType(AgentType.A2A);
      setNewAgentConfig('{}');
      fetchAgents(); // Refresh list
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteAgent = async () => {
    if (!selectedAgent) {
      setError("No agent selected for execution.");
      return;
    }
    setIsExecuting(true);
    setExecutionResult(null);
    let parsedParams = {};
    try {
      parsedParams = JSON.parse(executionParams);
    } catch (jsonError) {
      setError("Invalid JSON in execution parameters.");
      setIsExecuting(false);
      return;
    }

    const executionCreate: ExecutionCreate = { parameters: parsedParams };

    try {
      const response = await fetch(`${API_BASE_URL}/agents/${selectedAgent.agent_id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(executionCreate),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to execute agent: ${response.status} ${response.statusText}`);
      }
      const resultData: Execution = await response.json();
      setExecutionResult(resultData);
      setError(null);
      // Poll for completion if status is PENDING or RUNNING
      // For now, we assume direct completion or use what's returned.
    } catch (err: any) {
      setError(err.message);
      setExecutionResult(null);
    } finally {
      setIsExecuting(false);
    }
  };

  // Minimal DetailPanel integration for now:
  // Convert Agent to NodeConfigData for DetailPanel
  const selectedNodeForDetailPanel = selectedAgent ? {
    id: selectedAgent.agent_id,
    type: selectedAgent.agent_type, // Or a mapping if DetailPanel expects specific ReactFlow node types
    data: {
      label: selectedAgent.name,
      agent_id: selectedAgent.agent_id,
      agent_type: selectedAgent.agent_type,
      generic_config: JSON.stringify(selectedAgent.config, null, 2),
    }
  } : null;

  const handleNodeDataChange = async (nodeId: string, newData: Partial<NodeConfigData>) => {
    if (!selectedAgent || selectedAgent.agent_id !== nodeId) return;

    const updatedAgentData: Partial<Agent> = {};
    if(newData.label) updatedAgentData.name = newData.label;
    if(newData.generic_config) {
      try {
        updatedAgentData.config = JSON.parse(newData.generic_config);
      } catch (e) {
        setError("Invalid JSON in updated config.");
        return;
      }
    }

    if (Object.keys(updatedAgentData).length === 0) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/agents/${selectedAgent.agent_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedAgentData),
      });
      if (!response.ok) {
         const errorData = await response.json();
         throw new Error(errorData.detail || 'Failed to update agent');
      }
      fetchAgents(); // Refresh to see changes
      setError(null);
    } catch (err:any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="container mx-auto p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Column 1: Create Agent & Agent List */}
      <div className="md:col-span-1 space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Create New Agent</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateAgent} className="space-y-3">
              <div>
                <Label htmlFor="newAgentName">Agent Name</Label>
                <Input id="newAgentName" value={newAgentName} onChange={(e) => setNewAgentName(e.target.value)} placeholder="My Assistant" required />
              </div>
              <div>
                <Label htmlFor="newAgentType">Agent Type</Label>
                <Select value={newAgentType} onValueChange={(value) => setNewAgentType(value as AgentType)}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    {Object.values(AgentType).map(type => (
                      <SelectItem key={type} value={type}>{type.toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="newAgentConfig">Agent Configuration (JSON)</Label>
                <Textarea id="newAgentConfig" value={newAgentConfig} onChange={(e) => setNewAgentConfig(e.target.value)} rows={3} placeholder='{ "param": "value" }' />
              </div>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create Agent'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Available Agents</CardTitle></CardHeader>
          <CardContent>
            {isLoading && <p>Loading agents...</p>}
            <ul className="space-y-2">
              {agents.map(agent => (
                <li key={agent.agent_id}
                    className={`p-2 rounded cursor-pointer ${selectedAgent?.agent_id === agent.agent_id ? 'bg-blue-100' : 'hover:bg-gray-100'}`}
                    onClick={() => setSelectedAgent(agent)}>
                  {agent.name} ({agent.agent_type})
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Column 2: Selected Agent Details & Execution */}
      <div className="md:col-span-2 space-y-4">
        {selectedAgent ? (
          <>
            <Card>
              <CardHeader><CardTitle>Agent Details: {selectedAgent.name}</CardTitle></CardHeader>
              <CardContent>
                {/* Using a simplified DetailPanel-like structure directly for now */}
                {/* Or pass to actual DetailPanel if its props are aligned */}
                <div className="space-y-3">
                    <div>
                        <Label>Agent ID</Label>
                        <Input readOnly value={selectedAgent.agent_id} />
                    </div>
                    <div>
                        <Label>Agent Type</Label>
                        <Input readOnly value={selectedAgent.agent_type} />
                    </div>
                    <div>
                        <Label>Current Configuration (JSON)</Label>
                        <Textarea
                            value={JSON.stringify(selectedAgent.config, null, 2)}
                            readOnly
                            rows={6}
                        />
                        {/* If DetailPanel is used, it would handle editing config */}
                    </div>
                </div>
                 {/* If using DetailPanel, it would be rendered here: */}
                 {/* selectedNodeForDetailPanel && (
                    <DetailPanel
                        selectedNode={selectedNodeForDetailPanel as any} // Cast needed if types don't perfectly align
                        onNodeDataChange={handleNodeDataChange}
                    />
                 )*/}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Execute Agent: {selectedAgent.name}</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="executionParams">Execution Parameters (JSON)</Label>
                    <Textarea id="executionParams" value={executionParams} onChange={(e) => setExecutionParams(e.target.value)} rows={3}
                              placeholder={selectedAgent.agent_type === AgentType.FINANCIAL_HOST ? '{ "input_text": "Your query for financial agent" }' : '{ "input_data": "some_value" }'} />
                     <p className="text-xs text-gray-500 mt-1">
                       For FINANCIAL_HOST, use e.g., `{"input_text": "What is the stock price of GOOG?"}`.
                       For A2A/ADK mocks, use e.g., `{"data": "test"}`.
                     </p>
                  </div>
                  <Button onClick={handleExecuteAgent} disabled={isExecuting}>
                    {isExecuting ? 'Executing...' : 'Execute'}
                  </Button>
                </div>
              </CardContent>
              {executionResult && (
                <CardFooter className="mt-4">
                  <div>
                    <h4 className="font-semibold">Execution Result (Execution ID: {executionResult.execution_id})</h4>
                    <p>Status: {executionResult.status}</p>
                    {executionResult.result && <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">{JSON.stringify(executionResult.result, null, 2)}</pre>}
                    {executionResult.error && <p className="text-red-500">Error: {executionResult.error}</p>}
                    <p className="text-xs text-gray-500">Submitted: {new Date(executionResult.submitted_at).toLocaleString()}</p>
                    {executionResult.started_at && <p className="text-xs text-gray-500">Started: {new Date(executionResult.started_at).toLocaleString()}</p>}
                    {executionResult.completed_at && <p className="text-xs text-gray-500">Completed: {new Date(executionResult.completed_at).toLocaleString()}</p>}
                  </div>
                </CardFooter>
              )}
            </Card>
          </>
        ) : (
          <Card>
            <CardHeader><CardTitle>No Agent Selected</CardTitle></CardHeader>
            <CardContent>
              <p>Please select an agent from the list to see its details and execute it.</p>
            </CardContent>
          </Card>
        )}
        {error && <p className="text-red-500 mt-4">Error: {error}</p>}
      </div>
    </div>
  );
}
