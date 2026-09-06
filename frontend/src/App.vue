<template>
  <el-config-provider>
    <router-view v-slot="{ Component, route }">
      <transition name="fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </el-config-provider>
</template>

<script setup lang="ts">
</script>
