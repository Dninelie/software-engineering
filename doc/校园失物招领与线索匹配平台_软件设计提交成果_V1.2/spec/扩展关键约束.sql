-- SD V1.1 PostgreSQL design DDL. Run after 核心约束.sql in an empty test schema.
-- No production migration, actual decoding, auth or key-management claim.
SET search_path TO lost_found_design;

-- D01/D02: identity mapping and revocable sessions.
ALTER TABLE app_user ADD COLUMN identity_ref text;
ALTER TABLE app_user ADD COLUMN nickname varchar(40) NOT NULL DEFAULT '匿名用户';
ALTER TABLE app_user ADD COLUMN role varchar(16) NOT NULL DEFAULT 'USER'
  CHECK (role IN ('USER','ADMIN','RESPONSIBLE'));
ALTER TABLE app_user ADD COLUMN created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE UNIQUE INDEX uq_identity_ref ON app_user(campus_id,identity_ref) WHERE identity_ref IS NOT NULL;
CREATE TABLE auth_session (
  id uuid PRIMARY KEY, token_hash bytea NOT NULL UNIQUE,
  user_id uuid NOT NULL REFERENCES app_user(id), auth_epoch bigint NOT NULL CHECK(auth_epoch>=1),
  created_at timestamptz NOT NULL, last_seen_at timestamptz NOT NULL,
  revoked_at timestamptz, CHECK(last_seen_at>=created_at)
);

-- D03-D06: content lifespan / private handover fields.
ALTER TABLE item_record ADD COLUMN content_purge_at timestamptz;
ALTER TABLE item_record ADD COLUMN purged_at timestamptz;
ALTER TABLE item_record ADD CONSTRAINT ck_record_purge
  CHECK(content_purge_at IS NULL OR terminal_at IS NULL OR content_purge_at<=terminal_at+interval '2160 hours');
ALTER TABLE claim ADD COLUMN created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE claim ADD COLUMN purge_at timestamptz;
CREATE TABLE claim_content (
  claim_id uuid PRIMARY KEY REFERENCES claim(id),
  evidence varchar(500) NOT NULL CHECK(char_length(evidence) BETWEEN 10 AND 500),
  reject_reason varchar(200) CHECK(reject_reason IS NULL OR char_length(reject_reason) BETWEEN 1 AND 200),
  contact_lost varchar(100) NOT NULL DEFAULT '', contact_found varchar(100) NOT NULL DEFAULT '',
  place_code varchar(40), place_name_snapshot varchar(100), place_version varchar(32),
  confirmed_lost boolean NOT NULL DEFAULT false, confirmed_found boolean NOT NULL DEFAULT false,
  CHECK(place_code IS NOT NULL OR (NOT confirmed_lost AND NOT confirmed_found))
);

-- D08/D09: one authoritative binding across all three content scopes.
CREATE TABLE media_object (
  id uuid PRIMARY KEY, owner_id uuid REFERENCES app_user(id),
  scope varchar(24) NOT NULL CHECK(scope IN ('RECORD_PUBLIC','CLAIM_EVIDENCE','CASE_EVIDENCE')),
  storage_key text NOT NULL UNIQUE, mime varchar(8) NOT NULL CHECK(mime IN ('JPEG','PNG')),
  bytes integer NOT NULL CHECK(bytes BETWEEN 1 AND 2097152),
  width integer NOT NULL CHECK(width BETWEEN 1 AND 4096),
  height integer NOT NULL CHECK(height BETWEEN 1 AND 4096),
  state varchar(12) NOT NULL CHECK(state IN ('TEMP','ATTACHED','DELETING')),
  created_at timestamptz NOT NULL, purge_at timestamptz
);

-- D11/D12.
CREATE TABLE governance_case (
  id uuid PRIMARY KEY, record_id uuid REFERENCES item_record(id), claim_id uuid REFERENCES claim(id),
  kind varchar(8) NOT NULL CHECK(kind IN ('REPORT','APPEAL')),
  status varchar(24) NOT NULL CHECK(status IN ('QUEUED','WAITING_REVIEWER','IN_REVIEW','CLOSED_RESOLVED','CLOSED_UNRESOLVED')),
  reviewer_id uuid REFERENCES app_user(id), created_at timestamptz NOT NULL,
  waiting_started_at timestamptz, reviewer_deadline_at timestamptz,
  evidence_deadline_at timestamptz, closed_at timestamptz, reason_code varchar(40),
  version integer NOT NULL DEFAULT 1 CHECK(version>=1),
  CHECK((kind='REPORT' AND record_id IS NOT NULL AND claim_id IS NULL)
    OR (kind='APPEAL' AND claim_id IS NOT NULL AND record_id IS NULL)),
  CHECK((waiting_started_at IS NULL)=(reviewer_deadline_at IS NULL)),
  CHECK(status<>'WAITING_REVIEWER' OR waiting_started_at IS NOT NULL),
  CHECK(reviewer_deadline_at IS NULL OR reviewer_deadline_at<=LEAST(
    waiting_started_at+interval '168 hours',created_at+interval '4320 hours',
    coalesce(evidence_deadline_at,'infinity'::timestamptz))),
  CHECK((status IN ('CLOSED_RESOLVED','CLOSED_UNRESOLVED'))=(closed_at IS NOT NULL))
);
CREATE FUNCTION enforce_case_deadline() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='UPDATE' THEN
    IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
      RAISE EXCEPTION 'case created_at immutable' USING ERRCODE='23514';
    END IF;
    IF OLD.waiting_started_at IS NOT NULL AND NEW.waiting_started_at IS DISTINCT FROM OLD.waiting_started_at THEN
      RAISE EXCEPTION 'waiting start cannot reset' USING ERRCODE='23514';
    END IF;
    IF OLD.reviewer_deadline_at IS NOT NULL AND (NEW.reviewer_deadline_at IS NULL OR NEW.reviewer_deadline_at>OLD.reviewer_deadline_at) THEN
      RAISE EXCEPTION 'reviewer deadline cannot extend' USING ERRCODE='23514';
    END IF;
  END IF;
  -- First assignment of waiting fields must choose the exact minimum.
  IF NEW.waiting_started_at IS NOT NULL AND (TG_OP='INSERT' OR OLD.waiting_started_at IS NULL) THEN
    IF NEW.reviewer_deadline_at IS DISTINCT FROM LEAST(NEW.waiting_started_at+interval '168 hours',
       NEW.created_at+interval '4320 hours',coalesce(NEW.evidence_deadline_at,'infinity'::timestamptz)) THEN
      RAISE EXCEPTION 'initial reviewer deadline must be minimum' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER ct_case_deadline BEFORE INSERT OR UPDATE ON governance_case
  FOR EACH ROW EXECUTE FUNCTION enforce_case_deadline();
CREATE UNIQUE INDEX uq_open_report ON governance_case(record_id)
  WHERE kind='REPORT' AND status IN ('QUEUED','WAITING_REVIEWER','IN_REVIEW');
CREATE TABLE case_receipt (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES governance_case(id),
  submitter_id uuid NOT NULL REFERENCES app_user(id), created_at timestamptz NOT NULL
);
CREATE TABLE case_content (
  receipt_id uuid PRIMARY KEY REFERENCES case_receipt(id),
  reason_enum varchar(16) CHECK(reason_enum IS NULL OR reason_enum IN ('LEAK','FALSE','HARASSMENT','FRAUD')),
  description varchar(500) NOT NULL CHECK(char_length(description) BETWEEN 1 AND 500),
  purge_at timestamptz NOT NULL
);
CREATE TABLE media_binding (
  media_id uuid PRIMARY KEY REFERENCES media_object(id),
  scope varchar(24) NOT NULL,
  record_content_id uuid REFERENCES record_content(record_id),
  claim_content_id uuid REFERENCES claim_content(claim_id),
  case_content_id uuid REFERENCES case_content(receipt_id),
  ordinal integer NOT NULL, source_evidence_purge_at timestamptz,
  CHECK(num_nonnulls(record_content_id,claim_content_id,case_content_id)=1),
  CHECK((scope='RECORD_PUBLIC' AND record_content_id IS NOT NULL AND ordinal BETWEEN 1 AND 3)
    OR (scope='CLAIM_EVIDENCE' AND claim_content_id IS NOT NULL AND ordinal BETWEEN 1 AND 2)
    OR (scope='CASE_EVIDENCE' AND case_content_id IS NOT NULL AND ordinal BETWEEN 1 AND 2))
);
CREATE UNIQUE INDEX uq_record_media_ordinal ON media_binding(record_content_id,ordinal) WHERE record_content_id IS NOT NULL;
CREATE UNIQUE INDEX uq_claim_media_ordinal ON media_binding(claim_content_id,ordinal) WHERE claim_content_id IS NOT NULL;
CREATE UNIQUE INDEX uq_case_media_ordinal ON media_binding(case_content_id,ordinal) WHERE case_content_id IS NOT NULL;
CREATE FUNCTION enforce_media_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE media_scope text;
BEGIN
  SELECT scope INTO media_scope FROM media_object WHERE id=NEW.media_id FOR UPDATE;
  IF media_scope IS DISTINCT FROM NEW.scope THEN
    RAISE EXCEPTION 'media scope mismatch' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER ct_media_binding BEFORE INSERT OR UPDATE ON media_binding
  FOR EACH ROW EXECUTE FUNCTION enforce_media_binding();
CREATE FUNCTION immutable_bound_media_scope() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.scope IS DISTINCT FROM OLD.scope AND EXISTS(SELECT 1 FROM media_binding WHERE media_id=OLD.id) THEN
    RAISE EXCEPTION 'bound media scope immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER ct_media_scope_immutable BEFORE UPDATE ON media_object
  FOR EACH ROW EXECUTE FUNCTION immutable_bound_media_scope();
CREATE VIEW record_media AS SELECT record_content_id content_id,media_id,ordinal FROM media_binding WHERE scope='RECORD_PUBLIC';
CREATE VIEW claim_media AS SELECT claim_content_id content_id,media_id,ordinal FROM media_binding WHERE scope='CLAIM_EVIDENCE';
CREATE VIEW case_media AS SELECT case_content_id content_id,media_id,ordinal,source_evidence_purge_at FROM media_binding WHERE scope='CASE_EVIDENCE';

-- D10: scores below threshold exist only in computation / evaluation examples.
CREATE TABLE match_run (
  id uuid PRIMARY KEY, lost_id uuid NOT NULL REFERENCES item_record(id), lost_version integer NOT NULL CHECK(lost_version>=1),
  rule_version varchar(32) NOT NULL, rule_epoch bigint NOT NULL CHECK(rule_epoch>=1),
  status varchar(16) NOT NULL CHECK(status IN ('UPDATING','READY','FAILED','STALE')),
  updated_at timestamptz NOT NULL
);
CREATE TABLE match_result (
  run_id uuid NOT NULL REFERENCES match_run(id), found_id uuid NOT NULL REFERENCES item_record(id),
  found_version integer NOT NULL CHECK(found_version>=1),
  c integer NOT NULL CHECK(c IN (0,35)), k integer NOT NULL CHECK(k IN (0,15)),
  l integer NOT NULL CHECK(l IN (0,25)), t integer NOT NULL CHECK(t IN (0,10,25)),
  score integer NOT NULL CHECK(score BETWEEN 40 AND 100), rank integer NOT NULL CHECK(rank BETWEEN 1 AND 10),
  PRIMARY KEY(run_id,found_id), UNIQUE(run_id,rank), CHECK(score=c+k+l+t)
);

-- D13/D14 minimal payload and planned attempts. Recovery/redrive executions
-- are recorded separately to avoid reusing a MISSED planned slot.
CREATE TABLE outbox_event (
  id uuid PRIMARY KEY, type varchar(32) NOT NULL, aggregate_id uuid, aggregate_version integer NOT NULL CHECK(aggregate_version>=1),
  occurred_at timestamptz NOT NULL, recipient_ids uuid[], payload_min jsonb NOT NULL DEFAULT '{}'::jsonb,
  published boolean NOT NULL DEFAULT false, purge_at timestamptz NOT NULL,
  CHECK(jsonb_typeof(payload_min)='object'),
  CHECK((payload_min-ARRAY['deadlineAt','reasonCode','ruleEpoch','lostVersion','foundVersion']::text[])='{}'::jsonb)
);
CREATE TABLE job (
  id uuid PRIMARY KEY, event_id uuid NOT NULL REFERENCES outbox_event(id), handler varchar(40) NOT NULL,
  status varchar(16) NOT NULL CHECK(status IN ('READY','RUNNING','RETRY_WAIT','SUCCEEDED','FAILED','STALE')),
  first_failed_at timestamptz, next_due_at timestamptz,
  retry_slot integer NOT NULL DEFAULT 0 CHECK(retry_slot BETWEEN 0 AND 3),
  lease_until timestamptz, fence bigint NOT NULL DEFAULT 1 CHECK(fence>=1),
  redrive_count integer NOT NULL DEFAULT 0 CHECK(redrive_count BETWEEN 0 AND 1),
  UNIQUE(event_id,handler)
);
CREATE TABLE job_attempt (
  job_id uuid NOT NULL REFERENCES job(id), slot integer NOT NULL CHECK(slot BETWEEN 0 AND 3),
  planned_at timestamptz NOT NULL, started_at timestamptz, ended_at timestamptz,
  result varchar(16) NOT NULL CHECK(result IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','MISSED')),
  request_id uuid NOT NULL, missed_reason varchar(40), PRIMARY KEY(job_id,slot),
  CHECK(ended_at IS NULL OR started_at IS NULL OR ended_at>=started_at),
  CHECK(result<>'MISSED' OR missed_reason IS NOT NULL)
);
CREATE TABLE job_recovery_execution (
  id uuid PRIMARY KEY, job_id uuid NOT NULL REFERENCES job(id),
  recovery_id uuid NOT NULL, kind varchar(12) NOT NULL CHECK(kind IN ('CATCH_UP','REDRIVE')),
  started_at timestamptz NOT NULL, ended_at timestamptz, request_id uuid NOT NULL, reason_code varchar(40) NOT NULL,
  UNIQUE(job_id,recovery_id,kind), CHECK(ended_at IS NULL OR ended_at>=started_at)
);
CREATE UNIQUE INDEX uq_one_redrive ON job_recovery_execution(job_id) WHERE kind='REDRIVE';
CREATE INDEX ix_job_due ON job(status,next_due_at);
CREATE INDEX ix_outbox_due ON outbox_event(published,occurred_at);

-- D15/D16; notification exact templates remain server-generated NT-1 guards.
ALTER TABLE notification ADD COLUMN object_type varchar(8) CHECK(object_type IS NULL OR object_type IN ('RECORD','CLAIM','CASE'));
ALTER TABLE notification ADD COLUMN object_id uuid;
ALTER TABLE notification ADD COLUMN occurred_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE notification ADD COLUMN read boolean NOT NULL DEFAULT false;
ALTER TABLE notification ADD COLUMN read_at timestamptz;
ALTER TABLE notification ADD COLUMN purge_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE notification ADD CONSTRAINT ck_notification_read CHECK(read=(read_at IS NOT NULL));
ALTER TABLE notification ADD CONSTRAINT ck_notification_purge CHECK(purge_at<=created_at+interval '2160 hours');

-- D17 exact rolling quotas require the locked user row, not daily counters.
CREATE TABLE quota_event (
  id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES app_user(id),
  kind varchar(8) NOT NULL CHECK(kind IN ('PUBLISH','CLAIM')),
  found_id uuid REFERENCES item_record(id), occurred_at timestamptz NOT NULL,
  CHECK((kind='CLAIM')=(found_id IS NOT NULL))
);
CREATE INDEX ix_quota_user ON quota_event(user_id,kind,occurred_at);
CREATE INDEX ix_quota_found ON quota_event(user_id,found_id,occurred_at);

-- D18 no evidence/contact body columns. Map deletion is a purge obligation.
CREATE TABLE audit_event (
  id uuid PRIMARY KEY, random_actor_ref uuid NOT NULL, random_object_ref uuid NOT NULL,
  action varchar(40) NOT NULL, before_state varchar(24), after_state varchar(24),
  occurred_at timestamptz NOT NULL, reason_code varchar(40), request_id uuid NOT NULL,
  purge_at timestamptz NOT NULL CHECK(purge_at<=occurred_at+interval '4320 hours')
);
CREATE TABLE audit_map (random_ref uuid PRIMARY KEY, actual_id uuid NOT NULL);
CREATE TABLE audit_access_reason (
  event_id uuid PRIMARY KEY REFERENCES audit_event(id),
  reason varchar(200) NOT NULL CHECK(char_length(reason) BETWEEN 1 AND 200),
  purge_at timestamptz NOT NULL
);

-- D19 reference representation on separate deletion-manifest medium.
-- This table schema is illustrative for that medium, not permission to place
-- the sole authoritative manifest in the database being restored.
CREATE TABLE deletion_manifest (
  deletion_id uuid PRIMARY KEY, target_type varchar(32) NOT NULL, target_id uuid NOT NULL,
  storage_keys text[] NOT NULL DEFAULT ARRAY[]::text[], deleted_at timestamptz NOT NULL,
  retain_until timestamptz NOT NULL CHECK(retain_until=deleted_at+interval '744 hours'),
  phase varchar(8) NOT NULL CHECK(phase IN ('INTENT','APPLIED'))
);

CREATE TABLE favorite (
  user_id uuid NOT NULL REFERENCES app_user(id), record_id uuid NOT NULL REFERENCES item_record(id),
  created_at timestamptz NOT NULL, PRIMARY KEY(user_id,record_id)
);
CREATE TABLE location_dict (
  code varchar(16) PRIMARY KEY, campus_id varchar(16) NOT NULL,
  label varchar(100) NOT NULL CHECK(char_length(label) BETWEEN 1 AND 100)
);
ALTER TABLE record_content ADD CONSTRAINT fk_record_location FOREIGN KEY(location_code) REFERENCES location_dict(code);
CREATE TABLE public_place (
  code varchar(40) PRIMARY KEY CHECK(code NOT IN ('OTHER','UNKNOWN')),
  campus_id varchar(16) NOT NULL, display_name varchar(100) NOT NULL CHECK(char_length(display_name) BETWEEN 1 AND 100),
  enabled boolean NOT NULL DEFAULT true, opening_hours jsonb NOT NULL CHECK(jsonb_typeof(opening_hours)='array'),
  version varchar(32) NOT NULL
);
ALTER TABLE claim_content ADD CONSTRAINT fk_handover_place FOREIGN KEY(place_code) REFERENCES public_place(code);

CREATE TABLE rule_config (
  version varchar(32) PRIMARY KEY, epoch bigint NOT NULL UNIQUE CHECK(epoch>=1),
  parameters jsonb NOT NULL CHECK(jsonb_typeof(parameters)='object'),
  state varchar(8) NOT NULL CHECK(state IN ('ACTIVE','INACTIVE')), activated_at timestamptz
);
CREATE UNIQUE INDEX uq_single_active_rule ON rule_config(state) WHERE state='ACTIVE';
CREATE FUNCTION immutable_rule_parameters() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.version IS DISTINCT FROM OLD.version OR NEW.parameters IS DISTINCT FROM OLD.parameters THEN
    RAISE EXCEPTION 'rule version and parameters immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER ct_rule_immutable BEFORE UPDATE ON rule_config
  FOR EACH ROW EXECUTE FUNCTION immutable_rule_parameters();
CREATE TABLE quality_evaluation (
  id uuid PRIMARY KEY, rule_version varchar(32) NOT NULL REFERENCES rule_config(version),
  sample_count integer NOT NULL CHECK(sample_count>=0),
  hits integer NOT NULL CHECK(hits BETWEEN 0 AND sample_count),
  empty_count integer NOT NULL CHECK(empty_count BETWEEN 0 AND sample_count),
  search_hits integer NOT NULL CHECK(search_hits BETWEEN 0 AND sample_count),
  trial_passed boolean NOT NULL, mode varchar(16) NOT NULL CHECK(mode IN ('NORMAL','SEARCH_FIRST')),
  reason varchar(200) NOT NULL CHECK(char_length(reason) BETWEEN 1 AND 200),
  approved_by uuid REFERENCES app_user(id), created_at timestamptz NOT NULL,
  CHECK(mode<>'NORMAL' OR (sample_count=100 AND hits>=80 AND empty_count<=10 AND search_hits=100 AND trial_passed AND approved_by IS NOT NULL))
);
CREATE TABLE statistics_month (
  campus_id varchar(16) NOT NULL, month varchar(7) NOT NULL CHECK(month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
  found_published_count integer NOT NULL CHECK(found_published_count>=0),
  found_returned_count integer NOT NULL CHECK(found_returned_count>=0),
  PRIMARY KEY(campus_id,month)
);
-- Counts across different months need NOT satisfy returned<=published.
-- Identity revocation, current time guards, real sample provenance, no private
-- DTO fields, confirmed contact visibility and attached owner checks belong to
-- application services and are enumerated in 约束表达式清单.md.
