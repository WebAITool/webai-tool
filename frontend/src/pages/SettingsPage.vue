<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { settingsApi } from '../api/settingsApi'
import { useSnackbar } from '../composables/useSnackbar'

const snackbar = useSnackbar()

// LLM Configuration
const apiKey = ref('')
const apiUrl = ref('https://api.polza.ai/api/v1')
const modelName = ref('z-ai/glm-4.7')
const showApiKey = ref(false)
const testingConnection = ref(false)
const saving = ref(false)
const connectionResult = ref<{ success: boolean; message: string } | null>(null)

// Agent Configuration
const maxSteps = ref(50)
const patience = ref(3)
const actionMemory = ref(true)

// Frontend Verification
const enableFrontendVerify = ref(true)
const headlessMode = ref(true)
const verifyPort = ref(5173)

const apiKeyWarning = computed(() => !apiKey.value || apiKey.value.startsWith('****'))

onMounted(async () => {
  try {
    const s = await settingsApi.get()
    apiKey.value = s.api_key
    apiUrl.value = s.api_base_url
    modelName.value = s.model_name
    maxSteps.value = s.max_steps
    patience.value = s.patience
    actionMemory.value = s.action_memory
    enableFrontendVerify.value = s.enable_frontend_verify
    headlessMode.value = s.headless_mode
    verifyPort.value = s.verify_port
  } catch (e: any) {
    snackbar.show('Failed to load settings', 'error')
  }
})

async function saveSettings() {
  saving.value = true
  try {
    await settingsApi.save({
      api_key: apiKey.value,
      api_base_url: apiUrl.value,
      model_name: modelName.value,
      max_steps: maxSteps.value,
      patience: patience.value,
      action_memory: actionMemory.value,
      enable_frontend_verify: enableFrontendVerify.value,
      headless_mode: headlessMode.value,
      verify_port: verifyPort.value
    })
    snackbar.show('Settings saved!', 'success')
  } catch (e: any) {
    snackbar.show('Failed to save settings', 'error')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testingConnection.value = true
  connectionResult.value = null
  try {
    const result = await settingsApi.testConnection({
      api_key: apiKey.value,
      api_base_url: apiUrl.value,
      model_name: modelName.value,
      max_steps: maxSteps.value,
      patience: patience.value,
      action_memory: actionMemory.value,
      enable_frontend_verify: enableFrontendVerify.value,
      headless_mode: headlessMode.value,
      verify_port: verifyPort.value
    })
    connectionResult.value = result
  } catch (e: any) {
    connectionResult.value = { success: false, message: e.message || 'Connection failed' }
  } finally {
    testingConnection.value = false
    setTimeout(() => { connectionResult.value = null }, 5000)
  }
}
</script>

<template>
  <v-container>
    <h1 class="text-h4 mb-4">Settings</h1>

    <v-alert v-if="apiKeyWarning" type="warning" variant="tonal" class="mb-4">
      API Key is not configured. Agent execution will not work without a valid key.
    </v-alert>

    <v-alert v-if="connectionResult" :type="connectionResult.success ? 'success' : 'error'" variant="tonal" class="mb-4" closable>
      {{ connectionResult.message }}
    </v-alert>

    <!-- LLM Configuration -->
    <v-card max-width="700" class="mb-6">
      <v-card-title>
        <v-icon start>mdi-key</v-icon>
        LLM configuration
      </v-card-title>
      <v-card-text>
        <v-text-field
          v-model="apiKey"
          label="API key"
          :type="showApiKey ? 'text' : 'password'"
          :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
          hint="Your personal LLM API key"
          persistent-hint
          variant="outlined"
          class="mb-4"
          @click:append-inner="showApiKey = !showApiKey"
        ></v-text-field>

        <v-text-field
          v-model="apiUrl"
          label="API base URL"
          hint="Endpoint for the LLM API (e.g. https://api.polza.ai/api/v1)"
          persistent-hint
          variant="outlined"
          class="mb-4"
        ></v-text-field>

        <v-text-field
          v-model="modelName"
          label="Model name"
          hint="Model identifier (e.g., z-ai/glm-4.7)"
          persistent-hint
          variant="outlined"
        ></v-text-field>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="secondary"
          variant="tonal"
          :loading="testingConnection"
          @click="testConnection"
        >
          <v-icon start>mdi-lan-check</v-icon>
          Test connection
        </v-btn>
        <v-btn color="primary" :loading="saving" @click="saveSettings">Save settings</v-btn>
      </v-card-actions>
    </v-card>

    <!-- Agent Configuration -->
    <v-card max-width="700" class="mb-6">
      <v-card-title>
        <v-icon start>mdi-robot</v-icon>
        Agent configuration
      </v-card-title>
      <v-card-text>
        <v-text-field
          v-model.number="maxSteps"
          type="number"
          label="Max steps"
          min="1"
          max="200"
          hint="Maximum number of agent iterations per task"
          persistent-hint
          variant="outlined"
          class="mb-4"
        ></v-text-field>

        <v-text-field
          v-model.number="patience"
          type="number"
          label="Patience"
          min="1"
          max="10"
          hint="Number of consecutive errors before stopping"
          persistent-hint
          variant="outlined"
          class="mb-4"
        ></v-text-field>

        <v-checkbox
          v-model="actionMemory"
          label="Enable action memory"
          hint="Agent remembers previous actions across steps"
          persistent-hint
          color="primary"
        ></v-checkbox>
      </v-card-text>
    </v-card>

    <!-- Frontend Verification -->
    <v-card max-width="700">
      <v-card-title>
        <v-icon start>mdi-eye-check</v-icon>
        Frontend verification
      </v-card-title>
      <v-card-text>
        <v-checkbox
          v-model="enableFrontendVerify"
          label="Enable frontend verification"
          hint="Run UI screenshot analysis after code changes"
          persistent-hint
          color="primary"
          class="mb-2"
        ></v-checkbox>

        <v-expand-transition>
          <div v-if="enableFrontendVerify">
            <v-checkbox
              v-model="headlessMode"
              label="Headless mode"
              hint="Run browser in headless mode (no visible window)"
              persistent-hint
              color="primary"
              class="ml-4 mb-2"
            ></v-checkbox>

            <v-text-field
              v-model.number="verifyPort"
              type="number"
              label="Dev server port"
              min="1024"
              max="65535"
              hint="Port for the frontend dev server during verification"
              persistent-hint
              variant="outlined"
              class="ml-4"
            ></v-text-field>
          </div>
        </v-expand-transition>
      </v-card-text>
    </v-card>
  </v-container>
</template>
