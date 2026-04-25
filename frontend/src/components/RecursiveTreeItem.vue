<script setup lang="ts">
import { ref } from 'vue'
import type { FileNode } from '../types'

const props = defineProps<{ item: FileNode }>()
const emit = defineEmits<{ select: [item: FileNode] }>()

const isOpen = ref(false)

function handleClick() {
  if (props.item.is_directory) {
    isOpen.value = !isOpen.value
  } else {
    emit('select', props.item)
  }
}
</script>

<template>
  <div>
    <v-list-item @click="handleClick">
      <template v-slot:prepend>
        <v-icon>{{ item.is_directory ? (isOpen ? 'mdi-folder-open' : 'mdi-folder') : 'mdi-file-document-outline' }}</v-icon>
      </template>
      <v-list-item-title>{{ item.name }}</v-list-item-title>
      <template v-slot:append v-if="!item.is_directory && item.size">
        <span class="text-caption text-grey">{{ (item.size / 1024).toFixed(1) }} KB</span>
      </template>
    </v-list-item>
    <div v-if="isOpen && item.children" style="padding-left: 20px;">
      <RecursiveTreeItem
        v-for="child in item.children"
        :key="child.path"
        :item="child"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>
