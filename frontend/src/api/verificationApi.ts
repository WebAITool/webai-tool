import client from './client'
import type { VerificationResult } from '../types'

export const verificationApi = {
  async getResults(taskId: string): Promise<VerificationResult[]> {
    const response = await client.get<VerificationResult[]>(`/verification/${taskId}/results`)
    return response.data
  },

  async getScreenshot(taskId: string, route: string): Promise<{ route: string; image_base64: string }> {
    const response = await client.get<{ route: string; image_base64: string }>(`/verification/${taskId}/screenshot/${route}`)
    return response.data
  }
}
