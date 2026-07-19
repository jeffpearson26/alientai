create table if not exists public.v2_earnings_events (
    event_id text primary key,
    ticker text not null,
    fiscal_date_ending date not null,
    reported_date date not null,
    report_time text,
    available_at_utc timestamptz not null,
    reported_eps numeric,
    estimated_eps numeric,
    surprise numeric,
    surprise_percentage numeric,
    source text not null default 'ALPHA_VANTAGE_EARNINGS',
    source_url text not null,
    quality_flags text[] not null default '{}',
    is_training_eligible boolean not null default true,
    imported_at_utc timestamptz not null default now()
);

create index if not exists v2_earnings_ticker_available_idx
    on public.v2_earnings_events (ticker, available_at_utc desc);

create index if not exists v2_earnings_training_eligible_idx
    on public.v2_earnings_events (is_training_eligible, available_at_utc desc);
