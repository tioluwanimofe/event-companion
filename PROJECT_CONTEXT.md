# Event Companion: Project Context

> Handoff document. Summarizes all work done so far so a new conversation can continue without re-deriving anything.
> Read alongside `docs/product-spec.md` (the full product spec) and `index.html` (the full prototype source).
> Last updated: 2026-09-25.

---

## 1. What this project is

**Event Companion** is a mobile-first, web-first (PWA) app for event attendees: conferences, career fairs, expos, church and university events.

Core principle, from the spec:

> **The event should remember the attendee, not the phone.**

The user's progress (check-in, booth visits, notes, saved points) lives on a backend account, not only on the device, so it survives app closes, crashes, lost connectivity and switching phones.

**Owner:** Tioluwanimofe Adesanya (GitHub: `tioluwanimofe`, commit email `atioluwanimofe@gmail.com`).

**Immediate purpose:** the prototype is being shown to the owner's boss (planned for 2026-09-25) to pitch the idea.

---

## 2. Links

| What | Where |
|---|---|
| GitHub repo (public) | https://github.com/tioluwanimofe/event-companion |
| Live prototype (GitHub Pages) | https://tioluwanimofe.github.io/event-companion/ |
| Claude artifact version (private, first published copy) | https://claude.ai/artifact/BnmJrg3k2R8dmsj5bADFSH |
| Local folder | `C:\Users\atiol\New folder` (git repo, branch `main`, tracks `origin/main`) |
| Original spec file | `C:\Users\atiol\Downloads\event_companion_product_spec.md` (copied into repo as `docs/product-spec.md`) |

**Note on versions:** the GitHub/Pages `index.html` is the canonical version. The Claude artifact is an earlier copy and lacks the standalone-page fixes (doctype, `<head>`, mobile viewport meta), because the artifact host adds those itself. If the artifact is ever republished from `index.html`, that is fine; the host tolerates a full document.

---

## 3. Repo contents

```
event-companion/
├── index.html            # The clickable prototype: single self-contained file (HTML + CSS + JS inline)
├── docs/
│   └── product-spec.md   # Full product spec & MVP architecture (v1.0, "MVP Planning")
├── README.md             # Overview, live link, how to run, what's simulated, next steps
├── .gitignore            # OS/editor junk, node_modules/.next/out/dist, .env*, .claude/settings.local.json
└── PROJECT_CONTEXT.md    # This file
```

Commit history (all authored as Tioluwanimofe Adesanya <atioluwanimofe@gmail.com>, with `Co-Authored-By: Claude` trailer):
1. `Add Event Companion product spec and clickable MVP prototype`
2. `Make prototype a standalone web page and link the live demo`

---

## 4. The product spec in brief

Full detail is in `docs/product-spec.md`. Key points:

**MVP goals:** (1) persistent event identity, (2) QR-based interaction, (3) event navigation, (4) social presence (friends at the event), (5) session info plus saving points and notes.

**Explicit non-goals for MVP:** AI summaries, recommendations, live indoor GPS, native apps, payments and ticketing, chat, push notifications, facial recognition, advanced analytics, transcription, complex gamification, multiple simultaneous events, organizer marketplace.

**Navigation:** Home | Map | Schedule | Friends | Profile. Notes live inside sessions.

**Key architecture decisions in the spec:**
- The map is a **static floor plan with interactive pins** (x/y coordinates), not indoor positioning.
- Friends have **event-level presence only** ("checked in"), never exact location. Users control their visibility.
- Speaker key points are **organizer-provided**, not AI-generated (AI comes later).
- QR codes carry **identifiers only** (`event://checkin/evt_001`, `booth://booth_042`, `session://session_017`); the server resolves them.
- **Three state layers:** Local (IndexedDB / Service Worker / Cache) → Sync queue → Server (authoritative).
- **Recommended stack:** Next.js + TypeScript (alternative: React + Vite); Supabase (Postgres, Auth, RLS, Realtime, Storage).
- **Core tables:** users, events, event_members, booths, locations, sessions, speakers, check_ins, booth_visits, friendships, notes, saved_items.
- **Build phases:** 1 Foundation → 2 Event experience → 3 QR system → 4 Social → 5 Notes → 6 Offline/PWA.
- **Success criteria (spec §29):** 15 steps ending with "close browser, reopen, still see progress". Steps 13–15 are the core proof.

---

## 5. The prototype (`index.html`)

### 5.1 What it is
A single-file, no-build, clickable prototype of the MVP. It shows the app inside a phone frame, with a **prototype control panel** beside it (below it on narrow screens). Vanilla JS, no frameworks. It works when opened from disk, on GitHub Pages, or as a Claude artifact.

### 5.2 Screens and flows implemented
- **Landing / sign-in:** name + email (pre-filled with example data: Ada Morgan / ada.morgan@example.com). Signing in with an email that already has server data restores it ("Welcome back — restored N booth visits…"). Sign-in requires being online.
- **Event entry:** "Scan event QR". A valid code checks you in. An invalid code (`evt_417`, "poster from last spring's expo") shows a validation error.
- **Home:** greeting, event clock, a lanyard-style **attendee badge** (name, `usr_xxxxxx · evt_001`, "Checked in 2:2x PM", "waiting to sync" if pending), tiles for friends here and booths visited N/8 with a meter, Happening now, Up next, and View map / Schedule buttons.
- **Map:** SVG floor plan of the fictional "Meridian Convention Center": Hall A (8 booths in a 4×2 grid), Main Stage, Room 101, Room 102, Hall B, Food Court, Coffee Bar, Registration, 2 restroom sets, First Aid, North and South entrances. It has search, filter chips (All / Booths / Stages & rooms / Food / Services), a legend, tap-to-select with a bottom sheet, and a list of places below. Visited booths turn green with ✓. It notes that friends are never shown on the map.
- **Booth detail:** wayfinding-sign hero ("A42"), a rotated VISITED stamp once visited, category, location, visit card ("Visited at … · Scanned the booth QR / Marked by hand · waiting to sync / saved to your account"), blurb, Scan booth QR, Show on map, "No code? Mark as visited", and the QR payload shown.
- **Schedule:** today's sessions with a "Now" line, live/ended/upcoming states and Attended chips.
- **Session detail:** status chip, time, speaker, room (links to the map), description, attendance (scan session QR if live, "I was there" if past), **key points** each with Save point (hidden until the session starts: "The organiser publishes key points when the session starts"), **my notes** (list with delete, a textarea whose draft autosaves locally, Save note).
- **Friends:** friends checked in with times, "Not here yet", a pending friend request from Tobi Adeyemi (Accept adds them as checked in at 2:05 PM), and a privacy note.
- **Profile:** stats (booths, sessions attended, notes, saved points), visited booths, saved key points, notes, a **Sync card** (queued items "Waiting", recent items "Synced"), a "Show me to friends as attending" switch, and Sign out (with a confirm that warns unsynced changes will be discarded).
- **QR scanner overlay:** simulated camera (viewfinder, scan line, "Reading code…"). Codes are picked from context-aware lists: event codes at entry; this booth's or session's code first; live session doors; all Hall A booths. Esc closes it.
- **Toasts** for every action; a sync pill in the app bar (Saved / Syncing N… / Offline · N waiting).

### 5.3 Control panel
- **Online / Offline** toggle. Offline pauses sync; actions queue locally and flush when back online.
- **Close & reopen the app:** wipes in-memory state, shows the "Restoring your event…" splash, re-reads storage and returns to the same screen.
- **Sign in on a new phone:** deletes local storage (keeps the server), pre-fills the login. Signing in restores everything. It warns if unsynced changes would be lost (the only way to lose data).
- **Reset demo:** erases the server, local and demo data (with confirmation).
- **MVP test script checklist (12 items)**, auto-ticked. Bold items are the key persistence proofs: sign in; check in via event QR; open map; open a booth; scan booth QR; open schedule; open a session; save a point or note; see friends; **close & reopen**; **offline then online sync**; **new phone restore**.
- **"Where your data lives right now":** a live readout of the three layers. This phone (signed in, open screen, waiting to sync, drafts) → sync status → Your account/server (check-in, visits, sessions, notes, saved points).

### 5.4 Internal architecture (for editing the code)
- **Storage:** `localStorage` with an in-memory fallback (every access in try/catch). Keys:
  - `ec.server.v1`: simulated backend `{ users: { [email]: userState } }`
  - `ec.local.v1`: the phone `{ online, email, cache, queue[], log[], drafts{}, route{tab, detail} }`
  - `ec.demo.v1`: checklist flags, `clockBase`, `newPhone`
- **User state:** `{ name, email, checkedInAt, visits{boothId:{at,via}}, attended{sessionId:{at,via}}, saved{pointId:at}, notes[{id,session,content,at}], visible, friendReq }`
- **Sync engine:** `dispatch(type, payload)` → applies `reduce()` optimistically to `local.cache` → pushes to `local.queue` (tagged `offline` if made offline) → `flushSoon()` (900 ms) → `flush()` applies the queue to `server.users[email]`, moves items to `log`, and ticks `offlineSync` if any were offline actions. The reducers are idempotent.
- **Action types:** `checkin`, `visit`, `attend`, `save_point`, `unsave_point`, `note_add`, `note_delete`, `visibility`, `friend_req`.
- **QR handling:** `handleCode(code)` parses `scheme://id` for `event` / `booth` / `session`.
- **Event clock:** starts at 2:20 PM (minute 860) the first time the demo opens (`demo.clockBase`), then runs in real time, capped at 11:59 PM. Session live/past/next status derives from it. Reset demo restarts it.
- **Rendering:** one `render()` rebuilds `#screen` via template strings, preserves each screen's scroll position and input focus/caret, then `renderPanel()`. Event delegation uses `data-act` / `data-arg` attributes mapped to the `A` actions object. There's keyboard support for SVG pins (Enter/Space) and Esc for the scanner. It re-renders every 30 s for the clock (skipped while typing or scanning).
- **Pseudo-QR codes:** `qrSvg(seed)` draws a deterministic 21×21 pattern with finder squares. It is decorative, not scannable.

### 5.5 Sample data (all fictional)
- **Event:** Horizon Tech Summit 2026 · `evt_001` · Thursday, Sept 24 · Meridian Convention Center.
- **Booths (Hall A):** 12 Northwind Robotics (Robotics), 18 Clearpath Sensors (IoT & Sensors), 27 Lumen Labs (AR/VR), 42 Voltline Compute (AI & Computing; replaces the spec's "NVIDIA" example to avoid using a real brand), 55 Harbor Cloud (Cloud), 63 Keystone Security (Security), 71 Fieldnote Bio (Health Tech), 88 Career Commons (Careers).
- **Sessions:** 9:00 Opening Session (Priya Raman, Main Stage) · 10:30 The Future of Intelligent Systems (Dr. Jane Smith, Main Stage) · 12:00 Designing Sensors for the Real World (Marcus Oyelaran, Room 101) · 2:00 AI & The Physical World (Dr. Elena Park, Main Stage; key points taken from the spec's example) · 2:00 Shipping Edge AI on a Budget (Wen Li, Room 101) · 3:30 Robotics & Automation (Tomás Reyes, Room 102) · 5:00 Career Mixer (Career Commons, Hall B). Session IDs: `session_001/007/011/014/015/017/020`.
- **Friends:** David Okafor (10:42 AM), Sarah Lindqvist (11:13 AM), Michael Chen (12:04 PM), Amara Nwosu (1:37 PM), Jonah Weiss (not checked in); pending request from Tobi Adeyemi (2:05 PM).

### 5.6 Visual design
- **Concept:** venue wayfinding signage and a conference lanyard badge.
- **Fonts (Google Fonts):** Archivo (condensed variable widths, used for display and signage type), Atkinson Hyperlegible (body; chosen for legibility), JetBrains Mono (IDs and QR payloads).
- **Light palette:** ground `#E6E9E2`, surface `#FAFBF7`, ink `#15191C`, signage-orange accent `#D4430E`, visited green `#0E7A5F`, warn `#8F5B00`.
- **Dark mode:** full token set under `prefers-color-scheme` and `[data-theme]`. Signage and badge colours invert (light sign on dark ground).
- **Layout:** phone frame (392px, 50px radius) next to a 350px panel. Below 820px the panel stacks under the phone; below 520px the phone goes full-width and the fake status bar is hidden. Respects reduced motion.

### 5.7 What's simulated (tell viewers)
- **Camera / QR scanning:** you tap a code from a list. Real browsers in the artifact sandbox block the camera; a real build would use a camera QR library.
- **Backend:** simulated in browser storage in place of Supabase. Data is per browser: your boss won't see your data, and each viewer starts fresh.
- **All names** of exhibitors, speakers and friends are fictional.
- **Offline:** simulated by the toggle, not real network detection or a service worker.

---

## 6. Environment and setup already done (owner's Windows PC)

- Git 2.55 installed. **Global git email set to `atioluwanimofe@gmail.com`** (the machine previously used a work address, which the owner does not want on commits). Name: Tioluwanimofe Adesanya.
- **GitHub CLI (`gh` 2.101.0) installed** via winget at `C:\Program Files\GitHub CLI\gh.exe`, logged in as `tioluwanimofe` (scopes: repo, gist, read:org). `gh auth setup-git` has been run, so plain `git push` works.
- GitHub Pages is enabled from `main` / root. Every push to `main` redeploys the live site in about a minute.

---

## 7. Owner preferences learned

- Always commit with **atioluwanimofe@gmail.com**, never the work email.
- Wants everything kept together in one GitHub repo.
- Chose a **public** repo (warned that this makes the spec publicly readable; the owner accepted).
- Prefers the assistant to do the setup work end-to-end where possible.
- Isn't deeply technical about web internals yet (asked where the JS lives and whether local files persist data), so explain in plain language.

---

## 8. Status and next steps

**Done:** spec written (by the owner); clickable prototype built; published as a Claude artifact, a GitHub repo and a live GitHub Pages site; mobile rendering verified at 375×812 with no console errors.

**Possible next steps (none started):**
1. Personalize the demo for the pitch: real company or event name, real booth or exhibitor names, a real venue map.
2. Consider making the repo private if the idea is confidential, then invite the boss as a collaborator.
3. Start the real build, following spec Phase 1: Next.js + TypeScript + Supabase project, auth (magic link or Google), database schema from spec §18 with Row Level Security, basic event model.
4. Then Phases 2–6: port the prototype's screens into real components; real QR scanning (camera); `booth_visits` etc. in Postgres; friends; notes; service worker + IndexedDB sync queue (the prototype's `dispatch → queue → flush` model maps directly to this).
5. Later: an organizer dashboard (create events, upload maps, generate QR codes, publish key points) and AI features (live summaries, personalized recaps, recommendations).

**How to update the live demo:** edit `index.html` → commit (as atioluwanimofe@gmail.com) → `git push` → the live at https://tioluwanimofe.github.io/event-companion/ updates in about a minute.
