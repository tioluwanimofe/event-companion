import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { fakeApi, renderPage } from "../test-utils";
import AgendaPage from "./AgendaPage";

const AGENDA = {
  event_slug: "cdc", event_name: "CyberDataCon 2027", timezone: "America/Chicago",
  sessions: [
    { id: "1", title: "Opening keynote", description: "Why data is the new perimeter", track: null, kind: "keynote",
      room: "Ezell Chapel", building: null, speakers: [{ name: "Chris Simmons", company: "Lipscomb University" }],
      starts_at: "2027-04-16T08:30:00-05:00", ends_at: "2027-04-16T09:15:00-05:00" },
    { id: "2", title: "Securing the cloud", description: null, track: "Cloud", kind: "breakout",
      room: "Room 101", building: "Swang", speakers: [], starts_at: "2027-04-16T09:30:00-05:00", ends_at: "2027-04-16T10:00:00-05:00" },
    { id: "3", title: "Hacking smart homes", description: null, track: "IoT", kind: "breakout",
      room: "Room 102", building: "Swang", speakers: [], starts_at: "2027-04-16T09:30:00-05:00", ends_at: "2027-04-16T10:00:00-05:00" },
  ],
};

afterEach(() => vi.unstubAllGlobals());

it("shows the agenda in Nashville time and filters by track", async () => {
  fakeApi({ "GET /api/events/cdc/agenda": { status: 200, body: AGENDA } });
  renderPage("/events/:slug/agenda", "/events/cdc/agenda", <AgendaPage />);

  expect(await screen.findByRole("heading", { name: "Opening keynote" })).toBeInTheDocument();
  expect(screen.getByText("Chris Simmons (Lipscomb University)")).toBeInTheDocument();
  expect(screen.getByText("Room 101, Swang")).toBeInTheDocument();
  expect(screen.getByText(/All times are CDT/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "IoT" }));
  expect(screen.getByRole("heading", { name: "Hacking smart homes" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Securing the cloud" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Opening keynote" })).toBeInTheDocument(); // for everyone
  expect(screen.getByRole("button", { name: "IoT" })).toHaveAttribute("aria-pressed", "true");
});

it("says so when the event doesn't exist", async () => {
  fakeApi({ "GET /api/events/nope/agenda": { status: 404, body: { detail: "No event with slug 'nope'" } } });
  renderPage("/events/:slug/agenda", "/events/nope/agenda", <AgendaPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No event with slug 'nope'");
});
