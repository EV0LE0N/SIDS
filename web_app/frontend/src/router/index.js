import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '@/views/Dashboard.vue';
import Detect from '@/views/Detect.vue';

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: '网络攻击检测态势大屏',
      icon: 'DataAnalysis',
    },
  },
  {
    path: '/detect',
    name: 'Detect',
    component: Detect,
    meta: {
      title: '攻击检测分析',
      icon: 'UploadFilled',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫 - 页面标题设置
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - SIDS网络攻击检测系统`;
  } else {
    document.title = 'SIDS网络攻击检测系统';
  }
  
  next();
});

// 路由守卫 - 页面访问权限控制（如果需要）
router.beforeEach((to, from, next) => {
  // 这里可以添加权限验证逻辑
  // 例如：检查用户是否登录，是否有权限访问该页面等
  
  // 暂时不需要权限控制，直接放行
  next();
});

// 路由错误处理
router.onError((error) => {
  console.error('路由错误:', error);
});

export default router;