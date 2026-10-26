<template>
  <div class="post-edit">
    <el-card v-loading="loading">
      <template #header>
        <span class="card-title">{{ isEdit ? '编辑游记' : '发布游记' }}</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            maxlength="150"
            show-word-limit
            placeholder="请输入游记标题"
          />
        </el-form-item>
        <el-form-item label="关联景点">
          <el-select
            v-model="form.spot_ids"
            multiple
            filterable
            :loading="spotsLoading"
            placeholder="请选择关联景点"
            style="width: 100%"
          >
            <el-option
              v-for="spot in spots"
              :key="spot.id"
              :label="spot.name + '（' + spot.city + '）'"
              :value="spot.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="封面图 URL">
          <el-input v-model="form.cover" placeholder="请输入封面图片链接" clearable />
        </el-form-item>
        <el-form-item v-if="form.cover" label="封面预览">
          <img :src="form.cover" class="cover-preview" alt="cover" @error="onCoverError" />
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
import { getSpotList } from '@/api/spot'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const spotsLoading = ref(false)
const spots = ref([])
const coverError = ref(false)
const form = reactive({ title: '', content: '', cover: '', spot_ids: [] })

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

const onCoverError = () => {
  coverError.value = true
}

const fetchSpots = async () => {
  spotsLoading.value = true
  try {
    const res = await getSpotList({ page: 1, page_size: 100 })
    spots.value = res.data.items || []
  } catch (e) {
    spots.value = []
  } finally {
    spotsLoading.value = false
  }
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
    form.cover = data.cover || ''
    form.spot_ids = Array.isArray(data.spot_ids) ? data.spot_ids : []
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

  const payload = {
    title,
    content: form.content,
    cover: form.cover || undefined,
    spot_ids: Array.isArray(form.spot_ids) ? form.spot_ids : []
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updatePost(route.params.id, payload)
      ElMessage.success('保存成功，修改后需重新审核')
      router.push(`/post-detail/${route.params.id}`)
    } else {
      await createPost(payload)
      ElMessage.success('发布成功，等待管理员审核')
      router.push('/post-list')
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
  fetchSpots()
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
