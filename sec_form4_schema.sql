create table if not exists public.v2_sec_form4_purchases (
    transaction_id text primary key,
    ticker text not null,
    cik text not null,
    accession_number text not null,
    filing_timestamp_utc timestamptz not null,
    available_at_utc timestamptz not null,
    availability_precision text not null,
    transaction_date date not null,
    insider_name text,
    officer_title text,
    is_director boolean not null default false,
    is_officer boolean not null default false,
    is_ten_percent_owner boolean not null default false,
    transaction_code text not null check (transaction_code = 'P'),
    shares numeric not null check (shares > 0),
    price numeric not null check (price > 0),
    total_value numeric generated always as (shares * price) stored,
    ownership_type text,
    shares_owned_after numeric,
    is_amendment boolean not null default false,
    supersedes_accession text,
    source_url text not null,
    source text not null default 'SEC_QUARTERLY_345',
    quality_flags text[] not null default '{}',
    is_training_eligible boolean not null default true,
    imported_at_utc timestamptz not null default now(),
    unique (accession_number, transaction_id)
);

create index if not exists v2_sec_form4_purchases_ticker_available_idx
    on public.v2_sec_form4_purchases (ticker, available_at_utc desc);

create index if not exists v2_sec_form4_purchases_value_idx
    on public.v2_sec_form4_purchases (total_value desc);

alter table public.v2_sec_form4_purchases
    add column if not exists quality_flags text[] not null default '{}';

alter table public.v2_sec_form4_purchases
    add column if not exists is_training_eligible boolean not null default true;

create index if not exists v2_sec_form4_training_eligible_idx
    on public.v2_sec_form4_purchases (is_training_eligible, available_at_utc desc);
