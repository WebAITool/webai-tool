<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import type { TaskStatus } from '../types'

const taskStore = useTaskStore()

const recentTasks = computed(() => taskStore.tasks.slice(0, 5))

onMounted(() => {
  taskStore.fetchTasks()
})
</script>

<template>
  <v-container>
    <h1 class="text-h4 mb-4">Dashboard</h1>
    
    <v-row>
      <v-col cols="12" md="8">
        <v-card class="mb-4">
          <v-card-title>Welcome to WebAI tool</v-card-title>
          <v-card-text>
            <p class="text-body-1">
              This interface allows you to manage AI coding agent tasks. 
              Create new tasks, monitor execution in real-time, and verify generated code.
            </p>
            <v-btn color="primary" class="mt-4" to="/tasks/new">
              <v-icon start>mdi-plus</v-icon>
              Create new task
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title>Recent tasks</v-card-title>
          <v-table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Goal</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="recentTasks.length === 0">
                <td colspan="4" class="text-center">No tasks yet</td>
              </tr>
              <tr v-for="task in recentTasks" :key="task.id">
                <td>{{ task.id.substring(0, 8) }}...</td>
                <td>{{ task.goal.substring(0, 30) }}...</td>
                <td>
                  <v-chip size="small" :color="task.status === 'running' ? 'primary' : 'default'">
                    {{ task.status }}
                  </v-chip>
                </td>
                <td>
                  <v-btn icon size="small" :to="`/tasks/${task.id}`">
                    <v-icon>mdi-eye</v-icon>
                  </v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>System status</v-card-title>
          <v-list>
            <v-list-item>
              <v-list-item-title>Agent status</v-list-item-title>
              <v-list-item-subtitle class="text-success">Available</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Active tasks</v-list-item-title>
              <v-list-item-subtitle>{{ taskStore.tasks.filter((t: TaskStatus) => t.status === 'running').length }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
