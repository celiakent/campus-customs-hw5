import { useEffect, useRef, useState } from "react";
import { AGENTS } from "../agents";
import { AgentFace } from "./AgentFace";
import type { AgentEvent, AgentName } from "../types";

const prettyTool = (tool: string) => tool.replaceAll("_", " ");

interface Props {
  events: AgentEvent[];
  running: boolean;
  activeAgent: AgentName | null;
}

function argsText(args: Record<string, unknown> | null) {
  if (!args) return "";
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === "string" ? JSON.stringify(v) : JSON.stringify(v)}`)
    .join(", ");
}

function shortResult(raw: string) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function ToolResults({ ev }: { ev: AgentEvent }) {
  const [open, setOpen] = useState(false);
  if (!ev.tool_results.length) return null;
  const names = ev.tool_results.map((r) => prettyTool(r.tool)).join(", ");
  return (
    <div className="result-row" style={{ marginLeft: ev.depth * 28 }}>
      <button className="result-toggle" onClick={() => setOpen(!open)}>
        <span className="paperclip" aria-hidden>
          ⎘
        </span>
        {AGENTS[ev.agent].label} got back: {names}
        <span className="caret">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="result-body">
          {ev.tool_results.map((r) => (
            <div key={r.call_id}>
              <div className="result-name">{r.tool}</div>
              <pre>{shortResult(r.result)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** "The floor": everything the agents say and do, in order, indented by how
 *  deep in the delegation chain they are. */
export function Floor({ events, running, activeAgent }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (running) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length, running]);

  if (!events.length) {
    return (
      <div className="floor empty">
        <div className="empty-faces" aria-hidden>
          <AgentFace agent="boss" size={40} />
          <AgentFace agent="inventory" size={40} />
          <AgentFace agent="accounting" size={40} />
          <AgentFace agent="facilities" size={40} />
          <AgentFace agent="customer_service" size={40} />
        </div>
        <p>The desk is quiet. Start the team and you’ll see every agent think, call tools, and hand work to each other here.</p>
      </div>
    );
  }

  return (
    <div className="floor">
      {events.map((ev, i) => {
        const a = AGENTS[ev.agent];
        const style = {
          "--agent": a.color,
          "--agent-text": a.text,
          marginLeft: ev.depth * 28,
        } as React.CSSProperties;
        const key = `${ev.ts}-${i}`;

        switch (ev.event) {
          case "run_start":
            if (ev.depth > 0) return null; // the handoff card already shows this
            return (
              <div key={key} className="floor-marker">
                <span>{a.label} picked up the ticket</span>
                <time>{new Date(ev.ts).toLocaleTimeString()}</time>
              </div>
            );

          case "delegation_start": {
            const to = AGENTS[ev.delegated_to as AgentName];
            return (
              <div key={key} className="handoff" style={style}>
                <div className="handoff-route">
                  <AgentFace agent={ev.agent} size={24} />
                  <span>{a.label}</span>
                  <span className="arrow">⟶</span>
                  {to && <AgentFace agent={to.name} size={24} />}
                  <span>{to?.label ?? ev.delegated_to}</span>
                </div>
                <div className="handoff-task">“{ev.said}”</div>
              </div>
            );
          }

          case "delegation_end": {
            const from = AGENTS[ev.delegated_to as AgentName];
            return (
              <div key={key} className="floor-note" style={style}>
                ↩ {from?.label} reported back to {a.label}
              </div>
            );
          }

          case "delegation_refused":
            return (
              <div key={key} className="floor-note warn" style={style}>
                ⚠ {a.label} tried to hand off to {AGENTS[ev.delegated_to as AgentName]?.label}:{" "}
                {ev.reason}
              </div>
            );

          case "model_response": {
            const tools = ev.tools_called.filter((t) => t.tool !== "delegate");
            if (!ev.said && !tools.length) return null;
            return (
              <div key={key} className="bubble" style={style}>
                <AgentFace agent={ev.agent} size={34} />
                <div className="bubble-body">
                  <div className="bubble-who">{a.label}</div>
                  {ev.said && <p className="bubble-text">{ev.said}</p>}
                  {tools.length > 0 && (
                    <div className="tool-chips">
                      {tools.map((t, j) => (
                        <code key={j} className="tool-chip" title={argsText(t.args)}>
                          <span className="wrench" aria-hidden>
                            ⚙
                          </span>
                          {t.tool}
                          {t.args && Object.keys(t.args).length > 0 && (
                            <span className="tool-args">({argsText(t.args)})</span>
                          )}
                        </code>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          }

          case "tool_results":
            return <ToolResults key={key} ev={ev} />;

          case "final_output":
            return (
              <div key={key} className="bubble final" style={style}>
                <AgentFace agent={ev.agent} size={34} />
                <div className="bubble-body">
                  <div className="bubble-who">
                    {a.label} <span className="final-tag">{ev.depth === 0 ? "final call" : "report"}</span>
                  </div>
                  <p className="bubble-text">{ev.said}</p>
                </div>
              </div>
            );

          case "error":
            return (
              <div key={key} className="floor-note error" style={style}>
                ✕ {a.label} hit an error: {ev.said}
              </div>
            );

          default:
            return null;
        }
      })}

      {running && activeAgent && (
        <div className="typing">
          <AgentFace agent={activeAgent} size={30} state="working" />
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
          {AGENTS[activeAgent].label} is working
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
