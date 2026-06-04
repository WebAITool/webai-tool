import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskApi } from '../api/taskApi'
import type { TaskCreate, TaskStatus } from '../types'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskStatus[]>([])
  const currentTask = ref<TaskStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTasks() {
    loading.value = true
    error.value = null
    try {
      tasks.value = await taskApi.listTasks()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id: string) {
    loading.value = true
    error.value = null
    try {
      const task = await taskApi.getTask(id)
      currentTask.value = task
      return task
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: TaskCreate) {
    loading.value = true
    error.value = null
    try {
      const newTask = await taskApi.createTask(data)
      tasks.value.push(newTask)
      return newTask
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(id: string) {
    loading.value = true
    error.value = null
    try {
      await taskApi.deleteTask(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
      if (currentTask.value?.id === id) {
        currentTask.value = null
      }
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { tasks, currentTask, loading, error, fetchTasks, fetchTask, createTask, deleteTask }
})
