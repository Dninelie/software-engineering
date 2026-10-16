-- Future EXPLAIN/affected-row exercise; no results are claimed in the package.
-- Run after 安装设计schema.psql in its isolated DB. All data here roll back.
-- Head-table-only fixture: not an N-01 complete-content load test.
\set ON_ERROR_STOP on
\set VERBOSITY verbose
\timing on
BEGIN;
SET search_path TO lost_found_design;
INSERT INTO app_user(id,campus_id,status) VALUES
 ('a1000000-0000-4000-8000-000000000001','C01','ACTIVE'),
 ('a1000000-0000-4000-8000-000000000002','C01','ACTIVE');
INSERT INTO item_record(id,owner_id,campus_id,type,status,published_at,expires_at,terminal_at)
SELECT md5('lf-head-'||g::text)::uuid,
 CASE WHEN g%2=1 THEN 'a1000000-0000-4000-8000-000000000001'::uuid ELSE 'a1000000-0000-4000-8000-000000000002'::uuid END,
 'C01',CASE WHEN g%2=1 THEN 'LOST' ELSE 'FOUND' END,
 CASE WHEN g<=10000 THEN 'OPEN' ELSE 'RETURNED' END,
 '2026-10-14T12:00:00+08:00'::timestamptz,
 '2026-11-13T12:00:00+08:00'::timestamptz,
 CASE WHEN g<=10000 THEN NULL ELSE '2026-10-14T12:30:00+08:00'::timestamptz END
FROM generate_series(1,60000) g;
INSERT INTO claim(id,found_id,lost_id,applicant_id,status)
VALUES(md5('lf-claim-1')::uuid,md5('lf-head-2')::uuid,md5('lf-head-1')::uuid,'a1000000-0000-4000-8000-000000000001','PENDING');
SET CONSTRAINTS ALL IMMEDIATE;
ANALYZE item_record;
ANALYZE claim;
ANALYZE active_reservation;
SELECT status,count(*) AS fixture_rows FROM item_record GROUP BY status ORDER BY status;
SELECT count(*) AS affected_records FROM item_record
WHERE id=ANY(ARRAY[md5('lf-head-1')::uuid,md5('lf-head-2')::uuid]);
SELECT count(*) AS affected_claims FROM claim WHERE id=ANY(ARRAY[md5('lf-claim-1')::uuid]);
EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON)
SELECT id,status FROM item_record
WHERE id=ANY(ARRAY[md5('lf-head-1')::uuid,md5('lf-head-2')::uuid]);
EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON)
SELECT c.id,c.status,f.status AS found_status,l.status AS lost_status
FROM claim c JOIN item_record f ON f.id=c.found_id JOIN item_record l ON l.id=c.lost_id
WHERE c.id=ANY(ARRAY[md5('lf-claim-1')::uuid]);
EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON)
SELECT claim_id,side FROM active_reservation WHERE claim_id=ANY(ARRAY[md5('lf-claim-1')::uuid]);
SELECT check_pair_ids(ARRAY[md5('lf-claim-1')::uuid],ARRAY[md5('lf-head-1')::uuid,md5('lf-head-2')::uuid]);
-- Timing of one call is not P95. Repeat a parameterized two-ID fixture call
-- at least 1000 times with client-measured full-transaction latency, reporting
-- p50/p95/max and observed plan rows; concurrency is a separate DV02 exercise.
ROLLBACK;
