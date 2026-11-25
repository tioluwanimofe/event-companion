// Tests for the scan page. We fake the API (fetch) and check what a person sees.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import ScanPage from "./ScanPage";

const preview = {
  booth_name: "Harbor Cloud", description: "Cloud security for ports",
  location_label: "Booth 12, Swang Atrium", event_name: "CyberDataCon 2027",
  signed_in: true, already_shared_at: null,
};

/** Fake API: each entry answers one "METHOD /path". Records every call. */
function fakeApi(routes: Record<string, { status: number; body?: unknown }>) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    calls.push(key);
    const answer = routes[key] ?? { status: 404, body: { detail: "Not Found" } };
    return new Response(JSON.stringify(answer.body ?? null), { status: answer.status });
  }));
  return calls;
}

function openScanPage(token = "abc123") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/scan/${token}`]}>
        <Routes><Route path="/scan/:token" element={<ScanPage />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("ScanPage", () => {
  it("shows the booth, and opening the page shares nothing", async () => {
    const calls = fakeApi({ "GET /api/scan/abc123": { status: 200, body: preview } });
    openScanPage();
    expect(await screen.findByRole("heading", { name: "Harbor Cloud" })).toBeInTheDocument();
    expect(screen.getByText("Booth 12, Swang Atrium")).toBeInTheDocument();
    expect(calls).toEqual(["GET /api/scan/abc123"]); // no POST: consent needs a tap
  });

  it("sends signed-out visitors to Google and back to this booth", async () => {
    fakeApi({ "GET /api/scan/abc123": { status: 200, body: { ...preview, signed_in: false } } });
    openScanPage();
    const link = await screen.findByRole("link", { name: /sign in with google/i });
    expect(link).toHaveAttribute("href", "/api/auth/google/login?next=%2Fscan%2Fabc123");
  });

  it("shares on tap and shows the booth's notes", async () => {
    const calls = fakeApi({
      "GET /api/scan/abc123": { status: 200, body: preview },
      "POST /api/scan/abc123": { status: 200, body: {
        booth_name: "Harbor Cloud", location_label: "Booth 12, Swang Atrium",
        preloaded_notes: "Slides: example.com/slides\nRaffle at 3pm",
        shared_at: "2027-04-16T15:42:00Z", first_time: true } },
    });
    openScanPage();
    await userEvent.click(await screen.findByRole("button", { name: "Share my profile" }));
    expect(await screen.findByText("✓ Shared")).toBeInTheDocument();
    expect(screen.getByText(/Raffle at 3pm/)).toBeInTheDocument();
    expect(calls).toContain("POST /api/scan/abc123");
  });

  it("explains when the person isn't registered for the event", async () => {
    fakeApi({
      "GET /api/scan/abc123": { status: 200, body: preview },
      "POST /api/scan/abc123": { status: 403, body: { detail: "You're not on the registration list for this event." } },
    });
    openScanPage();
    await userEvent.click(await screen.findByRole("button", { name: "Share my profile" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("not on the registration list");
  });

  it("explains a retired or fake QR code, with no pointless retry button", async () => {
    fakeApi({ "GET /api/scan/old": { status: 404, body: { detail: "This QR code isn't active." } } });
    openScanPage("old");
    expect(await screen.findByText("This QR code isn't active.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });

  it("offers a retry when the connection drops", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    openScanPage();
    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
