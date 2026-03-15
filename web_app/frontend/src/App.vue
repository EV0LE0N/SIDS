<template>
  <div id="app">
    <el-container class="app-container">
      <!-- 侧边栏导航 -->
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h2>SIDS</h2>
          <p>网络攻击检测系统</p>
        </div>
        <el-menu
          :default-active="activeMenu"
          class="nav-menu"
          @select="handleMenuSelect"
          router
        >
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <span>态势大屏</span>
          </el-menu-item>
          <el-menu-item index="/detect">
            <el-icon><Search /></el-icon>
            <span>攻击检测</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header class="header">
          <div class="header-content">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
            <div class="user-info">
              <el-avatar :size="32" :src="userAvatar" />
              <span class="username">管理员</span>
            </div>
          </div>
        </el-header>
        
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, Search } from '@element-plus/icons-vue'

const route = useRoute()

// 计算当前激活的菜单项
const activeMenu = computed(() => route.path)

// 计算当前页面标题
const currentPageTitle = computed(() => {
  const routeMap = {
    '/dashboard': '态势大屏',
    '/detect': '攻击检测'
  }
  return routeMap[route.path] || 'SIDS'
})

// 用户头像（示例）
const userAvatar = ref('https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png')

// 菜单选择处理
const handleMenuSelect = (index) => {
  console.log('导航到:', index)
}
</script>

<style scoped>
#app {
  height: 100vh;
  overflow: hidden;
}

.app-container {
  height: 100%;
}

.sidebar {
  background-color: #001529;
  color: #fff;
  height: 100%;
  border-right: 1px solid #e6e6e6;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo h2 {
  color: #fff;
  margin: 0;
  font-size: 20px;
  font-weight: bold;
}

.logo p {
  color: rgba(255, 255, 255, 0.7);
  margin: 5px 0 0;
  font-size: 12px;
}

.nav-menu {
  border-right: none;
  background-color: transparent;
}

.nav-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.7);
  height: 50px;
  line-height: 50px;
}

.nav-menu :deep(.el-menu-item.is-active) {
  background-color: #1890ff;
  color: #fff;
}

.nav-menu :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1);
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  height: 60px;
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  font-weight: 500;
  color: #303133;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>