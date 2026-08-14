"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Clerk can still be hydrating its session when the first views mount, and `getToken()`
 * resolves to `null` until it isn't. Sending the request anyway produced an unauthenticated
 * call, a 401, and a view stuck on its empty state until the user refreshed by hand — so
 * wait briefly for the token instead of firing without one.
 */
async function waitForToken(getToken: () => Promise<string | null>): Promise<string | null> {
  for (let attempt = 0; attempt < 8; attempt++) {
    const token = await getToken();
    if (token) return token;
    await sleep(150 * (attempt + 1)); // ~5s total, well past normal hydration
  }
  return null;
}

/** Hook returning fetch helpers that attach the Clerk JWT to every backend call. */
export function useApi() {
  const { getToken } = useAuth();

  const request = useCallback(
    async <T = unknown>(path: string, opts: RequestInit = {}): Promise<T> => {
      const token = await waitForToken(getToken);
      const res = await fetch(BASE + path, {
        ...opts,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(opts.headers || {}),
        },
      });
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          detail = body.detail || detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      if (res.status === 204) return null as T;
      return res.json();
    },
    [getToken],
  );

  // Stable identity so consumers' useEffect deps don't change every render.
  return useMemo(
    () => ({
      get: <T = unknown>(p: string) => request<T>(p),
      post: <T = unknown>(p: string, body?: unknown) =>
        request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
      put: <T = unknown>(p: string, body?: unknown) =>
        request<T>(p, { method: "PUT", body: JSON.stringify(body) }),
    }),
    [request],
  );
}

export const API_BASE = BASE;
