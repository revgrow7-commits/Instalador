-- Installation Notifications & Cron Reminders Migration
-- Created: 2026-03-31
-- Purpose: Create notification infrastructure for email/WhatsApp + cron job skeleton
--
-- Phase 1: Database schema for storing notifications
-- Phase 2: pg_cron scheduler + Resend/Twilio integration

-- ============================================================================
-- TABLE: installation_notifications
-- ============================================================================
-- Stores all notifications (email + WhatsApp) with delivery tracking
-- Used by Edge Function: send-notifications (Phase 1: mock, Phase 2: real)

CREATE TABLE IF NOT EXISTS installation_notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  installer_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  assignment_id uuid NOT NULL REFERENCES installation_job_assignments(id) ON DELETE CASCADE,

  -- Notification metadata
  email_type text NOT NULL,
  channel text NOT NULL CHECK (channel IN ('email', 'whatsapp')),
  email_data jsonb NOT NULL,

  -- Email content (Phase 1: template, Phase 2: rendered + sent)
  email_subject text,
  email_html text,
  email_body text,

  -- WhatsApp content (Phase 2: sent via Twilio)
  whatsapp_body text,

  -- Delivery tracking
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'bounced')),
  email_sent_at timestamp with time zone,
  failed_at timestamp with time zone,
  error_message text,
  retry_count integer DEFAULT 0,

  -- Audit
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX idx_installation_notifications_installer_id
  ON installation_notifications(installer_id);

CREATE INDEX idx_installation_notifications_assignment_id
  ON installation_notifications(assignment_id);

CREATE INDEX idx_installation_notifications_status
  ON installation_notifications(status);

CREATE INDEX idx_installation_notifications_created_at
  ON installation_notifications(created_at DESC);

CREATE INDEX idx_installation_notifications_pending
  ON installation_notifications(created_at ASC)
  WHERE status = 'pending';

-- ============================================================================
-- RLS POLICIES: installation_notifications
-- ============================================================================

ALTER TABLE installation_notifications ENABLE ROW LEVEL SECURITY;

-- Policy 1: Admin sees all notifications
CREATE POLICY "admin_see_all_notifications" ON installation_notifications
  FOR SELECT
  USING ((auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'admin_instal');

-- Policy 2: Instalador sees their own notifications
CREATE POLICY "instalador_see_own_notifications" ON installation_notifications
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'instalador'
    AND installer_id = auth.uid()
  );

-- Policy 3: Gerente sees notifications from their branch installers
CREATE POLICY "gerente_see_branch_notifications" ON installation_notifications
  FOR SELECT
  USING (
    (auth.jwt() ->> 'user_metadata')::jsonb ->> 'role' = 'gerente_instal'
    AND assignment_id IN (
      SELECT id FROM installation_job_assignments
      WHERE branch_id = (SELECT branch_id FROM auth.users WHERE id = auth.uid())
    )
  );

-- ============================================================================
-- FUNCTION: installation_reminder_24h (Phase 1 Skeleton)
-- ============================================================================
-- This function will be called by pg_cron to send 24-hour reminders
--
-- Phase 1: Skeleton with logging
-- Phase 2: Actual implementation that:
--   1. Queries installation_job_assignments where scheduled_date = tomorrow
--   2. Fetches installer + client + branch details
--   3. Creates records in installation_notifications with type='lembrete_24h'
--   4. Triggers send-notifications Edge Function via pg_net extension

CREATE OR REPLACE FUNCTION installation_reminder_24h()
RETURNS TABLE(processed integer, job_count integer) AS $$
DECLARE
  v_count integer := 0;
BEGIN
  -- Phase 1: Log skeleton
  -- Phase 2 implementation will:
  -- SELECT COUNT(*) INTO v_count FROM installation_job_assignments
  -- WHERE DATE(scheduled_date) = CURRENT_DATE + INTERVAL '1 day'
  -- AND status = 'scheduled';

  RAISE NOTICE '[Phase 1] Reminder cron would process % jobs for tomorrow', v_count;

  RETURN QUERY SELECT v_count::integer as processed, v_count::integer as job_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: installation_notify_on_assignment (Trigger)
-- ============================================================================
-- Automatically send agendamento (scheduling) notification when job is created
-- Called by trigger after INSERT on installation_job_assignments

CREATE OR REPLACE FUNCTION installation_notify_on_assignment()
RETURNS TRIGGER AS $$
BEGIN
  -- Phase 1: Insert agendamento notification
  INSERT INTO installation_notifications (
    installer_id,
    assignment_id,
    email_type,
    channel,
    email_data,
    status
  )
  SELECT
    ija.installer_id,
    ija.id,
    'agendamento',
    'email',
    jsonb_build_object(
      'installer_name', u.raw_user_meta_data ->> 'full_name',
      'job_title', 'Nova Instalação',
      'branch', b.name,
      'scheduled_date_pt_br', TO_CHAR(ija.scheduled_date, 'DD/MM/YYYY'),
      'scheduled_time', TO_CHAR(ija.scheduled_date, 'HH24:MI'),
      'client_name', 'Cliente'
    ),
    'pending'
  FROM
    installation_job_assignments ija
    LEFT JOIN auth.users u ON ija.installer_id = u.id
    LEFT JOIN installation_branches b ON ija.branch_id = b.id
  WHERE ija.id = NEW.id;

  -- Phase 2: Also send WhatsApp
  -- INSERT INTO installation_notifications (channel='whatsapp') ...

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for new assignments
DROP TRIGGER IF EXISTS trigger_notify_on_assignment ON installation_job_assignments;

CREATE TRIGGER trigger_notify_on_assignment
  AFTER INSERT ON installation_job_assignments
  FOR EACH ROW
  EXECUTE FUNCTION installation_notify_on_assignment();

-- ============================================================================
-- CRON SKELETON (Phase 2 Implementation Required)
-- ============================================================================
--
-- To enable pg_cron in Supabase:
-- 1. Run as superuser: CREATE EXTENSION IF NOT EXISTS pg_cron;
-- 2. Grant execute to postgres user
--
-- Phase 2 will uncomment and enable:
--
-- -- Send 24-hour reminders every day at 9 AM
-- SELECT cron.schedule(
--   'installation-reminder-24h',
--   '0 9 * * *',
--   $$SELECT installation_reminder_24h()$$
-- );
--
-- -- Send checkout reminders every evening at 5 PM
-- SELECT cron.schedule(
--   'installation-reminder-checkout',
--   '0 17 * * *',
--   $$SELECT installation_remind_checkout()$$
-- );

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
--
-- Phase 1 Status: COMPLETE
--   ✓ installation_notifications table created
--   ✓ RLS policies configured
--   ✓ Trigger for automatic notifications on assignment
--   ✓ Cron skeleton function
--   ✓ Edge Function: send-notifications (mock dispatcher)
--
-- Phase 2 TODOs:
--   - Enable pg_cron extension in Supabase
--   - Implement actual installation_reminder_24h() logic
--   - Add Resend API integration (emails)
--   - Add Twilio API integration (WhatsApp)
--   - Configure pg_net extension for HTTP calls to send-notifications
--   - Add retry logic with exponential backoff
--   - Add delivery webhooks from Resend/Twilio
--   - Add notification preferences per installer
--   - Add admin dashboard for notification logs
--
-- Testing Phase 1:
--   1. Create manual installation_job_assignments record
--   2. Check installation_notifications table for 'agendamento' record
--   3. Call Edge Function: POST /functions/v1/send-notifications
--      with { "mode": "process_pending" }
--   4. Verify status changed to 'sent'
