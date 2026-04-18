<template>
  <div class="detect-container">
    <el-page-header content="网络攻击检测" />
    
    <el-row :gutter="20" class="detect-content">
      <!-- 左侧：文件上传和检测区域 -->
      <el-col :span="12">
        <el-card shadow="hover" class="upload-card">
          <template #header>
            <div class="card-header">
              <el-icon><UploadFilled /></el-icon>
              <span>上传网络流量数据</span>
            </div>
          </template>
          
          <div class="upload-area">
            <el-upload
              class="upload-demo"
              drag
              action="/api/predict"
              :headers="uploadHeaders"
              :data="uploadData"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :show-file-list="false"
              accept=".csv"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <div class="el-upload__tip">
                支持 CSV 格式，文件大小不超过 500MB
              </div>
            </el-upload>
            
            <div class="upload-info">
              <el-alert
                title="上传说明"
                type="info"
                :closable="false"
                description="上传包含网络流量特征的数据文件，系统将使用训练好的XGBoost模型进行攻击检测。"
              />
            </div>
          </div>
          
          <div class="detect-actions">
            <el-button 
              type="primary" 
              :loading="detecting" 
              :disabled="!selectedFile"
              @click="handleDetect"
            >
              <el-icon><Search /></el-icon>
              开始检测
            </el-button>
            <el-button @click="resetDetection">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </div>
        </el-card>
        
        <!-- 检测结果 -->
        <el-card shadow="hover" class="result-card" v-if="detectionStats">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>检测结果</span>
            </div>
          </template>
          
          <div class="result-content">
            <div class="result-summary">
              <div class="result-item" :class="getResultClass(detectionStats)">
                <div class="result-label">总体检测结果</div>
                <div class="result-value">{{ getResultText(detectionStats) }}</div>
              </div>
              
              <div class="result-stats">
                <div class="stat-item">
                  <div class="stat-label">处理记录数</div>
                  <div class="stat-value">{{ detectionStats.total }}</div>
                </div>
              </div>
            </div>
            
            <el-divider />
            
            <div class="result-details">
              <div class="detail-header">详细检测结果</div>
              <el-table
                :data="detectionDetails"
                stripe
                style="width: 100%"
                max-height="300"
              >
                <el-table-column prop="row_id" label="记录ID" width="100" />
                <el-table-column prop="type" label="预测结果" width="120">
                  <template #default="scope">
                    <el-tag :type="getPredictionTagType(scope.row.type)">
                      {{ scope.row.type }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="140">
                  <template #default="scope">
                    <el-progress 
                      :percentage="Math.round(scope.row.confidence * 100)" 
                      :status="getConfidenceStatus(scope.row.confidence)"
                      :show-text="false"
                    />
                    <span style="margin-left: 10px">{{ (scope.row.confidence * 100).toFixed(1) }}%</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：检测统计和说明 -->
      <el-col :span="12">
        <el-card shadow="hover" class="stats-card">
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>检测统计</span>
            </div>
          </template>
          
          <div class="stats-content">
            <div class="stats-chart" ref="detectStatsChartRef"></div>
            
            <div class="stats-info">
              <el-descriptions title="模型信息" :column="1" border>
                <el-descriptions-item label="模型名称">XGBoost攻击检测模型</el-descriptions-item>
                <el-descriptions-item label="训练准确率">{{ modelInfo.accuracy }}%</el-descriptions-item>
                <el-descriptions-item label="特征数量">{{ modelInfo.feature_count }}</el-descriptions-item>
                <el-descriptions-item label="最后训练时间">{{ modelInfo.last_trained }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </el-card>
        
        <el-card shadow="hover" class="help-card">
          <template #header>
            <div class="card-header">
              <el-icon><QuestionFilled /></el-icon>
              <span>使用说明</span>
            </div>
          </template>
          
          <div class="help-content">
            <el-steps direction="vertical" :active="4">
              <el-step title="准备数据">
                <template #description>
                  <p>准备包含网络流量特征的数据文件，确保包含以下特征：</p>
                  <ul>
                    <li>流量持续时间、数据包大小、协议类型等</li>
                    <li>源/目标IP地址、端口号</li>
                    <li>流量统计特征（如包数量、字节数等）</li>
                  </ul>
                </template>
              </el-step>
              <el-step title="上传文件">
                <template #description>
                  <p>点击上传区域或拖拽文件到指定区域，支持CSV和Parquet格式。</p>
                </template>
              </el-step>
              <el-step title="开始检测">
                <template #description>
                  <p>点击"开始检测"按钮，系统将使用训练好的模型进行分析。</p>
                </template>
              </el-step>
              <el-step title="查看结果">
                <template #description>
                  <p>查看检测结果，包括总体判断、详细记录和置信度分析。</p>
                </template>
              </el-step>
            </el-steps>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { 
  UploadFilled, Search, Refresh, Document, 
  DataAnalysis, QuestionFilled 
} from '@element-plus/icons-vue'
import { uploadPredict } from '@/api/predict'

// 上传相关
const selectedFile = ref(null)
const detecting = ref(false)
const uploadHeaders = ref({
  'Content-Type': 'multipart/form-data'
})
const uploadData = ref({})

// 检测结果（严格使用 stats + details 二元结构）
const detectionStats = ref(null)
const detectionDetails = ref([])

// 模型信息
const modelInfo = ref({
  accuracy: '85.3',
  feature_count: 42,
  last_trained: '2024-01-15'
})

// 图表实例
const detectStatsChart = ref(null)
const detectStatsChartRef = ref(null)

// 上传前处理
const beforeUpload = (file) => {
  const isCSV = file.name.toLowerCase().endsWith('.csv')
  const isLt500M = file.size / 1024 / 1024 < 500
  
  if (!isCSV) {
    ElMessage.error('只能上传 CSV 格式的文件!')
    return false
  }
  if (!isLt500M) {
    ElMessage.error('文件大小不能超过 500MB!')
    return false
  }
  
  selectedFile.value = file
  return true
}

// 上传成功处理
const handleUploadSuccess = (response, file) => {
  ElMessage.success('文件上传成功！')
  selectedFile.value = file
}

// 上传错误处理
const handleUploadError = (error, file) => {
  console.error('上传失败:', error)
  ElMessage.error('文件上传失败，请重试！')
  selectedFile.value = null
}

// 开始检测
const handleDetect = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要检测的文件')
    return
  }
  
  detecting.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const response = await uploadPredict(formData)
    // API 返回结构：{ status: 'success', result: { stats: {...}, details: [...] } }
    const resultData = response.result
    detectionStats.value = resultData.stats
    detectionDetails.value = resultData.details
    
    // 更新统计图表
    updateStatsChart(resultData.stats)
    
    ElMessage.success('检测完成！')
  } catch (error) {
    console.error('检测失败:', error)
    ElMessage.error('检测失败：' + (error.message || '未知错误'))
  } finally {
    detecting.value = false
  }
}

// 重置检测
const resetDetection = () => {
  ElMessageBox.confirm('确定要重置检测结果吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    selectedFile.value = null
    detectionStats.value = null
    detectionDetails.value = []
    ElMessage.success('已重置')
  }).catch(() => {})
}

// 获取结果样式类
const getResultClass = (stats) => {
  if (!stats) return 'result-normal'
  const hasAttack = (stats.dos || 0) + (stats.bruteforce || 0) > 0
  return hasAttack ? 'result-attack' : 'result-normal'
}

// 获取结果文本
const getResultText = (stats) => {
  if (!stats) return '未知状态'
  const hasAttack = (stats.dos || 0) + (stats.bruteforce || 0) > 0
  return hasAttack ? '检测到攻击' : '正常流量'
}

// 获取预测标签类型
const getPredictionTagType = (type) => {
  if (type === '正常流量') return 'success'
  if (type === 'DoS攻击') return 'danger'
  if (type === '暴力破解') return 'warning'
  return 'info'
}

// 获取置信度状态
const getConfidenceStatus = (confidence) => {
  if (confidence >= 0.9) return 'success'
  if (confidence >= 0.7) return 'warning'
  return 'exception'
}

// 更新统计图表
const updateStatsChart = (stats) => {
  if (!detectStatsChart.value || !stats) return
   
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'center'
    },
    series: [
      {
        name: '检测结果分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: stats.normal || 0, name: '正常流量' },
          { value: stats.dos || 0, name: 'DoS/DDoS攻击' },
          { value: stats.bruteforce || 0, name: '暴力破解攻击' }
        ]
      }
    ]
  }
  
  detectStatsChart.value.setOption(option)
}

// 初始化图表
onMounted(() => {
  if (detectStatsChartRef.value) {
    detectStatsChart.value = echarts.init(detectStatsChartRef.value)
    
    // 初始空图表
    const initialOption = {
      title: {
        text: '暂无检测数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14,
          fontWeight: 'normal'
        }
      },
      graphic: {
        type: 'text',
        left: 'center',
        top: '45%',
        style: {
          text: '请上传文件开始检测',
          fill: '#ccc',
          fontSize: 12
        }
      }
    }
    detectStatsChart.value.setOption(initialOption)
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

// 处理窗口大小变化
const handleResize = () => {
  if (detectStatsChart.value) {
    detectStatsChart.value.resize()
  }
}

// 组件卸载时清理
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (detectStatsChart.value) {
    detectStatsChart.value.dispose()
  }
})
</script>

<style scoped>
.detect-container {
  padding: 20px;
}

.detect-content {
  margin-top: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.upload-card,
.result-card,
.stats-card,
.help-card {
  margin-bottom: 20px;
}

.upload-area {
  padding: 20px;
}

.upload-info {
  margin-top: 20px;
}

.detect-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  justify-content: center;
}

.result-content {
  padding: 10px;
}

.result-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.result-item {
  padding: 15px 25px;
  border-radius: 8px;
  text-align: center;
  min-width: 200px;
}

.result-normal {
  background-color: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.result-attack {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

.result-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.result-value {
  font-size: 24px;
  font-weight: bold;
}

.result-stats {
  display: flex;
  gap: 30px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.detail-header {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-chart {
  width: 100%;
  height: 300px;
}

.stats-info {
  margin-top: 10px;
}

.help-content {
  padding: 10px;
}

.help-content ul {
  margin: 5px 0;
  padding-left: 20px;
  color: #606266;
}

.help-content li {
  margin: 3px 0;
  font-size: 13px;
}
</style>