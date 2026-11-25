// Pure helpers for the agenda page: no React, so they're easy to test.
// 🧠 Times are shown in the EVENT's time zone, not the phone's. Someone flying in from
// California still needs "9:30 AM" to mean 9:30 in Nashville, where the talk happens.
import type { AgendaSession } from "./types";

export function timeIn(iso: string, timeZone: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone });
}

function dayIn(iso: string, timeZone: string): string {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", timeZone });
}

/** "CST" / "CDT": the short name of the event's zone on that date. */
export function zoneLabel(iso: string, timeZone: string): string {
  const part = new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: "short" })
    .formatToParts(new Date(iso)).find((p) => p.type === "timeZoneName");
  return part?.value ?? timeZone;
}

export interface TimeSlot { start: string; sessions: AgendaSession[] }
export interface AgendaDay { day: string; slots: TimeSlot[] }

/** Sessions (already in time order from the API) → days → slots that start together. */
export function groupAgenda(sessions: AgendaSession[], timeZone: string): AgendaDay[] {
  const days: AgendaDay[] = [];
  for (const session of sessions) {
    const day = dayIn(session.starts_at, timeZone);
    const start = timeIn(session.starts_at, timeZone);
    let today = days.at(-1);
    if (today?.day !== day) days.push((today = { day, slots: [] }));
    let slot = today.slots.at(-1);
    if (slot?.start !== start) today.slots.push((slot = { start, sessions: [] }));
    slot.sessions.push(session);
  }
  return days;
}

export type Timing = "past" | "now" | "later";

export function timing(session: AgendaSession, now: Date): Timing {
  if (now >= new Date(session.ends_at)) return "past";
  if (now >= new Date(session.starts_at)) return "now";
  return "later";
}

/** Every track used, A to Z, for the filter buttons. */
export function tracksOf(sessions: AgendaSession[]): string[] {
  return [...new Set(sessions.map((s) => s.track).filter((t): t is string => !!t))].sort();
}

/** Sessions with no track (keynotes, lunch, networking) are for everyone, so a filter keeps them. */
export function matchesTrack(session: AgendaSession, track: string | null): boolean {
  return track === null || !session.track || session.track === track;
}
