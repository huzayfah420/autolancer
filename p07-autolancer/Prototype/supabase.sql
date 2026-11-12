-- Autolancer Phase 1: row-level security for the six API tables.
--
-- Run this once in the Supabase SQL editor AFTER the API has started at least once
-- (the API creates the tables on startup with SQLAlchemy create_all).
--
-- The API itself connects as the `postgres` role (which bypasses RLS) and filters every
-- query by owner_id. These policies are the second layer: anyone using the anon or
-- authenticated keys directly (e.g. through the Supabase REST API) only ever sees rows
-- whose owner_id equals their own auth.uid().

do $$
declare
  t text;
begin
  -- Ordinary owner-only tables: full access to your own rows, nothing else.
  foreach t in array array['profiles', 'connections', 'listings', 'assessments'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('drop policy if exists owner_only on public.%I', t);
    execute format(
      'create policy owner_only on public.%I for all to authenticated '
      'using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()))', t);
  end loop;

  -- Append-only tables (policy history and the AI cost ledger): read and insert only.
  foreach t in array array['policy_versions', 'ai_usage'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon', t);
    execute format('revoke update, delete on public.%I from authenticated', t);
    execute format('drop policy if exists owner_read on public.%I', t);
    execute format('drop policy if exists owner_insert on public.%I', t);
    execute format(
      'create policy owner_read on public.%I for select to authenticated '
      'using (owner_id = (select auth.uid()))', t);
    execute format(
      'create policy owner_insert on public.%I for insert to authenticated '
      'with check (owner_id = (select auth.uid()))', t);
  end loop;
end $$;
