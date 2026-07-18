create table if not exists public.v2_short_interest_snapshots (
    snapshot_id text primary key,
    ticker text not null,
    settlement_date date not null,
    publication_timestamp_utc timestamptz not null,
    available_at_utc timestamptz not null,
    short_interest_shares numeric not null check (short_interest_shares >= 0),
    float_shares numeric check (float_shares > 0),
    shares_outstanding numeric check (shares_outstanding > 0),
    average_daily_volume numeric check (average_daily_volume > 0),
    days_to_cover numeric check (days_to_cover >= 0),
    source text not null,
    source_url text,
    quality_flags text[] not null default '{}',
    is_training_eligible boolean not null default true,
    raw_payload jsonb not null default '{}'::jsonb,
    imported_at_utc timestamptz not null default now(),
    unique (ticker, settlement_date, source)
);

create index if not exists v2_short_interest_ticker_available_idx
    on public.v2_short_interest_snapshots (ticker, available_at_utc desc);

create index if not exists v2_short_interest_training_idx
    on public.v2_short_interest_snapshots (is_training_eligible, available_at_utc desc);

create table if not exists public.v2_daily_short_sale_volume (
    record_id text primary key,
    ticker text not null,
    trade_date date not null,
    available_at_utc timestamptz not null,
    short_volume numeric not null check (short_volume >= 0),
    short_exempt_volume numeric not null default 0 check (short_exempt_volume >= 0),
    reported_total_volume numeric not null check (reported_total_volume >= 0),
    venue text not null,
    source text not null default 'FINRA_DAILY_SHORT_SALE_VOLUME',
    source_url text,
    is_training_eligible boolean not null default true,
    imported_at_utc timestamptz not null default now(),
    unique (ticker, trade_date, venue)
);

create index if not exists v2_daily_short_volume_ticker_date_idx
    on public.v2_daily_short_sale_volume (ticker, trade_date desc);
