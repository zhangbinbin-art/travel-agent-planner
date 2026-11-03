<template>
  <div class="hotel-info-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">酒店详情</span>
          <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
        </div>
      </template>

      <el-alert
        v-if="!status.verified"
        :title="bannerText"
        :type="status.profile_status === 'rejected' || status.cert_status === 'rejected' ? 'error' : 'warning'"
        :closable="false"
        show-icon
        class="status-alert"
      />

      <el-tabs v-model="activeTab">
        <!-- ================= 酒店资料 ================= -->
        <el-tab-pane label="酒店资料编辑" name="profile">
          <div class="tab-status">
            <el-tag :type="profileTagType" size="small">{{ profileStatusText }}</el-tag>
            <span v-if="profile.audit_msg" class="reject-msg">驳回原因：{{ profile.audit_msg }}</span>
            <span v-else-if="profile.status === 'pending'" class="pending-msg">资料正在等待管理员审核</span>
            <span v-else-if="profile.status === 'approved'" class="pending-msg">资料已审核通过并锁定</span>
          </div>

          <el-form :model="profileForm" label-width="110px" :disabled="profileReadonly">
            <el-form-item label="酒店名称" required>
              <el-input v-model="profileForm.name" maxlength="150" placeholder="请输入酒店名称" />
            </el-form-item>
            <el-form-item label="酒店地址">
              <div class="addr-row">
                <el-input v-model="profileForm.address" placeholder="详细地址，如：杭州市西湖区北山街88号" />
                <el-button :loading="geoLoading" @click="fillCoords">获取经纬度</el-button>
              </div>
              <div class="coord-tip">
                经纬度：{{ profileForm.lng || '-' }}, {{ profileForm.lat || '-' }}
              </div>
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="profileForm.phone" maxlength="30" placeholder="酒店前台电话" />
            </el-form-item>
            <el-form-item label="单日房价">
              <el-input-number v-model="profileForm.price" :min="0" :step="50" />
              <span class="hint-inline">审核通过后作为酒店基础房价对外展示</span>
            </el-form-item>
            <el-form-item label="酒店简介">
              <el-input
                v-model="profileForm.intro"
                type="textarea"
                :rows="4"
                placeholder="介绍酒店特色、配套服务（停车场、wifi、早餐、24 小时前台等）"
              />
            </el-form-item>
            <el-form-item label="酒店相册">
              <el-upload
                v-model:file-list="profileFileList"
                list-type="picture-card"
                :http-request="uploadImage"
                :limit="8"
                :on-remove="syncProfileImgs"
                :disabled="profileReadonly"
              >
                <span class="upload-plus">+</span>
              </el-upload>
              <div class="hint">支持多张，第一张作为封面；jpg/png/webp，单张不超过 5MB</div>
            </el-form-item>
            <el-form-item label="酒店标签">
              <el-checkbox-group v-model="profileForm.tags">
                <el-checkbox-button v-for="t in HOTEL_TAGS" :key="t" :value="t">{{ t }}</el-checkbox-button>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="营业/入住规则">
              <el-input v-model="profileForm.checkin_rule" maxlength="255" placeholder="入住 14:00 后，退房 12:00 前" />
            </el-form-item>
          </el-form>

          <div class="form-actions">
            <template v-if="profileEditable">
              <el-button @click="saveProfile(false)" :loading="savingProfile">保存草稿</el-button>
              <el-button type="primary" @click="saveProfile(true)" :loading="savingProfile">提交资料审核</el-button>
            </template>
            <el-button v-else-if="profile.status === 'approved'" @click="reopenProfile">申请修改</el-button>
          </div>
        </el-tab-pane>

        <!-- ================= 资质认证 ================= -->
        <el-tab-pane label="酒店资质认证" name="cert">
          <div class="tab-status">
            <el-tag :type="certTagType" size="small">{{ certStatusText }}</el-tag>
            <span v-if="cert.audit_msg" class="reject-msg">驳回原因：{{ cert.audit_msg }}</span>
            <span v-else-if="cert.status === 'pending'" class="pending-msg">认证资料正在等待管理员审核</span>
          </div>

          <el-form :model="certForm" label-width="140px" :disabled="certReadonly">
            <el-form-item label="酒店全称" required>
              <el-input v-model="certForm.hotel_full_name" maxlength="150" placeholder="营业执照上的名称" />
            </el-form-item>
            <el-form-item label="统一社会信用代码" required>
              <el-input v-model="certForm.credit_code" maxlength="50" placeholder="18 位统一社会信用代码" />
            </el-form-item>
            <el-form-item label="法人姓名">
              <el-input v-model="certForm.legal_name" maxlength="50" />
            </el-form-item>
            <el-form-item label="法人手机号">
              <el-input v-model="certForm.legal_phone" maxlength="30" />
            </el-form-item>
            <el-form-item label="营业执照">
              <el-upload
                v-model:file-list="licenseFileList"
                list-type="picture-card"
                :http-request="uploadImage"
                :limit="1"
                :on-remove="syncLicense"
                :disabled="certReadonly"
              >
                <span class="upload-plus">+</span>
              </el-upload>
            </el-form-item>
            <el-form-item label="法人身份证正反面">
              <el-upload
                v-model:file-list="idCardFileList"
                list-type="picture-card"
                :http-request="uploadImage"
                :limit="2"
                :on-remove="syncIdCards"
                :disabled="certReadonly"
              >
                <span class="upload-plus">+</span>
              </el-upload>
            </el-form-item>
          </el-form>

          <div class="form-actions">
            <template v-if="certEditable">
              <el-button @click="saveCert(false)" :loading="savingCert">保存草稿</el-button>
              <el-button type="primary" @click="saveCert(true)" :loading="savingCert">提交认证审核</el-button>
            </template>
            <el-button v-else-if="cert.status === 'approved'" @click="reopenCert">申请修改</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import {
  getHotelCert,
  getHotelProfile,
  getHotelStatus,
  reopenHotelCert,
  reopenHotelProfile,
  saveHotelCert,
  saveHotelProfile
} from '@/api/hotel'
import { geoCode } from '@/api/map'

const HOTEL_TAGS = ['连锁酒店', '商务酒店', '民宿', '电竞酒店', '其他酒店']

const STATUS_TEXT = {
  draft: '草稿',
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}
const STATUS_TAG = { draft: 'info', pending: 'warning', approved: 'success', rejected: 'danger' }

const activeTab = ref('profile')
const status = ref({ profile_status: null, cert_status: null, profile_msg: '', cert_msg: '', verified: false })
const profile = ref({})
const cert = ref({})

const profileForm = reactive({
  name: '',
  address: '',
  lng: '',
  lat: '',
  phone: '',
  price: 300,
  intro: '',
  imgs: [],
  tags: [],
  checkin_rule: ''
})
const certForm = reactive({
  hotel_full_name: '',
  credit_code: '',
  legal_name: '',
  legal_phone: '',
  license_img: '',
  id_card_imgs: []
})
const profileFileList = ref([])
const licenseFileList = ref([])
const idCardFileList = ref([])

const geoLoading = ref(false)
const savingProfile = ref(false)
const savingCert = ref(false)

const statusText = computed(() => {
  if (status.value.verified) return '已上线'
  const p = status.value.profile_status
  const c = status.value.cert_status
  if (!p && !c) return '未提交'
  if (p === 'rejected' || c === 'rejected') return '已驳回'
  if (p === 'pending' || c === 'pending') return '待审核'
  return '资料未完成'
})
const statusTagType = computed(() => {
  if (status.value.verified) return 'success'
  const p = status.value.profile_status
  const c = status.value.cert_status
  if (!p && !c) return 'info'
  if (p === 'rejected' || c === 'rejected') return 'danger'
  if (p === 'pending' || c === 'pending') return 'warning'
  return 'info'
})
const bannerText = computed(() => {
  const p = status.value.profile_status
  const c = status.value.cert_status
  if (!p && !c) return '请前往酒店详情页完善酒店资料并提交审核'
  if (p === 'rejected') return `酒店资料审核已驳回：${status.value.profile_msg || '资料不符合要求'}`
  if (c === 'rejected') return `酒店资质审核已驳回：${status.value.cert_msg || '资料不符合要求'}`
  if (p === 'pending' && (!c || c === 'draft')) return '酒店资料待审核，请补充酒店资质认证'
  if (c === 'pending' && (!p || p === 'draft')) return '酒店资质待审核，请补充酒店资料'
  return '酒店资料与资质认证全部通过后才会在客户端展示'
})

const profileStatusText = computed(() => STATUS_TEXT[profile.value.status] || '未提交')
const profileTagType = computed(() => STATUS_TAG[profile.value.status] || 'info')
const certStatusText = computed(() => STATUS_TEXT[cert.value.status] || '未提交')
const certTagType = computed(() => STATUS_TAG[cert.value.status] || 'info')

const profileReadonly = computed(() => ['pending', 'approved'].includes(profile.value.status))
const profileEditable = computed(() => !profile.value.status || ['draft', 'rejected'].includes(profile.value.status))
const certReadonly = computed(() => ['pending', 'approved'].includes(cert.value.status))
const certEditable = computed(() => !cert.value.status || ['draft', 'rejected'].includes(cert.value.status))

const fillProfileForm = (data) => {
  if (!data) return
  Object.assign(profileForm, {
    name: data.name || '',
    address: data.address || '',
    lng: data.lng ?? '',
    lat: data.lat ?? '',
    phone: data.phone || '',
    price: Number(data.price ?? 300),
    intro: data.intro || '',
    imgs: data.imgs || [],
    tags: data.tags || [],
    checkin_rule: data.checkin_rule || ''
  })
  profileFileList.value = (data.imgs || []).map((url, i) => ({ name: 'img' + i, url }))
}

const fillCertForm = (data) => {
  if (!data) return
  Object.assign(certForm, {
    hotel_full_name: data.hotel_full_name || '',
    credit_code: data.credit_code || '',
    legal_name: data.legal_name || '',
    legal_phone: data.legal_phone || '',
    license_img: data.license_img || '',
    id_card_imgs: data.id_card_imgs || []
  })
  licenseFileList.value = data.license_img ? [{ name: 'license', url: data.license_img }] : []
  idCardFileList.value = (data.id_card_imgs || []).map((url, i) => ({ name: 'id' + i, url }))
}

const loadAll = async () => {
  try {
    const [st, pf, ct] = await Promise.all([getHotelStatus(), getHotelProfile(), getHotelCert()])
    status.value = st.data || status.value
    profile.value = pf.data?.profile || {}
    cert.value = ct.data?.cert || {}
    fillProfileForm(profile.value)
    fillCertForm(cert.value)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载酒店资料失败')
  }
}

// 复用现有图片上传接口
const uploadImage = async ({ file, onSuccess, onError }) => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await api.post('/api/v1/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    onSuccess(res.data)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '图片上传失败')
    onError(e)
  }
}

const syncProfileImgs = () => {
  profileForm.imgs = profileFileList.value.map((f) => f.url).filter(Boolean)
}
const syncLicense = () => {
  certForm.license_img = licenseFileList.value[0]?.url || ''
}
const syncIdCards = () => {
  certForm.id_card_imgs = idCardFileList.value.map((f) => f.url).filter(Boolean)
}

const fillCoords = async () => {
  const address = (profileForm.address || '').trim()
  if (!address) {
    ElMessage.warning('请先填写酒店地址')
    return
  }
  geoLoading.value = true
  try {
    const res = await geoCode(address)
    profileForm.lng = res.data?.lng
    profileForm.lat = res.data?.lat
    ElMessage.success('已获取经纬度')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '地理编码失败，请检查地址')
  } finally {
    geoLoading.value = false
  }
}

const saveProfile = async (submit) => {
  if (!profileForm.name.trim()) {
    ElMessage.warning('请填写酒店名称')
    return
  }
  syncProfileImgs()
  savingProfile.value = true
  try {
    await saveHotelProfile(
      {
        ...profileForm,
        lng: profileForm.lng === '' ? null : Number(profileForm.lng),
        lat: profileForm.lat === '' ? null : Number(profileForm.lat)
      },
      submit
    )
    ElMessage.success(submit ? '已提交审核' : '草稿已保存')
    await loadAll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

const saveCert = async (submit) => {
  syncLicense()
  syncIdCards()
  savingCert.value = true
  try {
    await saveHotelCert({ ...certForm }, submit)
    ElMessage.success(submit ? '认证已提交审核' : '草稿已保存')
    await loadAll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingCert.value = false
  }
}

const reopenProfile = async () => {
  try {
    await ElMessageBox.confirm('资料已通过审核并锁定，申请修改后会回到草稿状态，确定继续？', '提示', { type: 'warning' })
    await reopenHotelProfile()
    ElMessage.success('已回到草稿状态，可修改后重新提交')
    await loadAll()
  } catch (e) {
    /* 取消 */
  }
}

const reopenCert = async () => {
  try {
    await ElMessageBox.confirm('认证已通过，申请修改后会回到草稿状态，确定继续？', '提示', { type: 'warning' })
    await reopenHotelCert()
    ElMessage.success('已回到草稿状态')
    await loadAll()
  } catch (e) {
    /* 取消 */
  }
}

onMounted(loadAll)
</script>

<style scoped>
.hotel-info-page {
  max-width: 1100px;
}
.page-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-title {
  font-size: 18px;
  font-weight: 800;
  color: #222;
}
.status-alert {
  margin-bottom: 16px;
  border-radius: 10px;
}
.tab-status {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  font-size: 13px;
}
.reject-msg {
  color: #f56c6c;
}
.pending-msg {
  color: #e6a23c;
}
.addr-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.addr-row :deep(.el-input) {
  flex: 1;
}
.coord-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #7b8794;
}
.upload-plus {
  font-size: 22px;
  color: #909399;
  line-height: 1;
}
.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.form-actions {
  margin-top: 8px;
  padding-left: 110px;
}
</style>
