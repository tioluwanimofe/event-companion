# Event Companion
## Product Specification & MVP Architecture

**Version:** 1.0  
**Status:** MVP Planning  
**Product Type:** Progressive Web App (PWA)  
**Primary Platform:** Mobile Web / PWA  
**Future Platforms:** Native mobile applications, event-admin dashboard

---

# 1. Product Overview

Event Companion is a web-first event application designed to help attendees navigate and participate in an event through a single digital experience.

The application allows attendees to:

1. Check into an event using a QR code.
2. View an interactive map of the event and locate booths, stages, rooms, food, and other important locations.
3. Discover which friends are currently attending or checked into the event.
4. Follow speakers and view important points from presentations.
5. Save important information during the event.
6. Track booths, sessions, and activities they have visited.
7. Maintain their event progress even if the application closes, the browser crashes, the phone restarts, or the user temporarily loses internet connectivity.

The core design principle is:

> **The event should remember the attendee, not the phone.**

The user's event state should therefore be synchronized with a persistent backend rather than existing only inside the application.

---

# 2. Problem

Large events can become difficult to navigate and participate in.

Attendees may need to:

- Find specific booths.
- Remember where they have already been.
- Find friends.
- Determine which sessions are currently happening.
- Remember important information from speakers.
- Keep track of their participation.
- Check into different areas.
- Navigate unfamiliar venues.

These activities are often fragmented across physical maps, schedules, paper materials, QR codes, social media, and separate event applications.

Event Companion combines these interactions into one experience.

---

# 3. Target User

## Primary User

An attendee at a conference, career fair, convention, expo, university event, church conference, technology conference, or similar organized event.

### Example

A student attends a technology conference.

They:

1. Scan the event QR code.
2. Enter the event.
3. See the event map.
4. Locate NVIDIA's booth.
5. Scan the booth QR code.
6. The booth is marked as visited.
7. They see that two friends are currently at the event.
8. They attend a keynote.
9. They follow the speaker's key points through the app.
10. They save a particularly interesting point.
11. Their phone accidentally closes.
12. They reopen the application.
13. Their check-in, booth visit, saved notes, and event progress remain intact.

---

# 4. Product Goals

## MVP Goals

The MVP should prove five things:

### Goal 1 — Persistent Event Identity

A user can identify themselves and return to their event session without losing progress.

### Goal 2 — QR-Based Interaction

A user can scan a QR code to perform an event action.

### Goal 3 — Event Navigation

A user can see where important event locations are.

### Goal 4 — Social Presence

A user can see which friends are participating in the event.

### Goal 5 — Event Information

A user can access speaker/session information and save important points.

---

# 5. Non-Goals for MVP

The following should NOT be part of the initial MVP:

- AI-generated speaker summaries
- Complex recommendation algorithms
- Live indoor GPS positioning
- Native iOS application
- Native Android application
- Payments
- Ticket purchasing
- Messaging/chat
- Push notifications
- Facial recognition
- Advanced analytics
- Automatic speech transcription
- Complex gamification
- Multiple simultaneous events for the same user
- Full event organizer marketplace

These can be added after the core system works.

---

# 6. Core User Experience

## Main Navigation

The attendee should have five primary areas:

```text
┌─────────────────────────────┐
│       EVENT COMPANION       │
├─────────────────────────────┤
│                             │
│        EVENT HOME           │
│                             │
│  ✓ Checked In               │
│  👥 12 Friends Here         │
│  🎤 Current Session         │
│  📍 7 Booths Visited        │
│                             │
├─────────────────────────────┤
│ Map | Schedule | Friends   │
│           Notes             │
└─────────────────────────────┘
```

For MVP, the navigation can be:

**Home | Map | Schedule | Friends | Profile**

Notes can initially live inside sessions rather than requiring a separate navigation item.

---

# 7. Feature Specification

## 7.1 Event Check-In

### User Flow

```text
Open Event Companion
        ↓
Scan Event QR Code
        ↓
Identify / authenticate user
        ↓
Event confirmed
        ↓
User marked as checked in
        ↓
Event Home
```

### QR Code

Each event has a unique QR code.

Example payload:

```text
event://checkin/event_2026_001
```

The QR code should not contain sensitive user information.

The server validates the event identifier.

### Check-In Data

```text
User
Event
Check-in timestamp
Last activity
```

Example:

```json
{
  "user_id": "usr_123",
  "event_id": "evt_001",
  "checked_in_at": "2026-09-24T14:30:00Z"
}
```

---

# 8. Booth System

Every booth receives a unique identifier.

Example:

```text
Booth:
id: booth_042
name: NVIDIA
category: AI
location: Hall A
coordinates: x/y
```

The booth can have its own QR code.

### User Flow

```text
User approaches booth
        ↓
Scans QR code
        ↓
Server identifies booth
        ↓
Booth marked "Visited"
        ↓
User sees booth information
```

Example:

```text
✓ NVIDIA

AI & Computing

Hall A — Booth 42

Visited at 2:31 PM

[View Booth]
```

---

# 9. Event Map

The MVP should use a **static event map with interactive locations** rather than attempting real-time indoor GPS.

The map contains:

- Booths
- Main stage
- Session rooms
- Restrooms
- Food
- Registration
- Entrances
- Other important locations

Example conceptual data:

```json
{
  "id": "booth_042",
  "type": "booth",
  "name": "NVIDIA",
  "x": 72,
  "y": 38
}
```

The frontend renders these coordinates on top of an event floor-plan image or SVG.

### Important architectural decision

Do NOT initially build a sophisticated indoor positioning system.

Instead:

> **Map = visual navigation.**

Later:

> **Indoor positioning = optional advanced feature.**

---

# 10. Friends System

Users can optionally connect with friends.

The MVP should avoid building a full social network.

Instead, use a simple relationship model:

```text
User A
  ↕
Friend relationship
  ↕
User B
```

When attending an event, a user can see:

```text
Friends at this event

● David
  Checked in 10:42 AM

● Sarah
  Checked in 11:13 AM

● Michael
  Checked in 12:04 PM
```

The application should distinguish:

**"Checked into event"**

from:

**"Currently at this exact location."**

For MVP, friends should only have event-level presence.

Exact location sharing can be an optional future feature because of privacy concerns.

---

# 11. Speaker / Session System

Each event contains sessions.

Example:

```text
2:00 PM

The Future of Intelligent Systems

Speaker:
Dr. Jane Smith

Room:
Main Stage
```

The session page contains:

- Speaker
- Title
- Description
- Time
- Location
- Key points
- Save button
- Personal notes

---

# 12. Speaker Key Points

For the MVP, key points should be **event-provided content** rather than AI-generated content.

Example:

```text
KEY POINTS

• AI systems increasingly interact with
  physical environments.

• Reliable sensor data is essential.

• Engineers should design for failure.

[Save Point]
```

This allows the feature to work without paying for an AI API.

### Future AI version

Later:

```text
Audio / Transcript
        ↓
AI processing
        ↓
Key points
        ↓
Speaker page
```

Potential future functionality:

- Live transcription
- Automatic summaries
- Important quotes
- Topic extraction
- Personalized summaries
- Questions generated from the presentation

---

# 13. Personal Notes

Users can create notes during sessions.

Example:

```text
SESSION NOTES

"Need to look into edge AI for
sensor systems."

[Save]
```

Notes must be associated with:

```text
User
Event
Session
Timestamp
```

---

# 14. Persistent State

This is one of the most important architectural requirements.

The system should have three layers of state.

## Layer 1 — Local State

Used for temporary/offline operation.

Possible technologies:

- IndexedDB
- Service Worker
- Cache API

Store:

- Current event
- Recently viewed data
- Unsynchronized actions
- Draft notes
- UI preferences

---

## Layer 2 — Server State

The backend is the authoritative source.

Store:

- User
- Event
- Check-ins
- Booth visits
- Friends
- Sessions
- Notes
- Saved items

---

## Layer 3 — Synchronization

When connectivity exists:

```text
Local Action
     ↓
Local database
     ↓
Sync queue
     ↓
Backend
     ↓
Confirmed
```

If the internet disappears:

```text
User scans QR
     ↓
Action stored locally
     ↓
"Waiting to sync"
     ↓
Internet returns
     ↓
Action uploaded
     ↓
Server confirms
```

This is what makes the application resilient.

---

# 15. Recommended MVP Technology Stack

## Frontend

**Next.js + TypeScript**

Why:

- Excellent web application framework
- React ecosystem
- Easy routing
- Good PWA support
- Strong TypeScript support
- Can eventually support more complex applications

Alternative:

**React + Vite**

This is perfectly reasonable if you want a simpler learning environment.

---

# 16. Backend

For the MVP, use:

**Supabase**

Use:

- PostgreSQL
- Authentication
- Database
- Row-level security
- Realtime capabilities
- Storage

This significantly reduces backend infrastructure that would otherwise need to be built.

---

# 17. Database

Core tables:

```text
users
events
event_members
booths
locations
sessions
speakers
check_ins
booth_visits
friendships
notes
saved_items
```

### Relationship

```text
User
 │
 ├── Event Membership
 │
 ├── Check-ins
 │
 ├── Booth Visits
 │
 ├── Friendships
 │
 └── Notes
```

```text
Event
 │
 ├── Booths
 ├── Locations
 ├── Sessions
 │     └── Speakers
 └── Users
```

---

# 18. Simplified Database Schema

## users

```text
id
name
email
avatar_url
created_at
```

## events

```text
id
name
description
start_date
end_date
venue
map_url
created_at
```

## booths

```text
id
event_id
name
description
category
location_id
qr_code
```

## locations

```text
id
event_id
name
type
x
y
```

## sessions

```text
id
event_id
speaker_id
title
description
start_time
end_time
location_id
```

## speakers

```text
id
name
bio
photo_url
```

## check_ins

```text
id
user_id
event_id
checked_in_at
```

## booth_visits

```text
id
user_id
booth_id
visited_at
```

## friendships

```text
id
user_id
friend_id
status
```

## notes

```text
id
user_id
session_id
content
created_at
updated_at
```

---

# 19. QR Architecture

The QR system should use identifiers rather than embedding large amounts of data.

Example:

```text
event://evt_001
booth://booth_042
session://session_017
```

The frontend reads the QR code and sends the identifier to the backend.

The backend determines what the identifier represents.

This prevents users from modifying important information simply by editing QR contents.

---

# 20. PWA Architecture

The application should be installable from the browser.

```text
Browser
   │
   ├── Web App
   │
   ├── Service Worker
   │
   ├── IndexedDB
   │
   └── Cache
          │
          ↓
       Backend
```

The service worker can cache:

- Application shell
- Event map
- Event information
- Session information
- Previously accessed booth information

The application can therefore remain partially functional when connectivity is poor.

---

# 21. Offline Strategy

Not everything needs to work offline.

### Offline MVP

Should work:

- Open previously loaded event
- View cached map
- View cached booths
- View cached sessions
- View saved notes
- Create notes
- Record booth visit locally
- Queue actions for synchronization

### Requires connectivity

Initially:

- Login
- Loading a completely new event
- Finding newly added friends
- Server-side validation
- Cross-device synchronization

---

# 22. Authentication

MVP options:

### Option A — Email/password

Simple and familiar.

### Option B — Magic link

User enters email and receives a login link.

### Option C — Google authentication

Convenient for users.

For the first prototype, authentication can be simplified while developing.

Before real deployment, persistent accounts should be implemented.

---

# 23. MVP Screens

The first production-quality prototype should contain approximately these screens:

### 1. Landing / Login

```text
Event Companion

[Continue]
```

### 2. Event Entry

```text
Scan Event QR

[Scan QR]
```

### 3. Home

```text
Welcome, Attendee

✓ Checked in

12 friends here

Current session:
AI & The Physical World

[View Map]
[View Schedule]
```

### 4. Map

```text
EVENT MAP

● Booth 1
● Booth 2
● Main Stage
● Food
● Registration
```

### 5. Booth

```text
NVIDIA

AI & Computing

Hall A — Booth 42

[Mark as visited]
```

### 6. Schedule

```text
TODAY

1:00 PM
Opening Session

2:00 PM
The Future of AI

3:30 PM
Robotics & Automation
```

### 7. Session

```text
The Future of AI

Dr. Jane Smith

2:00 PM
Main Stage

KEY POINTS
...

MY NOTES
[                    ]

[Save]
```

### 8. Friends

```text
FRIENDS HERE

● Sarah
● David
● Michael
```

### 9. Profile

```text
MY EVENT

✓ Event checked in

7 booths visited

3 sessions attended

5 saved notes
```

---

# 24. MVP User Journey

The entire MVP should support this journey:

```text
                    START
                      │
                      ↓
                Scan Event QR
                      │
                      ↓
                  Check In
                      │
                      ↓
                  Event Home
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
        MAP       SCHEDULE     FRIENDS
          │           │
          ↓           ↓
       Booth       Session
          │           │
          ↓           ↓
       Scan QR     Key Points
          │           │
          ↓           ↓
       Visited       Notes
          │           │
          └──────┬────┘
                 ↓
             Sync State
                 ↓
          Persistent Account
```

---

# 25. MVP Development Phases

## Phase 1 — Foundation

Build:

- Next.js application
- TypeScript
- Supabase
- Authentication
- Database schema
- Basic event model

**Deliverable:** User can enter an event.

---

## Phase 2 — Event Experience

Build:

- Home screen
- Event map
- Booth database
- Schedule
- Speaker pages

**Deliverable:** User can explore an event digitally.

---

## Phase 3 — QR System

Build:

- QR scanning
- Event check-in
- Booth QR codes
- Booth visit tracking

**Deliverable:** Physical event actions become digital actions.

---

## Phase 4 — Social

Build:

- Friend relationships
- Event attendance
- Friends-at-event view

**Deliverable:** Users can discover which friends are attending.

---

## Phase 5 — Notes

Build:

- Session notes
- Saved key points
- Personal event history

**Deliverable:** User can create a personal record of the event.

---

## Phase 6 — Offline/PWA

Build:

- Service worker
- IndexedDB
- Offline cache
- Sync queue
- Conflict handling

**Deliverable:** Closing/crashing/temporarily losing connectivity doesn't destroy event progress.

---

# 26. Future Architecture

Once the MVP works:

```text
                         EVENT PLATFORM
                               │
              ┌────────────────┼────────────────┐
              │                │                │
           Attendee         Organizer           AI
              │                │                │
         ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
         │         │      │         │      │         │
        Map     Friends  Events   Booths  Summaries Transcripts
        QR      Notes    Sessions Analytics Key Pts  Q&A
```

Eventually the platform could have two applications:

### Attendee App

The experience being designed now.

### Organizer Dashboard

Event organizers could:

- Create events
- Upload maps
- Create booths
- Generate QR codes
- Add speakers
- Create schedules
- Publish key points
- Monitor attendance
- View booth engagement
- Manage attendees

---

# 27. Future AI Features

AI should be added **after the core product works**.

Potential AI functionality:

### Live Speaker Summarization

```text
Speaker
   ↓
Audio
   ↓
Speech-to-text
   ↓
LLM
   ↓
Key Points
   ↓
Attendee App
```

### Personalized Event Summary

At the end:

> "Here's what you experienced today."

The system could summarize:

- Sessions attended
- Booths visited
- Notes
- Saved points

### Intelligent Recommendations

Eventually:

> "Based on the sessions you've attended, you might be interested in Booth 31."

AI should be a useful layer on top of the product rather than a requirement for the basic product.

---

# 28. Security & Privacy

The application should follow several principles.

### Friends

Users should control whether they appear as attending.

### Location

MVP should NOT expose precise real-time location.

### QR codes

QR codes should contain identifiers, not sensitive personal information.

### Authentication

All event-specific data should be protected by authenticated access rules.

### Database

Supabase Row Level Security should restrict users to data they are authorized to access.

---

# 29. Success Criteria for MVP

The MVP is successful if a test attendee can:

1. Open the application.
2. Join an event.
3. Check in using a QR code.
4. View the event map.
5. Find a booth.
6. Scan the booth QR code.
7. See that the booth was visited.
8. View the event schedule.
9. Open a speaker/session.
10. Read key points.
11. Save a personal note.
12. See friends attending the event.
13. Close the browser.
14. Reopen the application.
15. Still see their event progress.

**Steps 13–15 are especially important.**

That is the fundamental proof that the architecture works.

---

# 30. MVP Definition

The first version should NOT attempt to be the complete event platform.

The MVP is:

> **A persistent, mobile-first event companion that combines event check-in, interactive navigation, booth tracking, social attendance, and session information into one web application.**

The core technical experiment is:

> **Can a PWA maintain a reliable attendee state across QR interactions, temporary offline conditions, application closures, and different devices?**

---

# 31. Recommended First Build

Do not build the entire specification at once.

The first proof of concept should be:

```text
Event
  ↓
QR Check-In
  ↓
Home
  ↓
Map
  ↓
Booth QR
  ↓
Persistent Booth Visit
```

Once that works, add:

```text
Friends
  ↓
Sessions
  ↓
Speaker Key Points
  ↓
Personal Notes
  ↓
Offline Synchronization
  ↓
AI Features
```

This creates a deliberate progression:

**Physical QR → Web App → Database → Persistent State → Offline System → Social Features → AI**

That progression allows each technical layer to be tested before adding the next one.
