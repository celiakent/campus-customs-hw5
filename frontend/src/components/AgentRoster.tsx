import { AGENTS, AGENT_ORDER } from "../agents";
import type { AgentName } from "../types";
import { AgentFace } from "./AgentFace";

interface Props {
  involved: Set<AgentName>;
  active: AgentName | null;
  running: boolean;
}

/** The five faces. Agents the ticket doesn't need fade back; the one working
 *  right now gets a ring and starts talking. */
export function AgentRoster({ involved, active, running }: Props) {
  const anyone = involved.size > 0;
  return (
    <div className="team-row">
      {AGENT_ORDER.map((name) => {
        const a = AGENTS[name];
        const working = running && active === name;
        const joined = involved.has(name);
        const state = working ? "working" : anyone && !joined ? "off" : "idle";
        return (
          <div key={name} className={`member ${state}`}>
            <div className="member-face">
              <AgentFace agent={name} size={84} state={state} title={a.label} />
            </div>
            <div className="member-name">{a.label}</div>
            <div className="member-role">{a.role}</div>
            <div className="member-state">
              {working ? "working…" : !anyone ? a.personality : joined ? "on this ticket" : "not needed"}
            </div>
          </div>
        );
      })}
    </div>
  );
}
