import { TICKET_KIND, ticketPhotos } from "../agents";
import type { Ticket } from "../types";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  runningIds: Set<number>;
  onSelect: (id: number) => void;
}

/** "The board": numbered photo cards on a cream band, like the tour cards in
 *  the inspiration. The selected ticket lights up yellow. */
export function TicketInbox({ tickets, selectedId, runningIds, onSelect }: Props) {
  return (
    <section className="band cream" id="board">
      <div className="band-head">
        <h2 className="display">The board</h2>
        <p className="band-sub">Pick a ticket, then start the team from the top.</p>
      </div>

      <div className="ticket-row">
        {tickets.map((t, i) => {
          const photos = ticketPhotos(t);
          const running = runningIds.has(t.id);
          const selected = selectedId === t.id;
          return (
            <button
              key={t.id}
              className={`tcard ${selected ? "selected" : ""} ${t.is_resolved ? "resolved" : ""}`}
              onClick={() => onSelect(t.id)}
            >
              <div className={`tcard-photo n${photos.srcs.length}`}>
                <span className="tcard-num">{String(i + 1).padStart(2, "0")}</span>
                {photos.srcs.map((src) => (
                  <img key={src} src={src} alt="" />
                ))}
                {t.is_resolved && <span className="tcard-stamp">Resolved</span>}
              </div>
              <div className="tcard-body">
                <div className="tcard-title">
                  {t.subject}
                  <span className="tcard-arrow">↗</span>
                </div>
                <div className="tcard-meta">
                  #{t.id} · {TICKET_KIND[t.type]?.label ?? t.type} · from {t.requester}
                </div>
                <div className="tcard-status">
                  {running ? (
                    <span className="chip live">
                      <span className="pulse" /> agents working
                    </span>
                  ) : t.is_resolved ? (
                    <span className="chip done">resolved</span>
                  ) : (
                    <span className="chip">{t.status.replace("_", " ")}</span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
