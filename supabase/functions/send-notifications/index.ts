/**
 * Edge Function: Send Notifications Dispatcher
 * Processes pending notifications and sends via email/WhatsApp
 *
 * Endpoint: POST /functions/v1/send-notifications
 *
 * Request Body (Phase 1 - Mock):
 * {
 *   "mode": "process_pending" | "send_single",
 *   "notification_id": "uuid" (optional, for send_single mode),
 *   "limit": 50
 * }
 *
 * Response (Phase 1):
 * {
 *   "success": true,
 *   "processed": number,
 *   "phase": "Phase 1 - Mock"
 * }
 *
 * Phase 1: Mock implementation
 * - Marks notifications as "sent" without actual delivery
 * - Updates installation_notifications.status
 * - Used for testing infrastructure
 *
 * Phase 2: Real integration
 * - Email via Resend API (https://resend.com)
 * - WhatsApp via Twilio API (https://twilio.com)
 * - Retry logic with exponential backoff
 * - Delivery tracking and webhooks
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// ============================================================================
// ENVIRONMENT & INITIALIZATION
// ============================================================================

const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

if (!supabaseUrl || !supabaseServiceKey) {
  throw new Error('Missing Supabase configuration (SUPABASE_URL or SERVICE_ROLE_KEY)')
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

// Phase 2: Will be set from environment variables
// const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY')
// const TWILIO_ACCOUNT_SID = Deno.env.get('TWILIO_ACCOUNT_SID')
// const TWILIO_AUTH_TOKEN = Deno.env.get('TWILIO_AUTH_TOKEN')

// ============================================================================
// TYPES
// ============================================================================

interface ProcessPendingRequest {
  mode: 'process_pending' | 'send_single'
  notification_id?: string
  limit?: number
}

interface NotificationRecord {
  id: string
  installer_id: string
  assignment_id: string
  email_type: string
  channel: 'email' | 'whatsapp'
  email_data: Record<string, any>
  email_subject?: string
  email_html?: string
  whatsapp_body?: string
  status: string
  created_at: string
}

// ============================================================================
// REQUEST VALIDATION
// ============================================================================

function validateRequest(body: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!body || typeof body !== 'object') {
    errors.push('Request body must be a JSON object')
    return { valid: false, errors }
  }

  const bodyObj = body as Record<string, unknown>

  if (!('mode' in bodyObj)) {
    errors.push('mode field is required (process_pending | send_single)')
  } else if (!['process_pending', 'send_single'].includes(String(bodyObj.mode))) {
    errors.push('mode must be "process_pending" or "send_single"')
  }

  if (bodyObj.mode === 'send_single' && !('notification_id' in bodyObj)) {
    errors.push('notification_id is required for send_single mode')
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

// ============================================================================
// PHASE 1: MOCK DISPATCHER
// ============================================================================

/**
 * Phase 1 Mock: Mark notification as sent without actual delivery
 * Used for testing infrastructure and validating workflow
 */
async function processPendingMock(limit: number = 50): Promise<number> {
  try {
    // Fetch pending notifications
    const { data: pending, error: fetchError } = await supabase
      .from('installation_notifications')
      .select('id, channel')
      .eq('status', 'pending')
      .order('created_at', { ascending: true })
      .limit(limit)

    if (fetchError) {
      throw new Error(`Fetch error: ${fetchError.message}`)
    }

    if (!pending || pending.length === 0) {
      console.log('[Phase 1] No pending notifications to process')
      return 0
    }

    // Mark all as sent (Phase 2: actual delivery happens here)
    const ids = pending.map((n) => n.id)
    const { error: updateError } = await supabase
      .from('installation_notifications')
      .update({
        status: 'sent',
        email_sent_at: new Date().toISOString(),
      })
      .in('id', ids)

    if (updateError) {
      throw new Error(`Update error: ${updateError.message}`)
    }

    console.log(`[Phase 1] Marked ${ids.length} notifications as sent (mock)`)
    return ids.length
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : 'Unknown error'
    console.error(`[Phase 1] Error processing pending: ${errMsg}`)
    throw error
  }
}

/**
 * Phase 1 Mock: Send single notification
 * Marks one notification as sent
 */
async function sendSingleMock(notificationId: string): Promise<boolean> {
  try {
    const { error } = await supabase
      .from('installation_notifications')
      .update({
        status: 'sent',
        email_sent_at: new Date().toISOString(),
      })
      .eq('id', notificationId)

    if (error) {
      throw new Error(`Update error: ${error.message}`)
    }

    console.log(`[Phase 1] Marked notification ${notificationId} as sent (mock)`)
    return true
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : 'Unknown error'
    console.error(`[Phase 1] Error sending single: ${errMsg}`)
    throw error
  }
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

async function handleSendNotifications(req: Request): Promise<Response> {
  const headers = {
    'Content-Type': 'application/json',
  }

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return new Response('OK', { status: 200, headers })
  }

  // Only POST allowed
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed. Use POST.' }),
      { status: 405, headers }
    )
  }

  try {
    const body = await req.json()
    const validation = validateRequest(body)

    if (!validation.valid) {
      return new Response(
        JSON.stringify({
          error: 'Validation failed',
          details: validation.errors,
        }),
        { status: 400, headers }
      )
    }

    const request = body as ProcessPendingRequest
    let processed = 0

    // Phase 1: Mock dispatch
    if (request.mode === 'process_pending') {
      processed = await processPendingMock(request.limit || 50)
    } else if (request.mode === 'send_single') {
      const success = await sendSingleMock(request.notification_id!)
      processed = success ? 1 : 0
    }

    return new Response(
      JSON.stringify({
        success: true,
        processed,
        phase: 'Phase 1 - Mock',
        message: 'Phase 1: Notifications marked as sent (Phase 2: actual delivery via Resend/Twilio)',
      }),
      {
        headers,
        status: 200,
      }
    )
  } catch (error) {
    console.error('Error in send-notifications:', error)

    const errorMessage = error instanceof Error ? error.message : 'Unknown error'

    return new Response(
      JSON.stringify({
        error: 'Failed to process notifications',
        details: errorMessage,
        phase: 'Phase 1',
      }),
      { status: 500, headers }
    )
  }
}

// ============================================================================
// DENO SERVE
// ============================================================================

Deno.serve(handleSendNotifications)
