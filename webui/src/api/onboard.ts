/**
 * Onboarding API — wraps POST /admin/agents/create-openclaw
 */
import api from '@/api/client'

export interface CreateOpenClawRequest {
  name: string
  role: 'planner' | 'executor' | 'reviewer' | 'patrol'
  cron_schedule?: string
}

export interface CreateOpenClawResponse {
  role: string
  name: string
  skill_zip_name: string
  registration_token: string
  api_url_hint: string
  openclaw_setup_steps: string[]
}

export const onboardApi = {
  /**
   * Create a new OpenClaw agent and return setup instructions.
   */
  createOpenClaw: (data: CreateOpenClawRequest) =>
    api.post<CreateOpenClawResponse>('/admin/agents/create-openclaw', data),
}
