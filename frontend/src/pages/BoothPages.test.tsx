// Tests for the booth owner's pages: My booths and the leads list.
import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fakeApi, ME, renderPage } from "../test-utils";
import BoothLeadsPage, { leadSubtitle } from "./BoothLeadsPage";
import MyBoothsPage from "./MyBoothsPage";

const HARBOR = {
  id: "b1", event_slug: "cdc", name: "Harbor Cloud", location_label: "Booth 12",
  lead_count: 2, leads_csv: "/my-booths/b1/leads.csv",
};
const ADA = {
  first_name: "Ada", last_name: "Lovelace", email: "ada@example.com", company: "Analytical Engines",
  job_title: "Engineer", is_student: false, university: null, major: null,
  shared_at: "2027-04-16T15:42:00Z",
};
const GRACE = {
  ...ADA, first_name: "Grace", last_name: "Hopper", email: "grace@example.com",
  company: null, job_title: null, is_student: true, university: "Lipscomb University", major: "Computer Science",
};

afterEach(() => vi.unstubAllGlobals());

describe("MyBoothsPage", () => {
  it("lists my booths with their lead counts", async () => {
    fakeApi({ "GET /api/auth/me": { status: 200, body: ME }, "GET /api/my-booths": { status: 200, body: [HARBOR] } });
    renderPage("/my-booths", "/my-booths", <MyBoothsPage />);
    const row = await screen.findByRole("link", { name: /Harbor Cloud/ });
    expect(row).toHaveAttribute("href", "/my-booths/b1");
    expect(screen.getByLabelText("2 leads")).toBeInTheDocument();
  });

  it("asks signed-out people to sign in and come back here", async () => {
    fakeApi({ "GET /api/auth/me": { status: 401, body: { detail: "Not signed in" } } });
    renderPage("/my-booths", "/my-booths", <MyBoothsPage />);
    expect(await screen.findByRole("link", { name: "Sign in with Google" }))
      .toHaveAttribute("href", "/api/auth/google/login?next=%2Fmy-booths");
  });
});

describe("BoothLeadsPage", () => {
  const routes = {
    "GET /api/auth/me": { status: 200, body: ME },
    "GET /api/my-booths": { status: 200, body: [HARBOR] },
    "GET /api/my-booths/b1/leads": { status: 200, body: [ADA, GRACE] },
  };

  it("shows each lead with a way to email them, and the spreadsheet link", async () => {
    fakeApi(routes);
    renderPage("/my-booths/:boothId", "/my-booths/b1", <BoothLeadsPage />);
    expect(await screen.findByRole("heading", { name: "Ada Lovelace" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Harbor Cloud" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "grace@example.com" })).toHaveAttribute("href", "mailto:grace@example.com");
    expect(screen.getByRole("link", { name: "Download spreadsheet" })).toHaveAttribute("href", "/api/my-booths/b1/leads.csv");
  });

  it("shows the API's reason when it's not your booth", async () => {
    fakeApi({ ...routes, "GET /api/my-booths/b1/leads": { status: 403, body: { detail: "Only this booth's owners can see its leads" } } });
    renderPage("/my-booths/:boothId", "/my-booths/b1", <BoothLeadsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Only this booth's owners");
    expect(screen.queryByRole("link", { name: "Download spreadsheet" })).not.toBeInTheDocument();
  });

  it("describes students and professionals differently", () => {
    expect(leadSubtitle(ADA)).toBe("Engineer at Analytical Engines");
    expect(leadSubtitle(GRACE)).toBe("Student · Lipscomb University · Computer Science");
    expect(leadSubtitle({ ...ADA, job_title: null })).toBe("Analytical Engines");
  });
});
