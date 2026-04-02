/**
 * Edge Function: Coins Webhook - Bulk Setup
 * Creates initial coin balance records for installers
 *
 * Endpoint: POST /functions/v1/coins-webhook
 *
 * Request Body:
 * {
 *   "user_ids": ["uuid1", "uuid2", ...]
 * }
 *
 * Response:
 * {
 *   "success": true,
 *   "created": number
 * }
 *
 * Purpose:
 * - Initialize installer_coins_balance for new users
 * - Used during onboarding or bulk migration
 * - Idempotent: safe to call multiple times (uses upsert)
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

if (!supabaseUrl || !supabaseServiceKey) {
  throw new Error('Missing Supabase configuration')
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

/**
 * Validates request body format
 */
function validateRequestBody(body: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!body || typeof body !== 'object') {
    errors.push('Request body must be a JSON object')
    return { valid: false, errors }
  }

  const bodyObj = body as Record<string, unknown>

  if (!('user_ids' in bodyObj)) {
    errors.push('user_ids field is required')
  } else if (!Array.isArray(bodyObj.user_ids)) {
    errors.push('user_ids must be an array')
  } else if (bodyObj.user_ids.length === 0) {
    errors.push('user_ids array must not be empty')
  } else if (!bodyObj.user_ids.every((id: unknown) => typeof id === 'string')) {
    errors.push('All user_ids must be strings (UUIDs)')
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

/**
 * Main handler function
 */
async function handleCoinsSetup(req: Request) {
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
    const validation = validateRequestBody(body)

    if (!validation.valid) {
      return new Response(
        JSON.stringify({ error: 'Validation failed', details: validation.errors }),
        { status: 400, headers }
      )
    }

    const userIds = (body as { user_ids: string[] }).user_ids

    // Create balance records for each user
    // Using upsert for idempotency (safe to call multiple times)
    const records = userIds.map((id) => ({
      installer_id: id,
      total_coins: 0,
    }))

    const { error } = await supabase
      .from('installer_coins_balance')
      .upsert(records, { onConflict: 'installer_id' })

    if (error) {
      throw new Error(`Setup error: ${error.message}`)
    }

    return new Response(
      JSON.stringify({
        success: true,
        created: userIds.length,
      }),
      {
        headers,
        status: 201,
      }
    )
  } catch (error) {
    console.error('Error in coins-webhook:', error)

    const errorMessage = error instanceof Error ? error.message : 'Unknown error'

    return new Response(
      JSON.stringify({
        error: 'Failed to setup coin balances',
        details: errorMessage,
      }),
      { status: 500, headers }
    )
  }
}

// Export the handler for Deno
Deno.serve(handleCoinsSetup)
