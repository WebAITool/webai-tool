import client from './client'

export interface SettingsData {
  api_key: string
  api_base_url: string
  model_name: string
  max_steps: number
  patience: number
  action_memory: boolean
  enable_frontend_verify: boolean
  headless_mode: boolean
  verify_port: number
}

export const settingsApi = {
  async get(): Promise<SettingsData> {
    const response = await client.get<SettingsData>('/settings')
    return response.data
  },

  async save(data: SettingsData): Promise<SettingsData> {
    const response = await client.put<SettingsData>('/settings', data)
    return response.data
  },

  async testConnection(data: SettingsData): Promise<{ success: boolean; message: string }> {
    const response = await client.post<{ success: boolean; message: string }>('/settings/test-connection', data)
    return response.data
  }
}
