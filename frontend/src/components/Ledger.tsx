import { useState } from "react";
import { money } from "../agents";
import { useAnimatedNumber } from "../hooks";
import type { ApprovalRequest, Cash } from "../types";

interface Props {
  cash: Cash | null;
  approvals: ApprovalRequest[];
  approver: string;
  setApprover: (s: string) => void;
  onApprove: (id: number) => Promise<void>;
  onReject: (id: number) => Promise<void>;
  lastDrop: number | null;
}

const KIND_LABEL: Record<ApprovalRequest["kind"], string> = {
  invoice: "Vendor invoice",
  rent: "Rent",
  purchase_order: "Purchase order",
};

function Slip({
  req,
  balance,
  approver,
  onApprove,
  onReject,
}: {
  req: ApprovalRequest;
  balance: number;
  approver: string;
  onApprove: (id: number) => Promise<void>;
  onReject: (id: number) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const short = req.amount > balance;
  const pending = req.status === "pending";
  const act = async (fn: (id: number) => Promise<void>) => {
    setBusy(true);
    try {
      await fn(req.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className={`slip ${req.status}`}>
      <div className="slip-top">
        <span className="slip-kind">{KIND_LABEL[req.kind]}</span>
        <span className="slip-no">No. {String(req.id).padStart(4, "0")}</span>
      </div>
      <div className="slip-payee">
        <span className="slip-label">Pay to the order of</span>
        <span className="slip-payee-name">{req.payee}</span>
      </div>
      <div className="slip-amount">{money(req.amount)}</div>
      <div className="slip-memo">
        <span className="slip-label">Memo</span> {req.details ?? req.reason}
        {req.ticket_id && <span className="slip-ticket"> · ticket #{req.ticket_id}</span>}
      </div>
      <div className="slip-prep">prepared by {req.requested_by.replace("_", " ")}</div>

      {pending ? (
        <>
          {short && (
            <div className="slip-warn">
              Not enough cash: {money(balance)} on hand. The bank will refuse this.
            </div>
          )}
          <div className="slip-actions">
            <button
              className="btn sign"
              disabled={busy || !approver.trim()}
              onClick={() => act(onApprove)}
              title={!approver.trim() ? "Type your name above to sign" : "Approve and pay"}
            >
              {busy ? "…" : "✍ Sign & pay"}
            </button>
            <button className="btn link" disabled={busy || !approver.trim()} onClick={() => act(onReject)}>
              Reject
            </button>
          </div>
        </>
      ) : (
        <div className="slip-decided">
          {req.status === "paid" ? "Approved" : "Rejected"} by {req.decided_by}
        </div>
      )}
      {req.status !== "pending" && <div className={`stamp ${req.status}`}>{req.status}</div>}
    </article>
  );
}

export function Ledger({ cash, approvals, approver, setApprover, onApprove, onReject, lastDrop }: Props) {
  const balance = useAnimatedNumber(cash?.balance ?? 0);
  const pending = approvals.filter((a) => a.status === "pending");
  const decided = approvals.filter((a) => a.status !== "pending").slice().reverse();
  const committedPct =
    cash && cash.balance > 0 ? Math.min(100, (cash.pending_requests_total / cash.balance) * 100) : 0;

  return (
    <aside className="ledger" id="cash">
      <h2 className="display">Cash</h2>

      <section className="balance-card">
        <div className="balance-label">Checking balance</div>
        <div className="balance-amount">{money(balance)}</div>
        {lastDrop !== null && <div className="balance-drop">−{money(lastDrop)}</div>}
        {cash && (
          <>
            <div className="commit-bar" aria-hidden>
              <div
                className={`commit-fill ${cash.balance_after_pending < 0 ? "over" : ""}`}
                style={{ width: `${committedPct}%` }}
              />
            </div>
            <div className="balance-meta">
              <span>{money(cash.pending_requests_total)} waiting for approval</span>
              <span className={cash.balance_after_pending < 0 ? "neg" : ""}>
                {money(cash.balance_after_pending)} left if all approved
              </span>
            </div>
          </>
        )}
        <div className="balance-note">Cash only goes out in this shop. Nothing is paid without a signature.</div>
      </section>

      <label className="signer">
        <span>Signing as</span>
        <input
          value={approver}
          onChange={(e) => setApprover(e.target.value)}
          placeholder="Your name"
        />
      </label>

      <div className="slips">
        {pending.length === 0 && (
          <div className="slips-empty">No payments waiting. When Accounting prepares one, it lands here for you to sign.</div>
        )}
        {pending.map((r) => (
          <Slip
            key={r.id}
            req={r}
            balance={cash?.balance ?? 0}
            approver={approver}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
        {decided.length > 0 && <div className="slips-divider">Signed &amp; filed</div>}
        {decided.map((r) => (
          <Slip
            key={r.id}
            req={r}
            balance={cash?.balance ?? 0}
            approver={approver}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
      </div>
    </aside>
  );
}
