-- Installation RLS Policies Migration
-- Created: 2026-03-31
-- Purpose: Create comprehensive RLS policies with role-based access control (admin_instal, gerente_instal, instalador)
-- Also includes trigger function for auto-updating assignment timestamps

-- ============================================================================
-- DROP OLD POLICIES (from initial schema migration)
-- ============================================================================

DROP POLICY IF EXISTS "Users can view assignments for their branch" ON installation_job_assignments;
DROP POLICY IF EXISTS "Installers can view their own checklists" ON installation_checklists;
DROP POLICY IF EXISTS "Installers can insert their own checklists" ON installation_checklists;
DROP POLICY IF EXISTS "Installers can view their own coins balance" ON installer_coins_balance;
DROP POLICY IF EXISTS "Only system can update coins balance" ON installer_coins_balance;
DROP POLICY IF EXISTS "Installers can view their own coins transactions" ON coins_transactions;

-- ============================================================================
-- RLS POLICIES: installation_job_assignments
-- ============================================================================

-- Policy: Admin sees all assignments
CREATE POLICY "admin_see_all" ON installation_job_assignments
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Gerente sees assignments for their branch
CREATE POLICY "gerente_see_branch" ON installation_job_assignments
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
  );

-- Policy: Instalador sees only assignments where they are assigned
CREATE POLICY "instalador_see_assigned" ON installation_job_assignments
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND EXISTS (
      SELECT 1 FROM installation_assignment_items
      WHERE assignment_id = installation_job_assignments.id
      AND auth.uid() = ANY(assigned_installer_ids)
    )
  );

-- Policy: Admin and Gerente can create assignments
CREATE POLICY "admin_gerente_create_assignments" ON installation_job_assignments
  FOR INSERT
  WITH CHECK (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' IN ('admin_instal', 'gerente_instal')
  );

-- ============================================================================
-- RLS POLICIES: installation_assignment_items
-- ============================================================================

-- Policy: Admin sees all items
CREATE POLICY "admin_see_all" ON installation_assignment_items
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Gerente sees items for their branch assignments
CREATE POLICY "gerente_see_branch_items" ON installation_assignment_items
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND assignment_id IN (
      SELECT id FROM installation_job_assignments
      WHERE branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    )
  );

-- Policy: Instalador sees items they are assigned to
CREATE POLICY "instalador_see_assigned_items" ON installation_assignment_items
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND auth.uid() = ANY(assigned_installer_ids)
  );

-- ============================================================================
-- RLS POLICIES: installation_checklists
-- ============================================================================

-- Policy: Admin sees all checklists
CREATE POLICY "admin_see_all" ON installation_checklists
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador sees only their own checklists
CREATE POLICY "instalador_see_own" ON installation_checklists
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- Policy: Instalador can create their own checklists
CREATE POLICY "create_own_checklists" ON installation_checklists
  FOR INSERT
  WITH CHECK (installer_id = auth.uid());

-- ============================================================================
-- RLS POLICIES: installation_photos
-- ============================================================================

-- Policy: Admin sees all photos
CREATE POLICY "admin_see_all" ON installation_photos
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador sees only their own photos
CREATE POLICY "instalador_see_own" ON installation_photos
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- ============================================================================
-- RLS POLICIES: installation_pause_logs
-- ============================================================================

-- Policy: Admin sees all pause logs
CREATE POLICY "admin_see_all" ON installation_pause_logs
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador can insert their own pause logs
CREATE POLICY "instalador_create_pauses" ON installation_pause_logs
  FOR INSERT
  WITH CHECK (installer_id = auth.uid());

-- ============================================================================
-- RLS POLICIES: installation_notifications
-- ============================================================================

-- Policy: Admin sees all notifications
CREATE POLICY "admin_see_all" ON installation_notifications
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador sees their own notifications
CREATE POLICY "instalador_see_own_notifications" ON installation_notifications
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- ============================================================================
-- RLS POLICIES: installer_coins_balance
-- ============================================================================

-- Policy: Admin sees all balances
CREATE POLICY "admin_see_all" ON installer_coins_balance
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador sees only their own balance
CREATE POLICY "instalador_see_own" ON installer_coins_balance
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- ============================================================================
-- RLS POLICIES: coins_transactions
-- ============================================================================

-- Policy: Admin sees all transactions
CREATE POLICY "admin_see_all" ON coins_transactions
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy: Instalador sees their own transactions
CREATE POLICY "instalador_see_own_transactions" ON coins_transactions
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- ============================================================================
-- TRIGGER FUNCTION: update_assignment_updated_at
-- ============================================================================
-- Auto-updates the updated_at timestamp on installation_job_assignments
-- when checklists or pause logs are modified

CREATE OR REPLACE FUNCTION update_assignment_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE installation_job_assignments
  SET updated_at = now()
  WHERE id = NEW.assignment_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS for cascading timestamp updates
-- ============================================================================

-- Trigger: Update assignment timestamp when checklist is created
CREATE TRIGGER trg_checklist_update_assignment
  AFTER INSERT ON installation_checklists
  FOR EACH ROW
  EXECUTE FUNCTION update_assignment_updated_at();

-- Trigger: Update assignment timestamp when pause log is created
CREATE TRIGGER trg_pauses_update_assignment
  AFTER INSERT ON installation_pause_logs
  FOR EACH ROW
  EXECUTE FUNCTION update_assignment_updated_at();

-- ============================================================================
-- COMMENTS (documentation)
-- ============================================================================

COMMENT ON FUNCTION update_assignment_updated_at() IS
  'Trigger function that cascades updated_at timestamp updates from checklists and pause logs to their parent assignment';

COMMENT ON TRIGGER trg_checklist_update_assignment ON installation_checklists IS
  'Automatically updates parent assignment updated_at timestamp when a checklist is created';

COMMENT ON TRIGGER trg_pauses_update_assignment ON installation_pause_logs IS
  'Automatically updates parent assignment updated_at timestamp when a pause log is created';
