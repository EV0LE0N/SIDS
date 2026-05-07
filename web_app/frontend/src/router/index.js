import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '@/views/Dashboard.vue';
import Detect from '@/views/Detect.vue';
import SopDashboard from '@/views/SopDashboard.vue';
import AssetManager from '@/views/AssetManager.vue';
import Login from '@/views/Login.vue';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: '系统登入',
      public: true // 标记为公开路由
    }
  },
  {
    path: '/',
    redirect: '/sop',
  },
  {
    path: '/sop',
    name: 'SopDashboard',
    component: SopDashboard,
    meta: {
      title: '安全运营态势中心',
      icon: 'Monitor',
    },
  },
  {
    path: '/assets',
    name: 'AssetManager',
    component: AssetManager,
    meta: {
      title: '探针资产管理',
      icon: 'Setting',
    },
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
    redirect: '/sop',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫 - 合并标题设置与权限控制（严禁使用多个 beforeEach）
router.beforeEach((to, from, next) => {
  // 设置标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - SIDS网络攻击检测系统`;
  } else {
    document.title = 'SIDS网络攻击检测系统';
  }

  // 鉴权拦截
  const token = localStorage.getItem('sids_token')
  if (!to.meta.public && !token) {
    // 目标路由需要鉴权且无 token，跳转登录
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已经登录但访问登录页，重定向到首页
    next('/sop')
  } else {
    // 正常放行
    next()
  }
});

router.onError((error) => {
  console.error('路由错误:', error);
});

export default router;