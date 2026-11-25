// Helpers shared by the page tests.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

type Answer = { status: number; body?: unknown };

/** Fake API: each entry answers one "METHOD /path". Returns the list of calls made. */
export function fakeApi(routes: Record<string, Answer>) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    calls.push(key);
    const answer = routes[key] ?? { status: 404, body: { detail: "Not Found" } };
    return new Response(JSON.stringify(answer.body ?? null), { status: answer.status });
  }));
  return calls;
}

/** Render one page at `url`, matched by the route `path`, with a fresh cache. */
export function renderPage(path: string, url: string, page: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <Routes><Route path={path} element={page} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export const ME = {
  id: "u1", email: "maya@harbor.example", first_name: "Maya", last_name: "Okafor",
  is_platform_admin: false, roles: [{ event_slug: "cdc", role: "booth_owner" }],
};
