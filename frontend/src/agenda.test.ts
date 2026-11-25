import { describe, expect, it } from "vitest";
import { groupAgenda, matchesTrack, timeIn, timing, tracksOf, zoneLabel } from "./agenda";
import type { AgendaSession } from "./types";

const CHICAGO = "America/Chicago";
const session = (over: Partial<AgendaSession>): AgendaSession => ({
  id: over.title ?? "x", title: "Talk", description: null, track: null, kind: "breakout",
  room: null, building: null, speakers: [],
  starts_at: "2027-04-16T09:30:00-05:00", ends_at: "2027-04-16T10:00:00-05:00", ...over,
});

describe("agenda helpers", () => {
  it("shows the event's local time, whatever the phone's zone", () => {
    // 14:30 UTC is 9:30 AM in Nashville on April 16 (CDT, UTC-5)
    expect(timeIn("2027-04-16T14:30:00Z", CHICAGO)).toBe("9:30 AM");
    expect(zoneLabel("2027-04-16T14:30:00Z", CHICAGO)).toBe("CDT");
  });

  it("groups sessions into days and slots that start together", () => {
    const days = groupAgenda([
      session({ title: "Welcome", starts_at: "2027-04-16T08:00:00-05:00" }),
      session({ title: "Cloud" }), session({ title: "IoT" }),
      session({ title: "Day two", starts_at: "2027-04-17T09:00:00-05:00" }),
    ], CHICAGO);
    expect(days.map((d) => d.day)).toEqual(["Friday, April 16", "Saturday, April 17"]);
    expect(days[0].slots.map((s) => [s.start, s.sessions.length])).toEqual([["8:00 AM", 1], ["9:30 AM", 2]]);
  });

  it("knows what's happening now", () => {
    const s = session({});
    expect(timing(s, new Date("2027-04-16T14:29:00Z"))).toBe("later");
    expect(timing(s, new Date("2027-04-16T14:45:00Z"))).toBe("now");
    expect(timing(s, new Date("2027-04-16T15:00:00Z"))).toBe("past");
  });

  it("filters by track but keeps untracked sessions (keynote, lunch) for everyone", () => {
    const cloud = session({ track: "Cloud" });
    const iot = session({ track: "IoT" });
    const lunch = session({ kind: "meal" });
    expect(tracksOf([iot, cloud, lunch, cloud])).toEqual(["Cloud", "IoT"]);
    expect([cloud, iot, lunch].filter((s) => matchesTrack(s, "Cloud"))).toEqual([cloud, lunch]);
    expect([cloud, iot, lunch].filter((s) => matchesTrack(s, null))).toHaveLength(3);
  });
});
