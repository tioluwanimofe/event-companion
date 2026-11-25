// Every call to FastAPI goes through here. Pages never call fetch() directly.
// The paths start with /api, so they go to the same address as the page (ADR 0005)
// and the browser attaches the sign-in cookie by itself. No tokens in JavaScript.
import type { Agenda, Lead, Me, MyBooth, ScanPreview, ScanResult, Visit } from "./types";

/** An error the API answered with, e.g. 404 "This QR code isn't active". */
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      ...init,
    });
  } catch {
    // fetch only throws when there's no answer at all: offline, Wi-Fi dropped, API down
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (!response.ok) {
    // FastAPI puts its human-readable reason in { "detail": "..." }
    let message = `Something went wrong (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") message = body.detail;
    } catch {
      /* not JSON: keep the generic message */
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const token = (t: string) => encodeURIComponent(t);

export const api = {
  /** The signed-in person, or null if nobody is signed in. */
  async me(): Promise<Me | null> {
    try {
      return await request<Me>("/auth/me");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    }
  },
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  scanPreview: (t: string) => request<ScanPreview>(`/scan/${token(t)}`),
  shareWithBooth: (t: string) => request<ScanResult>(`/scan/${token(t)}`, { method: "POST" }),
  myVisits: () => request<Visit[]>("/me/booth-visits"),
  agenda: (slug: string) => request<Agenda>(`/events/${encodeURIComponent(slug)}/agenda`),
  myBooths: () => request<MyBooth[]>("/my-booths"),
  boothLeads: (boothId: string) => request<Lead[]>(`/my-booths/${encodeURIComponent(boothId)}/leads`),
};

/**
 * The leads spreadsheet. A plain link (not fetch) so the browser downloads the file
 * itself, sending the sign-in cookie like any other request to this address.
 */
export function leadsCsvUrl(boothId: string): string {
  return `/api/my-booths/${encodeURIComponent(boothId)}/leads.csv`;
}

/**
 * Sign-in is a full page visit, not fetch(): the browser has to go to Google and back.
 * `next` brings the person back to the page they were on (checked by safe_next() in FastAPI).
 */
export function signInUrl(next: string): string {
  return `/api/auth/google/login?next=${encodeURIComponent(next)}`;
}
