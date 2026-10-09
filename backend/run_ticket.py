"""Run the agent team on tickets from the command line (run from backend/).

    python run_ticket.py 101          # one ticket
    python run_ticket.py --all        # every open ticket, in order
"""

import argparse
import asyncio
import json

from agents import call_shop_tool, run_ticket


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ticket_ids", nargs="*", type=int)
    p.add_argument("--all", action="store_true", help="run every open ticket")
    args = p.parse_args()
    if args.all:
        open_tickets = await call_shop_tool("list_open_tickets")
        ids = [t["id"] for t in open_tickets["tickets"]]
    else:
        ids = args.ticket_ids
    if not ids:
        p.error("give ticket ids or --all")
    for tid in ids:
        result = await run_ticket(tid)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
