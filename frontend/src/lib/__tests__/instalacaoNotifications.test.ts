/**
 * Unit Tests for Installation Notifications Module
 * Using Vitest framework
 *
 * Tests cover:
 * - Template validation (all 5 templates)
 * - Variable substitution
 * - renderTemplate function
 * - enviarNotificacao function
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  WHATSAPP_TEMPLATES,
  EMAIL_TEMPLATES,
  renderTemplate,
  enviarNotificacao,
  supabase,
} from '../instalacaoNotifications'

// Mock Supabase
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    from: vi.fn(),
  })),
}))

describe('instalacaoNotifications - Email + WhatsApp Templates', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ============================================================================
  // Template Validation Tests
  // ============================================================================

  describe('Template Structure', () => {
    it('should have all 5 notification types in WHATSAPP_TEMPLATES', () => {
      const templates = Object.keys(WHATSAPP_TEMPLATES)
      expect(templates).toHaveLength(5)
      expect(templates).toContain('AGENDAMENTO')
      expect(templates).toContain('LEMBRETE_24H')
      expect(templates).toContain('CHECKIN')
      expect(templates).toContain('JOB_CONCLUIDO')
      expect(templates).toContain('JOB_CANCELADO')
    })

    it('should have all 5 notification types in EMAIL_TEMPLATES', () => {
      const templates = Object.keys(EMAIL_TEMPLATES)
      expect(templates).toHaveLength(5)
      expect(templates).toContain('AGENDAMENTO')
      expect(templates).toContain('LEMBRETE_24H')
      expect(templates).toContain('CHECKIN')
      expect(templates).toContain('JOB_CONCLUIDO')
      expect(templates).toContain('JOB_CANCELADO')
    })
  })

  describe('Template Variable Requirements', () => {
    it('AGENDAMENTO should contain required variables', () => {
      const template = WHATSAPP_TEMPLATES.AGENDAMENTO
      expect(template).toContain('{{installer_name}}')
      expect(template).toContain('{{job_title}}')
      expect(template).toContain('{{branch}}')
      expect(template).toContain('{{scheduled_date_pt_br}}')
      expect(template).toContain('{{scheduled_time}}')
      expect(template).toContain('{{client_name}}')
    })

    it('LEMBRETE_24H should contain required variables', () => {
      const template = WHATSAPP_TEMPLATES.LEMBRETE_24H
      expect(template).toContain('{{installer_name}}')
      expect(template).toContain('{{job_title}}')
      expect(template).toContain('{{branch}}')
      expect(template).toContain('{{scheduled_time}}')
      expect(template).toContain('{{client_name}}')
    })

    it('CHECKIN should contain required variables', () => {
      const template = WHATSAPP_TEMPLATES.CHECKIN
      expect(template).toContain('{{installer_name}}')
      expect(template).toContain('{{job_title}}')
      expect(template).toContain('{{branch}}')
      expect(template).toContain('{{checkin_time}}')
    })

    it('JOB_CONCLUIDO should contain gamification variable', () => {
      const template = WHATSAPP_TEMPLATES.JOB_CONCLUIDO
      expect(template).toContain('{{coins_earned_msg}}')
      expect(template).toContain('{{total_time_formatted}}')
      expect(template).toContain('{{photo_count}}')
    })

    it('JOB_CANCELADO should contain cancellation reason', () => {
      const template = WHATSAPP_TEMPLATES.JOB_CANCELADO
      expect(template).toContain('{{cancellation_reason}}')
    })

    it('EMAIL templates should have HTML structure', () => {
      const emailTemplate = EMAIL_TEMPLATES.AGENDAMENTO
      expect(emailTemplate).toContain('<h2>')
      expect(emailTemplate).toContain('<p>')
      expect(emailTemplate).toContain('<div')
      expect(emailTemplate).toContain('<a href=')
    })
  })

  // ============================================================================
  // renderTemplate Function Tests
  // ============================================================================

  describe('renderTemplate', () => {
    it('should replace single variable', () => {
      const template = 'Hello {{name}}'
      const result = renderTemplate(template, { name: 'John' })
      expect(result).toBe('Hello John')
    })

    it('should replace multiple variables', () => {
      const template = '{{greeting}} {{name}}, você tem um job em {{branch}}'
      const result = renderTemplate(template, {
        greeting: 'Olá',
        name: 'João',
        branch: 'São Paulo',
      })
      expect(result).toBe('Olá João, você tem um job em São Paulo')
    })

    it('should handle missing variables gracefully', () => {
      const template = 'Hello {{name}}, you have {{count}} jobs'
      const result = renderTemplate(template, { name: 'John' })
      expect(result).toBe('Hello John, you have {{count}} jobs')
    })

    it('should handle empty variables object', () => {
      const template = 'Hello {{name}}'
      const result = renderTemplate(template, {})
      expect(result).toBe('Hello {{name}}')
    })

    it('should convert number values to strings', () => {
      const template = 'You earned {{coins}} coins'
      const result = renderTemplate(template, { coins: 500 })
      expect(result).toBe('You earned 500 coins')
    })

    it('should handle special characters in values', () => {
      const template = 'Client: {{client_name}}'
      const result = renderTemplate(template, {
        client_name: "O'Brien & Associates",
      })
      expect(result).toBe("Client: O'Brien & Associates")
    })

    it('should render AGENDAMENTO template with real data', () => {
      const dados = {
        installer_name: 'João Silva',
        job_title: 'Instalação de Painéis',
        branch: 'São Paulo',
        scheduled_date_pt_br: '31/03/2026',
        scheduled_time: '14:30',
        client_name: 'Acme Corp',
      }
      const result = renderTemplate(WHATSAPP_TEMPLATES.AGENDAMENTO, dados)

      expect(result).toContain('João Silva')
      expect(result).toContain('Instalação de Painéis')
      expect(result).toContain('São Paulo')
      expect(result).toContain('31/03/2026')
      expect(result).toContain('14:30')
      expect(result).toContain('Acme Corp')
      expect(result).not.toContain('{{')
    })

    it('should render JOB_CONCLUIDO template with coins message', () => {
      const dados = {
        installer_name: 'Maria',
        job_title: 'Instalação Grande',
        total_time_formatted: '4h 30m',
        pause_summary: '2 pausas, 15min total',
        photo_count: '12 fotos',
        coins_earned_msg: '🏆 Você ganhou 500 coins!',
      }
      const result = renderTemplate(WHATSAPP_TEMPLATES.JOB_CONCLUIDO, dados)

      expect(result).toContain('Maria')
      expect(result).toContain('4h 30m')
      expect(result).toContain('500 coins')
      expect(result).not.toContain('{{')
    })
  })

  // ============================================================================
  // enviarNotificacao Function Tests
  // ============================================================================

  describe('enviarNotificacao', () => {
    it('should throw error for unknown notification type', async () => {
      const invalidCall = async () => {
        await enviarNotificacao(
          'installer-123',
          'assignment-456',
          'unknown_type' as any,
          {}
        )
      }

      expect(invalidCall()).rejects.toThrow('Unknown notification type')
    })

    it('should default to email channel if not specified', async () => {
      // Mock supabase.from()
      const mockInsert = vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 'notif-123' },
            error: null,
          }),
        }),
      })

      const mockFrom = vi.fn().mockReturnValue({
        insert: mockInsert,
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom)

      const result = await enviarNotificacao(
        'installer-123',
        'assignment-456',
        'agendamento',
        {
          installer_name: 'João',
          job_title: 'Job 1',
          branch: 'SP',
          scheduled_date_pt_br: '31/03/2026',
          scheduled_time: '14:00',
          client_name: 'Client',
        }
      )

      expect(result.status).toBe('queued')
      expect(result.channels).toHaveLength(1)
      expect(result.channels[0].canal).toBe('email')
    })

    it('should support multiple channels', async () => {
      const mockInsert = vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 'notif-123' },
            error: null,
          }),
        }),
      })

      const mockFrom = vi.fn().mockReturnValue({
        insert: mockInsert,
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom)

      const result = await enviarNotificacao(
        'installer-123',
        'assignment-456',
        'agendamento',
        {
          installer_name: 'João',
          job_title: 'Job 1',
          branch: 'SP',
          scheduled_date_pt_br: '31/03/2026',
          scheduled_time: '14:00',
          client_name: 'Client',
        },
        ['email', 'whatsapp']
      )

      expect(result.channels).toHaveLength(2)
      expect(result.channels[0].canal).toBe('email')
      expect(result.channels[1].canal).toBe('whatsapp')
    })

    it('should include message preview in response', async () => {
      const mockInsert = vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 'notif-123' },
            error: null,
          }),
        }),
      })

      const mockFrom = vi.fn().mockReturnValue({
        insert: mockInsert,
      })

      vi.spyOn(supabase, 'from').mockImplementation(mockFrom)

      const result = await enviarNotificacao(
        'installer-123',
        'assignment-456',
        'agendamento',
        {
          installer_name: 'João',
          job_title: 'Job 1',
          branch: 'SP',
          scheduled_date_pt_br: '31/03/2026',
          scheduled_time: '14:00',
          client_name: 'Acme',
        }
      )

      expect(result.message_preview).toBeDefined()
      expect(result.message_preview).toContain('João')
      expect(result.message_preview).toContain('Job 1')
      expect(result.message_preview).toContain('Acme')
    })
  })

  // ============================================================================
  // Template Format Tests
  // ============================================================================

  describe('Template Format & Readability', () => {
    it('WHATSAPP templates should have emoji icons', () => {
      expect(WHATSAPP_TEMPLATES.AGENDAMENTO).toContain('🎯')
      expect(WHATSAPP_TEMPLATES.LEMBRETE_24H).toContain('⏰')
      expect(WHATSAPP_TEMPLATES.CHECKIN).toContain('✅')
      expect(WHATSAPP_TEMPLATES.JOB_CONCLUIDO).toContain('🎉')
      expect(WHATSAPP_TEMPLATES.JOB_CANCELADO).toContain('❌')
    })

    it('Templates should not contain hardcoded HTML tags', () => {
      expect(WHATSAPP_TEMPLATES.AGENDAMENTO).not.toContain('<h2>')
      expect(WHATSAPP_TEMPLATES.LEMBRETE_24H).not.toContain('<p>')
    })

    it('Email templates should contain proper HTML structure', () => {
      expect(EMAIL_TEMPLATES.AGENDAMENTO).toContain('<h2>')
      expect(EMAIL_TEMPLATES.AGENDAMENTO).toContain('<div')
      expect(EMAIL_TEMPLATES.AGENDAMENTO).toContain('<a href=')
    })

    it('Should contain portal link in WhatsApp templates', () => {
      expect(WHATSAPP_TEMPLATES.AGENDAMENTO).toContain(
        'https://visual-connect-tau.vercel.app'
      )
      expect(WHATSAPP_TEMPLATES.LEMBRETE_24H).toContain(
        'https://visual-connect-tau.vercel.app'
      )
    })
  })
})
