<template>
  <div class="register">
    <el-card class="register-card">
      <template #header>注册</template>
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
        <el-form-item>
          <el-button type="primary" @click="handleRegister" :loading="loading">注册</el-button>
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
.register {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-image: url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=1920&q=80');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  position: relative;
  padding: 20px;
}

.register::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 28, 63, 0.45);
  z-index: 0;
}

.register-card {
  width: 420px;
  position: relative;
  z-index: 1;
  border-radius: 12px;
}
</style>
