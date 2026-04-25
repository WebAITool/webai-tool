import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '../api/agentApi'
import { useWebSocket } from '../composables/useWebSocket'
import type { TaskStatus, AgentEvent } from '../types'

export const useAgentStore = defineStore('agent', () => {
  const status = ref<TaskStatus | null>(null)
  const logs = ref<string>('')
  const events = ref<AgentEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // WebSocket connection
  const { connected, eventHistory, connect, disconnect, clearHistory, onMessage } = useWebSocket()

  // Subscribe to incoming WebSocket events globally
  onMessage.value = (event: AgentEvent) => {
    events.value.push(event)
  }

  async function startAgent(taskId: string) {
    loading.value = true
    error.value = null
    try {
      status.value = await agentApi.startAgent(taskId)
      // Connect to WebSocket for streaming
      connect(taskId)
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function stopAgent(taskId: string) {
    loading.value = true
    error.value = null
    try {
      status.value = await agentApi.stopAgent(taskId)
      disconnect()
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus(taskId: string) {
    loading.value = true
    error.value = null
    try {
      status.value = await agentApi.getStatus(taskId)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchLogs(taskId: string) {
    loading.value = true
    error.value = null
    try {
      logs.value = await agentApi.getLogs(taskId)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchActions(taskId: string) {
    loading.value = true
    error.value = null
    try {
      events.value = await agentApi.getActions(taskId)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function clearEvents() {
    events.value = []
    clearHistory()
  }

  // Computed properties for UI
  const isRunning = computed(() => status.value?.status === 'running')
  const progress = computed(() => {
    if (!status.value) return 0
    return (status.value.step_number / status.value.max_steps) * 100
  })

  return { 
    status, 
    logs, 
    events, 
    loading, 
    error, 
    connected,
    eventHistory,
    startAgent, 
    stopAgent, 
    fetchStatus, 
    fetchLogs, 
    fetchActions,
    clearEvents,
    isRunning,
    progress
  }
})
