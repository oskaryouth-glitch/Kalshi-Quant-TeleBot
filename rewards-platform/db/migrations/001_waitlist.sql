-- Early-access signups. Collects only what the public privacy policy discloses.
-- Apply with: npm run db:migrate   (requires DATABASE_URL)

create table if not exists waitlist_signups (
  id                     bigint generated always as identity primary key,
  email                  text        not null check (char_length(email) between 3 and 254),
  email_normalized       text        not null unique,
  platform               text        not null check (platform in ('android', 'iphone', 'other')),
  note                   text                 check (note is null or char_length(note) <= 500),
  source                 text                 check (source is null or source ~ '^[a-z0-9_-]{1,64}$'),
  privacy_policy_version text        not null,
  age_confirmed          boolean     not null check (age_confirmed),
  created_at             timestamptz not null default now()
);

comment on table waitlist_signups is
  'Pre-launch early-access list. Delete rows on request; see /privacy.';
