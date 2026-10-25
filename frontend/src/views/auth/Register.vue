<template>
  <div class="register">
    <el-card class="register-card">
      <template #header>注册</template>
      <el-form ref="formRef" label-width="80px" :model="form" :rules="rules" @submit.prevent>
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
          <el-button type="primary" @click="handleRegister">注册</el-button>
          <el-button text @click="$router.push('/login')">已有账号，去登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const formRef = ref()
const form = reactive({
  username: '',
  password: '',
  confirm: ''
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
  formRef.value.validate((valid) => {
    if (!valid) {
      ElMessage.error('请按要求填写注册信息')
      return
    }
    ElMessage.success('注册信息校验通过（暂未对接后端）')
  })
}
</script>

<style scoped>
.register {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f7f8fa;
}
.register-card {
  width: 420px;
}
</style>
