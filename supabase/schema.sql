-- Flowstate sync schema — run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Requires Google provider enabled under Authentication → Providers.

-- ---------------------------------------------------------------------------
-- Tasks (mirrors todos.json)
-- ---------------------------------------------------------------------------
create table if not exists public.tasks (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  completed boolean not null default false,
  notes text not null default '',
  created_at timestamptz not null,
  client_updated_at timestamptz not null,
  server_updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists tasks_user_server_idx
  on public.tasks (user_id, server_updated_at);

-- ---------------------------------------------------------------------------
-- Planner tasks (mirrors planner.json tasks[] — never virt-* IDs)
-- ---------------------------------------------------------------------------
create table if not exists public.planner_tasks (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  task_date date not null,
  start_min integer not null default 540,
  end_min integer not null default 600,
  all_day boolean not null default false,
  notes text not null default '',
  completed boolean not null default false,
  repeat text not null default 'none',
  color text not null default 'coral',
  created_at timestamptz not null,
  client_updated_at timestamptz not null,
  server_updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists planner_tasks_user_server_idx
  on public.planner_tasks (user_id, server_updated_at);

-- ---------------------------------------------------------------------------
-- Planner inbox (mirrors planner.json inbox[])
-- ---------------------------------------------------------------------------
create table if not exists public.inbox_items (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  client_updated_at timestamptz not null,
  server_updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists inbox_items_user_server_idx
  on public.inbox_items (user_id, server_updated_at);

-- ---------------------------------------------------------------------------
-- server_updated_at triggers
-- ---------------------------------------------------------------------------
create or replace function public.set_server_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.server_updated_at = now();
  return new;
end;
$$;

drop trigger if exists tasks_server_updated_at on public.tasks;
create trigger tasks_server_updated_at
  before update on public.tasks
  for each row execute function public.set_server_updated_at();

drop trigger if exists planner_tasks_server_updated_at on public.planner_tasks;
create trigger planner_tasks_server_updated_at
  before update on public.planner_tasks
  for each row execute function public.set_server_updated_at();

drop trigger if exists inbox_items_server_updated_at on public.inbox_items;
create trigger inbox_items_server_updated_at
  before update on public.inbox_items
  for each row execute function public.set_server_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
alter table public.tasks enable row level security;
alter table public.planner_tasks enable row level security;
alter table public.inbox_items enable row level security;

create policy tasks_select on public.tasks
  for select using (auth.uid() = user_id);
create policy tasks_insert on public.tasks
  for insert with check (auth.uid() = user_id);
create policy tasks_update on public.tasks
  for update using (auth.uid() = user_id);
create policy tasks_delete on public.tasks
  for delete using (auth.uid() = user_id);

create policy planner_tasks_select on public.planner_tasks
  for select using (auth.uid() = user_id);
create policy planner_tasks_insert on public.planner_tasks
  for insert with check (auth.uid() = user_id);
create policy planner_tasks_update on public.planner_tasks
  for update using (auth.uid() = user_id);
create policy planner_tasks_delete on public.planner_tasks
  for delete using (auth.uid() = user_id);

create policy inbox_items_select on public.inbox_items
  for select using (auth.uid() = user_id);
create policy inbox_items_insert on public.inbox_items
  for insert with check (auth.uid() = user_id);
create policy inbox_items_update on public.inbox_items
  for update using (auth.uid() = user_id);
create policy inbox_items_delete on public.inbox_items
  for delete using (auth.uid() = user_id);

-- Optional: enable Realtime (Dashboard → Database → Replication) on these tables.
