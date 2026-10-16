-- FUTURE PostgreSQL integration exercise; no execution result is claimed.
-- Use an isolated empty schema. Load 核心约束.sql then 扩展关键约束.sql.
-- psql -v ON_ERROR_STOP=1 -f <this-file>
-- This fixture transaction ROLLBACKs; does not test 20-request concurrency.
BEGIN;
SET search_path TO lost_found_design;
INSERT INTO app_user(id,campus_id,status) VALUES
 ('10000000-0000-4000-8000-000000000001','C01','ACTIVE'),
 ('10000000-0000-4000-8000-000000000002','C01','ACTIVE');
INSERT INTO item_record(id,owner_id,campus_id,type,status,published_at,expires_at) VALUES
 ('20000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','C01','LOST','OPEN','2026-10-14T12:00:00+08:00','2026-11-13T12:00:00+08:00'),
 ('20000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000002','C01','FOUND','OPEN','2026-10-14T12:00:00+08:00','2026-11-13T12:00:00+08:00');
INSERT INTO claim(id,found_id,lost_id,applicant_id,status) VALUES
 ('30000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002','20000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','PENDING');
SET CONSTRAINTS ALL IMMEDIATE;
INSERT INTO location_dict(code,campus_id,label) VALUES('LIB','C01','测试图书馆区域');
INSERT INTO record_content(record_id,category,title,color,location_code,verification_hint) VALUES
 ('20000000-0000-4000-8000-000000000001','KEY','测试寻物','BLACK','LIB',NULL),
 ('20000000-0000-4000-8000-000000000002','KEY','测试招领','BLACK','LIB','仅用于构造测试的未公开图案');
INSERT INTO claim_content(claim_id,evidence)
VALUES('30000000-0000-4000-8000-000000000001','仅用于构造测试的认领证据文本');

DO $$
BEGIN
  BEGIN
    INSERT INTO media_object(id,owner_id,scope,storage_key,mime,bytes,width,height,state,created_at)
    VALUES('40000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','RECORD_PUBLIC','synthetic/key','PNG',2097153,100,100,'TEMP',CURRENT_TIMESTAMP);
    RAISE EXCEPTION 'FAIL: oversized media accepted';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: media byte limit; SQLSTATE=%', SQLSTATE; END;
  BEGIN
    INSERT INTO media_object(id,owner_id,scope,storage_key,mime,bytes,width,height,state,created_at)
    VALUES('40000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','RECORD_PUBLIC','synthetic/key','PNG',100,4097,100,'TEMP',CURRENT_TIMESTAMP);
    RAISE EXCEPTION 'FAIL: oversized pixels accepted';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: media pixel limit; SQLSTATE=%', SQLSTATE; END;
END; $$;

INSERT INTO media_object(id,owner_id,scope,storage_key,mime,bytes,width,height,state,created_at)
VALUES('40000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000001','RECORD_PUBLIC','synthetic/valid','PNG',100,100,100,'ATTACHED',CURRENT_TIMESTAMP);
INSERT INTO media_binding(media_id,scope,record_content_id,ordinal)
VALUES('40000000-0000-4000-8000-000000000002','RECORD_PUBLIC','20000000-0000-4000-8000-000000000001',1);
DO $$
BEGIN
  BEGIN
    INSERT INTO media_binding(media_id,scope,record_content_id,ordinal)
    VALUES('40000000-0000-4000-8000-000000000002','RECORD_PUBLIC','20000000-0000-4000-8000-000000000002',1);
    RAISE EXCEPTION 'FAIL: same media bound twice';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'PASS: unique cross-content binding; SQLSTATE=%', SQLSTATE; END;
  BEGIN
    INSERT INTO media_binding(media_id,scope,claim_content_id,ordinal)
    VALUES('40000000-0000-4000-8000-000000000002','CLAIM_EVIDENCE','30000000-0000-4000-8000-000000000001',1);
    RAISE EXCEPTION 'FAIL: public media reused as evidence';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: cross-scope media rejected; SQLSTATE=%', SQLSTATE; END;
END; $$;

INSERT INTO governance_case(id,record_id,kind,status,created_at,waiting_started_at,reviewer_deadline_at)
VALUES('50000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002','REPORT','WAITING_REVIEWER',
 '2026-10-14T12:00:00+08:00','2026-10-14T12:00:00+08:00','2026-10-21T12:00:00+08:00');
DO $$
BEGIN
  BEGIN
    UPDATE governance_case SET reviewer_deadline_at=reviewer_deadline_at+interval '1 second'
    WHERE id='50000000-0000-4000-8000-000000000001';
    RAISE EXCEPTION 'FAIL: waiting deadline extended';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: deadline cannot extend; SQLSTATE=%', SQLSTATE; END;
  BEGIN
    UPDATE governance_case SET waiting_started_at=waiting_started_at+interval '1 second'
    WHERE id='50000000-0000-4000-8000-000000000001';
    RAISE EXCEPTION 'FAIL: waiting start reset';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: waiting start immutable; SQLSTATE=%', SQLSTATE; END;
  BEGIN
    UPDATE claim SET status='SELECTED',selected_at='2026-10-14T12:00:00+08:00',deadline_at='2026-10-16T12:00:00+08:00'
    WHERE id='30000000-0000-4000-8000-000000000001';
    RAISE EXCEPTION 'FAIL: SELECTED without pair accepted';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: two reservations required; SQLSTATE=%', SQLSTATE; END;
END; $$;

INSERT INTO match_run(id,lost_id,lost_version,rule_version,rule_epoch,status,updated_at)
VALUES('60000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',1,'MR-1',1,'READY',CURRENT_TIMESTAMP);
DO $$
BEGIN
  BEGIN
    INSERT INTO match_result(run_id,found_id,found_version,c,k,l,t,score,rank)
    VALUES('60000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002',1,35,0,0,0,35,1);
    RAISE EXCEPTION 'FAIL: score 35 stored';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: below-threshold score not stored; SQLSTATE=%', SQLSTATE; END;
END; $$;
INSERT INTO outbox_event(id,type,aggregate_version,occurred_at,purge_at)
VALUES('70000000-0000-4000-8000-000000000001','MATCH_UPDATED',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+interval '24 hours');
INSERT INTO job(id,event_id,handler,status)
VALUES('80000000-0000-4000-8000-000000000001','70000000-0000-4000-8000-000000000001','MATCH_REBUILD','READY');
DO $$
BEGIN
  BEGIN
    INSERT INTO job(id,event_id,handler,status)
    VALUES('80000000-0000-4000-8000-000000000002','70000000-0000-4000-8000-000000000001','MATCH_REBUILD','READY');
    RAISE EXCEPTION 'FAIL: duplicate event/handler accepted';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'PASS: job deduplication; SQLSTATE=%', SQLSTATE; END;
END; $$;

-- Valid paired commit within a deferred transaction; both sides are changed.
SET CONSTRAINTS ALL DEFERRED;
UPDATE item_record SET status='RESERVED',version=version+1
WHERE id IN ('20000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002');
UPDATE claim SET status='SELECTED',selected_at='2026-10-14T12:00:00+08:00',deadline_at='2026-10-16T12:00:00+08:00'
WHERE id='30000000-0000-4000-8000-000000000001';
INSERT INTO active_reservation(record_id,claim_id,side) VALUES
 ('20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001','LOST'),
 ('20000000-0000-4000-8000-000000000002','30000000-0000-4000-8000-000000000001','FOUND');
SET CONSTRAINTS ALL IMMEDIATE;
DO $$ BEGIN RAISE NOTICE 'PASS: complete paired reservation satisfies local deferred constraints; SQLSTATE=%', SQLSTATE; END; $$;
INSERT INTO rule_config(version,epoch,parameters,state) VALUES('MR-1',1,'{}'::jsonb,'ACTIVE');
DO $$
BEGIN
  BEGIN
    INSERT INTO quality_evaluation(id,rule_version,sample_count,hits,empty_count,search_hits,trial_passed,mode,reason,approved_by,created_at)
    VALUES('90000000-0000-4000-8000-000000000001','MR-1',100,79,10,100,true,'NORMAL','仅构造门槛负例','10000000-0000-4000-8000-000000000001',CURRENT_TIMESTAMP);
    RAISE EXCEPTION 'FAIL: 79/100 NORMAL accepted';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: quality threshold required; SQLSTATE=%', SQLSTATE; END;
END; $$;
ROLLBACK;
