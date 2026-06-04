<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useVerificationStore } from '../stores/verificationStore'

const route = useRoute()
const verificationStore = useVerificationStore()

const taskId = route.params.task_id as string

// Dialog state
const dialog = ref(false)
const selectedResult = ref<any>(null)

// Helper functions for UI
function getStatusColor(status: string): string {
  switch (status) {
    case 'OK': return 'success'
    case 'NEEDS_WORK': return 'warning'
    case 'BROKEN': return 'error'
    default: return 'grey'
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'OK': return 'mdi-check-circle'
    case 'NEEDS_WORK': return 'mdi-alert-circle'
    case 'BROKEN': return 'mdi-close-circle'
    default: return 'mdi-help-circle'
  }
}

function openDialog(result: any) {
  selectedResult.value = result
  dialog.value = true
}

function runVerificationAgain() {
  // Trigger re-verification
  // Note: The backend endpoint for re-running verification might need to be implemented separately.
  // For now, we simulate the action by refreshing the results.
  verificationStore.fetchResults(taskId)
}

onMounted(() => {
  verificationStore.fetchResults(taskId)
})
</script>

<template>
  <v-container>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h4">Verification Gallery</h1>
      <v-btn 
        color="primary" 
        prepend-icon="mdi-refresh" 
        @click="runVerificationAgain" 
        :loading="verificationStore.loading"
        :disabled="verificationStore.loading"
      >
        Run Verification Again
      </v-btn>
    </div>

    <v-alert v-if="verificationStore.error" type="error" variant="tonal" class="mb-4" closable>
      {{ verificationStore.error }}
    </v-alert>

    <!-- Loading State -->
    <div v-if="verificationStore.loading && verificationStore.results.length === 0" class="d-flex justify-center align-center" style="min-height: 400px;">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
    </div>

    <!-- Results Grid -->
    <v-row v-else-if="verificationStore.results.length > 0">
      <v-col 
        v-for="(result, index) in verificationStore.results" 
        :key="index" 
        cols="12" 
        sm="6" 
        md="4" 
        lg="3"
      >
        <v-card class="h-100 d-flex flex-column cursor-pointer" hover elevation="2" @click="openDialog(result)">
          <!-- Screenshot Thumbnail -->
          <div class="d-flex justify-center pa-2 bg-grey-darken-4">
            <v-img
              v-if="result.screenshot_base64"
              :src="'data:image/png;base64,' + result.screenshot_base64"
              max-height="200"
              contain
              class="border rounded"
            >
              <template v-slot:placeholder>
                <div class="d-flex align-center justify-center fill-height">
                  <v-progress-circular indeterminate color="grey"></v-progress-circular>
                </div>
              </template>
            </v-img>
            <div v-else class="d-flex align-center justify-center fill-height text-grey" style="height: 200px;">
              <v-icon size="48">mdi-image-off</v-icon>
            </div>
          </div>
          
          <!-- Card Content -->
          <v-card-title class="text-subtitle-1 py-2 text-truncate">
            <v-icon start size="small">mdi-route</v-icon>
            {{ result.route }}
          </v-card-title>
          
          <v-card-text class="flex-grow-1">
            <v-chip 
              :color="getStatusColor(result.status)" 
              size="small" 
              label 
              class="mb-2"
            >
              <v-icon start size="small">{{ getStatusIcon(result.status) }}</v-icon>
              {{ result.status }}
            </v-chip>
            <p class="text-body-2 text-truncate-3 text-grey-darken-1 mb-0">
              {{ result.analysis }}
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Empty State -->
    <v-alert v-else-if="!verificationStore.loading" type="info" variant="tonal">
      No verification results available for this task yet.
    </v-alert>

    <!-- Full Size Dialog -->
    <v-dialog v-model="dialog" max-width="90%">
      <v-card v-if="selectedResult">
        <v-toolbar color="grey-darken-3" density="compact">
          <v-toolbar-title class="text-h6">
            <v-icon start>mdi-route</v-icon>
            {{ selectedResult.route }}
          </v-toolbar-title>
          <v-spacer></v-spacer>
          <v-chip :color="getStatusColor(selectedResult.status)" label class="mr-2">
            {{ selectedResult.status }}
          </v-chip>
          <v-btn icon variant="text" @click="dialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="pa-0 bg-black d-flex justify-center">
          <v-img
            v-if="selectedResult.screenshot_base64"
            :src="'data:image/png;base64,' + selectedResult.screenshot_base64"
            contain
            max-height="80vh"
            width="100%"
          ></v-img>
          <div v-else class="d-flex align-center justify-center pa-10 text-white">
            No screenshot available
          </div>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-text class="pt-4">
          <h3 class="text-h6 mb-2">VLM Analysis</h3>
          <p class="text-body-1 whitespace-pre-wrap">{{ selectedResult.analysis }}</p>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="dialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.text-truncate-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.h-100 {
  height: 100%;
}
.cursor-pointer {
  cursor: pointer;
}
.whitespace-pre-wrap {
  white-space: pre-wrap;
}
</style>
