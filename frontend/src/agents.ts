import type { AgentName, Ticket } from "./types";

export interface AgentMeta {
  name: AgentName;
  label: string;
  role: string;
  personality: string;
  color: string; // the agent's brand color (circle fill, bubble background)
  text: string; // readable text color on that background
}

// Brand palette (from the inspiration board)
export const BRAND = {
  sky: "#D1E6F6",
  white: "#FFFFFF",
  ink: "#131718",
  pink: "#FFDAE4",
  peach: "#FEC29F",
  cream: "#FFF6C6",
};

export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: {
    name: "boss",
    label: "Boss",
    role: "Reads the ticket, makes the call",
    personality: "A little stern. Fair, but not here to chat.",
    color: BRAND.ink,
    text: "#FFFFFF",
  },
  inventory: {
    name: "inventory",
    label: "Inventory",
    role: "Stock, shortfalls, restock",
    personality: "Spectacles on, always counting shelves.",
    color: BRAND.sky,
    text: BRAND.ink,
  },
  accounting: {
    name: "accounting",
    label: "Accounting",
    role: "Cash, invoices, margins",
    personality: "Serious. Every dollar gets a second look.",
    color: BRAND.cream,
    text: BRAND.ink,
  },
  facilities: {
    name: "facilities",
    label: "Facilities",
    role: "Lease, rent, the shop space",
    personality: "Calm and steady. Keeps the lights on.",
    color: BRAND.peach,
    text: BRAND.ink,
  },
  customer_service: {
    name: "customer_service",
    label: "Customer Service",
    role: "Drafts customer messages",
    personality: "Cheery. Says it kindly, never overpromises.",
    color: BRAND.pink,
    text: BRAND.ink,
  },
};

export const AGENT_ORDER: AgentName[] = [
  "boss",
  "inventory",
  "accounting",
  "facilities",
  "customer_service",
];

export const TICKET_KIND: Record<string, { label: string }> = {
  customer_order: { label: "Customer order" },
  rent_notice: { label: "Rent notice" },
  price_override: { label: "Discount request" },
  unpaid_bill: { label: "Unpaid bill" },
};

/** Campus Customs product photos (white-background copies from HW4's data).
 *  The shop has no exact "Classic Bulldog Tee" photo, so a navy Yale tee
 *  stands in for CC-TEE-WHITE. */
const SKU_PHOTOS: Record<string, { src: string; caption: string }> = {
  "CC-HOOD-NAVY": { src: "/photos/basic-hoodie-big-yale.jpg", caption: "Basic Hoodie Big Yale" },
  "CC-TEE-WHITE": { src: "/photos/boola-boola-t-shirt.jpg", caption: "Yale tee (stand-in photo)" },
};

const SHOP_WALL = [
  "/photos/champion-reverse-weave-crewneck.jpg",
  "/photos/district-vit-hoodie-vintage-bulldog.jpg",
  "/photos/big-yale-tri-blend-t-shirt.jpg",
];

export function ticketPhotos(t: Ticket | null): { srcs: string[]; caption: string } {
  if (t?.sku && SKU_PHOTOS[t.sku]) {
    const p = SKU_PHOTOS[t.sku];
    return { srcs: [p.src], caption: p.caption };
  }
  return { srcs: SHOP_WALL, caption: "The Chapel Street shop" };
}

export const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });
