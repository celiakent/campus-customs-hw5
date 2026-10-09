import { TICKET_KIND, money, ticketPhotos } from "../agents";
import type { Cash, Ticket } from "../types";

interface Props {
  ticket: Ticket | null;
  tickets: Ticket[];
  cash: Cash | null;
  running: boolean;
  starting: boolean;
  online: boolean;
  onStart: () => void;
}

/** The big sky-blue hero: the selected ticket's name in huge type over its
 *  photo, a description, and the black "Start the team" button tucked into a
 *  notch in the corner. Underneath sits a three-up stats row. */
export function Hero({ ticket, tickets, cash, running, starting, online, onStart }: Props) {
  const kind = ticket ? TICKET_KIND[ticket.type]?.label ?? ticket.type : "";
  const photos = ticketPhotos(ticket);
  const open = tickets.filter((t) => !t.is_resolved).length;

  return (
    <section className="hero-panel" id="top">
      <div className="hero">
        <div className={`hero-photos n${photos.srcs.length}`} aria-hidden>
          {photos.srcs.map((src) => (
            <img key={src} src={src} alt="" />
          ))}
        </div>

        <div className="hero-copy">
          <div className="hero-kicker">
            {ticket ? `Ticket #${ticket.id} · ${kind}` : "Operations desk"}
          </div>
          <h1 className="hero-title">{ticket ? ticket.subject : "Run the desk"}</h1>

          {ticket && (
            <div className="hero-left-note">
              <p>From {ticket.requester}.</p>
              {ticket.notes && <p>“{ticket.notes.split("\n")[0]}”</p>}
            </div>
          )}

          {ticket && (
            <div className="hero-right-note">
              <p className="lead">
                {ticket.sku
                  ? `${ticket.qty} × ${ticket.sku}${ticket.size ? ` · size ${ticket.size}` : ""}`
                  : ticket.lease_id
                    ? `Lease #${ticket.lease_id} · the Chapel Street shop`
                    : ""}
                {ticket.invoice_id ? ` · invoice #${ticket.invoice_id}` : ""}
              </p>
              <p>
                Boss reads it, calls in only the agents it needs, and leaves anything that costs money
                for you to sign.
              </p>
              <p className="photo-caption">Photo: {photos.caption}</p>
            </div>
          )}

          {ticket?.is_resolved && !running && <div className="hero-stamp">Resolved</div>}
        </div>

        <div className="hero-notch">
          <button className="btn-black" disabled={!ticket || running || starting || !online} onClick={onStart}>
            {running ? (
              <>
                <span className="spinner" /> Team is working
              </>
            ) : ticket?.is_resolved ? (
              <>Run the team again <span className="arrow">→</span></>
            ) : (
              <>Start the team <span className="arrow">→</span></>
            )}
          </button>
        </div>
      </div>

      <div className="stats">
        <div>
          <div className="stat-big">{tickets.length} tickets</div>
          <p>
            {open} open, {tickets.length - open} resolved on the board right now
          </p>
        </div>
        <div>
          <div className="stat-big">{cash ? money(cash.balance) : "—"}</div>
          <p>in checking. Cash only goes out, and nothing is paid without your signature</p>
        </div>
        <div>
          <div className="stat-big">Pro team</div>
          <p>five agents on gpt-6-luna that hand work to each other</p>
        </div>
      </div>
    </section>
  );
}
