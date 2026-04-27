<template>
  <div class="detect-container">
    <el-page-header content="攻击检测模块" />

    <!-- 顶部：操作与指标 -->
    <el-row :gutter="15" class="top-row">
      <!-- 左侧：文件上传区 -->
      <el-col :span="6">
        <el-card shadow="hover" class="upload-card">
          <el-upload
            class="upload-area"
            drag
            action="#"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
          >
            <el-icon class="el-icon--upload" style="margin-bottom: 5px; font-size: 32px;"><upload-filled /></el-icon>
            <div class="el-upload__text" style="font-size: 13px;">
              拖拽 CSV 到此处，或 <em>点击上传</em>
            </div>
          </el-upload>
        </el-card>
      </el-col>
      
      <!-- 右侧：4 个横向平铺的统计卡片 (复用 Dashboard.vue 样式) -->
      <el-col :span="18">
        <el-row :gutter="15" style="height: 100%;">
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background-color: #409eff;"><el-icon><DataLine /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value" :title="stats.total">{{ formatNumber(stats.total) }}</div>
                  <div class="stat-label">总检测量</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background-color: #67c23a;"><el-icon><Check /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value" :title="stats.normal">{{ formatNumber(stats.normal) }}</div>
                  <div class="stat-label">正常流量</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background-color: #e6a23c;"><el-icon><Warning /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value" :title="stats.attack">{{ formatNumber(stats.attack) }}</div>
                  <div class="stat-label">攻击流量</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card">
              <div class="stat-content">
                <div class="stat-icon" style="background-color: #f56c6c;"><el-icon><CloseBold /></el-icon></div>
                <div class="stat-info">
                  <div class="stat-value">{{ attackRate }}%</div>
                  <div class="stat-label">攻击比例</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>

    <!-- 中部：样本画像展板 (3栏均等布局的 ECharts 展板) -->
    <el-row :gutter="15" class="main-row" v-loading="loading">
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header><div class="card-header">攻击类型分布</div></template>
          <div class="chart-container" ref="attackDistChartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header><div class="card-header">多维特征对比雷达图 (Top 6)</div></template>
          <div class="chart-container" ref="radarChartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header><div class="card-header">模型置信度分布</div></template>
          <div class="chart-container" ref="confidenceDistChartRef"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部：取证明细表格 -->
    <el-row :gutter="15" class="table-row">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><div class="card-header">取证明细表格 (前 100 条)</div></template>
          <el-table :data="detailsData" style="width: 100%" max-height="400" v-loading="loading">
            <el-table-column prop="row_id" label="记录 ID" width="100" />
            <el-table-column prop="type" label="检测类型" width="150" />
            <el-table-column label="置信度 (Confidence)">
              <template #default="scope">
                <el-tag :type="getConfidenceType(scope.row.confidence)">
                  {{ (scope.row.confidence * 100).toFixed(2) }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, markRaw, nextTick } from 'vue';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import { DataLine, Check, Warning, CloseBold, UploadFilled } from '@element-plus/icons-vue';
// 假设 uploadPredict 已经根据规范在 api/predict.js 中实现
import { uploadPredict } from '@/api/predict';

// 加载状态
const loading = ref(false);

// 顶部统计卡片数据
const stats = ref({
  total: 0,
  normal: 0,
  attack: 0
});

const attackRate = computed(() => {
  return stats.value.total > 0 
    ? ((stats.value.attack / stats.value.total) * 100).toFixed(2) 
    : 0;
});

// 表格明细数据
const detailsData = ref([]);

// 格式化大数字
const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  }
  return num;
};

// 置信度 tag 类型计算
const getConfidenceType = (confidence) => {
  if (confidence >= 0.9) return 'danger';
  if (confidence >= 0.8) return 'warning';
  return 'info';
};

// 英文特征名 → 中文名称映射字典 (复刻 Dashboard.vue)
const FEATURE_CN_MAP = {
  'Flow Duration':    '流持续时间',
  'Tot Fwd Pkts':     '前向包总数',
  'Tot Bwd Pkts':     '后向包总数',
  'TotLen Fwd Pkts':  '前向包总长度',
  'TotLen Bwd Pkts':  '后向包总长度',
  'Fwd Pkt Len Max':  '前向包最大长度',
  'Fwd Pkt Len Min':  '前向包最小长度',
  'Fwd Pkt Len Mean': '前向包平均长度',
  'Flow Byts/s':      '流字节速率',
  'Flow Pkts/s':      '流包速率',
  'Bwd Pkt Len Max':  '后向包最大长度',
  'Bwd Pkt Len Min':  '后向包最小长度',
  'Bwd Pkt Len Mean': '后向包平均长度',
  'Flow IAT Mean':    '流间隔均值',
  'Flow IAT Max':     '流间隔最大值',
};

const toCN = (name) => FEATURE_CN_MAP[name] || name;

// DOM 引用
const attackDistChartRef = ref(null);
const radarChartRef = ref(null);
const confidenceDistChartRef = ref(null);

// 图表实例
const attackDistChart = ref(null);
const radarChart = ref(null);
const confidenceDistChart = ref(null);

// 基础图表配置 (复刻 Dashboard.vue)
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

const radarOption = ref({
  title: { text: '' },
  tooltip: { trigger: 'item' },
  legend: { data: ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'], bottom: 0 },
  radar: {
    indicator: [],
    radius: '60%',
    splitNumber: 5,
    axisName: { color: '#909399' },
    splitArea: { show: false },
    splitLine: { lineStyle: { color: 'rgba(238, 238, 238, 0.5)' } }
  },
  series: [{
    name: '特征维度对比',
    type: 'radar',
    data: []
  }]
});

const confidenceDistOption = ref({
  tooltip: { 
    trigger: 'axis', 
    axisPointer: { type: 'shadow' },
    formatter: function (params) {
      const p = params[0];
      return p.name + ' 区间<br/>记录条数: ' + p.value;
    }
  },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { 
    type: 'category', 
    data: ['>0.95', '0.9-0.95', '0.8-0.9', '<0.8'], 
    axisLabel: { rotate: 0 } 
  },
  yAxis: { type: 'value' },
  series: [{
    name: '记录条数',
    type: 'bar',
    barWidth: '60%',
    data: [],
    itemStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: '#83bff6' },
        { offset: 0.5, color: '#188df0' },
        { offset: 1, color: '#188df0' }
      ])
    }
  }]
});

const resizeAllCharts = () => {
  attackDistChart.value?.resize();
  radarChart.value?.resize();
  confidenceDistChart.value?.resize();
};

onMounted(() => {
  attackDistChart.value = markRaw(echarts.init(attackDistChartRef.value));
  radarChart.value = markRaw(echarts.init(radarChartRef.value));
  confidenceDistChart.value = markRaw(echarts.init(confidenceDistChartRef.value));
  
  // 初始化空图表
  attackDistChart.value.setOption(attackDistOption.value);
  radarChart.value.setOption(radarOption.value);
  confidenceDistChart.value.setOption(confidenceDistOption.value);

  window.addEventListener('resize', resizeAllCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAllCharts);
  if (attackDistChart.value) attackDistChart.value.dispose();
  if (radarChart.value) radarChart.value.dispose();
  if (confidenceDistChart.value) confidenceDistChart.value.dispose();
});

// 文件上传与预测逻辑
const handleFileChange = async (file) => {
  if (!file.name.endsWith('.csv')) {
    ElMessage.error('仅支持 CSV 格式文件');
    return;
  }
  
  const formData = new FormData();
  formData.append('file', file.raw);
  
  loading.value = true;
  try {
    const response = await uploadPredict(formData);
    const res = response.result;
    
    // 更新统计数据
    stats.value.total = res.stats.total;
    stats.value.normal = res.stats.normal;
    stats.value.attack = res.stats.dos + res.stats.bruteforce;
    
    // 更新攻击类型分布饼图
    if (res.attack_distribution) {
      attackDistOption.value.series[0].data = [
        { value: res.attack_distribution['0'] || 0, name: '正常流量' },
        { value: res.attack_distribution['1'] || 0, name: 'DoS/DDoS攻击' },
        { value: res.attack_distribution['2'] || 0, name: '暴力破解攻击' }
      ];
      attackDistChart.value?.setOption(attackDistOption.value);
    }
    
    // 更新置信度分布柱状图
    if (res.details) {
      let count1 = 0; // >0.95
      let count2 = 0; // 0.9-0.95
      let count3 = 0; // 0.8-0.9
      let count4 = 0; // <0.8
      
      res.details.forEach(item => {
        const conf = item.confidence;
        if (conf > 0.95) count1++;
        else if (conf >= 0.9) count2++;
        else if (conf >= 0.8) count3++;
        else count4++;
      });
      
      confidenceDistOption.value.series[0].data = [count1, count2, count3, count4];
      confidenceDistChart.value?.setOption(confidenceDistOption.value);
    }
    
    // 更新雷达图
    if (res.radar_data) {
      const { features, normal, dos, bruteforce } = res.radar_data;
      radarOption.value.radar.indicator = features.map(f => ({ name: toCN(f) }));
      radarOption.value.series[0].data = [
        { value: normal, name: '正常流量', areaStyle: { color: 'rgba(103, 194, 58, 0.3)' } },
        { value: dos, name: 'DoS/DDoS攻击', areaStyle: { color: 'rgba(230, 162, 60, 0.3)' } },
        { value: bruteforce, name: '暴力破解攻击', areaStyle: { color: 'rgba(245, 108, 108, 0.3)' } }
      ];
      radarChart.value?.setOption(radarOption.value);
    }
    
    // 更新明细表格
    detailsData.value = res.details || [];
    
    ElMessage.success('检测与画像生成完成');
  } catch (err) {
    console.error('检测失败', err);
    ElMessage.error(err.message || '检测失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.detect-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.top-row {
  margin-top: 15px;
}

.main-row {
  margin-top: 15px;
}

.table-row {
  margin-top: 15px;
}

.card-header {
  font-weight: bold;
  font-size: 15px;
  color: #303133;
}

.chart-card {
  transition: all 0.3s ease;
  background: #fff;
}
.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
}

.chart-container {
  width: 100%;
  height: 350px;
}

/* 上传区域调整 */
.upload-card {
  height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
:deep(.upload-card .el-card__body) {
  padding: 0;
  height: 100%;
}
:deep(.upload-area) {
  height: 100%;
}
:deep(.upload-area .el-upload) {
  height: 100%;
}
:deep(.upload-area .el-upload-dragger) {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 0;
}

/* 顶部统计卡片 - 物理复用 Dashboard.vue 样式 */
.stat-card {
  height: 100px;
  cursor: default;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px 0 rgba(0,0,0,.1) !important;
}
:deep(.stat-card .el-card__body) {
  padding: 15px 25px;
  height: 100%;
  box-sizing: border-box;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 100%;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
  overflow: hidden;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1.1;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 6px;
}
</style>