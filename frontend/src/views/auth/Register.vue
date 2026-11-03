<template>
  <div class="register-page">
    <svg
      class="register-scene"
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <circle cx="1130" cy="180" r="86" fill="#ffe1b8" />
      <ellipse cx="1130" cy="180" r="118" fill="#ffeccc" opacity="0.55" />
      <g fill="#ffffff" opacity="0.85">
        <ellipse cx="250" cy="170" rx="78" ry="30" />
        <ellipse cx="310" cy="158" rx="58" ry="24" />
        <ellipse cx="860" cy="140" rx="66" ry="26" />
        <ellipse cx="912" cy="132" rx="48" ry="20" />
      </g>
      <path d="M0 660 L190 470 L330 610 L470 430 L640 660 Z" fill="#bfe0ff" opacity="0.75" />
      <path d="M420 660 L610 500 L760 640 L920 470 L1120 660 Z" fill="#a9d4ff" opacity="0.6" />
      <path d="M0 700 C240 640 420 740 660 700 C900 660 1080 740 1440 690 L1440 900 L0 900 Z" fill="#d7ecff" />
      <path d="M0 780 C260 730 480 800 740 760 C980 724 1180 790 1440 752 L1440 900 L0 900 Z" fill="#c3e2ff" opacity="0.85" />
      <g opacity="0.9">
        <path d="M300 742 L350 660 L400 742 Z" fill="#ffd2a8" />
        <path d="M350 742 L350 660" stroke="#e9a86f" stroke-width="4" />
        <circle cx="350" cy="648" r="6" fill="#ffb073" />
      </g>
    </svg>

    <el-card class="register-card" shadow="never">
      <header class="register-brand">
        <span class="brand-logo">TR</span>
        <div class="brand-text">
          <h1 class="brand-name">旅游规划平台</h1>
          <span class="brand-en">Travel Route</span>
        </div>
      </header>
      <p class="register-welcome">创建账号 · Join Us</p>

      <el-form ref="formRef" label-width="80px" :model="form" :rules="rules" @submit.prevent>
        <el-form-item label="账号类型" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio-button value="user">游客</el-radio-button>
            <el-radio-button value="merchant">酒店商家</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.role === 'merchant'" label="店铺名称" prop="shop_name">
          <el-input v-model="form.shop_name" placeholder="请输入酒店/店铺名称" clearable />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" placeholder="请确认密码" show-password />
        </el-form-item>
        <el-form-item class="register-actions">
          <el-button type="primary" class="register-btn" @click="handleRegister" :loading="loading">注册</el-button>
          <el-button text @click="$router.push('/login')">已有账号，去登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
  confirm: '',
  role: 'user',
  shop_name: ''
})

const validatePassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入密码'))
    return
  }
  if (value.length < 6 || value.length > 12) {
    callback(new Error('密码长度需为6~12位'))
    return
  }
  const hasLetter = /[A-Za-z]/.test(value)
  const hasDigit = /[0-9]/.test(value)
  if (!(hasLetter && hasDigit)) {
    callback(new Error('密码必须包含字母和数字'))
    return
  }
  callback()
}

const validateConfirm = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度需为3~50位', trigger: 'blur' }
  ],
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' }
  ],
  confirm: [
    { required: true, validator: validateConfirm, trigger: 'blur' }
  ]
}

const handleRegister = () => {
  formRef.value.validate(async (valid) => {
    if (!valid) {
      ElMessage.error('请按要求填写注册信息')
      return
    }
    loading.value = true
    try {
      await api.post('/api/v1/user/register', {
        username: form.username,
        password: form.password,
        role: form.role,
        shop_name: form.role === 'merchant' ? form.shop_name : undefined
      })
      if (form.role === 'merchant') {
        ElMessage.success('商家账号注册成功，请等待管理员审核通过后登录')
      } else {
        ElMessage.success('注册成功')
      }
      router.push('/login')
    } catch (e) {
      console.log('register error:', e)
      console.log('register error.response:', e?.response)
      console.log('register error.response.data:', e?.response?.data)
      const data = e?.response?.data
      let msg = ''
      if (typeof data?.detail === 'string') {
        msg = data.detail
      } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
        const first = data.detail[0]
        if (typeof first?.msg === 'string') {
          msg = first.msg
        } else if (typeof first === 'string') {
          msg = first
        }
      } else if (typeof data?.message === 'string') {
        msg = data.message
      } else if (typeof e?.message === 'string') {
        msg = e.message
      }
      if (!msg) {
        if (!e?.response) {
          msg = '无法连接后端服务，请检查后端是否启动、接口地址是否正确'
        } else {
          msg = '注册失败'
        }
      }
      if (msg === '注册失败' && e?.response) {
        ElMessage.error('注册失败：' + msg)
      } else if (msg.includes('无法连接')) {
        ElMessage.error(msg)
      } else {
        ElMessage.error('注册失败：' + msg)
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.register-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px 20px;
  background: linear-gradient(180deg, #eef7ff 0%, #e8f4ff 45%, #dceeff 100%);
  overflow: hidden;
}

.register-scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.5;
}

.register-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
  background: #fff;
  border: 2px solid #222;
  border-radius: 24px;
  box-shadow: 6px 6px 0 rgba(34, 34, 34, 0.14);
}

.register-card :deep(.el-card__body) {
  padding: 28px 28px 22px;
}

.register-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #ff7a2f;
  border: 2px solid #222;
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 rgba(34, 34, 34, 0.16);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-name {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #222;
}

.brand-en {
  font-size: 12px;
  letter-spacing: 1.6px;
  color: #7b8794;
}

.register-welcome {
  margin: 20px 0 18px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #5a6472;
  letter-spacing: 0.6px;
}

.register-actions {
  margin-top: 8px;
  margin-bottom: 0;
}

.register-btn {
  min-width: 108px;
  height: 40px;
  font-weight: 700;
  letter-spacing: 2px;
}
</style>
