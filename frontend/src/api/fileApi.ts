import client from './client'
import type { FileNode } from '../types'

export const fileApi = {
  async getTree(prjdir: string): Promise<FileNode> {
    const response = await client.get<FileNode>('/files/tree', { params: { prjdir } })
    return response.data
  },

  async getContent(path: string): Promise<{ content: string; path: string }> {
    const response = await client.get<{ content: string; path: string }>('/files/content', { params: { path } })
    return response.data
  },

  getDownloadUrl(path: string): string {
    return `${client.defaults.baseURL}/files/download?path=${encodeURIComponent(path)}`
  }
}
