# Event Companion

A mobile-first event app for attendees: check in with a QR code, find booths on a venue map, follow sessions and save key points, see which friends are at the event, and keep all of that even if the phone closes, goes offline, or gets replaced.

> **The event should remember the attendee, not the phone.**

## What's in this repo

| Path | What it is |
|---|---|
| [`docs/product-spec.md`](docs/product-spec.md) | Product specification and MVP architecture |
| [`index.html`](index.html) | Clickable prototype of the MVP (a single self-contained file) |

## Running the prototype

Open `index.html` in any modern browser (double-click it). There's no build step and nothing to install.

The page shows the app in a phone frame, with a control panel beside it for testing the persistence requirements from the spec:

- **Online / Offline**: actions made offline wait in a local sync queue and upload when you reconnect.
- **Close & reopen the app**: simulates a crash; your screen and progress are restored.
- **Sign in on a new phone**: wipes local storage; signing in with the same email restores everything from the account.
- **MVP test script**: the success criteria from the spec (section 29), ticked off as you complete them.

### What the prototype simulates

- **Camera / QR scanning**: codes are picked from an on-screen list. Payloads follow the spec's format (`event://checkin/evt_001`, `booth://booth_042`, `session://session_014`).
- **Backend**: a "server" store kept in the browser's `localStorage`, standing in for Supabase. Each browser has its own data.
- **Event content**: exhibitors, speakers and friends are fictional sample data.

## Next steps

Follow the phases in the spec (section 25): a Next.js + TypeScript app backed by Supabase, starting with auth, the database schema and QR check-in.
