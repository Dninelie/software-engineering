-- PostgreSQL core reference DDL, design artifact, not a full production migration.
-- All objects live in a dedicated schema. No DROP statements.
-- Complete content/auxiliary field specification is in document section 4.2.
CREATE SCHEMA IF NOT EXISTS lost_found_design;
SET search_path TO lost_found_design;

CREATE TABLE app_user (
  id uuid PRIMARY KEY,
  campus_id varchar(16) NOT NULL,
  status varchar(16) NOT NULL CHECK (status IN ('ACTIVE','DISABLED','PURGING')),
  auth_epoch bigint NOT NULL DEFAULT 1 CHECK (auth_epoch >= 1)
);

CREATE TABLE item_record (
  id uuid PRIMARY KEY,
  owner_id uuid REFERENCES app_user(id),
  campus_id varchar(16) NOT NULL,
  type varchar(8) NOT NULL CHECK (type IN ('LOST','FOUND')),
  status varchar(16) NOT NULL CHECK (status IN ('OPEN','RESERVED','RETURNED','WITHDRAWN','EXPIRED')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  hidden boolean NOT NULL DEFAULT false,
  frozen boolean NOT NULL DEFAULT false,
  published_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  terminal_at timestamptz,
  CHECK (expires_at = published_at + interval '720 hours'),
  CHECK ((status IN ('RETURNED','WITHDRAWN','EXPIRED')) = (terminal_at IS NOT NULL))
);

CREATE TABLE record_content (
  record_id uuid PRIMARY KEY REFERENCES item_record(id),
  category varchar(16) NOT NULL CHECK (category IN ('CARD','KEY','ELECTRONIC','BOOK','CLOTHING','OTHER')),
  title varchar(40) NOT NULL CHECK (char_length(title) BETWEEN 1 AND 40),
  description varchar(500) NOT NULL DEFAULT '',
  color varchar(8) NOT NULL CHECK (color IN ('BLACK','WHITE','RED','BLUE','GREEN','YELLOW','MULTI','UNKNOWN')),
  location_code varchar(16) NOT NULL,
  event_start timestamptz,
  event_end timestamptz,
  verification_hint varchar(200),
  CHECK ((event_start IS NULL) = (event_end IS NULL)),
  CHECK (event_start IS NULL OR (event_start <= event_end AND event_end - event_start <= interval '720 hours')),
  CHECK (verification_hint IS NULL OR char_length(verification_hint) BETWEEN 10 AND 200)
  -- Submission-time event_end <= Clock and FOUND required hint are service guards.
);

CREATE TABLE claim (
  id uuid PRIMARY KEY,
  found_id uuid NOT NULL REFERENCES item_record(id),
  lost_id uuid NOT NULL REFERENCES item_record(id),
  applicant_id uuid REFERENCES app_user(id),
  status varchar(16) NOT NULL CHECK (status IN ('PENDING','SELECTED','REJECTED','INVALIDATED','CANCELLED','TIMED_OUT','COMPLETED')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  selected_at timestamptz,
  deadline_at timestamptz,
  ended_at timestamptz,
  CHECK (found_id <> lost_id),
  CHECK ((selected_at IS NULL) = (deadline_at IS NULL)),
  CHECK (deadline_at IS NULL OR deadline_at = selected_at + interval '48 hours'),
  CHECK ((status IN ('REJECTED','INVALIDATED','CANCELLED','TIMED_OUT','COMPLETED')) = (ended_at IS NOT NULL)),
  CHECK (status <> 'SELECTED' OR deadline_at IS NOT NULL)
);

CREATE UNIQUE INDEX uq_active_claim_pair ON claim(found_id,lost_id)
  WHERE status IN ('PENDING','SELECTED');

CREATE TABLE active_reservation (
  record_id uuid PRIMARY KEY REFERENCES item_record(id),
  claim_id uuid NOT NULL REFERENCES claim(id),
  side varchar(8) NOT NULL CHECK (side IN ('LOST','FOUND')),
  UNIQUE(claim_id,side)
);

-- Local deferred verification. Inputs come from OLD/NEW affected IDs.
CREATE FUNCTION check_pair_ids(p_claims uuid[], p_records uuid[]) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM claim c
    JOIN item_record f ON f.id=c.found_id
    JOIN item_record l ON l.id=c.lost_id
    WHERE c.id = ANY(p_claims) AND (f.type <> 'FOUND' OR l.type <> 'LOST'
       OR f.campus_id <> l.campus_id
       OR f.owner_id = l.owner_id
       OR (c.applicant_id IS NOT NULL AND c.applicant_id IS DISTINCT FROM l.owner_id))
  ) THEN RAISE EXCEPTION 'claim pair identity/type mismatch' USING ERRCODE='23514'; END IF;
  IF EXISTS (
    SELECT 1 FROM claim c
    JOIN item_record f ON f.id=c.found_id JOIN item_record l ON l.id=c.lost_id
    WHERE c.id=ANY(p_claims) AND c.status='COMPLETED'
      AND (f.status<>'RETURNED' OR l.status<>'RETURNED')
  ) THEN RAISE EXCEPTION 'COMPLETED must return both records' USING ERRCODE='23514'; END IF;
  IF EXISTS (
    SELECT 1 FROM claim c
    WHERE c.id=ANY(p_claims) AND c.status='SELECTED' AND (
      (SELECT count(*) FROM active_reservation a WHERE a.claim_id=c.id) <> 2
      OR NOT EXISTS (SELECT 1 FROM active_reservation a JOIN item_record r ON r.id=a.record_id
          WHERE a.claim_id=c.id AND a.record_id=c.found_id AND a.side='FOUND' AND r.status='RESERVED')
      OR NOT EXISTS (SELECT 1 FROM active_reservation a JOIN item_record r ON r.id=a.record_id
          WHERE a.claim_id=c.id AND a.record_id=c.lost_id AND a.side='LOST' AND r.status='RESERVED')
    )
  ) THEN RAISE EXCEPTION 'SELECTED must reserve both records' USING ERRCODE='23514'; END IF;
  IF EXISTS (
    SELECT 1 FROM active_reservation a JOIN claim c ON c.id=a.claim_id
    WHERE (a.claim_id=ANY(p_claims) OR a.record_id=ANY(p_records)) AND (c.status <> 'SELECTED'
      OR (a.side='FOUND' AND a.record_id<>c.found_id)
      OR (a.side='LOST' AND a.record_id<>c.lost_id))
  ) THEN RAISE EXCEPTION 'invalid reservation' USING ERRCODE='23514'; END IF;
  IF EXISTS (
    SELECT 1 FROM item_record r
    WHERE r.id=ANY(p_records) AND ((r.status='RESERVED') <> EXISTS(SELECT 1 FROM active_reservation a WHERE a.record_id=r.id))
  ) THEN RAISE EXCEPTION 'RESERVED occupancy mismatch' USING ERRCODE='23514'; END IF;
  RETURN;
END; $$;

CREATE FUNCTION check_pair_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  cids uuid[] := ARRAY[]::uuid[];
  rids uuid[] := ARRAY[]::uuid[];
  associated uuid[];
  identity_changed boolean := false;
BEGIN
  IF TG_TABLE_NAME='claim' THEN
    IF TG_OP <> 'INSERT' THEN
      cids:=cids || ARRAY[OLD.id]; rids:=rids || ARRAY[OLD.found_id,OLD.lost_id];
    END IF;
    IF TG_OP <> 'DELETE' THEN
      cids:=cids || ARRAY[NEW.id]; rids:=rids || ARRAY[NEW.found_id,NEW.lost_id];
    END IF;
  ELSIF TG_TABLE_NAME='active_reservation' THEN
    IF TG_OP <> 'INSERT' THEN
      cids:=cids || ARRAY[OLD.claim_id]; rids:=rids || ARRAY[OLD.record_id];
    END IF;
    IF TG_OP <> 'DELETE' THEN
      cids:=cids || ARRAY[NEW.claim_id]; rids:=rids || ARRAY[NEW.record_id];
    END IF;
  ELSIF TG_TABLE_NAME='item_record' THEN
    IF TG_OP <> 'INSERT' THEN rids:=rids || ARRAY[OLD.id]; END IF;
    IF TG_OP <> 'DELETE' THEN rids:=rids || ARRAY[NEW.id]; END IF;
    IF TG_OP='UPDATE' THEN
      identity_changed:=NEW.owner_id IS DISTINCT FROM OLD.owner_id
        OR NEW.type IS DISTINCT FROM OLD.type OR NEW.campus_id IS DISTINCT FROM OLD.campus_id;
    END IF;
    -- Status/version updates follow at most the current reservation, not history.
    SELECT coalesce(array_agg(claim_id),ARRAY[]::uuid[]) INTO associated
      FROM active_reservation WHERE record_id=ANY(rids);
    cids:=cids || associated;
    IF identity_changed THEN
      SELECT coalesce(array_agg(id),ARRAY[]::uuid[]) INTO associated FROM claim
        WHERE found_id=ANY(rids) OR lost_id=ANY(rids);
      cids:=cids || associated;
    END IF;
  END IF;
  SELECT coalesce(array_agg(DISTINCT x),ARRAY[]::uuid[]) INTO cids
    FROM unnest(cids) x WHERE x IS NOT NULL;
  -- Include current partner rows, while retaining OLD rows for deletes/relinks.
  SELECT coalesce(array_agg(x),ARRAY[]::uuid[]) INTO associated FROM (
    SELECT found_id x FROM claim WHERE id=ANY(cids)
    UNION SELECT lost_id x FROM claim WHERE id=ANY(cids)
  ) q;
  rids:=rids || associated;
  SELECT coalesce(array_agg(DISTINCT x),ARRAY[]::uuid[]) INTO rids
    FROM unnest(rids) x WHERE x IS NOT NULL;
  PERFORM check_pair_ids(cids,rids);
  RETURN NULL;
END; $$;

CREATE CONSTRAINT TRIGGER ct_claim_pair AFTER INSERT OR UPDATE OR DELETE ON claim
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_pair_integrity();
CREATE CONSTRAINT TRIGGER ct_reservation_pair AFTER INSERT OR UPDATE OR DELETE ON active_reservation
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_pair_integrity();
CREATE CONSTRAINT TRIGGER ct_record_pair AFTER INSERT OR UPDATE OR DELETE ON item_record
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_pair_integrity();

CREATE TABLE idempotency_request (
  user_id uuid NOT NULL REFERENCES app_user(id),
  request_key uuid NOT NULL,
  route text NOT NULL,
  input_hmac bytea NOT NULL,
  result_ref jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY(user_id,request_key),
  CHECK (expires_at=created_at+interval '24 hours')
);

CREATE TABLE notification (
  id uuid PRIMARY KEY,
  event_id uuid NOT NULL,
  recipient_id uuid NOT NULL REFERENCES app_user(id),
  type varchar(24) NOT NULL CHECK (type IN ('MATCH_UPDATED','CLAIM_SUBMITTED','CLAIM_REJECTED','SELECTED','CANCELLED','EXPIRED','TIMED_OUT','RETURNED','ADMIN_PROCESSED','CLAIM_INVALIDATED')),
  created_at timestamptz NOT NULL,
  template_version varchar(8) NOT NULL CHECK (template_version='NT-1'),
  summary text NOT NULL,
  UNIQUE(event_id,recipient_id)
);

CREATE INDEX ix_public_records ON item_record(campus_id,type,status,published_at DESC,id ASC)
  WHERE hidden=false AND frozen=false;
CREATE INDEX ix_record_expiry ON item_record(expires_at) WHERE status='OPEN';
CREATE INDEX ix_claim_found_status ON claim(found_id,status);
CREATE INDEX ix_claim_lost_status ON claim(lost_id,status);

-- Delete order: private content/media refs, reservations, claims, record_content,
-- records, identity maps. Closure and purge must be coordinated by UnitOfWork.
-- Run spec/扩展关键约束.sql next for media, cases, tasks and other constraints.
-- Full production access privileges/migrations and deployment encryption remain
-- implementation work; SQL execution and concurrency tests are not yet claimed.
