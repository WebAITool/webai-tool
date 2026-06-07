<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>My App</v-app-bar-title>
      <template v-slot:append>
        <v-btn
          :icon="theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
          @click="toggleTheme"
        ></v-btn>
      </template>
    </v-app-bar>
    <v-main>
      <v-container>
        <v-card class="pa-4">
          <v-card-title>Welcome</v-card-title>
          <v-card-text>
            This is the main content area.
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="elevated">Action</v-btn>
          </v-card-actions>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { useTheme } from 'vuetify'

const theme = useTheme()

// Initialize from localStorage
const savedTheme = localStorage.getItem('theme')
if (savedTheme) {
  theme.global.name.value = savedTheme
}

function toggleTheme () {
  const newTheme = theme.global.current.value.dark ? 'light' : 'dark'
  theme.global.name.value = newTheme
  localStorage.setItem('theme', newTheme)
}
</script>
