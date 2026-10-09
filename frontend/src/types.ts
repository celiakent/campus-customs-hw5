export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  notes: string | null;
  created_at: string;
  is_resolved: boolean;
  agents_running: boolean;
}

export interface TicketsResponse {
  date_today: string;
  tickets: Ticket[];
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown> | null;
}

export interface ToolResult {
  tool: string;
  call_id: string;
  result: string;
}

export type EventKind =
  | "run_start"
  | "model_request"
  | "model_response"
  | "tool_results"
  | "delegation_start"
  | "delegation_end"
  | "delegation_refused"
  | "final_output"
  | "error";

export interface AgentEvent {
  ts: string;
  run_id: string;
  ticket_id: number | null;
  agent: AgentName;
  depth: number;
  chain: AgentName[];
  event: EventKind;
  said: string | null;
  tools_called: ToolCall[];
  tool_results: ToolResult[];
  delegated_to: AgentName | null;
  output: Record<string, unknown> | null;
  reason: string | null;
}

export interface BossDecision {
  ticket_id: number;
  status: string;
  decision: string;
  reasoning: string;
  agents_consulted: AgentName[];
  approvals_needed: string[];
  drafts_for_review: string[];
  next_steps: string[];
}

export interface SpecialistReport {
  summary: string;
  facts: string[];
  actions_taken: string[];
  blockers: string[];
  recommendation: string;
}

export interface Run {
  run_id: string;
  ticket_id: number;
  status: "running" | "done" | "error";
  started_at: string;
  finished_at: string | null;
  decision: BossDecision | null;
  boss_status: string | null;
  error: string | null;
}

export interface Cash {
  name: string;
  balance: number;
  date: string;
  pending_requests_total: number;
  balance_after_pending: number;
}

export interface ApprovalRequest {
  id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number | null;
  payee: string;
  amount: number;
  account: string;
  ticket_id: number | null;
  requested_by: string;
  reason: string;
  details: string | null;
  status: "pending" | "paid" | "rejected";
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
}

export interface Draft {
  id: number;
  ticket_id: number;
  recipient: string;
  subject: string;
  body: string;
  drafted_by: string;
  status: string;
  created_at: string;
}
