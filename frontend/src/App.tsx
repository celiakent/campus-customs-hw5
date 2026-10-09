import { useCallback, useMemo, useState } from "react";
import { api, ApiError } from "./api";
import { AgentRoster } from "./components/AgentRoster";
import { Floor } from "./components/Floor";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { Ledger } from "./components/Ledger";
import { Outbox } from "./components/Outbox";
import { AgentSummaries, BossMemo } from "./components/Summaries";
import { TicketInbox } from "./components/TicketInbox";
import { useInterval, useStoredString } from "./hooks";
import type {
  AgentEvent,
  AgentName,
  ApprovalRequest,
  BossDecision,
  Cash,
  Draft,
  Run,
  Ticket,
} from "./types";

interface Toast {
  kind: "ok" | "err";
  text: string;
}

export default function App() {
  const [online, setOnline] = useState(false);
  const [model, setModel] = useState<string | null>(null);
  const [dateToday, setDateToday] = useState<string | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  // ?ticket=101 opens the board on that ticket (handy for links and screenshots)
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const t = Number(new URLSearchParams(window.location.search).get("ticket"));
    return Number.isFinite(t) && t > 0 ? t : null;
  });
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [runIndex, setRunIndex] = useState<number | null>(null); // null = latest
  const [cash, setCash] = useState<Cash | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [approver, setApprover] = useStoredString("cc-approver");
  const [toast, setToast] = useState<Toast | null>(null);
  const [starting, setStarting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [lastDrop, setLastDrop] = useState<number | null>(null);

  const flash = (t: Toast) => {
    setToast(t);
    setTimeout(() => setToast(null), 4500);
  };

  const runningIds = useMemo(
    () =>
      new Set([
        ...runs.filter((r) => r.status === "running").map((r) => r.ticket_id),
        ...tickets.filter((t) => t.agents_running).map((t) => t.id),
      ]),
    [runs, tickets],
  );
  const anyRunning = runningIds.size > 0;

  // ---- polling ------------------------------------------------------------
  const refreshBoard = useCallback(async () => {
    try {
      const [h, t, r, c, a, d] = await Promise.all([
        api.health(),
        api.tickets(),
        api.runs(),
        api.cash(),
        api.approvals(),
        api.drafts(),
      ]);
      setOnline(true);
      setModel(h.model);
      setDateToday(t.date_today);
      setTickets(t.tickets);
      setRuns(r.runs);
      setCash(c);
      setApprovals(a.requests);
      setDrafts(d.drafts);
      setSelectedId((cur) => cur ?? t.tickets[0]?.id ?? null);
    } catch {
      setOnline(false);
    }
  }, []);

  const refreshEvents = useCallback(async () => {
    if (selectedId == null) return;
    try {
      const e = await api.events(selectedId);
      setEvents(e.events);
    } catch {
      /* board refresh reports offline */
    }
  }, [selectedId]);

  useInterval(refreshBoard, anyRunning ? 1500 : 4000);
  useInterval(refreshEvents, anyRunning ? 1200 : 4000);

  // ---- derived view of the selected ticket ------------------------------------
  const ticket = tickets.find((t) => t.id === selectedId) ?? null;
  const runIds = useMemo(() => [...new Set(events.map((e) => e.run_id))], [events]);
  const shownRunId = runIds.length
    ? runIds[runIndex == null ? runIds.length - 1 : Math.min(runIndex, runIds.length - 1)]
    : null;
  const runEvents = useMemo(
    () => events.filter((e) => e.run_id === shownRunId),
    [events, shownRunId],
  );
  const runIsLive =
    !!shownRunId && runs.some((r) => r.run_id === shownRunId && r.status === "running");

  const involved = useMemo(() => {
    const s = new Set<AgentName>();
    runEvents.forEach((e) => {
      s.add(e.agent);
      if (e.delegated_to && e.event === "delegation_start") s.add(e.delegated_to);
    });
    return s;
  }, [runEvents]);

  const activeAgent: AgentName | null = useMemo(() => {
    const last = runEvents[runEvents.length - 1];
    if (!last) return runIsLive ? "boss" : null;
    if (last.event === "delegation_start" && last.delegated_to) return last.delegated_to;
    if (last.event === "final_output" && last.chain.length > 1)
      return last.chain[last.chain.length - 2];
    return last.agent;
  }, [runEvents, runIsLive]);

  const bossDecision = useMemo(() => {
    const fin = runEvents.filter((e) => e.event === "final_output" && e.depth === 0).pop();
    return (fin?.output as unknown as BossDecision) ?? null;
  }, [runEvents]);

  const ticketDrafts = drafts.filter((d) => d.ticket_id === selectedId);
  const ticketRunning = selectedId != null && runningIds.has(selectedId);

  // ---- actions --------------------------------------------------------------------
  const startRun = async () => {
    if (selectedId == null) return;
    setStarting(true);
    try {
      await api.runTicket(selectedId);
      setRunIndex(null);
      flash({ kind: "ok", text: `The team picked up ticket #${selectedId}.` });
      await refreshBoard();
      await refreshEvents();
    } catch (e) {
      flash({ kind: "err", text: e instanceof ApiError ? e.message : String(e) });
    } finally {
      setStarting(false);
    }
  };

  const approve = async (id: number) => {
    const before = cash?.balance ?? 0;
    try {
      const r = await api.approve(id, approver);
      setLastDrop(before - r.new_balance);
      setTimeout(() => setLastDrop(null), 2600);
      flash({ kind: "ok", text: `Signed and paid. Checking is now $${r.new_balance.toLocaleString()}.` });
    } catch (e) {
      flash({ kind: "err", text: e instanceof ApiError ? e.message : String(e) });
    }
    await refreshBoard();
  };

  const reject = async (id: number) => {
    try {
      await api.reject(id, approver);
      flash({ kind: "ok", text: `Request #${id} rejected. No money moved.` });
    } catch (e) {
      flash({ kind: "err", text: e instanceof ApiError ? e.message : String(e) });
    }
    await refreshBoard();
  };

  const reset = async () => {
    if (!window.confirm("Reset the working database to the original values? Tickets reopen and cash goes back to $3,400. The audit trail is kept.")) return;
    setResetting(true);
    try {
      const r = await api.reset();
      setRunIndex(null);
      flash({ kind: "ok", text: r.message });
      await refreshBoard();
    } catch (e) {
      flash({ kind: "err", text: e instanceof ApiError ? e.message : String(e) });
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="app">
      <Header dateToday={dateToday} model={model} online={online} onReset={reset} resetting={resetting} />

      {!online && (
        <div className="offline">
          Can’t reach the backend at <code>http://localhost:8000</code>. Start it from <code>backend/</code> with{" "}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="page">
        <Hero
          ticket={ticket}
          tickets={tickets}
          cash={cash}
          running={ticketRunning}
          starting={starting}
          online={online}
          onStart={startRun}
        />

        <TicketInbox
          tickets={tickets}
          selectedId={selectedId}
          runningIds={runningIds}
          onSelect={(id) => {
            setSelectedId(id);
            setRunIndex(null);
            setEvents([]);
          }}
        />

        <div className="split">
          <div className="split-main">
            <section className="band pink" id="team">
              <div className="band-head">
                <h2 className="display">The team</h2>
                {runIds.length > 1 && (
                  <div className="run-picker">
                    {runIds.map((id, i) => (
                      <button key={id} className={id === shownRunId ? "on" : ""} onClick={() => setRunIndex(i)}>
                        Run {i + 1}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <AgentRoster involved={involved} active={activeAgent} running={runIsLive} />
              {bossDecision && !runIsLive && <BossMemo decision={bossDecision} />}
              {!runIsLive && <AgentSummaries events={runEvents} />}
              {!runIsLive && <Outbox drafts={ticketDrafts} />}
            </section>

            <section className="band white" id="floor">
              <div className="band-head">
                <h2 className="display">On the floor</h2>
                <p className="band-sub">Everything the agents say and every tool they call, live.</p>
              </div>
              <Floor events={runEvents} running={runIsLive} activeAgent={activeAgent} />
            </section>
          </div>

          <Ledger
            cash={cash}
            approvals={approvals}
            approver={approver}
            setApprover={setApprover}
            onApprove={approve}
            onReject={reject}
            lastDrop={lastDrop}
          />
        </div>
      </main>

      {toast && <div className={`toast ${toast.kind}`}>{toast.text}</div>}
    </div>
  );
}
