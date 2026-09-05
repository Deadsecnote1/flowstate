-- Flowstate patch: last-write-wins on client_updated_at
-- Run once in Supabase SQL Editor if you already applied schema.sql earlier.
-- (Also included in supabase/schema.sql for new projects.)

create or replace function public.reject_stale_client_update()
returns trigger
language plpgsql
as $$
begin
  if new.client_updated_at < old.client_updated_at then
    return null;
  end if;
  return new;
end;
$$;

drop trigger if exists tasks_reject_stale on public.tasks;
create trigger tasks_reject_stale
  before update on public.tasks
  for each row execute function public.reject_stale_client_update();

drop trigger if exists planner_tasks_reject_stale on public.planner_tasks;
create trigger planner_tasks_reject_stale
  before update on public.planner_tasks
  for each row execute function public.reject_stale_client_update();

drop trigger if exists inbox_items_reject_stale on public.inbox_items;
create trigger inbox_items_reject_stale
  before update on public.inbox_items
  for each row execute function public.reject_stale_client_update();
