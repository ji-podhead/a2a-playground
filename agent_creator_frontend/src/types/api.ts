export enum AgentType {
  MCP = "mcp",
  A2A = "a2a",
  ADK = "adk", // Added
  FINANCIAL_HOST = "financial_host", // Added
  CUSTOM = "custom_agent_type",
}

export enum AgentStatus {
  CREATED = "created",
  READY = "ready",
  RUNNING = "running",
  STOPPED = "stopped",
  ERROR = "error",
  UPDATED = "updated",
}

export enum ExecutionStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface Agent {
  agent_id: string; // UUID
  name: string;
  agent_type: AgentType;
  config: Record<string, any>;
  status: AgentStatus;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

export interface AgentCreatePayload {
  name: string;
  agent_type: AgentType;
  config: Record<string, any>;
}

export interface AgentUpdatePayload {
  name?: string;
  config?: Record<string, any>;
}

export interface Execution {
  execution_id: string; // UUID
  agent_id: string; // UUID
  parameters: Record<string, any>;
  status: ExecutionStatus;
  submitted_at: string; // ISO datetime string
  started_at?: string | null; // ISO datetime string
  completed_at?: string | null; // ISO datetime string
  result?: Record<string, any> | null;
  error?: string | null;
}

export interface ExecutionCreatePayload {
  parameters: Record<string, any>;
}
