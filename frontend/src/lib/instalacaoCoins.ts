/**
 * Gamification Coins Module
 * Handles coin credits, balance queries, and transaction history
 *
 * Coins are awarded based on productivity:
 * - 10 coins per m² of installation area
 *
 * Integration points:
 * - Called after checkout with area_m2 from installation_checklists
 * - Maintains audit trail in coins_transactions
 * - Auto-creates balance record on first access
 */

import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || ''
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseKey)

/**
 * Credits coins based on installation productivity (area in m²)
 *
 * @param installerId - UUID of the installer
 * @param checkinId - UUID of the related installation checklist
 * @param areaMeter2 - Area installed in square meters
 * @returns Object with coins_earned and transaction_id
 * @throws Error if transaction or balance update fails
 */
export async function creditarMoedasPorProdutividade(
  installerId: string,
  checkinId: string,
  areaMeter2: number
): Promise<{ coins_earned: number; transaction_id: string }> {
  // Calculate coins: 10 coins per m²
  const coinsEarned = Math.round(areaMeter2 * 10)

  // Insert transaction record for audit trail
  const { data: transaction, error: txError } = await supabase
    .from('coins_transactions')
    .insert({
      installer_id: installerId,
      amount: coinsEarned,
      reason: 'checkout_productivity',
      related_checklist_id: checkinId,
    })
    .select()
    .single()

  if (txError) {
    throw new Error(`Transaction error: ${txError.message}`)
  }

  // Get current balance
  const { data: balance, error: balanceError } = await supabase
    .from('installer_coins_balance')
    .select('total_coins')
    .eq('installer_id', installerId)
    .single()

  if (balanceError && balanceError.code !== 'PGRST116') {
    throw new Error(`Balance query error: ${balanceError.message}`)
  }

  const newTotal = (balance?.total_coins || 0) + coinsEarned

  // Update balance
  const { error: updateError } = await supabase
    .from('installer_coins_balance')
    .upsert({
      installer_id: installerId,
      total_coins: newTotal,
      updated_at: new Date().toISOString(),
    })

  if (updateError) {
    throw new Error(`Update error: ${updateError.message}`)
  }

  return {
    coins_earned: coinsEarned,
    transaction_id: transaction.id,
  }
}

/**
 * Retrieves the current coin balance for an installer
 * Auto-creates balance record if it doesn't exist
 *
 * @param installerId - UUID of the installer
 * @returns Total coins balance (integer)
 * @throws Error if query fails
 */
export async function obterSaldoMoedas(installerId: string): Promise<number> {
  const { data, error } = await supabase
    .from('installer_coins_balance')
    .select('total_coins')
    .eq('installer_id', installerId)
    .single()

  // If not found (PGRST116), create new balance with 0 coins
  if (error && error.code === 'PGRST116') {
    await supabase.from('installer_coins_balance').insert({
      installer_id: installerId,
      total_coins: 0,
    })
    return 0
  }

  if (error) {
    throw new Error(`Error: ${error.message}`)
  }

  return data?.total_coins || 0
}

/**
 * Retrieves transaction history for an installer
 * Returns most recent transactions first
 *
 * @param installerId - UUID of the installer
 * @param limit - Maximum number of transactions to return (default: 10)
 * @returns Array of transaction objects
 * @throws Error if query fails
 */
export async function obterHistoricoMoedas(
  installerId: string,
  limit: number = 10
): Promise<any[]> {
  const { data, error } = await supabase
    .from('coins_transactions')
    .select('*')
    .eq('installer_id', installerId)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Error: ${error.message}`)
  }

  return data || []
}

export default {
  creditarMoedasPorProdutividade,
  obterSaldoMoedas,
  obterHistoricoMoedas,
}
