<script setup lang="ts">
import { useTheme } from 'vuetify'

const theme = useTheme()
// Initialize theme from localStorage or default to dark
const savedTheme = localStorage.getItem('theme') || 'dark'
theme.global.name.value = savedTheme
</script>

<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
