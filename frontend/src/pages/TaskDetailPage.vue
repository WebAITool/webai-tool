<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import { useAgentStore } from '../stores/agentStore'
import { useWebSocket } from '../composables/useWebSocket'
import type { AgentEvent } from '../types'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const agentStore = useAgentStore()

const taskId = route.params.id as string
const eventsContainer = ref<HTMLElement | null>(null)
const logsDialog = ref(false)
const logsLoading = ref(false)

// WebSocket Setup
const { connected, connect, disconnect, onMessage } = useWebSocket()

onMounted(async () => {
  await taskStore.fetchTask(taskId)
  await agentStore.fetchStatus(taskId)
  
  // Set up WebSocket listener
  onMessage.value = (event: AgentEvent) => {
    agentStore.events.push(event)
    scrollToBottom()
  }

  if (agentStore.isRunning) {
    connect(taskId)
  }
})

onUnmounted(() => {
  disconnect()
})

function scrollToBottom() {
  nextTick(() => {
    if (eventsContainer.value) {
      eventsContainer.value.scrollTop = eventsContainer.value.scrollHeight
    }
  })
}

async function toggleAgent() {
  if (agentStore.isRunning) {
    await agentStore.stopAgent(taskId)
  } else {
    await agentStore.startAgent(taskId)
  }
  await taskStore.fetchTask(taskId)
}

async function openLogs() {
  logsDialog.value = true
  logsLoading.value = true
  try {
    await agentStore.fetchLogs(taskId)
  } finally {
    logsLoading.value = false
  }
}

function getIconForType(type: string) {
  switch(type) {
    case 'thinking': return 'mdi-lightbulb'
    case 'code_writing': return 'mdi-code-tags'
    case 'code_executing': return 'mdi-play'
    case 'frontend_verify': return 'mdi-eye'
    case 'goal_achieved': return 'mdi-check-circle'
    case 'error': return 'mdi-alert-circle'
    case 'screenshot': return 'mdi-image'
    case 'state_check': return 'mdi-magnify'
    default: return 'mdi-information'
  }
}
</script>

<template>
  <v-container class="fill-height" fluid v-if="taskStore.currentTask">
    <v-row>
      <!-- Main Event Stream -->
      <v-col cols="12" md="8">
        <v-card height="80vh" class="d-flex flex-column">
          <v-toolbar>
            <v-toolbar-title>Execution log</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-chip :color="connected ? 'success' : 'error'" size="small">
              {{ connected ? 'Connected' : 'Disconnected' }}
            </v-chip>
          </v-toolbar>
          
          <v-divider></v-divider>
          
          <div ref="eventsContainer" style="flex: 1; overflow-y: auto; padding: 1rem; background: #1e1e1e;">
            <div v-if="agentStore.events.length === 0" class="text-grey text-center mt-10">
              Waiting for events...
            </div>
            
            <v-card v-for="(event, index) in agentStore.events" :key="index" class="mb-2" :color="event.event_type === 'error' ? 'error' : 'default'" variant="tonal">
              <v-card-subtitle class="d-flex align-center">
                <v-icon :icon="getIconForType(event.event_type)" class="mr-2"></v-icon>
                {{ event.event_type }}
                <v-spacer></v-spacer>
                <small>{{ new Date(event.timestamp).toLocaleTimeString() }}</small>
              </v-card-subtitle>
              
              <v-card-text v-if="event.event_type === 'thinking'">
                <strong>Plan:</strong> {{ event.data.plan }}<br>
                <strong>Recap:</strong> {{ event.data.recap }}
              </v-card-text>
              
              <v-card-text v-else-if="event.event_type === 'code_writing'">
                <pre class="mt-2">{{ event.data.code }}</pre>
              </v-card-text>
              
              <v-card-text v-else-if="event.event_type === 'code_executing'" :class="event.data.success ? 'text-success' : 'text-error'">
                <pre>{{ event.data.output }}</pre>
              </v-card-text>

              <v-card-text v-else-if="event.event_type === 'screenshot'">
                 <v-img :src="'data:image/png;base64,' + event.data.image_base64" max-width="200" contain></v-img>
                 <p class="mt-2">Route: {{ event.data.route }}</p>
              </v-card-text>
              
              <v-card-text v-else>
                {{ JSON.stringify(event.data) }}
              </v-card-text>
            </v-card>
          </div>
          
          <v-divider></v-divider>
          
          <v-card-actions>
            <v-btn @click="openLogs">
              <v-icon start>mdi-text-box</v-icon> View full logs
            </v-btn>
            <v-btn @click="router.push(`/files?prjdir=${taskStore.currentTask.prjdir}`)">
              <v-icon start>mdi-folder</v-icon> Browse files
            </v-btn>
            <v-btn @click="router.push(`/verification/${taskId}`)">
              <v-icon start>mdi-camera</v-icon> Screenshots
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <!-- Sidebar -->
      <v-col cols="12" md="4">
        <v-card class="mb-4">
          <v-card-title>Task details</v-card-title>
          <v-card-text>
            <p><strong>Goal:</strong> {{ taskStore.currentTask.goal }}</p>
            <v-progress-linear 
              :model-value="agentStore.progress" 
              color="primary" 
              height="25"
              class="mt-2"
            >
              <template v-slot:default="{ value }">
                <strong>{{ Math.ceil(value) }}%</strong>
              </template>
            </v-progress-linear>
            <p class="mt-2">Step {{ taskStore.currentTask.step_number }} of {{ taskStore.currentTask.max_steps }}</p>
            
            <v-btn 
              block 
              :color="agentStore.isRunning ? 'error' : 'success'" 
              @click="toggleAgent"
              class="mt-4"
            >
              {{ agentStore.isRunning ? 'Stop Agent' : 'Start Agent' }}
            </v-btn>
          </v-card-text>
        </v-card>
        
        <v-card>
          <v-card-title>Current state</v-card-title>
          <v-list>
            <v-list-item>
              <v-list-item-title>Status</v-list-item-title>
              <v-list-item-subtitle>{{ taskStore.currentTask.status }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Current step</v-list-item-title>
              <v-list-item-subtitle>{{ taskStore.currentTask.current_step }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <!-- Full Logs Dialog -->
    <v-dialog v-model="logsDialog" max-width="80%">
      <v-card>
        <v-toolbar flat>
          <v-toolbar-title>Full execution logs</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon variant="text" @click="logsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>
        <v-divider></v-divider>
        <v-card-text class="pa-0">
          <div v-if="logsLoading" class="d-flex justify-center pa-10">
            <v-progress-circular indeterminate></v-progress-circular>
          </div>
          <div v-else style="max-height: 70vh; overflow-y: auto; padding: 16px;">
            <pre style="white-space: pre-wrap; word-break: break-word; font-family: monospace; font-size: 0.85rem; margin: 0;">{{ agentStore.logs || 'No logs available.' }}</pre>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
  <v-container v-else>
    <v-progress-circular indeterminate></v-progress-circular>
  </v-container>
</template>
