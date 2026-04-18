<template>
  <div class="eda-analysis-container">
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>多分类混淆矩阵热力图</span>
        </div>
      </template>
      <div ref="confusionMatrixChart" class="chart-container"></div>
    </el-card>

    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>二维聚类散点图（PCA降维）</span>
        </div>
      </template>
      <div ref="scatterChart" class="chart-container"></div>
    </el-card>

    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>皮尔逊相关系数热力图</span>
        </div>
      </template>
      <div ref="correlationChart" class="chart-container"></div>
    </el-card>

    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>特征分布箱线图</span>
        </div>
      </template>
      <div ref="boxplotChart" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts';
import { onMounted, onBeforeUnmount, ref } from 'vue';

export default {
  name: 'EdaAnalysis',
  setup() {
    const confusionMatrixChart = ref(null);
    const scatterChart = ref(null);
    const correlationChart = ref(null);
    const boxplotChart = ref(null);

    let confusionMatrixInstance = null;
    let scatterInstance = null;
    let correlationInstance = null;
    let boxplotInstance = null;

    // 获取统计数据
    const fetchStatsData = async () => {
      try {
        const response = await fetch('/api/stats');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Failed to fetch stats data:', error);
        return null;
      }
    };

    // 渲染混淆矩阵热力图
    const renderConfusionMatrix = (confusionMatrixData) => {
      if (!confusionMatrixInstance || !confusionMatrixData) return;

      const labels = ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'];
      const matrixData = confusionMatrixData.matrix;

      const option = {
        tooltip: {
          position: 'top'
        },
        grid: {
          height: '60%',
          top: '10%'
        },
        xAxis: {
          type: 'category',
          data: labels,
          splitArea: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: labels,
          splitArea: {
            show: true
          }
        },
        visualMap: {
          min: 0,
          max: Math.max(...matrixData.flat()),
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '15%'
        },
        series: [{
          name: '混淆矩阵',
          type: 'heatmap',
          data: matrixData.map((row, i) => 
            row.map((value, j) => [j, i, value])
          ).flat(),
          label: {
            show: true,
            color: '#000'
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      };

      confusionMatrixInstance.setOption(option);
    };

    // 渲染散点聚类图
    const renderScatterPlot = (edaSampleData) => {
      if (!scatterInstance || !edaSampleData?.scatter_data) return;

      const scatterData = edaSampleData.scatter_data;
      
      // 解析 scatter_data: [[x, y, label], ...]
      const sampleSize = Math.min(500, scatterData.length);
      const sampledData = scatterData.slice(0, sampleSize);

      const labelNames = ['正常流量', 'DoS/DDoS攻击', '暴力破解攻击'];
      const seriesData = [[], [], []];
      
      for (let i = 0; i < sampledData.length; i++) {
        const [x, y, label] = sampledData[i];
        if (label >= 0 && label < 3) {
          seriesData[label].push([x, y]);
        }
      }

      const option = {
        tooltip: {
          trigger: 'item',
          formatter: (params) => {
            return `${labelNames[params.seriesIndex]}<br/>X: ${params.value[0].toFixed(2)}<br/>Y: ${params.value[1].toFixed(2)}`;
          }
        },
        legend: {
          data: labelNames,
          bottom: '0%'
        },
        grid: {
          left: '10%',
          right: '10%',
          bottom: '15%',
          top: '10%'
        },
        xAxis: {
          type: 'value',
          name: '第一主成分'
        },
        yAxis: {
          type: 'value',
          name: '第二主成分'
        },
        series: labelNames.map((name, index) => ({
          name: name,
          type: 'scatter',
          data: seriesData[index],
          symbolSize: 6,
          emphasis: {
            focus: 'series'
          }
        }))
      };

      scatterInstance.setOption(option);
    };

    // 渲染相关系数热力图
    const renderCorrelationHeatmap = (edaSampleData) => {
      if (!correlationInstance || !edaSampleData?.correlation_matrix) return;

      const { features, values: matrix } = edaSampleData.correlation_matrix;
      
      // 限制特征数量以防止性能问题
      const maxFeatures = 15;
      const displayFeatures = features.slice(0, maxFeatures);
      const displayMatrix = matrix.slice(0, maxFeatures).map(row => row.slice(0, maxFeatures));

      const option = {
        tooltip: {
          position: 'top'
        },
        grid: {
          height: '70%',
          top: '10%',
          left: '15%',
          right: '10%'
        },
        xAxis: {
          type: 'category',
          data: displayFeatures,
          axisLabel: {
            rotate: 45,
            fontSize: 10
          },
          splitArea: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: displayFeatures.slice().reverse(),
          axisLabel: {
            fontSize: 10
          },
          splitArea: {
            show: true
          }
        },
        visualMap: {
          min: -1,
          max: 1,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '5%'
        },
        series: [{
          name: '相关系数',
          type: 'heatmap',
          data: displayMatrix.map((row, i) => 
            row.map((value, j) => [j, displayFeatures.length - 1 - i, value])
          ).flat(),
          label: {
            show: true,
            formatter: (params) => {
              return Math.abs(params.value[2]) > 0.5 ? params.value[2].toFixed(2) : '';
            },
            color: '#000',
            fontSize: 9
          }
        }]
      };

      correlationInstance.setOption(option);
    };

    // 渲染箱线图
    const renderBoxplot = (edaSampleData) => {
      if (!boxplotInstance || !edaSampleData?.boxplot_data) return;

      const boxplotData = edaSampleData.boxplot_data;
      
      // 计算每个攻击类型的5数统计
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
              `最大值: ${data[4]?.toFixed(2)}`,
              `上四分位: ${data[3]?.toFixed(2)}`,
              `中位数: ${data[2]?.toFixed(2)}`,
              `下四分位: ${data[1]?.toFixed(2)}`,
              `最小值: ${data[0]?.toFixed(2)}`
            ].join('<br/>');
          }
        },
        grid: {
          left: '10%',
          right: '10%',
          bottom: '15%',
          top: '10%'
        },
        xAxis: {
          type: 'category',
          data: categories,
          axisLabel: {
            fontSize: 12
          }
        },
        yAxis: {
          type: 'value',
          name: '特征值'
        },
        series: [{
          name: '特征分布',
          type: 'boxplot',
          data: seriesData,
          tooltip: {
            formatter: (param) => {
              const data = param.data;
              return [
                `${param.seriesName}`,
                `最大值: ${data[4]?.toFixed(2)}`,
                `上四分位: ${data[3]?.toFixed(2)}`,
                `中位数: ${data[2]?.toFixed(2)}`,
                `下四分位: ${data[1]?.toFixed(2)}`,
                `最小值: ${data[0]?.toFixed(2)}`
              ].join('<br/>');
            }
          }
        }]
      };

      boxplotInstance.setOption(option);
    };

    // 初始化图表实例
    const initCharts = () => {
      if (confusionMatrixChart.value) {
        confusionMatrixInstance = echarts.init(confusionMatrixChart.value);
      }
      if (scatterChart.value) {
        scatterInstance = echarts.init(scatterChart.value);
      }
      if (correlationChart.value) {
        correlationInstance = echarts.init(correlationChart.value);
      }
      if (boxplotChart.value) {
        boxplotInstance = echarts.init(boxplotChart.value);
      }
    };

    // 加载并渲染所有图表
    const loadAndRenderCharts = async () => {
      const statsData = await fetchStatsData();
      if (!statsData) return;

      // 渲染混淆矩阵
      if (statsData.confusion_matrix) {
        renderConfusionMatrix(statsData.confusion_matrix);
      }

      // 渲染EDA图表
      if (statsData.eda_sample) {
        renderScatterPlot(statsData.eda_sample);
        renderCorrelationHeatmap(statsData.eda_sample);
        renderBoxplot(statsData.eda_sample);
      }
    };

    // 响应式处理
    const resizeCharts = () => {
      if (confusionMatrixInstance) confusionMatrixInstance.resize();
      if (scatterInstance) scatterInstance.resize();
      if (correlationInstance) correlationInstance.resize();
      if (boxplotInstance) boxplotInstance.resize();
    };

    onMounted(() => {
      initCharts();
      loadAndRenderCharts();
      window.addEventListener('resize', resizeCharts);
    });

    onBeforeUnmount(() => {
      window.removeEventListener('resize', resizeCharts);
      if (confusionMatrixInstance) confusionMatrixInstance.dispose();
      if (scatterInstance) scatterInstance.dispose();
      if (correlationInstance) correlationInstance.dispose();
      if (boxplotInstance) boxplotInstance.dispose();
    });

    return {
      confusionMatrixChart,
      scatterChart,
      correlationChart,
      boxplotChart
    };
  }
};
</script>

<style scoped>
.eda-analysis-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.chart-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.chart-container {
  width: 100%;
  height: 400px;
}
</style>