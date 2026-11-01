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
            v-model="selectedSpotRefs"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            :loading="spotsLoading"
            placeholder="请选择或输入关联景点/地区"
            style="width: 100%"
          >
            <el-option
              v-for="spot in spots"
              :key="spot.id"
              :label="spot.name + '（' + spot.city + '）'"
              :value="spot.id"
            />
          </el-select>
          <div class="field-hint">可直接输入系统里没有的地区名称，例如：佛山祖庙</div>
        </el-form-item>
        <el-form-item label="图片">
          <div class="image-list">
            <div v-for="(img, idx) in form.images" :key="idx" class="image-row">
              <span class="image-marker">
                <el-tag v-if="idx === 0" size="small" type="success">封面</el-tag>
                <span v-else class="image-index">{{ idx + 1 }}</span>
              </span>
              <el-input
                v-model="form.images[idx]"
                class="image-input"
                placeholder="请输入图片链接"
                clearable
              />
              <div v-if="img && img.trim()" class="thumb">
                <el-icon class="thumb-fallback"><Picture /></el-icon>
                <img :key="img" :src="img" alt="" @error="onThumbError" />
              </div>
              <div v-else class="thumb thumb-empty"></div>
              <el-button
                size="small"
                text
                type="danger"
                class="image-remove"
                @click="removeImage(idx)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div v-if="uploadingList.length" class="uploading-strip">
              <div v-for="item in uploadingList" :key="item.id" class="thumb uploading-thumb">
                <img :src="item.preview" alt="" />
                <div class="uploading-mask">上传中</div>
              </div>
            </div>
            <div class="image-actions">
              <el-button size="small" :disabled="form.images.length >= 9" @click="addImage">
                <el-icon><Plus /></el-icon>
                <span>添加图片</span>
              </el-button>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="uploadingCount > 0"
                :disabled="form.images.length >= 9"
                @click="triggerPick"
              >
                <el-icon><Picture /></el-icon>
                <span>本地选择图片</span>
              </el-button>
              <input
                ref="fileInputRef"
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                multiple
                class="hidden-file"
                @change="onFilesPicked"
              />
            </div>
            <div class="image-tip">最多 9 张，第一张作为封面；支持上传本地图片或填写图片链接</div>
          </div>
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
import { Picture, Delete, Plus } from '@element-plus/icons-vue'
import { getPostDetail, createPost, updatePost } from '@/api/post'
import api from '@/api'
import { getSpotList } from '@/api/spot'
import { auth } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const spotsLoading = ref(false)
const spots = ref([])
const form = reactive({ title: '', content: '', cover: '', images: [], spot_ids: [] })

// 关联地点选择：数字=已有景点 id，字符串=用户自定义输入的地区名
const selectedSpotRefs = ref([])

// 本地图片上传
const MAX_IMAGES = 9
const MAX_FILE_SIZE = 5 * 1024 * 1024
const ACCEPTED_MIME = ['image/jpeg', 'image/png', 'image/webp']
const ACCEPTED_EXT = ['jpg', 'jpeg', 'png', 'webp']
const fileInputRef = ref(null)
const uploadingCount = ref(0)
const uploadingList = ref([])

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

const onThumbError = (e) => {
  e.target.style.display = 'none'
}

const addImage = () => {
  if (form.images.length < 9) form.images.push('')
}

const removeImage = (idx) => {
  form.images.splice(idx, 1)
}

const extOf = (name) => String(name || '').split('.').pop().toLowerCase()

const validateFile = (file) => {
  const okType =
    ACCEPTED_MIME.includes(file.type) || ACCEPTED_EXT.includes(extOf(file.name))
  if (!okType) return '仅支持 jpg / png / webp 图片'
  if (file.size > MAX_FILE_SIZE) return '图片大小不能超过 5MB'
  return ''
}

const triggerPick = () => {
  if (form.images.length >= MAX_IMAGES) {
    ElMessage.warning('最多上传 9 张图片')
    return
  }
  fileInputRef.value?.click()
}

const uploadOne = async (file) => {
  const item = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    preview: URL.createObjectURL(file)
  }
  uploadingList.value.push(item)
  uploadingCount.value += 1
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.post('/api/v1/upload/image', fd)
    const url = res.data?.url
    if (!url) throw new Error('未返回图片地址')
    // 自动回填：优先填充空的链接行，否则追加一行
    const emptyIdx = form.images.findIndex((s) => !String(s || '').trim())
    if (emptyIdx >= 0) form.images[emptyIdx] = url
    else form.images.push(url)
    ElMessage.success('图片上传成功')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '图片上传失败')
  } finally {
    URL.revokeObjectURL(item.preview)
    uploadingList.value = uploadingList.value.filter((x) => x.id !== item.id)
    uploadingCount.value = Math.max(0, uploadingCount.value - 1)
  }
}

const onFilesPicked = async (event) => {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (!files.length) return
  const remain = MAX_IMAGES - form.images.length - uploadingCount.value
  if (remain <= 0) {
    ElMessage.warning('最多上传 9 张图片')
    return
  }
  const accepted = []
  for (const file of files) {
    const err = validateFile(file)
    if (err) {
      ElMessage.warning(`${file.name}：${err}`)
      continue
    }
    if (accepted.length >= remain) {
      ElMessage.warning('最多上传 9 张图片')
      break
    }
    accepted.push(file)
  }
  // 串行上传，保证图片顺序与选择顺序一致
  for (const file of accepted) {
    await uploadOne(file)
  }
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
    const imgs = Array.isArray(data.images) ? data.images.filter((s) => typeof s === 'string' && s.trim()) : []
    form.images = imgs.length ? imgs.slice(0, 9) : (data.cover ? [data.cover] : [])
    form.cover = imgs.length ? imgs[0] : (data.cover || '')
    form.spot_ids = Array.isArray(data.spot_ids) ? data.spot_ids : []
    const customSpots = Array.isArray(data.custom_spots) ? data.custom_spots : []
    selectedSpotRefs.value = [...form.spot_ids, ...customSpots]
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

  const images = (form.images || []).map((s) => (s || '').trim()).filter(Boolean).slice(0, 9)

  // 拆分：已有景点 id 进 spot_ids，自定义地区文字进 custom_spots
  const optionIds = new Set(spots.value.map((s) => Number(s.id)))
  const spotIds = []
  const customSpots = []
  selectedSpotRefs.value.forEach((ref) => {
    if (typeof ref === 'number') {
      spotIds.push(ref)
      return
    }
    const text = String(ref ?? '').trim()
    if (!text) return
    if (/^\d+$/.test(text) && optionIds.has(Number(text))) {
      spotIds.push(Number(text))
      return
    }
    customSpots.push(text)
  })
  form.spot_ids = [...new Set(spotIds)]

  const payload = {
    title: form.title,
    content: form.content,
    spot_ids: [...new Set(spotIds)],
    custom_spots: [...new Set(customSpots)],
    images
  }
  // 无图时不传 cover（或传空串），有图时 cover = images[0]
  if (images.length) payload.cover = images[0]

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
.image-list {
  width: 100%;
}
.image-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.image-marker {
  width: 40px;
  flex-shrink: 0;
  display: inline-flex;
  justify-content: center;
  align-items: center;
}
.image-index {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.image-input {
  flex: 1;
  min-width: 0;
}
.thumb {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-light);
}
.thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-fallback {
  color: var(--el-text-color-placeholder);
  font-size: 20px;
}
.thumb-empty {
  background: var(--el-fill-color-lighter);
}
.image-remove {
  flex-shrink: 0;
}
.image-tip {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.field-hint {
  width: 100%;
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.image-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.hidden-file {
  display: none;
}
.uploading-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}
.uploading-thumb {
  overflow: hidden;
}
.uploading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 11px;
}
</style>
