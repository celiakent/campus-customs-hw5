# Campus Customs Multi-Agent Operations — Harness

The complete harness for the Campus Customs agent team: the data it works on, the MCP tools it's allowed to use, the five agents, the API, the dashboard, and the safety rules around real money and real customers.

- Original database: `data/campus_customs.db` (never modified; used to reset)
- Working copy: `data/campus_customs_new.db` (the MCP server and backend read and write this one)
- Model: **`gpt-6-luna`** for every agent, through Portkey (Responses API)

**How the pieces connect:** React dashboard (`frontend/`, :5173) → FastAPI (`backend/main.py`, :8000) → PydanticAI agent team (`backend/agents.py`) → MCP server (`mcp_server/server.py`, stdio) → SQLite working copy. A human approves payments on the dashboard, and that approve route is the only thing that calls the MCP pay tool.

| Section | Covers |
|---|---|
| 1–2 | Database tables and how the three tickets link to them |
| 3, 5 | MCP tools (the first three, then the full list with tables) |
| 4 | The five agents, delegation, and the agent loop |
| 6 | Safety rules and token limits |
| 7 | API routes |
| 8 | Dashboard |
| 9 | Full run results (Problem 9) |

---

## 1. Database tables

### `desk` (1 row)
Fields: `date_today`, `notes`

Why it matters: `date_today` (2026-08-31) is "today" for every agent, so all overdue and due-soon checks use it, not the real clock.

### `tickets` (3 rows)
Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`

Why it matters: this is the work board. Boss reads each open ticket and its `type` plus link fields (`sku`/`size`, `lease_id`, `invoice_id`) tell it which agents and tables to pull in.

### `inventory` (10 rows, key = `sku` + `size`)
Fields: `sku`, `name`, `size`, `qty`, `location`

Why it matters: Inventory checks stock per SKU and size here to spot shortfalls before anything is promised to a customer.

### `pricing` (4 rows)
Fields: `sku`, `unit_cost`, `list_price`

Why it matters: Accounting uses cost vs. list price to check margins on discount requests and to price purchase orders.

### `vendors` (3 rows)
Fields: `id`, `name`, `specialty`, `lead_days`

Why it matters: Inventory picks the vendor whose `specialty` fits the product, and `lead_days` sets when restocked goods can arrive.

### `invoices` (1 row)
Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`

Why it matters: an `open` invoice blocks that vendor from shipping new product, and Accounting compares `due_date` with `desk.date_today` to find overdue bills.

### `leases` (1 row)
Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

Why it matters: Facilities uses this to confirm rent amounts and due dates before Accounting prepares a rent payment.

### `cash_accounts` (1 row)
Fields: `name`, `balance`, `date`

Why it matters: this is the only money the shop has (cash only goes out), so the pay tool must check it and refuse any payment that would make it negative.

### `payments` (0 rows)
Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

Why it matters: this is the record of every approved payment, so `approved_by` shows that a human approved it and `ref_id` points back to the invoice or lease it paid.

---

## 2. How the three open tickets link to other tables

| Ticket | Type | Links | What the data shows |
|---|---|---|---|
| **101** — Tauhid Zaman, "Bulldog tee" | `customer_order` | `sku` CC-TEE-WHITE, `size` S, `qty` 1, `invoice_id` 501 | Inventory has **0** of the tee in S. Restocking apparel means Bulldog Print Co (vendor 1, 5 lead days), but **invoice 501** ($840, "Rush reprint CC-TEE-WHITE S") is still `open` and was due 2026-08-28, so it is **overdue** and blocks that vendor from shipping. |
| **102** — Elm City Properties, "Rent due" | `rent_notice` | `lease_id` 1 | Chapel Street shop lease, **$2,400** rent, `next_due` 2026-09-02, which is 2 days after `date_today`. Paying it needs human approval. |
| **103** — Yale AI Club, "Bulk hoodie discount" | `price_override` | `sku` CC-HOOD-NAVY, `size` M, `qty` 20 | Only **8** hoodies in M, so the shop is **12 short**. Pricing: cost $22 and list $58, so $36 margin per unit, which Accounting needs when judging a discount. A restock would also come from Bulldog Print Co, so it is blocked by invoice 501 too. |

### Cross-ticket constraints the agents must notice
- **One cash pool:** checking has **$3,400**. Invoice 501 ($840) plus rent ($2,400) is $3,240, which leaves **$160**. That is not enough for a 12-hoodie restock at cost (12 × $22 = $264). The team has to prioritize, and the pay tool has to refuse anything that would overdraw the account.
- **Invoice 501 is the bottleneck:** tickets 101 and 103 both need Bulldog Print Co, and that vendor won't ship until 501 is paid.
- **Everything with money waits for a human:** agents can only *prepare* payments or POs; a human approves them on the dashboard, and then the `payments`, `invoices`, and `cash_accounts` tables get updated.
- **Customer replies are drafts only:** Customer Service drafts messages to Tauhid and the Yale AI Club for the board and never sends them.

---

## 3. MCP tools (`mcp_server/server.py`)

All tools read `data/campus_customs_new.db` and return only what is in the database. A missing row comes back as `found: false` and the tool never makes up a value.

### `check_stock(sku, size=None)`
- **Reads:** `inventory`
- **Unlocks ticket:** **101** (Tauhid Zaman, Bulldog tee size S)
- **Why it's the right tool:** ticket 101 is a customer order for CC-TEE-WHITE in size S, and `check_stock` returns the exact qty for that SKU and size (0). That tells the team they can't fill the order from the shelf and need a restock first.

### `get_lease(lease_id)`
- **Reads:** `leases` (plus `desk.date_today`)
- **Unlocks ticket:** **102** (Elm City Properties rent notice)
- **Why it's the right tool:** ticket 102 only carries `lease_id` 1, and `get_lease` turns that into the real rent amount ($2,400), the landlord, and the due date (2026-09-02, 2 days after `date_today`). That lets Facilities check the landlord's email against the lease before Accounting prepares a payment for approval.

### `get_pricing(sku)`
- **Reads:** `pricing`
- **Unlocks ticket:** **103** (Yale AI Club, 20 hoodies size M, bulk discount)
- **Why it's the right tool:** ticket 103 is a price-override request, and `get_pricing` returns CC-HOOD-NAVY's unit cost ($22), list price ($58), and $36 margin per unit. Accounting needs those numbers to decide how big a discount the shop can afford without selling below cost.

---

## 4. Agent team (`backend/`)

Built with PydanticAI. Every agent runs on **`gpt-6-luna`** through Portkey (Responses API). The model name is a fixed constant in `backend/config.py` and nothing can override it. Each prompt lives in `backend/prompts/<agent>.md`, the data types are in `backend/models.py`, and the agents and their loop are in `backend/agents.py`.

| Agent | Role | Output type | MCP tools it can use |
|---|---|---|---|
| **Boss** (`boss.md`) | Reads each ticket, decides who works on it, makes the final call, sets the ticket status | `BossDecision` | get_desk_date, list_open_tickets, get_ticket, update_ticket, list_approval_requests, get_cash_balance |
| **Inventory** (`inventory.md`) | Stock by SKU and size, shortfalls, which vendor can restock, lead-time arrival dates, vendor holds | `SpecialistReport` | get_desk_date, get_ticket, check_stock, list_vendors, list_invoices, get_pricing |
| **Accounting** (`accounting.md`) | Cash, invoices, margins and discount math; the only agent that prepares payments and POs (all pending human approval) | `SpecialistReport` | get_desk_date, get_ticket, get_cash_balance, list_invoices, list_vendors, get_pricing, quote_discount, get_lease, request_payment, create_purchase_order, list_approval_requests |
| **Facilities** (`facilities.md`) | Shop space: checks rent notices against the lease, works out urgency from date_today | `SpecialistReport` | get_desk_date, get_ticket, get_lease, list_approval_requests |
| **Customer Service** (`customer_service.md`) | Drafts honest customer messages with confirmed facts; drafts only, never sent | `SpecialistReport` | get_desk_date, get_ticket, check_stock, get_pricing, quote_discount, list_vendors, draft_customer_message |

**Full connectivity:** every agent also has a `delegate(to_agent, task)` tool that can call *any* other agent, Boss included. The delegated agent runs its own loop and returns its structured report as the tool result. For example, in the ticket 102 test run Boss delegated to Facilities, and Facilities delegated to Accounting to prepare the rent request.

**Agent loop:** `run_agent()` drives each agent with `Agent.iter()` one node at a time (model request, model response with tool calls, tool results, final output) and appends every step to `output/audit_trail.json` as it happens.

**Running (from `backend/`):** `python reset_db.py` restores the working DB from the original, `python run_ticket.py 101` (or `--all`) runs a ticket, and `uvicorn main:app --reload --port 8000` starts the API (section 7).

---

## 5. MCP tools: full list (`mcp_server/server.py`)

Shop facts come only from these tools over `data/campus_customs_new.db`. There is no second data layer in the backend. The server also creates two board tables on the working copy if they're missing: `approval_requests` (payments and POs waiting on a human) and `drafts` (customer messages that are never sent).

| Tool | Tables used | Read / write | Used by |
|---|---|---|---|
| `get_desk_date` | desk | read | all |
| `list_open_tickets` | tickets | read | boss |
| `list_tickets` | tickets, desk | read (all tickets and their status) | API routes |
| `get_ticket` | tickets, inventory, leases, invoices, vendors, drafts, approval_requests | read | all |
| `update_ticket` | tickets | write (status and appended note) | boss |
| `check_stock` | inventory | read | inventory, customer_service |
| `get_pricing` | pricing | read | inventory, accounting, customer_service |
| `quote_discount` | pricing | read (does the math) | accounting, customer_service |
| `list_vendors` | vendors, invoices, desk | read (`can_ship` flag, arrival date) | inventory, accounting, customer_service |
| `list_invoices` | invoices, vendors, desk | read (days overdue) | inventory, accounting |
| `get_lease` | leases, desk | read | facilities, accounting |
| `get_cash_balance` | cash_accounts, approval_requests | read | boss, accounting |
| `request_payment` | invoices or leases, cash_accounts, approval_requests | write (pending request only) | accounting |
| `create_purchase_order` | vendors, invoices, inventory, pricing, desk, approval_requests | write (pending request only) | accounting |
| `list_approval_requests` | approval_requests | read | boss, accounting, facilities |
| `draft_customer_message` | tickets, drafts | write (draft only) | customer_service |
| `list_drafts` | drafts | read | API routes |
| `decide_approval_request` | approval_requests, cash_accounts, payments, invoices, leases | write (moves money) | **human approval route only (`POST /api/approvals/{id}/approve`), no agent** |

---

## 6. Safety

**Money**
- **A human approves every payment.** Agents can only create *pending* requests. The one tool that moves cash, `decide_approval_request`, is left out of every agent's toolset in code (and an `assert` checks this), so a prompt injection can't talk an agent into paying.
- **No negative balances.** The pay step refuses any payment larger than the account balance. `get_cash_balance` also shows `balance_after_pending` so agents can see when pending requests add up to more than the cash on hand.
- **Amounts come from the database, not the model.** `request_payment` looks up the invoice or rent amount itself, and `create_purchase_order` computes cost × qty. The agent never types in a dollar figure.
- **Vendor holds are enforced in code.** `create_purchase_order` refuses when the vendor has an open invoice.
- **No duplicates or double pays.** Duplicate pending requests are refused, and an already-decided request can't be decided again.
- **Paying updates every table.** Approval writes a `payments` row with `approved_by`, lowers `cash_accounts`, and marks the invoice `paid` or moves `lease.next_due` forward a month.

**Customers and the outside world**
- **Drafts only.** No tool can send email or contact vendors. `draft_customer_message` saves to the board with status `draft`.
- **Customer Service is told** never to promise unconfirmed dates or discounts, and never to reveal internal details (cash, unpaid invoices, margins).
- **No invented data.** Missing rows come back as `found: false` and prompts tell agents to say "unknown". Discounts at or below cost are flagged by `quote_discount`.
- **Least privilege.** Each agent sees only the tools it needs. Only Boss can change ticket status, and only Accounting can create payment or PO requests.
- **Everything is auditable.** Every model call, tool call (with arguments), tool result, delegation, and final output is appended to `output/audit_trail.json` with a run id, ticket id, agent, depth, and delegation chain. The file is never wiped, and if it ever gets corrupted it's set aside instead of overwritten.
- **Resets.** The original database is never touched, and `POST /api/reset` (or `python reset_db.py`) restores the working copy.

**Token limits** (in `backend/config.py`, shared by the whole team on each ticket)
- At most 40 model requests, 60 tool calls, and 250k total tokens per ticket (a PydanticAI `UsageLimits` object passed down through every delegation).
- Delegation depth is capped at 3, with at most 8 delegations per ticket. Agents can't delegate to themselves or back to anyone already in the chain, so they can't ping-pong.
- Each response is capped at 12,000 output tokens with reasoning effort set to `low`, and each agent allows 2 retries. The cap started at 4,000, but gpt-6-luna's hidden reasoning counts toward it, and Boss's final answer on ticket 102 ran out of room during the full run. Low effort keeps each call short, and the higher cap leaves room to finish.
- Tools return compact, pre-computed results (overdue days, margins, `can_ship`) so agents don't spend tokens reasoning over raw tables. Long audit strings are clipped at 2,000 characters.

---

## 7. Backend routes (`backend/main.py`)

FastAPI, started from `backend/` with `uvicorn main:app --reload --port 8000`, which serves `http://localhost:8000` (CORS is open to the Vite dashboard on :5173). Every route that reads or changes shop data goes through the MCP server. Agent events are read from `output/audit_trail.json`.

- `GET /api/health`: confirms the API, the model (`gpt-6-luna`), the working DB, and the shop's `date_today`.
- `GET /api/tickets`: all tickets with their status, plus `is_resolved` and whether agents are working on each one right now.
- `GET /api/tickets/{id}`: one ticket with its linked inventory, lease, invoice, drafts, and approval requests.
- `POST /api/tickets/{id}/run`: starts the agent team on that ticket in the background and returns a `run_id` right away. When the run finishes, the ticket is marked `resolved` and a note records Boss's own call and any pending approvals. A second run on the same ticket is refused with 409 while the first is still going.
- `GET /api/runs` and `GET /api/runs/{run_id}`: run status (`running`, `done`, or `error`) and Boss's final decision.
- `GET /api/events?limit=&ticket_id=&run_id=&after=`: recent agent events for the board to poll. Each event shows the agent, what it said, the tools it called (with arguments), the tool results, and any delegation.
- `GET /api/approvals?status=pending|paid|rejected|all`: payment and purchase-order requests the agents prepared.
- `POST /api/approvals/{id}/approve` (body `{"approver": "name"}`): **the only route that moves cash.** It pays the request, writes a `payments` row with `approved_by`, lowers `cash_accounts`, and marks the invoice paid or moves the lease due date forward. It refuses with 409 if cash would go negative or the request was already decided.
- `POST /api/approvals/{id}/reject` (body `{"approver": "name"}`): marks the request rejected, and no money moves.
- `GET /api/cash`: the current checking balance from `cash_accounts`, plus the pending total and the balance after pending requests.
- `GET /api/drafts?ticket_id=`: customer message drafts on the board (never sent).
- `POST /api/reset`: copies the original `campus_customs.db` over the working copy for a fresh run. It's refused while agents are running, and the audit trail is kept.

---

## 8. Dashboard (`frontend/`)

React + Vite + TypeScript. Start it from `frontend/` with `npm run dev`, which serves http://localhost:5173. It calls the backend directly at `http://localhost:8000`, and the backend's CORS setup allows the `http://localhost:5173` origin. The board lists the three tickets, starts the team on the one you pick, streams each agent's words and tool calls while it runs, marks the ticket resolved when the run finishes, shows a summary card per agent, lets a human sign or reject payment and PO requests, and shows the checking balance, which drops after an approved payment. Design choices are in `output/design.md`.

---

## 9. Full run results (Problem 9)

Run on 2026-10-09 after resetting the working database. The tickets ran in order 101 → 102 → 103, and a human (Celia Kent) signed each payment on the dashboard. Details: `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, `output/resolved_board.html` (screenshots), `output/audit_trail.json` (every step).

| Ticket | Agents (in order) | Money | Boss's status → board |
|---|---|---|---|
| 101 Bulldog tee | Boss → Inventory ∥ Accounting → Customer Service → Accounting (PO refused, vendor on hold) | −$840 invoice 501 (approved) | blocked → resolved |
| 102 Rent due | Boss → Facilities → Accounting (run 1; Boss's final answer hit the token cap) · Boss → Facilities (re-run) | −$2,400 rent (approved) | blocked → resolved |
| 103 Hoodie discount | Boss → Inventory ∥ Accounting → Customer Service | $0 (restock $264 > $160 cash) | blocked → resolved |

**Cash:** $3,400.00 − $840.00 − $2,400.00 = **$160.00**, which matches `cash_accounts.checking` in the working database. The `payments` table has 2 rows, both `approved_by = Celia Kent`.

**What the run taught us:**
- The guardrails held: no agent moved money, the vendor hold blocked the PO, the team didn't ask for money it didn't have, and it didn't pay rent twice.
- The token cap needs room for reasoning tokens. It's now 12,000 with low effort.
- When a payment changes data (rent moves `leases.next_due`), the agents need to see *why* the data changed. Otherwise they flag it as a conflict. One fix would be for the pay step to write a note on the lease or ticket.
- Boss usually calls specialists in parallel and goes straight to Accounting itself, rather than chaining Inventory → Accounting as I'd planned.

