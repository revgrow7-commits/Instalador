-- RLS Policies Test Suite
-- Tests for role-based access control in installation tables

-- ============================================================================
-- TEST 1: Verify RLS is enabled on all 8 tables
-- ============================================================================

-- Run this query to check RLS status:
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE tablename LIKE 'installation%' OR tablename IN ('installer_coins_balance', 'coins_transactions')
-- ORDER BY tablename;

-- Expected: All 8 tables should show rowsecurity = true

-- ============================================================================
-- TEST 2: Verify admin_instal role can see all assignments
-- ============================================================================

-- Setup test data:
-- INSERT INTO auth.users (id, email, raw_user_meta_data)
-- VALUES ('admin-uuid-1234', 'admin@test.com', '{"role": "admin_instal"}');

-- Then run as admin:
-- SELECT * FROM installation_job_assignments;
-- Expected: Should return all rows

-- ============================================================================
-- TEST 3: Verify gerente_instal role sees only their branch
-- ============================================================================

-- Setup gerente:
-- INSERT INTO auth.users (id, email, raw_user_meta_data, branch_id)
-- VALUES ('gerente-uuid-5678', 'gerente@branch1.com', '{"role": "gerente_instal"}', 'branch-001');

-- Add assignment for branch-001:
-- INSERT INTO installation_job_assignments (id, job_id, holdprint_job_data, scheduled_date, created_by, branch_id)
-- VALUES ('job-uuid-001', 'JOB-001', '{"customer": "Test"}', NOW(), 'admin-uuid-1234', 'branch-001');

-- Run as gerente:
-- SELECT * FROM installation_job_assignments;
-- Expected: Should only see assignments where branch_id = 'branch-001'

-- ============================================================================
-- TEST 4: Verify instalador_instal role sees only assigned jobs
-- ============================================================================

-- Setup instalador:
-- INSERT INTO auth.users (id, email, raw_user_meta_data)
-- VALUES ('installer-uuid-9999', 'installer@test.com', '{"role": "instalador"}');

-- Assign job to installer:
-- INSERT INTO installation_assignment_items (id, assignment_id, job_item_id, assigned_installer_ids, item_data)
-- VALUES ('item-uuid-001', 'job-uuid-001', 'ITEM-001', ARRAY['installer-uuid-9999'], '{"description": "Test"}');

-- Run as installer:
-- SELECT * FROM installation_job_assignments;
-- Expected: Should only see assignment 'job-uuid-001' where they are assigned

-- ============================================================================
-- TEST 5: Verify INSERT policies work correctly
-- ============================================================================

-- Test: Admin can create assignments
-- As admin, run:
-- INSERT INTO installation_job_assignments (job_id, holdprint_job_data, scheduled_date, created_by, branch_id)
-- VALUES ('JOB-NEW-001', '{"customer": "New"}', NOW(), 'admin-uuid-1234', 'branch-001');
-- Expected: Success

-- Test: Instalador cannot create assignments
-- As installer, run the same INSERT
-- Expected: Policy violation error

-- ============================================================================
-- TEST 6: Verify checklist INSERT permissions
-- ============================================================================

-- Test: Installer can create checklist for themselves
-- As installer, run:
-- INSERT INTO installation_checklists (assignment_id, assignment_item_id, installer_id, type, latitude, longitude, address, photo_url)
-- VALUES ('job-uuid-001', 'item-uuid-001', 'installer-uuid-9999', 'checkin', 37.7749, -122.4194, 'Test Address', 'http://photo.url');
-- Expected: Success

-- Test: Installer cannot create checklist for another installer
-- As installer, run:
-- INSERT INTO installation_checklists (assignment_id, assignment_item_id, installer_id, type, latitude, longitude, address, photo_url)
-- VALUES ('job-uuid-001', 'item-uuid-001', 'other-installer-uuid', 'checkin', 37.7749, -122.4194, 'Test Address', 'http://photo.url');
-- Expected: Policy violation error

-- ============================================================================
-- TEST 7: Verify trigger updates assignment timestamp
-- ============================================================================

-- Setup:
-- INSERT INTO installation_checklists (...) VALUES (...);

-- Run query to check:
-- SELECT updated_at FROM installation_job_assignments WHERE id = 'job-uuid-001';
-- Expected: updated_at should be updated to recent timestamp

-- ============================================================================
-- TEST 8: Verify pause log trigger works
-- ============================================================================

-- Setup:
-- Get current updated_at of assignment
-- SELECT updated_at FROM installation_job_assignments WHERE id = 'job-uuid-001' INTO old_timestamp;

-- Insert pause log:
-- INSERT INTO installation_pause_logs (assignment_id, installer_id, pause_type, started_at)
-- VALUES ('job-uuid-001', 'installer-uuid-9999', 'almoco', NOW());

-- Check updated_at:
-- SELECT updated_at FROM installation_job_assignments WHERE id = 'job-uuid-001';
-- Expected: updated_at > old_timestamp

-- ============================================================================
-- POLICY COUNT VERIFICATION
-- ============================================================================

-- Expected policy counts per table:
-- - installation_job_assignments: 4 policies (admin_see_all, gerente_see_branch, instalador_see_assigned, admin_gerente_create_assignments)
-- - installation_assignment_items: 3 policies (admin_see_all, gerente_see_branch_items, instalador_see_assigned_items)
-- - installation_checklists: 3 policies (admin_see_all, instalador_see_own, create_own_checklists)
-- - installation_photos: 2 policies (admin_see_all, instalador_see_own)
-- - installation_pause_logs: 2 policies (admin_see_all, instalador_create_pauses)
-- - installation_notifications: 2 policies (admin_see_all, instalador_see_own_notifications)
-- - installer_coins_balance: 2 policies (admin_see_all, instalador_see_own)
-- - coins_transactions: 2 policies (admin_see_all, instalador_see_own_transactions)
-- Total: 20 policies

-- Run this to verify:
-- SELECT
--   schemaname,
--   tablename,
--   policyname,
--   qual,
--   with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- AND (tablename LIKE 'installation%' OR tablename IN ('installer_coins_balance', 'coins_transactions'))
-- ORDER BY tablename, policyname;

-- ============================================================================
-- TRIGGER VERIFICATION
-- ============================================================================

-- Expected triggers:
-- - trg_checklist_update_assignment on installation_checklists
-- - trg_pauses_update_assignment on installation_pause_logs

-- Run this to verify:
-- SELECT
--   trigger_schema,
--   trigger_name,
--   event_object_table,
--   action_statement
-- FROM information_schema.triggers
-- WHERE trigger_name LIKE 'trg_%'
-- ORDER BY event_object_table, trigger_name;
