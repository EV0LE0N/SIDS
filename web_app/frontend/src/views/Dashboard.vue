<template>
  <div class="dashboard-container">
    <el-page-header content="网络攻击检测态势大屏" />
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">攻击类型分布</div>
          </template>
          <div class="chart-container" ref="attackDistChartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">Top10受击端口流量统计</div>
          </template>
          <div class="chart-container" ref="top10PortChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 系统状态卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff;">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalPackets }}</div>
              <div class="stat-label">总流量包数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a;">
              <el-icon><Check /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ normalPackets }}</div>
              <div class="stat-label">正常流量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c;">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ attackPackets }}</div>
              <div class="stat-label">攻击流量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #f56c6c;">
              <el-icon><CloseBold /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ attackRate }}%</div>
              <div class="stat-label">攻击比例</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { getStats } from '@/api/stats';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import { DataLine, Check, Warning, CloseBold } from '@element-plus/icons-vue';

// 图表实例
const attackDistChart = ref(null);
const top10PortChart = ref(null);

// 图表配置
const attackDistOption = ref({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, left: 'center' },
  series: [{
    name: '攻击类型分布',
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: false, position: 'center' },
    emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
    labelLine: { show: false },
    data: []
  }]
});

const top10PortOption = ref({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: [], axisLabel: { rotate: 0 } },
  yAxis: { type: 'value' },
  series: [{
    name: '流量包数量',
    type: 'bar',
    barWidth: '60%',
    data: []
  }]
});

// 统计数据
const totalPackets = ref(0);
const normalPackets = ref(0);
const attackPackets = ref(0);
const attackRate = ref(0);

// 加载统计数据（系统启动后自动执行）
const loadStatsData = async () => {
  try {
    const res = await getStats();
    
    // 处理攻击类型分布数据
    const attackDist = res.attack_distribution;
    const attackData = [
      { value: attackDist['0'], name: '正常流量' },
      { value: attackDist['1'], name: 'DoS/DDoS攻击' },
      { value: attackDist['2'], name: '暴力破解攻击' }
    ];
    attackDistOption.value.series[0].data = attackData;
  
    // 处理Top10 目标端口数据
    const top10Port = res.top10_dst_port;
    top10PortOption.value.xAxis.data = Object.keys(top10Port);
    top10PortOption.value.series[0].data = Object.values(top10Port);
    top10PortOption.value.tooltip = {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: '{b} 端口<br/>{a}: {c}'
    };
    
    // 更新统计数据（严格使用 stats_metadata.total_records）
    totalPackets.value = res.stats_metadata?.total_records || 0;
    normalPackets.value = attackDist['0'] || 0;
    attackPackets.value = (attackDist['1'] || 0) + (attackDist['2'] || 0);
    attackRate.value = totalPackets.value > 0 ? 
      ((attackPackets.value / totalPackets.value) * 100).toFixed(2) : 0;
  
    // 更新图表（确保图表已初始化）
    if (attackDistChart.value) {
      attackDistChart.value.setOption(attackDistOption.value);
    }
    if (top10PortChart.value) {
      top10PortChart.value.setOption(top10PortOption.value);
    }
  } catch (error) {
    console.error('加载统计数据失败：', error);
  
    // 【V1.2 增强】前端空态健壮性：区分不同错误类型，提供友好提示
    let userMessage = '加载统计数据失败';
  
    // 检查错误类型
    if (error.response && error.response.status === 404) {
      userMessage = '统计数据接口返回404，请先执行 ETL 任务生成数据文件';
    } else if (error.message && error.message.includes('Network Error')) {
      userMessage = '网络连接失败，请检查后端服务是否正常运行';
    } else if (error.message && error.message.includes('stats not found')) {
      userMessage = '统计数据文件不存在，请先执行 ETL 任务 (run_etl.sh)';
    } else {
      userMessage = '统计数据未生成，请先执行 ETL 任务 (run_etl.sh)';
    }
  
    // 使用 Element Plus 的消息提示组件
    if (typeof ElMessage !== 'undefined') {
      ElMessage.warning({
        message: userMessage,
        duration: 5000, // 延长显示时间
        showClose: true
      });
    }
  
    // 可选：在开发环境下记录更详细的错误信息
    if (process.env.NODE_ENV === 'development') {
      console.debug('详细错误信息:', {
        error: error.message,
        stack: error.stack,
        response: error.response
      });
    }
  }
};

// 初始化图表（系统启动后自动初始化）
// 注意：使用 ref 绑定 DOM 元素，而非 document.querySelector
const attackDistChartRef = ref(null);
const top10PortChartRef = ref(null);

onMounted(() => {
  attackDistChart.value = echarts.init(attackDistChartRef.value);
  top10PortChart.value = echarts.init(top10PortChartRef.value);
  loadStatsData();
  
  // 监听窗口大小变化，重新渲染图表
  window.addEventListener('resize', () => {
    if (attackDistChart.value) {
      attackDistChart.value.resize();
    }
    if (top10PortChart.value) {
      top10PortChart.value.resize();
    }
  });
});

// 组件卸载时清理
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => {});
  if (attackDistChart.value) {
    attackDistChart.value.dispose();
  }
  if (top10PortChart.value) {
    top10PortChart.value.dispose();
  }
});
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.chart-row {
  margin-top: 20px;
}

.stats-row {
  margin-top: 20px;
}

.card-header {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>