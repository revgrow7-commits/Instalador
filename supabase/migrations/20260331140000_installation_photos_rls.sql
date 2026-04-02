-- Installation Photos RLS Policies Migration
-- Created: 2026-03-31
-- Purpose: Create enhanced granular RLS policies for installation_photos table
-- Includes installer, gerente (manager), and admin access control
-- Also adds CREATE policy for installers to create their own photos

-- ============================================================================
-- DROP EXISTING POLICIES (from initial RLS migration)
-- ============================================================================

DROP POLICY IF EXISTS "admin_see_all" ON installation_photos;
DROP POLICY IF EXISTS "instalador_see_own" ON installation_photos;

-- ============================================================================
-- RLS POLICIES: installation_photos (Enhanced with Gerente access)
-- ============================================================================

-- Policy 1: Admin sees all photos
-- Admin role can view all photos across all branches and installers
CREATE POLICY "admin_see_all_photos" ON installation_photos
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy 2: Instalador sees their own photos
-- Installers can only view photos they personally took
CREATE POLICY "instalador_see_own_photos" ON installation_photos
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- Policy 3: Gerente sees photos from their branch installers
-- Managers can view photos taken by installers assigned to their branch
-- via the installation_job_assignments and installation_assignment_items relationships
CREATE POLICY "gerente_see_branch_photos" ON installation_photos
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND assignment_id IN (
      SELECT id FROM installation_job_assignments
      WHERE branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    )
  );

-- Policy 4: Instalador can create their own photos
-- Installers can insert photos only for themselves
CREATE POLICY "instalador_create_own_photos" ON installation_photos
  FOR INSERT
  WITH CHECK (installer_id = auth.uid());

-- ============================================================================
-- RLS POLICIES: installation_pause_logs (Enhanced)
-- ============================================================================

-- Policy: Gerente can see pause logs for their branch installers
CREATE POLICY "gerente_see_branch_pauses" ON installation_pause_logs
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND assignment_id IN (
      SELECT id FROM installation_job_assignments
      WHERE branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    )
  );

-- Policy: Instalador can see their own pause logs
CREATE POLICY "instalador_see_own_pauses" ON installation_pause_logs
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- ============================================================================
-- RLS POLICIES: installation_checklists (Enhanced with Gerente)
-- ============================================================================

-- Policy: Gerente can see checklists for their branch
CREATE POLICY "gerente_see_branch_checklists" ON installation_checklists
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND assignment_id IN (
      SELECT id FROM installation_job_assignments
      WHERE branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    )
  );

-- ============================================================================
-- COMMENTS (documentation for enhanced policies)
-- ============================================================================

COMMENT ON POLICY "admin_see_all_photos" ON installation_photos IS
  'Admin role can view all photos across all branches';

COMMENT ON POLICY "instalador_see_own_photos" ON installation_photos IS
  'Installers can only view photos they personally took';

COMMENT ON POLICY "gerente_see_branch_photos" ON installation_photos IS
  'Managers can view photos taken by installers in their branch';

COMMENT ON POLICY "instalador_create_own_photos" ON installation_photos IS
  'Installers can create photos only for themselves';

COMMENT ON POLICY "gerente_see_branch_pauses" ON installation_pause_logs IS
  'Managers can view pause logs for installers in their branch';

COMMENT ON POLICY "instalador_see_own_pauses" ON installation_pause_logs IS
  'Installers can view their own pause logs';

COMMENT ON POLICY "gerente_see_branch_checklists" ON installation_checklists IS
  'Managers can view checklists for installers in their branch';
