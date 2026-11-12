// Supabase is used ONLY for email/password sign-in. All data goes through the API.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

// Created lazily (in effects/handlers) so prerendering never needs the env vars.
export function supabase(): SupabaseClient {
  if (!client) {
    client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
    );
  }
  return client;
}
