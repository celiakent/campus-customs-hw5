import { AGENTS, AGENT_ORDER } from "../agents";
import { AgentFace } from "./AgentFace";
import type { AgentEvent, AgentName, BossDecision, SpecialistReport } from "../types";

/** Boss's final call, styled like a signed memo pinned to the ticket. */
export function BossMemo({ decision }: { decision: BossDecision }) {
  return (
    <section className="memo">
      <div className="memo-head">
        <span className="memo-label">
          <AgentFace agent="boss" size={34} /> The call
        </span>
        <span className="memo-status">Boss marked it: {decision.status.replace("_", " ")}</span>
      </div>
      <p className="memo-decision">{decision.decision}</p>
      <p className="memo-reason">{decision.reasoning}</p>
      {decision.next_steps.length > 0 && (
        <>
          <div className="memo-sub">Next steps for you</div>
          <ul>
            {decision.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </>
      )}
      <div className="memo-sign">— Boss</div>
    </section>
  );
}

/** One card per agent: what they did on this ticket, pulled from their final
 *  report(s) in the run. */
export function AgentSummaries({ events }: { events: AgentEvent[] }) {
  const reports = new Map<AgentName, AgentEvent[]>();
  for (const e of events) {
    if (e.event === "final_output") {
      reports.set(e.agent, [...(reports.get(e.agent) ?? []), e]);
    }
  }
  const toolsUsed = new Map<AgentName, Set<string>>();
  for (const e of events) {
    if (e.event === "model_response") {
      const s = toolsUsed.get(e.agent) ?? new Set<string>();
      e.tools_called.forEach((t) => s.add(t.tool));
      toolsUsed.set(e.agent, s);
    }
  }
  const agents = AGENT_ORDER.filter((a) => reports.has(a) && a !== "boss");
  if (!agents.length) return null;

  return (
    <section className="summaries">
      <h3 className="display-sm">What each agent did</h3>
      <div className="summary-grid">
        {agents.map((name) => {
          const a = AGENTS[name];
          const outs = reports.get(name)!;
          const r = outs[outs.length - 1].output as unknown as SpecialistReport;
          const tools = [...(toolsUsed.get(name) ?? [])].filter((t) => t !== "final_result");
          return (
            <article
              key={name}
              className="summary-card"
              style={{ "--agent": a.color } as React.CSSProperties}
            >
              <header>
                <AgentFace agent={name} size={40} />
                <div>
                  <div className="summary-name">{a.label}</div>
                  <div className="summary-role">{a.role}</div>
                </div>
              </header>
              <p>{r.summary}</p>
              {r.actions_taken?.length > 0 && (
                <div className="summary-block">
                  <div className="summary-sub">Did</div>
                  <ul>
                    {r.actions_taken.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                </div>
              )}
              {r.blockers?.length > 0 && (
                <div className="summary-block blockers">
                  <div className="summary-sub">Blocked by</div>
                  <ul>
                    {r.blockers.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                </div>
              )}
              {tools.length > 0 && (
                <div className="summary-tools">
                  {tools.map((t) => (
                    <code key={t}>{t}</code>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
