<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import { useAgentStore } from '../stores/agentStore'
import type { TaskStatus } from '../types'

const router = useRouter()
const taskStore = useTaskStore()
const agentStore = useAgentStore()

const search = ref('')
const statusFilter = ref('All')

onMounted(() => {
  taskStore.fetchTasks()
})

const filteredTasks = computed(() => {
  return taskStore.tasks.filter(task => {
    const matchesSearch = task.goal.toLowerCase().includes(search.value.toLowerCase())
    const matchesStatus = statusFilter.value === 'All' || task.status === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

async function handleStartStop(task: TaskStatus) {
  if (task.status === 'running') {
    await agentStore.stopAgent(task.id)
  } else {
    await agentStore.startAgent(task.id)
  }
  await taskStore.fetchTasks()
}

async function handleDelete(id: string) {
  if (confirm('Are you sure you want to delete this task?')) {
    await taskStore.deleteTask(id)
  }
}
</script>

<template>
  <v-container>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h4">Tasks</h1>
      <v-btn color="primary" to="/tasks/new">
        <v-icon start>mdi-plus</v-icon>
        New task
      </v-btn>
    </div>

    <v-card>
      <v-toolbar flat>
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
          variant="solo-filled"
          flat
          class="ml-2"
          style="max-width: 300px"
        ></v-text-field>
        
        <v-spacer></v-spacer>
        
        <v-select
          v-model="statusFilter"
          :items="['All', 'pending', 'running', 'completed', 'failed', 'stopped']"
          label="Status"
          hide-details
          variant="solo-filled"
          flat
          style="max-width: 150px"
        ></v-select>
      </v-toolbar>

      <v-table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Goal</th>
            <th>Status</th>
            <th>Steps</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in filteredTasks" :key="task.id" style="cursor: pointer" @click="router.push(`/tasks/${task.id}`)">
            <td>{{ task.id.substring(0, 8) }}...</td>
            <td>{{ task.goal.substring(0, 40) }}...</td>
            <td>
              <v-chip size="small" :color="task.status === 'running' ? 'primary' : task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : task.status === 'stopped' ? 'orange' : 'grey'">
                {{ task.status }}
              </v-chip>
            </td>
            <td>{{ task.step_number }} / {{ task.max_steps }}</td>
            <td>{{ new Date(task.created_at).toLocaleString() }}</td>
            <td @click.stop>
              <v-btn icon size="small" :loading="agentStore.loading" @click="handleStartStop(task)">
                <v-icon>{{ task.status === 'running' ? 'mdi-stop' : 'mdi-play' }}</v-icon>
              </v-btn>
              <v-btn icon size="small" color="error" @click="handleDelete(task.id)">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      
      <div v-if="filteredTasks.length === 0" class="text-center pa-4">
        No tasks found.
      </div>
    </v-card>
  </v-container>
</template>
