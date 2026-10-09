import type { AgentName } from "../types";

interface Props {
  agent: AgentName;
  size?: number;
  /** "working" = this agent is the one thinking right now */
  state?: "idle" | "working" | "off";
  title?: string;
}

/**
 * Each agent is one brand-colored circle with a minimal face — not an emoji,
 * just a few strokes — and one small signature animation:
 *
 *  Boss             ink #131718   stern: angled brows, flat mouth, slow blink
 *  Inventory        sky #D1E6F6   round spectacles, eyes scan left↔right
 *  Accounting       cream #FFF6C6 serious: level brows, eyes drop to the ledger
 *  Facilities       peach #FEC29F calm handyman: relaxed eyes, gentle sway
 *  Customer Service pink #FFDAE4  cheery: big smile, rosy cheeks, little hop
 *
 * While an agent is working, its mouth "talks".
 */
export function AgentFace({ agent, size = 56, state = "idle", title }: Props) {
  const ink = "#131718";
  const cls = `face face-${agent} ${state}`;
  return (
    <svg
      className={cls}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label={title ?? agent}
    >
      {title && <title>{title}</title>}
      {agent === "boss" && (
        <g className="body">
          <circle cx="50" cy="50" r="47" fill="#131718" />
          <g className="brows" stroke="#fff" strokeWidth="5" strokeLinecap="round">
            <line x1="26" y1="35" x2="42" y2="41" />
            <line x1="74" y1="35" x2="58" y2="41" />
          </g>
          <g className="eyes blink" fill="#fff">
            <rect x="30" y="47" width="11" height="6" rx="3" />
            <rect x="59" y="47" width="11" height="6" rx="3" />
          </g>
          <rect className="mouth" x="38" y="68" width="24" height="4.5" rx="2.25" fill="#fff" />
        </g>
      )}

      {agent === "inventory" && (
        <g className="body">
          <circle cx="50" cy="50" r="46" fill="#D1E6F6" stroke={ink} strokeWidth="3" />
          <g fill="none" stroke={ink} strokeWidth="3.5">
            <circle cx="35" cy="46" r="11" />
            <circle cx="65" cy="46" r="11" />
            <path d="M46 45 Q50 41 54 45" />
            <line x1="24" y1="44" x2="13" y2="40" />
            <line x1="76" y1="44" x2="87" y2="40" />
          </g>
          <g className="eyes scan" fill={ink}>
            <circle cx="35" cy="47" r="3.6" />
            <circle cx="65" cy="47" r="3.6" />
          </g>
          <path className="glint" d="M58 39 l4 -4" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
          <path className="mouth" d="M41 70 Q50 75 59 70" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
        </g>
      )}

      {agent === "accounting" && (
        <g className="body">
          <circle cx="50" cy="50" r="46" fill="#FFF6C6" stroke={ink} strokeWidth="3" />
          <g stroke={ink} strokeWidth="4" strokeLinecap="round">
            <line x1="27" y1="36" x2="42" y2="36" />
            <line x1="58" y1="36" x2="73" y2="36" />
          </g>
          <g className="eyes read" fill={ink}>
            <circle cx="35" cy="47" r="4" />
            <circle cx="65" cy="47" r="4" />
          </g>
          <rect className="mouth" x="42" y="68" width="16" height="4" rx="2" fill={ink} />
        </g>
      )}

      {agent === "facilities" && (
        <g className="body sway">
          <circle cx="50" cy="50" r="46" fill="#FEC29F" stroke={ink} strokeWidth="3" />
          <g fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round">
            <path d="M28 47 Q35 52 42 47" />
            <path d="M58 47 Q65 52 72 47" />
          </g>
          <path className="mouth" d="M40 66 Q50 74 60 66" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
        </g>
      )}

      {agent === "customer_service" && (
        <g className="body hop">
          <circle cx="50" cy="50" r="46" fill="#FFDAE4" stroke={ink} strokeWidth="3" />
          <g fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round">
            <path d="M28 47 Q35 39 42 47" />
            <path className="wink" d="M58 47 Q65 39 72 47" />
          </g>
          <circle cx="27" cy="60" r="6" fill="#F7A9BE" />
          <circle cx="73" cy="60" r="6" fill="#F7A9BE" />
          <path className="mouth" d="M36 62 Q50 80 64 62 Z" fill={ink} />
        </g>
      )}
    </svg>
  );
}
