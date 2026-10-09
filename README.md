# Campus Customs Multi-Agent Operations (HW5)

A five-agent team that runs the back office of Campus Customs, a Yale merch shop on Chapel Street. Open tickets (customer orders, rent, unpaid bills, discount requests) are worked by **Boss, Inventory, Accounting, Facilities and Customer Service**. A human watches the agents on a React dashboard and approves every payment.

```
React board (frontend/, :5173)
   → FastAPI backend (backend/main.py, :8000)
      → PydanticAI agent team (backend/agents.py, gpt-6-luna via Portkey)
         → MCP server (mcp_server/server.py, FastMCP over stdio)
            → SQLite working copy (data/campus_customs_new.db)
```

- **Every agent uses only `gpt-6-luna`** through Portkey (`backend/config.py`).
- **Shop facts come only from the MCP tools.** The agents have no other way to read or write the database.
- **Agents can only *prepare* payments.** Money moves only when a human clicks **Sign & pay** on the dashboard, and the pay step refuses anything that would make the balance negative.
- Every agent-loop step is appended to `output/audit_trail.json`.

Full design notes: `output/harness.md` (tables, tools, agents, routes, dashboard, safety) and `output/design.md` (dashboard look).

## Requirements

- Python 3.12+
- Node 20+ and npm
- A Portkey API key with access to `gpt-6-luna`

## 1. Set up

```bash
# Python (from the repo root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Your key: copy the template and fill in PORTKEY_API_KEY
cp .env.example .env

# React board
cd frontend && npm install && cd ..
```

## 2. Databases

| File | What it is |
|---|---|
| `data/campus_customs.db` | The **original** shop database. Never modified. |
| `data/campus_customs_new.db` | The **working copy** the MCP server and backend read and write. As committed, it holds the end state of my full three-ticket run (all resolved, $160 in checking). |

**To get a clean working copy, copy the original over it:**

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

(`cd backend && python reset_db.py` or the dashboard's **Reset desk ↺** button do the same thing.)

## 3. Start the MCP server

The backend starts the MCP server for you over stdio when it boots, so you don't need to run it separately to use the app. To run it on its own (for example to test the tools):

```bash
python mcp_server/server.py
```

To use the tools from Claude Code, open this folder in Claude Code. `.mcp.json` registers the server as `campus-customs`. It expects the venv at `.venv/`.

## 4. Start the FastAPI backend

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000 (http://localhost:8000/api/health should say `"ok": true`). All the routes are listed in `output/harness.md` section 7.

## 5. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The backend only accepts calls from this address, so keep the port at 5173.

## 6. A full three-ticket run

1. **Reset the database first** so you start clean: click **Reset desk ↺** on the board, or run `cp data/campus_customs.db data/campus_customs_new.db` while the backend is stopped. Checking should read **$3,400.00** and all three tickets should be open.
2. Pick **ticket 101** on the board and click **Start the team →**. Watch the agents on the floor.
3. When a payment check appears in the **Cash** panel, type your name on "Signing as" and click **Sign & pay** (or **Reject**).
4. Repeat for **102**, then **103**.

Each finished run marks its ticket resolved. Expected money for my run: −$840 (invoice 501) and −$2,400 (rent), for **$160.00** at the end. See the Cash tab in `output/desk_tickets.html`.

From the command line instead: `cd backend && python run_ticket.py 101` (or `--all`).

## Repo layout

```
AI_prompts.md          what I asked the AI, problem by problem
requirements.txt  .env.example  .gitignore  .mcp.json
data/                  campus_customs.db (original) · campus_customs_new.db (working)
mcp_server/            server.py (FastMCP tools) · README.md
backend/               main.py (routes) · agents.py · models.py · config.py · audit.py
                       run_ticket.py · reset_db.py · prompts/ (one file per agent)
frontend/              React + Vite + TypeScript dashboard
output/                harness.md · mcp_smoke.json · desk_tickets.html · design.md
                       resolved_tickets.json · resolved_board.html (+ screenshots/)
                       audit_trail.json · github_url.txt
```
