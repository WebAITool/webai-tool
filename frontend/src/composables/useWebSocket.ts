import { ref } from 'vue'
import type { AgentEvent } from '../types'

// Module-level singleton state — shared across all useWebSocket() callers
const connected = ref(false)
const socket = ref<WebSocket | null>(null)
const reconnectTimer = ref<any>(null)
const reconnectAttempts = ref(0)
const maxReconnectAttempts = 5
const eventHistory = ref<AgentEvent[]>([])
const currentTaskId = ref<string>('')

const onMessage = ref<(event: AgentEvent) => void>(() => {})
const onConnect = ref<() => void>(() => {})
const onDisconnect = ref<() => void>(() => {})

export function useWebSocket() {
  function connect(taskId: string) {
    if (socket.value?.readyState === WebSocket.OPEN) {
      // Already connected — if task changed, reconnect
      if (currentTaskId.value === taskId) return
      disconnect()
    }

    currentTaskId.value = taskId

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/agent/${taskId}`

    socket.value = new WebSocket(wsUrl)

    socket.value.onopen = () => {
      connected.value = true
      reconnectAttempts.value = 0
      onConnect.value()
      console.log('WebSocket connected')
    }

    socket.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const agentEvent = data as AgentEvent
        eventHistory.value.push(agentEvent)
        onMessage.value(agentEvent)
      } catch (e) {
        console.error('Failed to parse WebSocket message', e)
      }
    }

    socket.value.onclose = () => {
      connected.value = false
      onDisconnect.value()
      console.log('WebSocket disconnected')
      attemptReconnect(taskId)
    }

    socket.value.onerror = (error) => {
      console.error('WebSocket error', error)
      socket.value?.close()
    }
  }

  function attemptReconnect(taskId: string) {
    if (reconnectAttempts.value >= maxReconnectAttempts) return

    reconnectAttempts.value++
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)

    console.log(`Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts.value})`)

    reconnectTimer.value = setTimeout(() => {
      connect(taskId)
    }, delay)
  }

  function disconnect() {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
    }
    socket.value?.close()
    socket.value = null
    connected.value = false
    currentTaskId.value = ''
  }

  function clearHistory() {
    eventHistory.value = []
  }

  return { connected, eventHistory, connect, disconnect, clearHistory, onMessage, onConnect, onDisconnect }
}
