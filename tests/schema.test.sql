-- Schema Validation Tests
-- Tests to verify the installation schema is correctly implemented

-- Test 1: Verify enum exists and has correct values
SELECT
  t.typname as enum_name,
  e.enumlabel as enum_value
FROM pg_type t
  JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'installation_status'
ORDER BY e.enumsortorder;

-- Expected output:
-- enum_name       | enum_value
-- -----           | --------
-- installation_status | agendado
-- installation_status | em_progresso
-- installation_status | concluido
-- installation_status | cancelado

-- Test 2: Verify all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND table_name IN (
    'installation_job_assignments',
    'installation_assignment_items',
    'installation_checklists',
    'installation_photos',
    'installation_pause_logs',
    'installation_notifications',
    'installer_coins_balance',
    'coins_transactions'
  )
ORDER BY table_name;

-- Expected output: 8 rows with all table names

-- Test 3: Verify all indexes exist
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'installation_job_assignments',
    'installation_assignment_items',
    'installation_checklists',
    'installation_photos',
    'installation_pause_logs',
    'installation_notifications',
    'installer_coins_balance',
    'coins_transactions'
  )
ORDER BY indexname;

-- Expected output: 11 rows with all index names
-- idx_assignments_branch
-- idx_assignments_date
-- idx_assignments_status
-- idx_assignment_items_assignment
-- idx_checklists_assignment
-- idx_checklists_installer
-- idx_checklists_type
-- idx_coins_installer
-- idx_coins_transactions_installer
-- idx_notifications_installer
-- idx_pauses_assignment
-- idx_pauses_installer
-- idx_photos_assignment
-- idx_photos_installer

-- Test 4: Verify foreign key constraints
SELECT
  constraint_name,
  table_name,
  column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public'
  AND table_name IN (
    'installation_job_assignments',
    'installation_assignment_items',
    'installation_checklists',
    'installation_photos',
    'installation_pause_logs',
    'installation_notifications',
    'installer_coins_balance',
    'coins_transactions'
  )
  AND constraint_name NOT LIKE '%_pkey'
ORDER BY table_name, column_name;

-- Test 5: Verify view exists
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'VIEW'
  AND table_name = 'installation_jobs_public';

-- Expected output: 1 row with 'installation_jobs_public'

-- Test 6: Verify RLS is enabled on tables
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'installation_job_assignments',
    'installation_assignment_items',
    'installation_checklists',
    'installation_photos',
    'installation_pause_logs',
    'installation_notifications',
    'installer_coins_balance',
    'coins_transactions'
  )
ORDER BY tablename;

-- Expected output: 8 rows with rowsecurity = true

-- Test 7: Verify column types
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'installation_job_assignments'
ORDER BY ordinal_position;

-- Test 8: Verify unique constraints
SELECT
  constraint_name,
  table_name
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND constraint_type = 'UNIQUE'
  AND table_name IN (
    'installation_job_assignments',
    'installation_assignment_items',
    'installation_checklists',
    'installer_coins_balance'
  )
ORDER BY table_name;
