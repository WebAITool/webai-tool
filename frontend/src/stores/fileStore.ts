import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fileApi } from '../api/fileApi'
import type { FileNode } from '../types'

export const useFileStore = defineStore('file', () => {
  const tree = ref<FileNode | null>(null)
  const currentContent = ref<string | null>(null)
  const currentPath = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTree(prjdir: string) {
    loading.value = true
    error.value = null
    try {
      tree.value = await fileApi.getTree(prjdir)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchContent(path: string) {
    loading.value = true
    error.value = null
    currentPath.value = path
    try {
      const res = await fileApi.getContent(path)
      currentContent.value = res.content
    } catch (e: any) {
      error.value = e.message
      currentContent.value = null
    } finally {
      loading.value = false
    }
  }

  function clearContent() {
    currentContent.value = null
    currentPath.value = ''
  }

  return { tree, currentContent, currentPath, loading, error, fetchTree, fetchContent, clearContent }
})
