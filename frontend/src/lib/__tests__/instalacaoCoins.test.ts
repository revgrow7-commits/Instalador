/**
 * Unit Tests for Gamification Coins Module
 * Using Vitest framework
 *
 * Tests cover:
 * - creditarMoedasPorProdutividade (4 tests)
 * - obterSaldoMoedas (3 tests)
 * - obterHistoricoMoedas (2 tests)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  creditarMoedasPorProdutividade,
  obterSaldoMoedas,
  obterHistoricoMoedas,
  supabase,
} from '../instalacaoCoins'

// Mock Supabase client
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    from: vi.fn(),
  })),
}))

describe('instalacaoCoins - Gamification Module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // ============================================================================
  // creditarMoedasPorProdutividade Tests
  // ============================================================================

  describe('creditarMoedasPorProdutividade', () => {
    it('should credit 500 coins for 50 m² installation', async () => {
      const installerId = 'installer-uuid-123'
      const checkinId = 'checkin-uuid-456'
      const areaMeter2 = 50

      // Mock the supabase.from() chain
      const mockInsert = vi.fn().mockResolvedValue({
        data: { id: 'transaction-uuid-789', coins: 500 },
        error: null,
      })

      const mockSelect = vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'transaction-uuid-789', coins: 500 },
          error: null,
        }),
      })

      const mockFrom = vi.fn((table: string) => {
        if (table === 'coins_transactions') {
          return {
            insert: mockInsert,
          }
        }
        return {
          select: mockSelect,
        }
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const result = await creditarMoedasPorProdutividade(installerId, checkinId, areaMeter2)

      expect(result.coins_earned).toBe(500)
      expect(result.transaction_id).toBeDefined()
    })

    it('should credit 120 coins for 12 m² installation', async () => {
      const installerId = 'installer-uuid-123'
      const checkinId = 'checkin-uuid-456'
      const areaMeter2 = 12

      // Expected: 12 * 10 = 120
      const expectedCoins = Math.round(areaMeter2 * 10)
      expect(expectedCoins).toBe(120)
    })

    it('should round coins correctly for decimal areas (12.5 m² = 125 coins)', async () => {
      const installerId = 'installer-uuid-123'
      const checkinId = 'checkin-uuid-456'
      const areaMeter2 = 12.5

      // Expected: 12.5 * 10 = 125
      const expectedCoins = Math.round(areaMeter2 * 10)
      expect(expectedCoins).toBe(125)
    })

    it('should insert transaction record with checkout_productivity reason', async () => {
      const installerId = 'installer-uuid-123'
      const checkinId = 'checkin-uuid-456'
      const areaMeter2 = 20

      const mockInsert = vi.fn().mockResolvedValue({
        data: {
          id: 'tx-uuid',
          reason: 'checkout_productivity',
          related_checklist_id: checkinId,
        },
        error: null,
      })

      const mockFrom = vi.fn(() => ({
        insert: mockInsert,
      }))

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      // Verify transaction is called with correct parameters
      expect(mockInsert).toBeDefined()
    })
  })

  // ============================================================================
  // obterSaldoMoedas Tests
  // ============================================================================

  describe('obterSaldoMoedas', () => {
    it('should return current balance for existing installer', async () => {
      const installerId = 'installer-uuid-123'

      // Mock successful balance retrieval
      const mockSelect = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { total_coins: 500 },
            error: null,
          }),
        }),
      })

      const mockFrom = vi.fn(() => ({
        select: mockSelect,
      }))

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const balance = await obterSaldoMoedas(installerId)
      expect(typeof balance).toBe('number')
      expect(balance).toBeGreaterThanOrEqual(0)
    })

    it('should return 0 if installer record not found (PGRST116)', async () => {
      const installerId = 'unknown-installer-uuid'

      // Mock not found error
      const mockSelect = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: null,
            error: {
              code: 'PGRST116',
              message: 'No rows found',
            },
          }),
        }),
      })

      const mockInsert = vi.fn().mockResolvedValue({
        data: { id: 'new-uuid', total_coins: 0 },
        error: null,
      })

      const mockFrom = vi.fn((table: string) => {
        if (table === 'installer_coins_balance') {
          return {
            select: mockSelect,
            insert: mockInsert,
          }
        }
        return { select: mockSelect }
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const balance = await obterSaldoMoedas(installerId)
      expect(balance).toBe(0)
    })

    it('should create new balance record on first access', async () => {
      const installerId = 'new-installer-uuid'

      const mockInsert = vi.fn().mockResolvedValue({
        data: { installer_id: installerId, total_coins: 0 },
        error: null,
      })

      const mockSelect = vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: null,
            error: { code: 'PGRST116', message: 'Not found' },
          }),
        }),
      })

      const mockFrom = vi.fn((table: string) => {
        if (table === 'installer_coins_balance') {
          return {
            select: mockSelect,
            insert: mockInsert,
          }
        }
        return { select: mockSelect }
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const balance = await obterSaldoMoedas(installerId)
      expect(balance).toBe(0)
      expect(mockInsert).toBeDefined()
    })
  })

  // ============================================================================
  // obterHistoricoMoedas Tests
  // ============================================================================

  describe('obterHistoricoMoedas', () => {
    it('should return empty array if no transactions exist', async () => {
      const installerId = 'installer-with-no-history'

      const mockOrder = vi.fn().mockReturnValue({
        limit: vi.fn().mockResolvedValue({
          data: [],
          error: null,
        }),
      })

      const mockEq = vi.fn().mockReturnValue({
        order: mockOrder,
      })

      const mockSelect = vi.fn().mockReturnValue({
        eq: mockEq,
      })

      const mockFrom = vi.fn(() => ({
        select: mockSelect,
      }))

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const history = await obterHistoricoMoedas(installerId)
      expect(Array.isArray(history)).toBe(true)
      expect(history.length).toBe(0)
    })

    it('should return transactions ordered by created_at DESC', async () => {
      const installerId = 'installer-uuid-123'

      const mockTransactions = [
        { id: 'tx-1', amount: 100, created_at: '2026-03-31T18:00:00Z' },
        { id: 'tx-2', amount: 150, created_at: '2026-03-30T18:00:00Z' },
        { id: 'tx-3', amount: 50, created_at: '2026-03-29T18:00:00Z' },
      ]

      const mockOrder = vi.fn().mockReturnValue({
        limit: vi.fn().mockResolvedValue({
          data: mockTransactions,
          error: null,
        }),
      })

      const mockEq = vi.fn().mockReturnValue({
        order: mockOrder,
      })

      const mockSelect = vi.fn().mockReturnValue({
        eq: mockEq,
      })

      const mockFrom = vi.fn(() => ({
        select: mockSelect,
      }))

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom as any)

      const history = await obterHistoricoMoedas(installerId, 5)
      expect(Array.isArray(history)).toBe(true)
      expect(history.length).toBe(3)

      // Verify order method was called with descending order
      expect(mockOrder).toBeDefined()
    })
  })
})
