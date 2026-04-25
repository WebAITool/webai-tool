import client from './client'
import type { TaskStatus, AgentEvent } from '../types'

export const agentApi = {
  async startAgent(taskId: string): Promise<TaskStatus> {
    const response = await client.post<TaskStatus>(`/agent/${taskId}/start`)
    return response.data
  },

  async stopAgent(taskId: string): Promise<TaskStatus> {
    const response = await client.post<TaskStatus>(`/agent/${taskId}/stop`)
    return response.data
  },

  async getStatus(taskId: string): Promise<TaskStatus> {
    const response = await client.get<TaskStatus>(`/agent/${taskId}/status`)
    return response.data
  },

  async getLogs(taskId: string): Promise<string> {
    const response = await client.get<string>(`/agent/${taskId}/logs`)
    return response.data
  },

  async getActions(taskId: string): Promise<AgentEvent[]> {
    const response = await client.get<AgentEvent[]>(`/agent/${taskId}/actions`)
    return response.data
  }
}
