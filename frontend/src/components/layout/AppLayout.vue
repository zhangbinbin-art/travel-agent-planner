<template>
  <div class="layout">
    <AppHeader />
    <div class="layout-body">
      <main class="layout-main">
        <router-view v-slot="{ Component }">
          <KeepAlive include="Plan">
            <component :is="Component" v-if="$route.meta.keepAlive" />
          </KeepAlive>
          <component :is="Component" v-if="!$route.meta.keepAlive" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
</script>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #e8f4ff;
}
.layout-body {
  display: flex;
  flex: 1;
  min-width: 0;
}
.layout-main {
  flex: 1;
  min-width: 0;
  padding: 18px 20px 28px;
  background: transparent;
}
</style>
