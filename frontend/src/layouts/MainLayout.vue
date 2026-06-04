<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useSnackbar } from '../composables/useSnackbar'

const route = useRoute()
const theme = useTheme()
const snackbar = useSnackbar()

const drawer = ref(true)
const rail = ref(false)

const items = computed(() => [
  { title: 'Dashboard', icon: 'mdi-view-dashboard', to: '/' },
  { title: 'Tasks', icon: 'mdi-list-status', to: '/tasks' },
  { title: 'Files', icon: 'mdi-file-tree', to: '/files' },
  { title: 'Settings', icon: 'mdi-cog', to: '/settings' },
])

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}
</script>

<template>
  <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
    >
      <v-list-item
        prepend-avatar="https://api.dicebear.com/7.x/bottts/svg?seed=WebAI"
        :title="rail ? '' : 'WebAI tool'"
        nav
      >
        <template v-slot:append>
          <v-btn
            variant="text"
            icon="mdi-chevron-left"
            @click.stop="rail = !rail"
          ></v-btn>
        </template>
      </v-list-item>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="(item, i) in items"
          :key="i"
          :value="item"
          :to="item.to"
          :active="route.path === item.to"
        >
          <template v-slot:prepend>
            <v-icon :icon="item.icon"></v-icon>
          </template>
          <v-list-item-title v-text="item.title"></v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>

      <v-app-bar-title>WebAI interface</v-app-bar-title>

      <v-spacer></v-spacer>

      <v-btn icon @click="toggleTheme">
        <v-icon>mdi-theme-light-dark</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <v-snackbar
      v-model="snackbar.visible.value"
      :color="snackbar.color.value"
      :timeout="5000"
      location="top"
    >
      {{ snackbar.message.value }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.visible.value = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
</template>
