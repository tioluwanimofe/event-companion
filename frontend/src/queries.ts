import { QueryClient, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 🧠 Retry only when it might help. A 404 or 403 will say the same thing
      // every time, but a dropped connection (status 0) or a server hiccup (5xx) might not.
      retry: (failures, error) =>
        failures < 3 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
      refetchOnWindowFocus: false,
    },
  },
});

/** Query keys: the names TanStack Query files each answer under in its cache. */
export const keys = {
  me: ["me"] as const,
  scan: (token: string) => ["scan", token] as const,
  visits: ["visits"] as const,
  myBooths: ["my-booths"] as const,
  agenda: (slug: string) => ["agenda", slug] as const,
  leads: (boothId: string) => ["leads", boothId] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: api.me, staleTime: 60_000 });
}

/** Booths the signed-in person runs. Empty list for most attendees. */
export function useMyBooths(enabled = true) {
  return useQuery({ queryKey: keys.myBooths, queryFn: api.myBooths, enabled });
}
