<template>
  <div class="my-like-post">
    <!-- 扩展预留点：后端补齐 GET /api/v1/user/liked-posts（返回当前用户点赞的游记列表）后，把 likedPosts 换成真实请求即可。 -->
    <div class="section-title">我点赞的帖子</div>

    <div v-loading="loading">
      <EmptyState
        v-if="!loading && !likedPosts.length"
        description="暂无点赞帖子"
        hint="点赞过的游记会显示在这里"
      />
      <div v-else class="like-list">
        <div v-for="item in likedPosts" :key="item.id" class="like-item">
          {{ item.title }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(false)
const likedPosts = ref([])

// TODO(backend): 后端提供 GET /api/v1/user/liked-posts 后，替换为真实请求
const getMyLikedPosts = async () => {
  loading.value = true
  try {
    // 暂无后端接口，保持空列表，避免发起不存在的请求导致 404
    likedPosts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(getMyLikedPosts)
</script>

<style scoped>
.my-like-post {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}
.like-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.like-item {
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  color: #2c3e50;
}
</style>
