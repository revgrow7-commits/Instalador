/**
 * Installation Notifications Module
 * Email + WhatsApp templates and dispatcher
 *
 * Phase 1: Infrastructure (templates, DB records, mock dispatch)
 * Phase 2: Real integration (Resend for email, Twilio for WhatsApp, pg_cron scheduler)
 *
 * Templates support variable substitution: {{variable_name}}
 * Channels: email, whatsapp
 * Types: agendamento, lembrete_24h, checkin, job_concluido, job_cancelado
 */

import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || ''
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseKey)

/**
 * WhatsApp + Email templates for all notification types
 * Each template uses {{variable}} syntax for substitution
 */
export const WHATSAPP_TEMPLATES = {
  AGENDAMENTO: `🎯 Novo Job Agendado!
Olá {{installer_name}}!
Você tem um novo job agendado:
📋 **{{job_title}}**
📍 Filial: {{branch}}
📅 Data: {{scheduled_date_pt_br}}
⏰ Horário: {{scheduled_time}}
👤 Cliente: {{client_name}}
Acesse seu painel: https://visual-connect-tau.vercel.app/instalacao/jobs`,

  LEMBRETE_24H: `⏰ Lembrete: Job amanhã!
Olá {{installer_name}},
Amanhã você tem instalação agendada:
📋 **{{job_title}}**
📍 Filial: {{branch}}
📅 Horário: {{scheduled_time}}
👤 Cliente: {{client_name}}
Acesse seu painel: https://visual-connect-tau.vercel.app/instalacao/jobs`,

  CHECKIN: `✅ Você fez check-in!
Olá {{installer_name}},
Check-in realizado com sucesso:
📋 **{{job_title}}**
📍 Filial: {{branch}}
🕐 Hora: {{checkin_time}}
Comece o trabalho! 💪`,

  JOB_CONCLUIDO: `🎉 Job Concluído!
Olá {{installer_name}},
Parabéns! Seu job foi concluído com sucesso:
📋 **{{job_title}}**
⏱️ Tempo total: {{total_time_formatted}}
⏸️ Pausas: {{pause_summary}}
📸 Fotos: {{photo_count}}
{{coins_earned_msg}}
Até o próximo! 🚀`,

  JOB_CANCELADO: `❌ Job Cancelado
Olá {{installer_name}},
O seguinte job foi cancelado:
📋 **{{job_title}}**
📅 Data: {{scheduled_date_pt_br}}
Motivo: {{cancellation_reason}}`,
}

/**
 * Email templates (HTML format)
 * Same variables as WhatsApp but with richer formatting
 */
export const EMAIL_TEMPLATES = {
  AGENDAMENTO: `
    <h2>🎯 Novo Job Agendado!</h2>
    <p>Olá <strong>{{installer_name}}</strong>,</p>
    <p>Você tem um novo job agendado:</p>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
      <p><strong>📋 {{job_title}}</strong></p>
      <p>📍 Filial: {{branch}}</p>
      <p>📅 Data: {{scheduled_date_pt_br}}</p>
      <p>⏰ Horário: {{scheduled_time}}</p>
      <p>👤 Cliente: {{client_name}}</p>
    </div>
    <p><a href="https://visual-connect-tau.vercel.app/instalacao/jobs">Acesse seu painel</a></p>
  `,

  LEMBRETE_24H: `
    <h2>⏰ Lembrete: Job amanhã!</h2>
    <p>Olá <strong>{{installer_name}}</strong>,</p>
    <p>Amanhã você tem instalação agendada:</p>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
      <p><strong>📋 {{job_title}}</strong></p>
      <p>📍 Filial: {{branch}}</p>
      <p>⏰ Horário: {{scheduled_time}}</p>
      <p>👤 Cliente: {{client_name}}</p>
    </div>
    <p><a href="https://visual-connect-tau.vercel.app/instalacao/jobs">Acesse seu painel</a></p>
  `,

  CHECKIN: `
    <h2>✅ Você fez check-in!</h2>
    <p>Olá <strong>{{installer_name}}</strong>,</p>
    <p>Check-in realizado com sucesso:</p>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
      <p><strong>📋 {{job_title}}</strong></p>
      <p>📍 Filial: {{branch}}</p>
      <p>🕐 Hora: {{checkin_time}}</p>
    </div>
    <p>Comece o trabalho! 💪</p>
  `,

  JOB_CONCLUIDO: `
    <h2>🎉 Job Concluído!</h2>
    <p>Olá <strong>{{installer_name}}</strong>,</p>
    <p>Parabéns! Seu job foi concluído com sucesso:</p>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
      <p><strong>📋 {{job_title}}</strong></p>
      <p>⏱️ Tempo total: {{total_time_formatted}}</p>
      <p>⏸️ Pausas: {{pause_summary}}</p>
      <p>📸 Fotos: {{photo_count}}</p>
      <p>{{coins_earned_msg}}</p>
    </div>
    <p>Até o próximo! 🚀</p>
  `,

  JOB_CANCELADO: `
    <h2>❌ Job Cancelado</h2>
    <p>Olá <strong>{{installer_name}}</strong>,</p>
    <p>O seguinte job foi cancelado:</p>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
      <p><strong>📋 {{job_title}}</strong></p>
      <p>📅 Data: {{scheduled_date_pt_br}}</p>
      <p>Motivo: {{cancellation_reason}}</p>
    </div>
  `,
}

/**
 * Notification type enumeration
 */
export type NotificationType =
  | 'agendamento'
  | 'lembrete_24h'
  | 'checkin'
  | 'job_concluido'
  | 'job_cancelado'

/**
 * Notification channel enumeration
 */
export type NotificationChannel = 'email' | 'whatsapp'

/**
 * Sends a notification to an installer via email and/or WhatsApp
 *
 * Phase 1: Creates records in installation_notifications table
 * Phase 2: Actually sends via Resend (email) and Twilio (WhatsApp)
 *
 * @param installerId - UUID of the installer
 * @param assignmentId - UUID of the job assignment
 * @param tipo - Notification type (agendamento, lembrete_24h, etc.)
 * @param dados - Data object with template variables
 * @param canais - Channels to send to (default: ['email'])
 * @returns Object with message preview and status
 * @throws Error if database insert fails
 */
export async function enviarNotificacao(
  installerId: string,
  assignmentId: string,
  tipo: NotificationType,
  dados: Record<string, any>,
  canais: NotificationChannel[] = ['email']
) {
  const templateKey = tipo.toUpperCase() as keyof typeof WHATSAPP_TEMPLATES
  const whatsappTemplate = WHATSAPP_TEMPLATES[templateKey]
  const emailTemplate = EMAIL_TEMPLATES[templateKey]

  if (!whatsappTemplate || !emailTemplate) {
    throw new Error(`Unknown notification type: ${tipo}`)
  }

  const whatsappMsg = renderTemplate(whatsappTemplate, dados)
  const emailMsg = renderTemplate(emailTemplate, dados)

  const results = []

  for (const canal of canais) {
    try {
      const { data, error } = await supabase.from('installation_notifications').insert({
        installer_id: installerId,
        assignment_id: assignmentId,
        email_type: tipo,
        channel: canal,
        email_data: dados,
        email_subject: `[${tipo.toUpperCase()}] ${dados.job_title || 'Notificação'}`,
        email_html: emailMsg,
        whatsapp_body: whatsappMsg,
        status: 'pending',
      }).select().single()

      if (error) {
        console.error(`Error inserting ${canal} notification: ${error.message}`)
        results.push({ canal, status: 'error', error: error.message })
      } else {
        results.push({ canal, status: 'queued', id: data?.id })
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error'
      results.push({ canal, status: 'error', error: errMsg })
    }
  }

  return {
    message_preview: whatsappMsg,
    channels: results,
    status: results.every((r) => r.status !== 'error') ? 'queued' : 'partial_error',
  }
}

/**
 * Render template by replacing {{variable}} placeholders with actual values
 *
 * @param template - Template string with {{variable}} placeholders
 * @param variables - Object with variable values
 * @returns Rendered string with variables substituted
 */
export function renderTemplate(template: string, variables: Record<string, any>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    const value = variables[key]
    return value !== undefined ? String(value) : `{{${key}}}`
  })
}

/**
 * Mark notification as sent after successful delivery
 *
 * Phase 1: Manual update after mock dispatch
 * Phase 2: Automatic update after actual delivery
 *
 * @param notificationId - UUID of the notification record
 * @returns Result from Supabase update
 */
export async function marcarComoEnviado(notificationId: string) {
  return supabase
    .from('installation_notifications')
    .update({
      status: 'sent',
      email_sent_at: new Date().toISOString(),
    })
    .eq('id', notificationId)
}

/**
 * Mark notification as failed if delivery error occurs
 *
 * @param notificationId - UUID of the notification record
 * @param errorMessage - Error details
 * @returns Result from Supabase update
 */
export async function marcarComoFalhado(notificationId: string, errorMessage: string) {
  return supabase
    .from('installation_notifications')
    .update({
      status: 'failed',
      error_message: errorMessage,
      failed_at: new Date().toISOString(),
    })
    .eq('id', notificationId)
}

/**
 * Get pending notifications for processing
 *
 * @param limit - Max notifications to fetch (default: 50)
 * @returns Array of pending notification records
 */
export async function obterNotificacoesPendentes(limit: number = 50) {
  const { data, error } = await supabase
    .from('installation_notifications')
    .select('*')
    .eq('status', 'pending')
    .order('created_at', { ascending: true })
    .limit(limit)

  if (error) {
    throw new Error(`Error fetching pending notifications: ${error.message}`)
  }

  return data || []
}

/**
 * Get notification history for an installer
 *
 * @param installerId - UUID of the installer
 * @param limit - Max notifications to fetch (default: 20)
 * @returns Array of notification records ordered by most recent
 */
export async function obterHistoricoNotificacoes(installerId: string, limit: number = 20) {
  const { data, error } = await supabase
    .from('installation_notifications')
    .select('*')
    .eq('installer_id', installerId)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Error fetching notification history: ${error.message}`)
  }

  return data || []
}

export default {
  enviarNotificacao,
  renderTemplate,
  marcarComoEnviado,
  marcarComoFalhado,
  obterNotificacoesPendentes,
  obterHistoricoNotificacoes,
  WHATSAPP_TEMPLATES,
  EMAIL_TEMPLATES,
}
