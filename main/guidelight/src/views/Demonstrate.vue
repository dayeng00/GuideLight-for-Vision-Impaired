<script setup>
import { ref } from 'vue';
import { marked } from 'marked';
import markdownContent from '../assets/demonstrate.md?raw';

const htmlContent = ref(marked(markdownContent));
</script>

<template>
  <div v-html="htmlContent"></div>
</template>
