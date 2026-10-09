# Campus Customs Operations Desk (frontend)

React + Vite + TypeScript dashboard for the agent team.

```bash
npm install
npm run dev        # http://localhost:5173
```

It calls the FastAPI backend at `http://localhost:8000` (start it from `backend/` with `uvicorn main:app --reload --port 8000`). Set `VITE_API_URL` to point somewhere else. Design notes: `../output/design.md`.
