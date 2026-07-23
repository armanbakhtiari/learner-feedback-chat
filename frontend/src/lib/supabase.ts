"use client";

import { createClient, SupabaseClient } from "@supabase/supabase-js";

/**
 * Browser Supabase client authenticated with the Clerk session token
 * (Supabase third-party auth). Used ONLY for realtime notification subscriptions;
 * all writes go through the FastAPI backend.
 */
export function makeSupabase(getToken: () => Promise<string | null>): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      accessToken: async () => (await getToken()) ?? "",
      realtime: { params: { eventsPerSecond: 5 } },
    },
  );
}
