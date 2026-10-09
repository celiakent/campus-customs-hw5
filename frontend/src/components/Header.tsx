interface Props {
  dateToday: string | null;
  model: string | null;
  online: boolean;
  onReset: () => void;
  resetting: boolean;
}

export function Header({ dateToday, model, online, onReset, resetting }: Props) {
  const d = dateToday ? new Date(`${dateToday}T12:00:00`) : null;
  return (
    <nav className="topnav">
      <a className="wordmark" href="#top">
        Campus Customs<sup>®</sup>
      </a>

      <div className="navlinks">
        <div>
          <a href="#board">Tickets</a>
          <a href="#team">The team</a>
        </div>
        <div>
          <a href="#floor">On the floor</a>
          <a href="#cash">Cash &amp; approvals</a>
        </div>
      </div>

      <div className="nav-right">
        <span className={`nav-pill status ${online ? "on" : "off"}`}>
          <span className="dot" /> {online ? model ?? "online" : "offline"}
        </span>
        {d && (
          <span className="nav-pill" title="desk.date_today, the shop's 'today'">
            {d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </span>
        )}
        <button className="nav-pill btn-pill" onClick={onReset} disabled={resetting}>
          {resetting ? "Resetting…" : "Reset desk ↺"}
        </button>
      </div>
    </nav>
  );
}
