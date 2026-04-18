import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '@/views/Dashboard.vue';
import Detect from '@/views/Detect.vue';
import EdaAnalysis from '@/views/EdaAnalysis.vue';

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
    path: '/eda',
    name: 'EdaAnalysis',
    component: EdaAnalysis,
    meta: {
      title: '学术探索大屏',
      icon: 'DataBoard',
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

// 路由守卫 - 合并标题设置与权限控制（严禁使用多个 beforeEach）
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - SIDS网络攻击检测系统`;
  } else {
    document.title = 'SIDS网络攻击检测系统';
  }
  next();
});

router.onError((error) => {
  console.error('路由错误:', error);
});

export default router;