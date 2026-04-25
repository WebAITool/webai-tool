import { defineStore } from 'pinia'
import { ref } from 'vue'
import { verificationApi } from '../api/verificationApi'
import type { VerificationResult } from '../types'

export const useVerificationStore = defineStore('verification', () => {
  const results = ref<VerificationResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchResults(taskId: string) {
    loading.value = true
    error.value = null
    try {
      results.value = await verificationApi.getResults(taskId)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { results, loading, error, fetchResults }
})
