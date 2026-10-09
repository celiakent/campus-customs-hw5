# HW 5 — AI Prompts Log

This file records the prompts I gave to the AI assistant while working on HW 5 (Campus Customs Multi-Agent Operations), organized by problem.

---

## Problem 1: Vibe Coder Prompts

**Prompt:**
> Set up the HW5 folder and create an AI_prompts.md file in it. Keep it updated as we work through the assignment, one section per problem with the problem number and title, at least one prompt I typed, and any follow-up prompt with one sentence on what was missing after the first one.

---

## Problem 2: Study the Campus Customs Database

**Prompt:**
> The data.zip is in the HW5 folder now. Unzip it, then go through data/campus_customs.db and look at every table and its fields. Make a copy called data/campus_customs_new.db, since that's the working copy later problems will change. Look closely at the three open tickets and how they connect to the other tables. Then start output/harness.md: for each table, list its fields and write one short line on why that table matters for the agents. Set it up so we can keep adding to it later.

---

## Problem 3: Build the MCP Server

**Prompt:**
> Build an MCP server in mcp_server/ using FastMCP that connects to data/campus_customs_new.db. Every agent will use its tools, so start with three tools we'll definitely need for the three open tickets, with clear names. Only return what's actually in the database and never make up data. You don't have to connect or run it yet. Then add a section to output/harness.md listing each tool, which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why it's the right tool for that ticket. Also write a short mcp_server/README.md explaining what the server is for, which database file it uses, and the three tools.

---

## Problem 4: Add the MCP Server to the Vibe Coder and Test Each Tool

**Prompt:**
> Hook the MCP server up to Claude Code for this project so you can call its tools, and save the connection config in .mcp.json at the HW5 root. Then test each of the three tools for real through that connection and save the results in output/mcp_smoke.json, with the prompt I asked, the tool name, and the tool's output for each one. Make sure the outputs match what's actually in data/campus_customs_new.db.

**Follow-up prompt:**
> Use the campus-customs MCP tools to answer these, then save each prompt, tool name, and output in output/mcp_smoke.json:
> 1. How many Classic Bulldog Tees in size S do we have? (check_stock)
> 2. How much is rent on lease 1 and when is it due? (get_lease)
> 3. What's the cost, list price, and margin on CC-HOOD-NAVY? (get_pricing)

**Why I needed the follow-up:** The first prompt only saved the config; the tools only load in a new session, so I had to open one in HW5 and ask it to run the tests.

---

## Problem 5: Build the Agent Team and Grow the MCP Tools

**Prompt:**
> Build the Campus Customs agent team in PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Every agent should be able to delegate to any other agent. Put one prompt file per agent in backend/prompts/, the data types in backend/models.py, and the agent code under backend/. Use my PORTKEY_API_KEY and only gpt-6-luna for every agent. Make the prompts detailed, with the shop rules each agent needs. Add whatever MCP tools the agents need to work the open tickets. All shop facts have to come through the MCP server, with no separate tools layer that skips it. Have the agents append every agent-loop step to output/audit_trail.json without wiping it between runs. In output/harness.md, list each agent and each MCP tool with the tables it uses, and add a safety section on guardrails for real customers and real money plus limits that keep token use down. Update mcp_server/README.md so the tool list is current. Let me know if you don't have my Portkey API key, or tell me where to put it in the code.

---

## Problem 6: Plan the Three Tickets

**Prompt:**
> Before we wire the backend any further, build output/desk_tickets.html, a standalone page I can double-click to open, with one tab for each ticket (101, 102, 103), plus a Cash tab and a Reflection tab that just say “coming later” for now. On each ticket tab, fill in only an “Expected” section and leave an empty “Actual” section that we’ll fill in after running the agents. For each ticket’s Expected section, write what I think the team will do: 101 (Tauhid’s size S tee): Boss should call Inventory first, since the question is whether we have it. I expect Inventory to find 0 in stock and see that Bulldog Print Co can’t ship because invoice 501 is overdue. Then Boss or Inventory brings in Accounting to prepare the invoice payment for approval. Customer Service drafts an honest note to Tauhid with a realistic restock date. 102 (rent): Boss should call Facilities first to check the notice against the lease. Facilities hands it to Accounting, which prepares the $2,400 rent payment for approval. Inventory and Customer Service aren’t needed. (Yale AI Club hoodies): Boss should call Inventory first, because there’s no point pricing a discount on 20 hoodies when we only have 8 in size M. Then Accounting runs the discount and margin math and checks whether there’s cash for a restock. Customer Service drafts a reply to the club. Facilities isn’t needed. For each ticket, list who Boss calls first and why, every delegation I expect (not just “Boss calls everyone”), and which MCP tools I expect the run to use. Don’t send every specialist to every ticket.

---

## Problem 7: Backend Routes

**Prompt:**
> Build the FastAPI backend in backend/main.py so the React dashboard has routes to call. I need routes that:
> - return the three tickets and whether each one is open or resolved
> - take a ticket id and run the agent team on that ticket
> - return recent agent events (what each agent said and which tools it used) so the board can refresh
> - approve a payment or purchase order when a human clicks approve. The agents only prepare payments; this route is the only thing that actually changes cash, and it should still refuse if there isn't enough money.
> - return the current checking balance from cash_accounts
> - reset the database to the original values so I can try a fresh run

---

## Problem 8: Agent Dashboard

**Prompt:**
> Build the dashboard in frontend/ with React + Vite + TypeScript, calling the routes from Problem 7 at http://localhost:8000 (and let the backend allow the Vite origin at http://localhost:5173). It needs to list all three tickets, let me pick one and start the agent team on it, show each agent and what they're saying and doing while it runs, mark the ticket resolved when the run finishes, show a short summary of what each agent did, let a human approve a payment or purchase when asked, and show the checking balance so it drops after an approved payment. Make it look good and be creative, like a real desk people would want to sit at. It should start with npm run dev. Then write output/design.md explaining the look: layout, how agents read differently, how resolved tickets and cash show up, and the creative choices. I'm going to see what you build and then make changes to the design later, and we can update this, but go.

**Follow-up prompt:**
> I want to go back to question 8 that had to do with the design. Here are my two inspiration photos for what I want the design to be. Specifically, take cues from this for color, font, and layout. If you want to implement pictures, take them from Campus Customs or insert photos of the Yale campus. For each agent, I want it to be a circle with one of the branding colors, but have its own personality: the boss should be a little bit stern, for example, but use your best judgment for the personalities of the other ones. The circle/emoji should be very simple. I don't want it to look like an emoji, but it can have a face and a short, small animation. I do want you to integrate photos somewhere, but it's up to you where that fits best. Let's start there and see where to go from there.

**Why I needed the follow-up:** The first dashboard worked, but its look was the AI's own idea, and I wanted it to follow my inspiration board's colors, League Gothic type and color-block layout, with simple face characters for the agents and real Campus Customs photos.

---

## Problem 9: Resolve the Tickets

**Prompt:**
> Reset data/campus_customs_new.db so we start clean, and note the starting checking balance. Then run all three tickets (101, 102, 103) through the agent team until each one is resolved. I'll approve payments myself on the dashboard. After that:
> - In output/desk_tickets.html, fill in the Actual section on each ticket tab from this run: which agents worked, what they delegated, and which tools they used. Keep my Expected section so I can compare the two.
> - On the Cash tab, itemize the money: the starting balance after the reset, how cash changed for each ticket and why (which payment or purchase and the dollar amount), and the ending balance, which has to match cash_accounts in the working database.
> - Save output/resolved_tickets.json with each ticket's id, final status, a short outcome, what each agent contributed, and any human approvals.
> - Make output/resolved_board.html, a page I can double-click, with a screenshot of the React board for each resolved ticket.
> - Make sure the real runs are appended to output/audit_trail.json, and finish output/harness.md so it covers the tables, MCP tools, five agents, API routes, dashboard, and safety rules.

---

## Problem 10: Reflection

**Prompt:**
> For problem 10, we need to fill in the Reflection tab in output/desk_tickets.html and make it detailed. Tie every answer to this app and the three tickets that we ran, using the ticket tabs and the Cash tab as evidence.
> How the agents performed on each ticket and why. Here's my answer:
> - 103 was the best because it matched the plan and caught the cash shortfall: it offered the 8 hoodies at 10% off and didn't order a $264 restock we couldn't pay for with $160.
> - 101 was good, but the T-shirt still has no order. The $8 order was refused because invoice 501 was still unpaid at that moment, and nobody went back for it after I paid.
> - 102 was the worst because Boss hit the token cap and the run crashed, and then on the re-run it flagged the moved lease date as a mismatch. It did avoid paying rent twice, though.
>
> How Actual compared to my Expected plan for each ticket. I expected Boss would send agents out in a chain, and instead it sent them out in parallel. That surprised me, even though it was a small change. Also cover the other differences from the ticket tabs: on 101 it tried an extra purchase order and the draft didn't give a restock date, on 102 there was the crash and the re-run, and on 103 the vendor was already unblocked because I'd paid invoice 501 during 101.
> What would have been simpler as one agent with tools, and why. Ticket 102 is the one with only one lookup and one payment request, and the Boss to Facilities to Accounting chain added handoffs, tokens, and the crash without adding judgment.
> Three new problems Campus Customs might face that this team could solve with the tools we already built. My answers:
> 1. Customer service complaints: if a complaint comes in as a ticket with the item and size, the team can pull it up with get_ticket, check stock for a replacement with check_stock, and draft a reply. One limit: there's no order history table, so it only works if the ticket says what was ordered.
> 2. The Crest Mug is at 0 in stock. Inventory can pick Elm City Gifts (mugs, 3-day lead time, no open invoices), and Accounting can price a restock at $3.50 each and create a purchase order. Twenty mugs would be $70, which fits in the $160 we have left, and a human approves it.
> 3. Next month's rent: the lease now says $2,400 is due 2026-10-02 and we only have $160. Facilities and Accounting could catch that a month early with get_lease and get_cash_balance, and the pay tool would refuse to go negative.
>
> Three new problems the team could NOT solve with these tools, and the tools and agents we'd need.
> 1. Getting paid. Cash only goes out, so even if the Yale AI Club buys the 8 hoodies ($417.60), we can't record that money or use it for the $264 restock. We'd need a sales table and a record_sale / record_deposit tool (with human approval) that adds to cash_accounts, and a Sales agent, or Accounting could handle it.
> 2. Actually talking to people. Drafts just sit on the board, and the agents can't send email or read replies from customers, vendors, or the landlord. We'd need a send_message tool that only sends after a human approves a draft, plus an inbox tool that turns incoming emails into tickets, and a Communications agent to run both.
> 3. Receiving stock and shipping orders. Paying for a purchase order doesn't add anything to inventory when the boxes arrive, and nothing tracks orders being picked up or delivered, even though QuickShip CT is in the vendors table. We'd need an orders table, a receive_shipment tool that adds to inventory, a book_courier tool, and a Fulfillment agent.

**Follow-up prompt:**
> I need you to fill in what my answers would be in the prompt. I filled some of them out, but I'm not sure if they're right. I got to the last two, and I don't really know what to say for them. Can you rewrite the prompt as I wrote it below, but fill in those reflections?

**Why I needed the follow-up:** My first draft only had answers for the first three questions and one idea for the "could solve" list, so I asked for help checking my answers and filling in the last two before I sent the final prompt above.

---

## Problem 11: Submit to GitHub

**Prompt:**
> Get HW5 ready to submit and push it to a new public GitHub repo called `campus-customs-hw5` on my account. Match the file layout from the assignment:
> - Write a README.md at the root that explains how to copy the original database to the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React board, and reset the database before a full three-ticket run.
> - Retake the screenshots in output/resolved_board.html so they show the new dashboard design.
> - Include both database files in data/ (the original and the working copy), but do not push my real .env. Also leave out data.zip, .venv, and node_modules.
> - Before pushing, show me the list of files that will be committed so I can check it, and make sure no API key is anywhere in them.
> - After it's pushed, save the repo URL in output/github_url.txt and push that too.

**Follow-up prompt:**
> Push it.

**Why I needed the follow-up:** I had asked to review the file list and the secret check before anything went public, so the push waited for my OK.

---

