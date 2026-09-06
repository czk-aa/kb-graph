<template>
  <div class="empty-state">
    <el-icon :size="size" :color="iconColor"><component :is="icon" /></el-icon>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <el-button v-if="actionText" type="primary" @click="$emit('action')">
      {{ actionText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: any
  title: string
  description?: string
  actionText?: string
  size?: number
  iconColor?: string
}>()

defineEmits<{
  action: []
}>()
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: var(--space-16) 0;
  color: var(--color-gray-400);
}
.empty-state h3 {
  margin: var(--space-4) 0 var(--space-2);
  color: var(--color-gray-600);
  font-size: var(--font-size-lg);
  font-weight: 600;
}
.empty-state p {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-sm);
  color: var(--color-gray-400);
}
</style>