<template>
  <div class="dashboard-container">
    <el-page-header content="全量指挥大屏" />
    
    <!-- 全局放大遮罩层 -->
    <div v-if="zoomedChart" class="zoom-backdrop" @click="closeZoom"></div>

    <!-- 顶部统计卡片 一字排开 -->
    <el-row :gutter="15" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff;"><el-icon><DataLine /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value" :title="totalPackets">{{ formatNumber(totalPackets) }}</div>
              <div class="stat-label">总包数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a;"><el-icon><Check /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value" :title="normalPackets">{{ formatNumber(normalPackets) }}</div>
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
              <div class="stat-value" :title="attackPackets">{{ formatNumber(attackPackets) }}</div>
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

    <el-row :gutter="15" class="main-row">
      <!-- 左侧 6 份 -->
      <el-col :span="6" class="col-wrapper">
        <!-- 移除原有的 2x2 网格 -->

        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'attackDist' }" @click="zoomChart('attackDist')">
          <template #header><div class="card-header">攻击类型分布</div></template>
          <div class="chart-container" ref="attackDistChartRef"></div>
        </el-card>

        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'confusionMatrix' }" @click="zoomChart('confusionMatrix')">
          <template #header><div class="card-header">多分类混淆矩阵热力图</div></template>
          <div class="chart-container" ref="confusionMatrixChartRef"></div>
        </el-card>
      </el-col>

      <!-- 中间 12 份 -->
      <el-col :span="12" class="col-wrapper">
        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'correlation' }" @click="zoomChart('correlation')">
          <template #header><div class="card-header">皮尔逊相关系数热力图</div></template>
          <div class="chart-container large" ref="correlationChartRef"></div>
        </el-card>

        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'scatter' }" @click="zoomChart('scatter')">
          <template #header><div class="card-header">二维聚类散点图（PCA降维）</div></template>
          <div class="chart-container" ref="scatterChartRef"></div>
        </el-card>
      </el-col>

      <!-- 右侧 6 份 -->
      <el-col :span="6" class="col-wrapper">
        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'top10Port' }" @click="zoomChart('top10Port')">
          <template #header><div class="card-header">Top10受击端口流量统计</div></template>
          <div class="chart-container" ref="top10PortChartRef"></div>
        </el-card>

        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'radar' }" @click="zoomChart('radar')">
          <template #header><div class="card-header">多维特征对比雷达图 (Top 6)</div></template>
          <div class="chart-container" ref="radarChartRef"></div>
        </el-card>

        <el-card shadow="hover" class="chart-card" :class="{ 'is-zoomed': zoomedChart === 'boxplot' }" @click="zoomChart('boxplot')">
          <template #header><div class="card-header">特征分布箱线图</div></template>
          <div class="chart-container" ref="boxplotChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, markRaw, nextTick } from 'vue';
import { getStats } from '@/api/stats';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus';
import { DataLine, Check, Warning, CloseBold } from '@element-plus/icons-vue';

// 缩放逻辑
const zoomedChart = ref(null);
const zoomChart = (chartName) => {
  if (zoomedChart.value === chartName) return;
  zoomedChart.value = chartName;
  nextTick(() => resizeAllCharts());
};
const closeZoom = () => {
  zoomedChart.value = null;
  nextTick(() => resizeAllCharts());
};

// 格式化大数字
const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  }
  return num;
};

// 英文特征名 → 中文名称映射字典
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
const top10PortChartRef = ref(null);
const radarChartRef = ref(null);
const confusionMatrixChartRef = ref(null);
const scatterChartRef = ref(null);
const correlationChartRef = ref(null);
const boxplotChartRef = ref(null);

// 图表实例
const attackDistChart = ref(null);
const top10PortChart = ref(null);
const radarChart = ref(null);
const confusionMatrixChart = ref(null);
const scatterChart = ref(null);
const correlationChart = ref(null);
const boxplotChart = ref(null);

// 统计数据变量
const totalPackets = ref(0);
const normalPackets = ref(0);
const attackPackets = ref(0);
const attackRate = ref(0);

// 基础图表配置
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
  tooltip: { 
    trigger: 'axis', 
    axisPointer: { type: 'shadow' },
    formatter: function (params) {
      const p = params[0];
      return p.name + ' 端口<br/>流量包数: ' + p.value.toLocaleString();
    }
  },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: [], axisLabel: { rotate: 0 } },
  yAxis: { type: 'value' },
  series: [{
    name: '流量包数量',
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

// EDA渲染逻辑
const renderConfusionMatrix = (confusionMatrixData) => {
  if (!confusionMatrixChart.value || !confusionMatrixData) return;
  const labels = ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'];
  const matrixData = confusionMatrixData.matrix;
  const option = {
    tooltip: { position: 'top' },
    grid: { height: '60%', top: '10%' },
    xAxis: { type: 'category', data: labels, splitArea: { show: true } },
    yAxis: { type: 'category', data: labels, splitArea: { show: true } },
    visualMap: { min: 0, max: 1, show: false, dimension: 3 },
    series: [{
      name: '混淆矩阵', type: 'heatmap',
      data: matrixData.map((row, i) => {
        const rowSum = row.reduce((a, b) => a + b, 0);
        return row.map((value, j) => [j, i, value, rowSum === 0 ? 0 : value / rowSum]);
      }).flat(),
      label: { show: true, formatter: (params) => params.value[2], color: '#000' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
    }]
  };
  confusionMatrixChart.value.setOption(option);
};

const renderScatterPlot = (edaSampleData) => {
  if (!scatterChart.value || !edaSampleData?.scatter_data) return;
  const scatterData = edaSampleData.scatter_data;
  const labelNames = ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'];
  const seriesData = [[], [], []];
  
  for (let i = 0; i < scatterData.length; i++) {
    const [x, y, label] = scatterData[i];
    const labelIdx = Math.round(label);
    if (labelIdx >= 0 && labelIdx < 3) {
      seriesData[labelIdx].push([x, y]);
    }
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => `${labelNames[params.seriesIndex]}<br/>X: ${params.value[0].toFixed(2)}<br/>Y: ${params.value[1].toFixed(2)}`
    },
    legend: { data: labelNames, bottom: '0%' },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '10%' },
    xAxis: { type: 'value', name: '第一主成分' },
    yAxis: { type: 'value', name: '第二主成分' },
    series: labelNames.map((name, index) => ({
      name: name, type: 'scatter', data: seriesData[index], symbolSize: 6,
      emphasis: { focus: 'series' }
    }))
  };
  scatterChart.value.setOption(option);
};

const renderCorrelationHeatmap = (edaSampleData) => {
  if (!correlationChart.value || !edaSampleData?.correlation_matrix) return;
  const { features, values: matrix } = edaSampleData.correlation_matrix;
  const maxFeatures = 15;
  const displayFeatures = features.slice(0, maxFeatures);
  const displayCNFeatures = displayFeatures.map(toCN);
  const displayMatrix = matrix.slice(0, maxFeatures).map(row => row.slice(0, maxFeatures));

  const option = {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const xName = displayCNFeatures[params.value[0]];
        const yName = displayCNFeatures[displayFeatures.length - 1 - params.value[1]];
        return `${xName} ↔ ${yName}<br/>相关系数: ${params.value[2].toFixed(4)}`;
      }
    },
    grid: { top: '5%', left: '20%', right: '5%', bottom: '25%' },
    xAxis: {
      type: 'category', data: displayCNFeatures,
      axisLabel: { interval: 0, rotate: 45, fontSize: 10 },
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category', data: displayCNFeatures.slice().reverse(),
      axisLabel: { interval: 0, fontSize: 10 },
      splitArea: { show: true }
    },
    visualMap: { min: -1, max: 1, show: false },
    series: [{
      name: '相关系数', type: 'heatmap',
      data: displayMatrix.map((row, i) => 
        row.map((value, j) => [j, displayFeatures.length - 1 - i, value])
      ).flat(),
      label: { show: true, formatter: (params) => params.value[2].toFixed(2), color: '#000', fontSize: 9 }
    }]
  };
  correlationChart.value.setOption(option);
};

const renderBoxplot = (edaSampleData) => {
  if (!boxplotChart.value || !edaSampleData?.boxplot_data) return;
  const boxplotData = edaSampleData.boxplot_data;
  const computeBoxplotStats = (arr) => {
    const sorted = [...arr].sort((a, b) => a - b);
    const n = sorted.length;
    const q1 = sorted[Math.floor(n * 0.25)];
    const median = sorted[Math.floor(n * 0.5)];
    const q3 = sorted[Math.floor(n * 0.75)];
    const min = sorted[0];
    const max = sorted[n - 1];
    return [min, q1, median, q3, max];
  };

  const categories = ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'];
  const dataKeys = ['normal', 'dos', 'bruteforce'];
  const seriesData = dataKeys.map(key => {
    const arr = boxplotData[key];
    if (!arr || arr.length === 0) return [0, 0, 0, 0, 0];
    return computeBoxplotStats(arr);
  });

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (param) => {
        const data = param.data;
        return [
          `${param.seriesName}`,
          `最大值: ${data[5]?.toFixed(2)}`,
          `上四分位: ${data[4]?.toFixed(2)}`,
          `中位数: ${data[3]?.toFixed(2)}`,
          `下四分位: ${data[2]?.toFixed(2)}`,
          `最小值: ${data[1]?.toFixed(2)}`
        ].join('<br/>');
      }
    },
    grid: { left: '15%', right: '10%', bottom: '15%', top: '10%' },
    xAxis: { type: 'category', data: categories, axisLabel: { fontSize: 10, interval: 0 } },
    yAxis: { type: 'value', name: '特征值' },
    series: [{
      name: '特征分布', type: 'boxplot', data: seriesData
    }]
  };
  boxplotChart.value.setOption(option);
};

// 加载统计数据
const loadStatsData = async () => {
  try {
    const res = await getStats();
    
    // 1. 攻击类型分布
    const attackDist = res.attack_distribution;
    attackDistOption.value.series[0].data = [
      { value: attackDist['0'], name: '正常流量' },
      { value: attackDist['1'], name: 'DoS/DDoS攻击' },
      { value: attackDist['2'], name: '暴力破解攻击' }
    ];
  
    // 2. Top10 目标端口
    const top10Port = res.top10_dst_port;
    const sortedPorts = Object.entries(top10Port).sort((a, b) => b[1] - a[1]);
    top10PortOption.value.xAxis.data = sortedPorts.map(item => item[0]);
    top10PortOption.value.series[0].data = sortedPorts.map(item => item[1]);
    
    // 3. 雷达图
    if (res.radar_data) {
      const { features, normal, dos, bruteforce } = res.radar_data;
      radarOption.value.radar.indicator = features.map(f => ({ name: toCN(f) }));
      radarOption.value.series[0].data = [
        { value: normal, name: '正常流量', areaStyle: { color: 'rgba(103, 194, 58, 0.3)' } },
        { value: dos, name: 'DoS/DDoS攻击', areaStyle: { color: 'rgba(230, 162, 60, 0.3)' } },
        { value: bruteforce, name: '暴力破解攻击', areaStyle: { color: 'rgba(245, 108, 108, 0.3)' } }
      ];
    }

    // 更新元数据
    const attackDist2 = res.attack_distribution;
    totalPackets.value = res.stats_metadata?.total_records || 0;
    normalPackets.value = attackDist2['0'] || 0;
    attackPackets.value = (attackDist2['1'] || 0) + (attackDist2['2'] || 0);
    attackRate.value = totalPackets.value > 0
      ? ((attackPackets.value / totalPackets.value) * 100).toFixed(2)
      : 0;
  
    // 刷新基础图表
    attackDistChart.value?.setOption(attackDistOption.value);
    top10PortChart.value?.setOption(top10PortOption.value);
    radarChart.value?.setOption(radarOption.value);

    // 渲染 EDA 图表
    if (res.confusion_matrix) renderConfusionMatrix(res.confusion_matrix);
    if (res.eda_sample) {
      renderScatterPlot(res.eda_sample);
      renderCorrelationHeatmap(res.eda_sample);
      renderBoxplot(res.eda_sample);
    }
  } catch (error) {
    console.error('加载统计数据失败：', error);
    ElMessage.warning('统计数据未就绪，请先完成模型训练。');
  }
};

const resizeAllCharts = () => {
  attackDistChart.value?.resize();
  top10PortChart.value?.resize();
  radarChart.value?.resize();
  confusionMatrixChart.value?.resize();
  scatterChart.value?.resize();
  correlationChart.value?.resize();
  boxplotChart.value?.resize();
};

onMounted(() => {
  attackDistChart.value = markRaw(echarts.init(attackDistChartRef.value));
  top10PortChart.value = markRaw(echarts.init(top10PortChartRef.value));
  radarChart.value = markRaw(echarts.init(radarChartRef.value));
  confusionMatrixChart.value = markRaw(echarts.init(confusionMatrixChartRef.value));
  scatterChart.value = markRaw(echarts.init(scatterChartRef.value));
  correlationChart.value = markRaw(echarts.init(correlationChartRef.value));
  boxplotChart.value = markRaw(echarts.init(boxplotChartRef.value));
  
  loadStatsData();
  window.addEventListener('resize', resizeAllCharts);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAllCharts);
  if (attackDistChart.value) attackDistChart.value.dispose();
  if (top10PortChart.value) top10PortChart.value.dispose();
  if (radarChart.value) radarChart.value.dispose();
  if (confusionMatrixChart.value) confusionMatrixChart.value.dispose();
  if (scatterChart.value) scatterChart.value.dispose();
  if (correlationChart.value) correlationChart.value.dispose();
  if (boxplotChart.value) boxplotChart.value.dispose();
});
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.stats-row {
  margin-top: 15px;
}

.main-row {
  margin-top: 15px;
}

.col-wrapper {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.card-header {
  font-weight: bold;
  font-size: 15px;
  color: #303133;
}

.chart-card {
  transition: all 0.3s ease;
  cursor: pointer;
  background: #fff;
}
.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
}

.chart-container {
  width: 100%;
  height: 280px;
}
.chart-container.large {
  height: 480px;
}

/* 顶部统计卡片 */
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

/* 沉浸式放大交互 */
.zoom-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  z-index: 2000;
}

.chart-card.is-zoomed {
  position: fixed;
  top: 5vh;
  left: 5vw;
  width: 90vw;
  height: 90vh;
  z-index: 2001;
  cursor: default;
  margin: 0;
  display: flex;
  flex-direction: column;
}
.chart-card.is-zoomed:hover {
  transform: none;
}

.chart-card.is-zoomed :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.chart-card.is-zoomed .chart-container {
  flex: 1;
  height: 100% !important;
}
</style>
