-- X05 technical admission ledger. Temporary metadata, not a new business module.
-- Load after 核心约束.sql in an isolated test schema; no execution claim.
SET search_path TO lost_found_design;
CREATE TABLE admission_bucket (
  bucket_hash bytea PRIMARY KEY, rate_profile_id varchar(4) NOT NULL
    CHECK(rate_profile_id IN ('RF01','RF02','RF03','RF04','RF05','RF06','RF07')),
  last_used_at timestamptz NOT NULL
);
CREATE TABLE rate_attempt (
  request_id uuid PRIMARY KEY, bucket_hash bytea NOT NULL REFERENCES admission_bucket(bucket_hash),
  occurred_at timestamptz NOT NULL
);
CREATE INDEX ix_rate_window ON rate_attempt(bucket_hash,occurred_at);
CREATE TABLE admission_slot (
  bucket_hash bytea NOT NULL, slot_index integer NOT NULL CHECK(slot_index BETWEEN 1 AND 4),
  request_id uuid NOT NULL UNIQUE, admitted_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
  PRIMARY KEY(bucket_hash,slot_index), CHECK(expires_at=admitted_at+interval '45 seconds')
);
-- The rate bucket hash derives from the declared RF scope with a rotating
-- HMAC secret; the C hash derives from session/method/path-template, or from
-- trusted-source-IP/API00 for anonymous Demo login. No raw tokens/IPs here.
-- Admission service uses one short transaction: lock admission_bucket, delete
-- attempts outside (now-60s,now], count against RF max, record admitted attempt;
-- then atomically take a free permitted C slot (1..configured C only).
-- C rejection does not undo the F attempt already counted. Do not hold this
-- short transaction while uploading/reading private data or doing business SQL.
-- Slots released on success/timeout; 45s lease covers body30s + T<=10s + grace5s.
-- Remove rate_attempt data no later than 120s, slots on release/expiry, inactive
-- buckets no later than 120s. Current authentication still precedes admission.
