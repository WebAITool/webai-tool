import client from './client'
import type { TaskCreate, TaskStatus } from '../types'

export const taskApi = {
  async listTasks(): Promise<TaskStatus[]> {
    const response = await client.get<TaskStatus[]>('/tasks')
    return response.data
  },

  async getTask(id: string): Promise<TaskStatus> {
    const response = await client.get<TaskStatus>(`/tasks/${id}`)
    return response.data
  },

  async createTask(data: TaskCreate): Promise<TaskStatus> {
    const response = await client.post<TaskStatus>('/tasks', data)
    return response.data
  },

  async deleteTask(id: string): Promise<void> {
    await client.delete(`/tasks/${id}`)
  }
}
