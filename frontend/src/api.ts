import type {
  AgentEvent,
  ApprovalRequest,
  Cash,
  Draft,
  Run,
  TicketsResponse,
} from "./types";

// The FastAPI backend from Problem 7. Override with VITE_API_URL if needed.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, body.detail ?? `${res.status} ${res.statusText}`);
  }
  return body as T;
}

export const api = {
  health: () => request<{ ok: boolean; model: string; date_today: string }>("/api/health"),
  tickets: () => request<TicketsResponse>("/api/tickets"),
  runTicket: (id: number) => request<Run>(`/api/tickets/${id}/run`, { method: "POST" }),
  runs: () => request<{ runs: Run[] }>("/api/runs"),
  events: (ticketId: number) =>
    request<{ events: AgentEvent[] }>(`/api/events?ticket_id=${ticketId}&limit=1000`),
  cash: () => request<Cash>("/api/cash"),
  approvals: () => request<{ requests: ApprovalRequest[] }>("/api/approvals?status=all"),
  approve: (id: number, approver: string) =>
    request<{ ok: boolean; new_balance: number }>(`/api/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approver }),
    }),
  reject: (id: number, approver: string) =>
    request<{ ok: boolean }>(`/api/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ approver }),
    }),
  drafts: () => request<{ drafts: Draft[] }>("/api/drafts"),
  reset: () => request<{ ok: boolean; message: string }>("/api/reset", { method: "POST" }),
};
