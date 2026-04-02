-- Installation Schema Migration
-- Created: 2026-03-31
-- Purpose: Create 8 tables + enums + indices for installation job management system

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Create enum for job status
CREATE TYPE installation_status AS ENUM (
  'agendado',
  'em_progresso',
  'concluido',
  'cancelado'
);

-- ============================================================================
-- TABLE 1: installation_job_assignments (master)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_job_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL,
  holdprint_job_data JSONB NOT NULL,
  scheduled_date TIMESTAMP WITH TIME ZONE NOT NULL,
  scheduled_end_time TIMESTAMP WITH TIME ZONE,
  status installation_status DEFAULT 'agendado',
  created_by UUID NOT NULL REFERENCES auth.users(id),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  cancelled_at TIMESTAMP WITH TIME ZONE,
  cancellation_reason TEXT,
  branch_id TEXT,
  kanban_history JSONB,
  UNIQUE(job_id, scheduled_date)
);

CREATE INDEX idx_assignments_status ON installation_job_assignments(status);
CREATE INDEX idx_assignments_branch ON installation_job_assignments(branch_id);
CREATE INDEX idx_assignments_date ON installation_job_assignments(scheduled_date);

-- ============================================================================
-- TABLE 2: installation_assignment_items (detail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_assignment_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES installation_job_assignments(id) ON DELETE CASCADE,
  job_item_id TEXT NOT NULL,
  item_data JSONB,
  assigned_installer_ids UUID[] NOT NULL,
  assigned_installers JSONB,
  status TEXT DEFAULT 'aguardando',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_assignment_items_assignment ON installation_assignment_items(assignment_id);

-- ============================================================================
-- TABLE 3: installation_checklists (check-in/out with GPS + photo)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_checklists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES installation_job_assignments(id) ON DELETE CASCADE,
  assignment_item_id UUID REFERENCES installation_assignment_items(id) ON DELETE CASCADE,
  installer_id UUID NOT NULL REFERENCES auth.users(id),
  type TEXT NOT NULL CHECK (type IN ('checkin', 'checkout')),
  latitude DECIMAL(10, 8) NOT NULL,
  longitude DECIMAL(11, 8) NOT NULL,
  address TEXT,
  photo_url TEXT NOT NULL,
  photo_metadata JSONB,
  notes TEXT,
  rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE(assignment_item_id, installer_id, type)
);

CREATE INDEX idx_checklists_assignment ON installation_checklists(assignment_id);
CREATE INDEX idx_checklists_installer ON installation_checklists(installer_id);
CREATE INDEX idx_checklists_type ON installation_checklists(type);

-- ============================================================================
-- TABLE 4: installation_photos (índice/gallery)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES installation_job_assignments(id) ON DELETE CASCADE,
  assignment_item_id UUID REFERENCES installation_assignment_items(id) ON DELETE CASCADE,
  installer_id UUID NOT NULL REFERENCES auth.users(id),
  checklist_id UUID NOT NULL REFERENCES installation_checklists(id) ON DELETE CASCADE,
  photo_url TEXT NOT NULL,
  photo_key TEXT NOT NULL,
  thumbnail_url TEXT,
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  type TEXT NOT NULL,
  file_size INTEGER,
  mime_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_photos_assignment ON installation_photos(assignment_id);
CREATE INDEX idx_photos_installer ON installation_photos(installer_id);

-- ============================================================================
-- TABLE 5: installation_pause_logs (tracking breaks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_pause_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES installation_job_assignments(id) ON DELETE CASCADE,
  installer_id UUID NOT NULL REFERENCES auth.users(id),
  pause_type TEXT NOT NULL CHECK (pause_type IN ('almoco', 'banheiro', 'tecnico', 'material')),
  started_at TIMESTAMP WITH TIME ZONE NOT NULL,
  ended_at TIMESTAMP WITH TIME ZONE,
  duration_minutes INTEGER,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_pauses_assignment ON installation_pause_logs(assignment_id);
CREATE INDEX idx_pauses_installer ON installation_pause_logs(installer_id);

-- ============================================================================
-- TABLE 6: installation_notifications (email + WhatsApp)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installation_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID REFERENCES installation_job_assignments(id) ON DELETE CASCADE,
  installer_id UUID NOT NULL REFERENCES auth.users(id),
  email_type TEXT NOT NULL,
  channel TEXT DEFAULT 'email',
  email_data JSONB,
  whatsapp_message_id TEXT,
  phone_number_sent_to TEXT,
  status TEXT DEFAULT 'pending',
  email_sent_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_notifications_installer ON installation_notifications(installer_id);

-- ============================================================================
-- TABLE 7: installer_coins_balance (gamification - saldo de moedas)
-- ============================================================================

CREATE TABLE IF NOT EXISTS installer_coins_balance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  installer_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  total_coins INTEGER DEFAULT 0,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_coins_installer ON installer_coins_balance(installer_id);

-- ============================================================================
-- TABLE 8: coins_transactions (auditoria de transações)
-- ============================================================================

CREATE TABLE IF NOT EXISTS coins_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  installer_id UUID NOT NULL REFERENCES auth.users(id),
  amount INTEGER NOT NULL,
  reason TEXT NOT NULL,
  related_checklist_id UUID REFERENCES installation_checklists(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_coins_transactions_installer ON coins_transactions(installer_id);

-- ============================================================================
-- EXTENSIONS (for auth enhancements)
-- ============================================================================

-- Note: The following fields should be added to auth.users via Supabase dashboard:
-- - branch_id TEXT
-- - timezone TEXT
-- - phone_number TEXT

-- ============================================================================
-- VIEW: installation_jobs_public (segurança - sem preços para não-admin)
-- ============================================================================

CREATE VIEW installation_jobs_public AS
SELECT
  a.id,
  a.job_id,
  a.scheduled_date,
  a.scheduled_end_time,
  a.status,
  a.branch_id,
  a.created_at,
  a.updated_at,
  (a.holdprint_job_data ->> 'customer_name') AS customer_name,
  (a.holdprint_job_data ->> 'address') AS address,
  (a.holdprint_job_data ->> 'city') AS city,
  CASE
    WHEN auth.uid() = a.created_by OR (SELECT role FROM auth.users WHERE id = auth.uid()) = 'admin' THEN a.holdprint_job_data
    ELSE jsonb_set(a.holdprint_job_data, '{price,total}', 'null'::jsonb)
  END AS holdprint_job_data,
  a.created_by
FROM installation_job_assignments a;

-- ============================================================================
-- RLS (Row Level Security) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE installation_job_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE installation_assignment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE installation_checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE installation_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE installation_pause_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE installation_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE installer_coins_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE coins_transactions ENABLE ROW LEVEL SECURITY;

-- Policy: Installers can view assignments for their branch
CREATE POLICY "Users can view assignments for their branch"
  ON installation_job_assignments
  FOR SELECT
  USING (
    branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    OR (SELECT role FROM auth.users WHERE id = auth.uid()) = 'admin'
  );

-- Policy: Installers can view their own checklists
CREATE POLICY "Installers can view their own checklists"
  ON installation_checklists
  FOR SELECT
  USING (
    installer_id = auth.uid()
    OR (SELECT role FROM auth.users WHERE id = auth.uid()) = 'admin'
  );

-- Policy: Installers can insert their own checklists
CREATE POLICY "Installers can insert their own checklists"
  ON installation_checklists
  FOR INSERT
  WITH CHECK (installer_id = auth.uid());

-- Policy: Installers can view their own coins balance
CREATE POLICY "Installers can view their own coins balance"
  ON installer_coins_balance
  FOR SELECT
  USING (
    installer_id = auth.uid()
    OR (SELECT role FROM auth.users WHERE id = auth.uid()) = 'admin'
  );

-- Policy: Only system can update coins balance
CREATE POLICY "Only system can update coins balance"
  ON installer_coins_balance
  FOR UPDATE
  USING (false);

-- Policy: Installers can view their own transactions
CREATE POLICY "Installers can view their own coins transactions"
  ON coins_transactions
  FOR SELECT
  USING (
    installer_id = auth.uid()
    OR (SELECT role FROM auth.users WHERE id = auth.uid()) = 'admin'
  );

-- ============================================================================
-- COMMENTS (documentation)
-- ============================================================================

COMMENT ON TABLE installation_job_assignments IS 'Master record for installation jobs, linked to Holdprint ERP jobs';
COMMENT ON TABLE installation_assignment_items IS 'Detail records - individual items/services assigned to installers';
COMMENT ON TABLE installation_checklists IS 'Check-in/check-out records with GPS location and photo evidence';
COMMENT ON TABLE installation_photos IS 'Photo index/gallery for installation documentation';
COMMENT ON TABLE installation_pause_logs IS 'Tracks work breaks (lunch, bathroom, technical, material issues)';
COMMENT ON TABLE installation_notifications IS 'Email and WhatsApp notification history';
COMMENT ON TABLE installer_coins_balance IS 'Gamification: installer coin balance for rewards/marketplace';
COMMENT ON TABLE coins_transactions IS 'Audit log for all coin transactions and reasoning';
