<template>
  <div class="empty-state">
    <svg
      class="empty-illustration"
      width="96"
      height="96"
      viewBox="0 0 96 96"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="12" y="22" width="72" height="52" rx="10" fill="#f2f4f7" stroke="#e4e7ed" stroke-width="2" />
      <path
        d="M21 62l15-15 9.5 9.5 8.5-8.5 14 14"
        stroke="#d3d8e0"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <circle cx="34" cy="38" r="5" fill="#e4e7ed" />
      <path d="M14 80h68" stroke="#eceff3" stroke-width="2" stroke-linecap="round" />
    </svg>

    <p class="empty-desc">{{ description }}</p>
    <p v-if="hint" class="empty-hint">{{ hint }}</p>

    <div v-if="$slots.default" class="empty-action">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  description: { type: String, default: '暂无数据' },
  hint: { type: String, default: '' }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
  text-align: center;
}
.empty-illustration {
  display: block;
  margin-bottom: 12px;
}
.empty-desc {
  margin: 0;
  font-size: 14px;
  color: #606266;
}
.empty-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: #909399;
}
.empty-action {
  margin-top: 16px;
}
</style>
