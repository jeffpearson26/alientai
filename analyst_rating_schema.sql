create table if not exists public.v2_analyst_rating_events (
    event_id text primary key,
    ticker text not null,
    announcement_timestamp_utc timestamptz not null,
    analyst_firm text,
    analyst_name text,
    action text,
    normalized_action text not null,
    old_rating text,
    new_rating text,
    old_rating_score numeric,
    new_rating_score numeric,
    normalized_score_change numeric,
    normalization_version text not null,
    old_price_target numeric,
    new_price_target numeric,
    currency text,
    provider text not null,
    source_id text,
    source text not null,
    updated_at_utc timestamptz not null,
    raw_payload jsonb not null default '{}'::jsonb,
    imported_at_utc timestamptz not null default now()
);

create index if not exists v2_analyst_rating_ticker_time_idx
    on public.v2_analyst_rating_events (ticker, announcement_timestamp_utc desc);

create index if not exists v2_analyst_rating_action_idx
    on public.v2_analyst_rating_events (normalized_action, announcement_timestamp_utc desc);
