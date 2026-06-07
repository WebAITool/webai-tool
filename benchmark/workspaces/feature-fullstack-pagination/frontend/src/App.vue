<template>
  <div>
    <h1>Items</h1>
    <ul>
      <li v-for="item in items" :key="item.id">
        {{ item.name }} - ${{ item.price }}
      </li>
    </ul>
    <div class="pagination">
      <button :disabled="page <= 1" @click="prevPage">Previous</button>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="nextPage">Next</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const items = ref([])
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
const totalPages = ref(0)

async function fetchItems() {
  const res = await fetch(`/api/items?page=${page.value}&per_page=${perPage.value}`)
  const data = await res.json()
  items.value = data.items
  total.value = data.total
  totalPages.value = data.total_pages
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    fetchItems()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    fetchItems()
  }
}

onMounted(() => {
  fetchItems()
})
</script>

<style scoped>
.pagination {
  margin-top: 1em;
  display: flex;
  gap: 1em;
  align-items: center;
}
</style>
