<template>
  <v-app>
    <v-container>
      <v-text-field label="Name" variant="outlined"></v-text-field>
      <v-btn color="primary" @click="submit">Submit</v-btn>
    </v-container>
  </v-app>
</template>

<script setup>
function submit() {
  alert('Submitted!')
}
</script>