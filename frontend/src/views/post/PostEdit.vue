<template>
  <div class="post-edit">
    <el-card v-loading="loading">
      <template #header>
        <span class="card-title">{{ isEdit ? '编辑游记' : '发布游记' }}</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="72px">
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            maxlength="150"
            show-word-limit
            placeholder="请输入游记标题"
          />
        </el-form-item>
        <el-form-item label="正文" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="14"
            placeholder="分享你的旅行故事…"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getPostDetail, createPost, updatePost } from '@/api/post'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const form = reactive({ title: '', content: '' })

const isEdit = computed(() => !!route.params.id)

const rules = {
  title: [{ required: true, message: '请输入游记标题', trigger: 'blur' }]
}

const extractError = (e, fallback) => {
  if (e?.response?.status === 403) return '无权限操作'
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg || item?.message).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return fallback
}

const loadPost = async () => {
  loading.value = true
  try {
    const res = await getPostDetail(route.params.id)
    const data = res.data || {}
    if (!(auth.role === 'admin' || (auth.userId !== null && auth.userId === data.user_id))) {
      ElMessage.error('无权限操作')
      router.replace('/post-list')
      return
    }
    form.title = data.title || ''
    form.content = data.content || ''
  } catch (e) {
    if (e?.response?.status === 404) {
      ElMessage.error('游记不存在')
      router.replace('/post-list')
    } else {
      ElMessage.error(extractError(e, '获取游记详情失败'))
    }
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const title = form.title.trim()
  if (!title) {
    ElMessage.warning('请输入游记标题')
    return
  }

  const payload = { title, content: form.content }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updatePost(route.params.id, payload)
      ElMessage.success('保存成功')
      router.push(`/post-detail/${route.params.id}`)
    } else {
      const res = await createPost(payload)
      ElMessage.success('发布成功')
      router.push(`/post-detail/${res.data.id}`)
    }
  } catch (e) {
    ElMessage.error(extractError(e, '保存失败'))
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  router.push('/post-list')
}

onMounted(() => {
  if (isEdit.value) loadPost()
})
</script>

<style scoped>
.post-edit {
  max-width: 900px;
  margin: 0 auto;
}
.card-title {
  font-weight: 600;
}
</style>
