import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchItems, fetchItem, createItem } from '../api'

export const useItemsStore = defineStore('items', () => {
  // State
  const items = ref([])
  const currentItem = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const itemCount = computed(() => items.value.length)
  const isLoading = computed(() => loading.value)
  const hasError = computed(() => !!error.value)

  // Actions
  async function loadItems() {
    loading.value = true
    error.value = null
    try {
      items.value = await fetchItems()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function loadItem(id) {
    loading.value = true
    error.value = null
    try {
      currentItem.value = await fetchItem(id)
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addItem(data) {
    loading.value = true
    try {
      const newItem = await createItem(data)
      items.value.push(newItem)
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    items,
    currentItem,
    loading,
    error,
    itemCount,
    isLoading,
    hasError,
    loadItems,
    loadItem,
    addItem,
    clearError
  }
})
