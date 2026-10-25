<template>
  <div class="register">
    <el-card class="register-card">
      <template #header>注册</template>
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input type="password" placeholder="请确认密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary">注册</el-button>
          <el-button text @click="$router.push('/login')">已有账号，去登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.register {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 60px);
}
.register-card {
  width: 420px;
}
</style>
