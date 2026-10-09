# Operations Desk: Dashboard Design

The dashboard is `frontend/` (React + Vite + TypeScript). Start it with `npm run dev` and open http://localhost:5173. It calls the FastAPI backend at http://localhost:8000.

## Where the look comes from

I redesigned the board from two inspiration images (a travel brand called "Travel Lab"), taking three cues from them: **color, font and layout**.

- **Font:** **League Gothic**, a tall condensed sans, in all caps for every headline: the ticket name, section titles, agent names, the cash balance and check payees. Body text is **Source Sans 3**. Both are bundled with the app (`@fontsource`), so the page doesn't depend on a font CDN.
- **Color:** the inspiration's six-color palette, used as big rounded color-block sections:

| Color | Hex | Used for |
|---|---|---|
| Sky | `#D1E6F6` | Hero and stats row · Inventory's face |
| White | `#FFFFFF` | Page background, cards, "On the floor" |
| Ink | `#131718` | Text, black pill buttons, balance card · Boss's face |
| Pink | `#FFDAE4` | "The team" section · Customer Service's face |
| Peach | `#FEC29F` | "Cash" panel · Facilities' face |
| Cream | `#FFF6C6` | "The board" section · Accounting's face |

- **Layout:** a two-column nav with small caps links, a hero with a giant headline and a black button tucked into a notch in the corner, a three-up stats row with thin dividers ("3 tickets | $160.00 | Pro team"), and numbered photo cards (01 / 02 / 03) where the selected one lights up yellow, just like the tour cards in the inspiration.

## Page layout, top to bottom

1. **Nav:** the CAMPUS CUSTOMS® wordmark, jump links (Tickets, The team, On the floor, Cash & approvals), and pills for the model status, the shop date (desk.date_today) and **Reset desk ↺**.
2. **Hero (sky):** the selected ticket's name in huge League Gothic ("BULLDOG TEE"), its product photo, who sent it on the left, the SKU and invoice details in a frosted card on the right, and **Start the team →** in the notched corner. A rubber-stamp **RESOLVED** badge lands on it when the run finishes.
3. **Stats row:** how many tickets are open or resolved, the live checking balance, and the team.
4. **The board (cream):** the three tickets as numbered photo cards. Clicking one selects it, and the card turns yellow with an ↗ arrow.
5. **The team (pink)** and **On the floor (white)** on the left, with **Cash (peach)** as a sticky panel on the right, so money is always in view while the agents work.

## Photos

The photos are Campus Customs' own product shots (the white-background copies from the HW4 data), so nothing was downloaded:
- Ticket 103 uses **Basic Hoodie Big Yale**, the exact product (CC-HOOD-NAVY).
- Ticket 101 uses a navy Yale tee as a **stand-in**. The catalog has no photo of the white "Classic Bulldog Tee", and the hero says so in its caption.
- Ticket 102 (rent) has no product, so it shows a small "shop wall" of three Campus Customs pieces to stand for the Chapel Street store.

On the colored panels the images use `mix-blend-mode: multiply`, so the white photo background disappears and the garment sits right on the color. Yale campus photos would be a natural next step for the hero (especially the rent ticket), but they'd have to be downloaded first.

## The agents: five faces, five personalities

Each agent is **one circle in a brand color with a minimal face**: a few strokes, no emoji. Each has one small signature animation:

| Agent | Circle | Personality | Face | Animation |
|---|---|---|---|---|
| **Boss** | Ink | A little stern | Brows angled down, narrow eyes, flat mouth | A slow, unimpressed blink; brows lower further while it's working |
| **Inventory** | Sky | The careful counter | Round spectacles, small smile | Eyes scan left and right behind the glasses, like checking shelves, with a little lens glint |
| **Accounting** | Cream | Serious, double-checks every dollar | Level brows, dot eyes, short straight mouth | Eyes drop down to "the ledger" and back up |
| **Facilities** | Peach | Calm and steady | Relaxed closed eyes, gentle smile | A slow, easygoing sway |
| **Customer Service** | Pink | Cheery | Happy arched eyes, rosy cheeks, big smile | A little hop and a wink |

The faces aren't just decoration; they show state:
- **Working:** the agent who's thinking right now gets a black ring, and its mouth starts "talking". The same face appears with a "… is working" line at the bottom of the live feed.
- **Not needed:** agents the ticket didn't use fade back and stop moving, so you can see at a glance that the team didn't send every specialist to every ticket.
- **In the feed:** every speech bubble is in the agent's color (Boss's are black with white text), with its face beside it. Handoffs show both faces: Boss's face ⟶ Inventory's face.
- The faces also sign Boss's memo ("The call"), head each "What each agent did" card, and mark who drafted each letter in the Outbox.

All motion turns off for people who set "reduce motion" in their system settings.

## How resolved tickets and cash show up

- **Resolved:** a cream rubber-stamp RESOLVED lands on the ticket's photo card and on the hero, and its status chip turns black. Boss's own status (for example "blocked" or "waiting approval") stays on the memo, so a resolved ticket never hides an approval that's still waiting.
- **Cash:** the peach panel leads with CASH in League Gothic and a black balance card with the amount in big display type. A cream bar shows how much is committed to pending checks (it turns red if pending checks add up to more than the cash). Signing a check rolls the balance down and flashes the amount in peach.
- **Checks:** white cards with the payee in League Gothic, a big amount, the memo, and who prepared it. **Sign & pay** stays disabled until you type your name on the "Signing as" line. Paid or rejected checks get a stamp and move under "Signed & filed".

## Files

- `frontend/src/components/AgentFace.tsx`: the five faces (SVG) and their states
- `frontend/src/components/Hero.tsx`: the hero, notch button and stats row
- `frontend/src/components/TicketInbox.tsx`: the numbered photo cards
- `frontend/src/components/AgentRoster.tsx`, `Floor.tsx`, `Summaries.tsx`, `Outbox.tsx`, `Ledger.tsx`: team, live feed, memo and summaries, drafts, cash
- `frontend/src/agents.ts`: brand palette, each agent's color and personality, and the ticket → photo mapping
- `frontend/src/index.css`: the whole look, including the face animations
- `frontend/public/photos/`: the Campus Customs product photos
