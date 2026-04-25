<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import { useAgentStore } from '../stores/agentStore'
import { useSnackbar } from '../composables/useSnackbar'

const router = useRouter()
const taskStore = useTaskStore()
const agentStore = useAgentStore()
const snackbar = useSnackbar()

// Form Data
const goal = ref('')
const spec = ref('')
const prjdir = ref('')
const maxSteps = ref(50)
const enableCommits = ref(false)
const commitBranch = ref('dev')

// UI State
const loading = ref(false)
const valid = ref(false)

// File inputs refs
const specFileInput = ref<HTMLInputElement | null>(null)
const dirInput = ref<HTMLInputElement | null>(null)

// Validation Rules
const required = (value: string) => !!value || 'Required.'

// Handle file loading for Spec
function triggerFileInput() {
  specFileInput.value?.click()
}

function onSpecFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      spec.value = e.target?.result as string
    }
    reader.readAsText(file)
  }
}

// Handle directory browsing
function triggerDirInput() {
  dirInput.value?.click()
}

function onDirChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    // Browsers return a FileList for directories. 
    // We can't get the full path easily, but we can infer the directory name from the first file's webkitRelativePath
    const firstFile = target.files[0]
    if (firstFile.webkitRelativePath) {
      const pathParts = firstFile.webkitRelativePath.split('/')
      // Usually the first part is the directory name
      prjdir.value = pathParts[0] 
    }
  }
}

async function handleCreate(shouldStart: boolean = false) {
  if (!valid.value) return

  loading.value = true
  try {
    const taskData = {
      goal: goal.value,
      spec: spec.value,
      prjdir: prjdir.value,
      max_steps: maxSteps.value,
      enable_commits: enableCommits.value,
      commit_branch: commitBranch.value
    }

    const newTask = await taskStore.createTask(taskData)
    
    if (shouldStart) {
      await agentStore.startAgent(newTask.id)
    }

    router.push(`/tasks/${newTask.id}`)
  } catch (error: any) {
    console.error('Failed to create task:', error)
    const msg = error?.response?.data?.detail || error?.message || 'Unknown error'
    snackbar.show(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-container>
    <h1 class="text-h4 mb-4">Create new task</h1>
    
    <v-card max-width="800" class="mx-auto">
      <v-card-text>
        <v-form v-model="valid">
          <!-- Goal -->
          <v-textarea
            v-model="goal"
            label="Goal"
            required
            :rules="[required]"
            hint="Describe the goal for the agent"
            persistent-hint
            rows="3"
            variant="outlined"
            class="mb-4"
          ></v-textarea>

          <!-- Specification -->
          <div class="d-flex align-center mb-1 mt-2">
            <label class="text-subtitle-1">Specification</label>
            <v-spacer></v-spacer>
            <v-btn size="small" variant="text" @click="triggerFileInput">
              <v-icon start size="small">mdi-folder-open</v-icon>
              Load from file
            </v-btn>
            <input
              ref="specFileInput"
              type="file"
              accept=".txt,.md,.json,.py"
              style="display: none"
              @change="onSpecFileChange"
            >
          </div>
          <v-textarea
            v-model="spec"
            required
            :rules="[required]"
            hint="Project specification"
            persistent-hint
            rows="5"
            variant="outlined"
            class="font-family-monospace mb-4"
          ></v-textarea>

          <!-- Project Directory -->
          <v-text-field
            v-model="prjdir"
            label="Project directory"
            required
            :rules="[required]"
            hint="Output directory path (relative to workspace)"
            persistent-hint
            variant="outlined"
            class="mb-4"
          >
            <template v-slot:append-inner>
              <v-btn size="small" variant="text" @click="triggerDirInput" icon>
                <v-icon size="small">mdi-folder-multiple</v-icon>
              </v-btn>
              <input
                ref="dirInput"
                type="file"
                webkitdirectory
                directory
                style="display: none"
                @change="onDirChange"
              >
            </template>
          </v-text-field>

          <!-- Max Steps -->
          <v-text-field
            v-model.number="maxSteps"
            type="number"
            label="Max steps"
            min="1"
            max="200"
            hint="Maximum number of iterations"
            variant="outlined"
            class="mb-4"
          ></v-text-field>

          <!-- Enable Commits -->
          <v-checkbox
            v-model="enableCommits"
            color="primary"
          >
            <template v-slot:label>
              <div>
                Enable git commits
                <v-tooltip location="top">
                  <template v-slot:activator="{ props }">
                    <v-icon v-bind="props" size="x-small" class="ml-1">mdi-information</v-icon>
                  </template>
                  The agent will initialize a git repository in the project directory and commit each code change automatically.
                </v-tooltip>
              </div>
            </template>
          </v-checkbox>

          <!-- Commit Branch -->
          <v-expand-transition>
            <v-text-field
              v-if="enableCommits"
              v-model="commitBranch"
              label="Commit branch"
              hint="Git branch name for agent commits (created in the project directory repo)"
              persistent-hint
              variant="outlined"
              prepend-inner-icon="mdi-source-branch"
              class="ml-8 mb-4"
            ></v-text-field>
          </v-expand-transition>
        </v-form>
      </v-card-text>

      <v-card-actions class="justify-end pa-4">
        <v-btn
          color="grey"
          variant="text"
          :disabled="loading || !valid"
          @click="handleCreate(false)"
        >
          Create
        </v-btn>
        <v-btn
          color="primary"
          :loading="loading"
          :disabled="!valid"
          @click="handleCreate(true)"
        >
          Create & start
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<style scoped>
.font-family-monospace {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
</style>
