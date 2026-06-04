<script setup lang="ts">
import { onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useFileStore } from '../stores/fileStore'
import RecursiveTreeItem from '../components/RecursiveTreeItem.vue'
import type { FileNode } from '../types'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const route = useRoute()
const fileStore = useFileStore()

const rootPath = computed(() => (route.query.prjdir as string) || '')

onMounted(() => {
  if (rootPath.value) {
    fileStore.fetchTree(rootPath.value)
  }
})

watch(rootPath, (val) => {
  if (val) fileStore.fetchTree(val)
})

function handleNodeClick(item: FileNode) {
  if (!item.is_directory) {
    fileStore.fetchContent(item.path)
  }
}

function guessLanguage(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    py: 'python', ts: 'typescript', js: 'javascript', vue: 'xml',
    html: 'html', css: 'css', json: 'json', yaml: 'yaml', yml: 'yaml',
    md: 'markdown', sql: 'sql', sh: 'bash', tsx: 'tsx', jsx: 'jsx',
    go: 'go', rs: 'rust', java: 'java', rb: 'ruby', php: 'php',
    dockerfile: 'dockerfile', toml: 'toml', ini: 'ini', cfg: 'ini',
  }
  return map[ext] || 'plaintext'
}

const highlightedContent = computed(() => {
  if (!fileStore.currentContent || !fileStore.currentPath) return ''
  const lang = guessLanguage(fileStore.currentPath)
  try {
    if (lang === 'plaintext') {
      return hljs.highlightAuto(fileStore.currentContent).value
    }
    return hljs.highlight(fileStore.currentContent, { language: lang }).value
  } catch {
    return fileStore.currentContent
  }
})
</script>

<template>
  <v-container class="fill-height">
    <v-row>
      <v-col cols="12" md="4">
        <v-card height="80vh">
          <v-toolbar title="File tree"></v-toolbar>
          <v-divider></v-divider>
          <v-list density="compact" style="overflow-y: auto; height: calc(80vh - 64px);">
            <v-list-item v-if="!fileStore.tree">No directory loaded</v-list-item>
            <RecursiveTreeItem v-else :item="fileStore.tree" @select="handleNodeClick" />
          </v-list>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="8">
        <v-card height="80vh">
          <v-toolbar>
            <v-toolbar-title>{{ fileStore.currentPath || 'Select a file' }}</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn
              v-if="fileStore.currentContent"
              icon
              size="small"
              variant="text"
              :href="`/api/files/download?path=${encodeURIComponent(fileStore.currentPath)}`"
              download
            >
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </v-toolbar>
          <v-divider></v-divider>
          <div v-if="fileStore.loading" class="d-flex justify-center pa-10">
            <v-progress-circular indeterminate></v-progress-circular>
          </div>
          <pre v-else-if="fileStore.currentContent" class="pa-4" style="overflow: auto; height: calc(80vh - 64px);"><code v-html="highlightedContent"></code></pre>
          <div v-else class="d-flex align-center justify-center fill-height text-grey">
            File content will appear here
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
