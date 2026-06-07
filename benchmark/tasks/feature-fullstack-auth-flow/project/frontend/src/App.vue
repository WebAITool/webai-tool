<template>
  <v-app>
    <v-container>
      <h1>Items</h1>
      <v-list v-if="items.length">
        <v-list-item v-for="item in items" :key="item.id">
          <v-list-item-title>{{ item.name }}</v-list-item-title>
        </v-list-item>
      </v-list>
      <p v-else>Loading...</p>
    </v-container>
  </v-app>
</template>

<script>
export default {
  data() {
    return { items: [] }
  },
  async mounted() {
    const res = await fetch('http://localhost:8000/api/items')
    this.items = await res.json()
  }
}
</script>