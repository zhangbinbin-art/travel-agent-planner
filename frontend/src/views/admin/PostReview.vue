<template>
  <div class="post-review">
    <el-card>
      <template #header>
        <span class="card-title">内容审核</span>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="帖子审核" name="post">
          <div class="filter-bar">
            <el-select v-model="postFilter.status" placeholder="状态" clearable style="width: 140px">
              <el-option label="全部" value="" />
              <el-option label="待审核" :value="0" />
              <el-option label="已通过" :value="1" />
              <el-option label="已驳回" :value="2" />
            </el-select>
            <el-input v-model="postFilter.keyword" placeholder="关键词" clearable style="width: 220px" @keyup.enter="fetchPosts" />
            <el-button type="primary" @click="fetchPosts">查询</el-button>
            <el-button @click="resetPostFilter">重置</el-button>
          </div>

          <el-table v-loading="postLoading" :data="postList" border style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="封面" width="100">
              <template #default="{ row }">
                <el-image
                  v-if="row.cover"
                  :src="row.cover"
                  fit="cover"
                  style="width: 60px; height: 40px"
                  :preview-src-list="[row.cover]"
                  preview-teleported
                />
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="标题" min-width="200">
              <template #default="{ row }">
                <el-link type="primary" @click="openPostDetail(row)">{{ row.title }}</el-link>
              </template>
            </el-table-column>
            <el-table-column label="作者" width="120">
              <template #default="{ row }">
                {{ row.author?.username || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="关联景点" min-width="150">
              <template #default="{ row }">
                <span v-if="row.spots && row.spots.length">{{ row.spots.map(s => s.name).join('、') }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="浏览/点赞/评论" width="140">
              <template #default="{ row }">
                {{ row.view_count }}/{{ row.like_count }}/{{ row.comment_count }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 0" type="warning">待审核</el-tag>
                <el-tag v-else-if="row.status === 1" type="success">已通过</el-tag>
                <el-tag v-else-if="row.status === 2" type="danger">已驳回</el-tag>
                <span v-else>{{ row.status_text }}</span>
              </template>
            </el-table-column>
            <el-table-column label="提交时间" width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status !== 1" type="success" size="small" @click="handleReviewPost(row, 1)">通过</el-button>
                <el-button v-if="row.status !== 2" type="warning" size="small" @click="handleReviewPost(row, 2)">驳回</el-button>
                <el-button type="danger" size="small" @click="handleDeletePost(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="postTotal"
            :page-size="postPageSize"
            :current-page="postPage"
            @current-change="handlePostPageChange"
          />
        </el-tab-pane>

        <el-tab-pane label="评论审核" name="comment">
          <el-table v-loading="commentLoading" :data="commentList" border style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="所属帖子" min-width="150">
              <template #default="{ row }">
                <el-link v-if="row.post_id" type="primary" :href="`/post-detail/${row.post_id}`" target="_blank">
                  帖子 #{{ row.post_id }}
                </el-link>
                <span v-else>景点评论</span>
              </template>
            </el-table-column>
            <el-table-column label="评论者" width="120">
              <template #default="{ row }">
                {{ row.author?.username || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="内容" min-width="200">
              <template #default="{ row }">
                <el-tooltip :content="row.content" placement="top">
                  <div class="comment-content">{{ row.content }}</div>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="评分" width="80" />
            <el-table-column prop="like_count" label="点赞数" width="80" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 0" type="warning">待审核</el-tag>
                <el-tag v-else-if="row.status === 1" type="success">已通过</el-tag>
                <el-tag v-else-if="row.status === 2" type="danger">已驳回</el-tag>
                <span v-else>{{ row.status_text }}</span>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status !== 1" type="success" size="small" @click="handleReviewComment(row, 1)">通过</el-button>
                <el-button v-if="row.status !== 2" type="warning" size="small" @click="handleReviewComment(row, 2)">驳回</el-button>
                <el-button type="danger" size="small" @click="handleDeleteComment(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="commentTotal"
            :page-size="commentPageSize"
            :current-page="commentPage"
            @current-change="handleCommentPageChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-drawer v-model="postDetailVisible" title="帖子详情" size="50%">
      <div v-if="currentPost" class="post-detail">
        <div class="detail-item"><strong>标题：</strong>{{ currentPost.title }}</div>
        <div class="detail-item"><strong>作者：</strong>{{ currentPost.author?.username || '-' }}</div>
        <div class="detail-item"><strong>状态：</strong>
          <el-tag v-if="currentPost.status === 0" type="warning">待审核</el-tag>
          <el-tag v-else-if="currentPost.status === 1" type="success">已通过</el-tag>
          <el-tag v-else-if="currentPost.status === 2" type="danger">已驳回</el-tag>
        </div>
        <div class="detail-item"><strong>关联景点：</strong>
          <span v-if="currentPost.spots && currentPost.spots.length">{{ currentPost.spots.map(s => s.name).join('、') }}</span>
          <span v-else>-</span>
        </div>
        <div class="detail-item"><strong>封面：</strong>
          <el-image v-if="currentPost.cover" :src="currentPost.cover" style="max-width: 200px" />
          <span v-else>-</span>
        </div>
        <div class="detail-item"><strong>内容：</strong></div>
        <div class="content-preview">{{ currentPost.content }}</div>
        <div class="detail-actions">
          <el-button v-if="currentPost.status !== 1" type="success" @click="handleReviewPost(currentPost, 1); postDetailVisible = false">通过</el-button>
          <el-button v-if="currentPost.status !== 2" type="warning" @click="handleReviewPost(currentPost, 2); postDetailVisible = false">驳回</el-button>
          <el-button type="danger" @click="handleDeletePost(currentPost); postDetailVisible = false">删除</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { auth } from '@/utils/auth'
import { getAdminPostList, reviewPost, getAdminCommentList, reviewComment } from '@/api/admin'
import { deletePost } from '@/api/post'
import { deleteComment } from '@/api/comment'

const router = useRouter()

if (auth.role !== 'admin') {
  ElMessage.error('无权限访问')
  router.replace('/')
}

const activeTab = ref('post')

const postFilter = ref({
  status: '',
  keyword: ''
})
const postList = ref([])
const postTotal = ref(0)
const postPage = ref(1)
const postPageSize = ref(10)
const postLoading = ref(false)

const commentList = ref([])
const commentTotal = ref(0)
const commentPage = ref(1)
const commentPageSize = ref(10)
const commentLoading = ref(false)

const postDetailVisible = ref(false)
const currentPost = ref(null)

const extractError = (e, fallback) => {
  if (e?.response?.status === 403) return '无权限操作'
  const detailMsg = e?.response?.data?.detail
  if (typeof detailMsg === 'string' && detailMsg) return detailMsg
  if (Array.isArray(detailMsg)) {
    const messages = detailMsg.map((item) => item?.msg || item?.message).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

const formatDateTime = (val) => {
  if (!val) return '-'
  const date = new Date(val)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}`
}

const fetchPosts = async () => {
  postLoading.value = true
  try {
    const params = {
      page: postPage.value,
      page_size: postPageSize.value
    }
    if (postFilter.value.status !== '' && postFilter.value.status !== null) {
      params.status = postFilter.value.status
    }
    if (postFilter.value.keyword) {
      params.keyword = postFilter.value.keyword
    }
    const res = await getAdminPostList(params)
    postList.value = res.data.items || []
    postTotal.value = res.data.total || 0
  } catch (e) {
    ElMessage.error(extractError(e, '获取帖子列表失败'))
  } finally {
    postLoading.value = false
  }
}

const resetPostFilter = () => {
  postFilter.value.status = ''
  postFilter.value.keyword = ''
  postPage.value = 1
  fetchPosts()
}

const handlePostPageChange = (p) => {
  postPage.value = p
  fetchPosts()
}

const fetchComments = async () => {
  commentLoading.value = true
  try {
    const params = {
      page: commentPage.value,
      page_size: commentPageSize.value
    }
    if (postFilter.value.status !== '' && postFilter.value.status !== null && activeTab.value === 'comment') {
      // comments don't have keyword filter in requirements, but just in case
    }
    const res = await getAdminCommentList(params)
    commentList.value = res.data.items || []
    commentTotal.value = res.data.total || 0
  } catch (e) {
    ElMessage.error(extractError(e, '获取评论列表失败'))
  } finally {
    commentLoading.value = false
  }
}

const handleCommentPageChange = (p) => {
  commentPage.value = p
  fetchComments()
}

const openPostDetail = (row) => {
  currentPost.value = row
  postDetailVisible.value = true
}

const handleReviewPost = async (row, status) => {
  try {
    await reviewPost(row.id, status)
    ElMessage.success(status === 1 ? '审核通过' : '已驳回')
    await fetchPosts()
  } catch (e) {
    ElMessage.error(extractError(e, '操作失败'))
  }
}

const handleDeletePost = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除这篇帖子吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deletePost(row.id)
    ElMessage.success('删除成功')
    await fetchPosts()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

const handleReviewComment = async (row, status) => {
  try {
    await reviewComment(row.id, status)
    ElMessage.success(status === 1 ? '审核通过' : '已驳回')
    await fetchComments()
  } catch (e) {
    ElMessage.error(extractError(e, '操作失败'))
  }
}

const handleDeleteComment = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？删除后不可恢复', '提示', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await deleteComment(row.id)
    ElMessage.success('删除成功')
    await fetchComments()
  } catch (e) {
    ElMessage.error(extractError(e, '删除失败'))
  }
}

onMounted(() => {
  fetchPosts()
  fetchComments()
})
</script>

<style scoped>
.post-review {
  padding: 20px;
}

.card-title {
  font-weight: 600;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.comment-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.post-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  color: #303133;
}

.content-preview {
  white-space: pre-wrap;
  word-break: break-word;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}
</style>
