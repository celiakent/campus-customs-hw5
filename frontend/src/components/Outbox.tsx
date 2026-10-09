import { AGENTS } from "../agents";
import { AgentFace } from "./AgentFace";
import type { AgentName, Draft } from "../types";

/** Customer drafts, shown as unsent letters. Nothing here is ever sent. */
export function Outbox({ drafts }: { drafts: Draft[] }) {
  if (!drafts.length) return null;
  return (
    <section className="outbox">
      <h3 className="display-sm">
        Outbox <span className="outbox-note">drafts only · a human sends these</span>
      </h3>
      {drafts.map((d) => {
        const a = AGENTS[d.drafted_by as AgentName] ?? AGENTS.customer_service;
        return (
          <article key={d.id} className="letter">
            <div className="letter-head">
              <div>
                <div className="letter-to">To: {d.recipient}</div>
                <div className="letter-subject">{d.subject}</div>
              </div>
              <span className="letter-badge">Draft #{d.id} · not sent</span>
            </div>
            <div className="letter-body">{d.body}</div>
            <div className="letter-foot">
              <AgentFace agent={a.name} size={22} /> drafted by {a.label}
            </div>
          </article>
        );
      })}
    </section>
  );
}
