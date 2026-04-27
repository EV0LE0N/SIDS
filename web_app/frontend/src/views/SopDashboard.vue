<template>
  <div class="sop-dashboard">

    <!-- ===== 顶部状态栏 ===== -->
    <div class="top-bar">
      <div class="brand">
        <span class="brand-dot" :class="wsStatus === 'connected' ? 'dot-live' : 'dot-dead'"></span>
        <span class="brand-title">安全运营中心 · SOC</span>
      </div>
      <div class="top-bar-right">
        <!-- 仿真沙盘控制台 -->
        <div class="sim-console">
          <el-select
            v-model="simAttackType"
            placeholder="选择攻击类型"
            size="small"
            style="width: 130px"
          >
            <el-option label="Normal（正常）" value="Normal" />
            <el-option label="DoS（洪泛攻击）" value="DoS" />
            <el-option label="BruteForce（暴破）" value="BruteForce" />
          </el-select>

          <span class="sim-label">强度</span>
          <el-input-number
            v-model="simIntensity"
            :min="1"
            :max="10"
            :step="1"
            size="small"
            style="width: 90px"
          />

          <el-button
            type="danger"
            size="small"
            :loading="simLoading"
            @click="startSimulator"
          >
            ▶ 发动模拟
          </el-button>
          <el-button
            type="info"
            size="small"
            :loading="simLoading"
            @click="stopSimulator"
          >
            ■ 停止攻击
          </el-button>
        </div>

        <el-tag
          :type="wsStatus === 'connected' ? 'success' : wsStatus === 'connecting' ? 'warning' : 'danger'"
          size="small"
          effect="plain"
        >
          {{ wsStatusText }}
        </el-tag>
      </div>
    </div>

    <!-- ===== 统计卡片行 ===== -->
    <div class="stat-row">
      <div class="stat-card" v-for="card in statCards" :key="card.key">
        <div class="stat-icon" :style="{ background: card.bg }">{{ card.icon }}</div>
        <div class="stat-body">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value" :style="{ color: card.color }">
            {{ card.value.toLocaleString() }}
          </div>
          <div class="stat-unit">{{ card.unit }}</div>
        </div>
      </div>
    </div>

    <!-- ===== 主体区域 ===== -->
    <div class="main-body">

      <!-- 左侧：攻击趋势折线图 -->
      <div class="panel panel-chart">
        <div class="panel-header">
          <span class="panel-title">📈 攻击频次趋势</span>
          <span class="panel-sub">实线：实测 | 虚线：预测（EWMA，待接入）</span>
        </div>
        <div ref="chartRef" class="chart-container"></div>
      </div>

      <!-- 右侧：实时高危告警列表 -->
      <div class="panel panel-alerts">
        <div class="panel-header">
          <span class="panel-title">🚨 实时高危告警</span>
          <el-tag size="small" type="danger" effect="plain">{{ alertList.length }} 条</el-tag>
        </div>

        <div class="alert-list" ref="alertListRef">
          <transition-group name="alert-slide" tag="div">
            <div
              v-for="alert in alertList"
              :key="alert._uid"
              class="alert-item"
              :class="`alert-${alert.attack_type.toLowerCase()}`"
            >
              <el-tag
                :type="alert.attack_type === 'DoS' ? 'danger' : 'warning'"
                size="small"
                effect="dark"
                class="alert-badge"
              >{{ alert.attack_type }}</el-tag>
              <span class="alert-ip">{{ alert.ip }}</span>
              <div class="alert-conf">
                <el-progress
                  :percentage="+(alert.confidence * 100).toFixed(1)"
                  :color="alert.attack_type === 'DoS' ? '#f56c6c' : '#e6a23c'"
                  :show-text="false"
                  :stroke-width="6"
                  style="width: 80px"
                />
                <span class="conf-text">{{ (alert.confidence * 100).toFixed(1) }}%</span>
              </div>
              <span class="alert-time">{{ alert.time }}</span>
            </div>
          </transition-group>

          <div v-if="alertList.length === 0" class="alert-empty">
            <el-empty description="当前无高危事件" :image-size="60" />
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ─────────────────────────────────────────────
// 常量配置
// ─────────────────────────────────────────────
const WS_URL = 'ws://localhost:8000/ws/alerts'
const API_BASE = 'http://localhost:8000/api'
const MAX_TREND_POINTS = 30
const MAX_ALERTS = 50

// ─────────────────────────────────────────────
// 仿真控制台状态
// ─────────────────────────────────────────────
const simAttackType = ref('DoS')
const simIntensity = ref(3)
const simLoading = ref(false)

async function startSimulator() {
  simLoading.value = true
  try {
    await axios.post(`${API_BASE}/simulator/start`, {
      attack_type: simAttackType.value,
      intensity: simIntensity.value,
    })
    ElMessage.success(`✅ 仿真器已启动：${simAttackType.value}，强度 ${simIntensity.value}`)
  } catch (e) {
    ElMessage.error(`❌ 启动失败：${e.response?.data?.detail || e.message}`)
  } finally {
    simLoading.value = false
  }
}

async function stopSimulator() {
  simLoading.value = true
  try {
    await axios.post(`${API_BASE}/simulator/stop`)
    ElMessage.info('⏹ 仿真器已停止')
  } catch (e) {
    ElMessage.error(`❌ 停止失败：${e.response?.data?.detail || e.message}`)
  } finally {
    simLoading.value = false
  }
}

// ─────────────────────────────────────────────
// WebSocket 状态
// ─────────────────────────────────────────────
const wsStatus = ref('disconnected')
const wsStatusText = computed(() => ({
  connected: '● LIVE',
  connecting: '○ 连接中...',
  disconnected: '✕ 离线',
}[wsStatus.value] || '✕ 离线'))

let ws = null
let reconnectTimer = null
let _uidCounter = 0

// ─────────────────────────────────────────────
// 统计卡片
// ─────────────────────────────────────────────
const stats = reactive({ total: 0, normal: 0, attack: 0, batches: 0 })

const statCards = computed(() => [
  { key: 'total',   label: '累计监测',  value: stats.total,   color: '#303133', icon: '📦', bg: '#ecf5ff', unit: '条记录' },
  { key: 'normal',  label: '正常流量',  value: stats.normal,  color: '#67c23a', icon: '✅', bg: '#f0f9eb', unit: '条' },
  { key: 'attack',  label: '高危攻击',  value: stats.attack,  color: '#f56c6c', icon: '🔥', bg: '#fef0f0', unit: '条' },
  { key: 'batches', label: '微批总计',  value: stats.batches, color: '#409eff', icon: '📡', bg: '#ecf5ff', unit: '批次' },
])

// ─────────────────────────────────────────────
// 折线图
// ─────────────────────────────────────────────
const chartRef = ref(null)
let chartInstance = null

const trendTimes = ref([])
const trendActual = ref([])
const trendForecast = ref([])

function initChart() {
  if (!chartRef.value) return
  // 明亮主题：不传 'dark'
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(buildChartOption())
}

function buildChartOption() {
  return {
    backgroundColor: '#ffffff',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['实测攻击频次', 'EWMA 预测（待接入）'],
      textStyle: { color: '#606266', fontSize: 12 },
      top: 8,
    },
    grid: { left: '4%', right: '4%', bottom: '8%', top: '16%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trendTimes.value,
      axisLabel: { color: '#909399', fontSize: 11, rotate: 30 },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '攻击条数',
      nameTextStyle: { color: '#909399' },
      axisLabel: { color: '#909399' },
      splitLine: { lineStyle: { color: '#f2f3f5', type: 'dashed' } },
    },
    series: [
      {
        name: '实测攻击频次',
        type: 'line',
        data: trendActual.value,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: '#f56c6c', width: 2 },
        itemStyle: { color: '#f56c6c' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245,108,108,0.2)' },
            { offset: 1, color: 'rgba(245,108,108,0.01)' },
          ]),
        },
      },
      {
        name: 'EWMA 预测（待接入）',
        type: 'line',
        data: trendForecast.value,
        smooth: true,
        lineStyle: { color: '#e6a23c', width: 2, type: 'dashed' },
        itemStyle: { color: '#e6a23c' },
        symbol: 'none',
      },
    ],
  }
}

function pushTrendPoint(timestamp, attackCount) {
  const label = new Date(timestamp * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
  trendTimes.value.push(label)
  trendActual.value.push(attackCount)
  trendForecast.value.push(null)

  if (trendTimes.value.length > MAX_TREND_POINTS) {
    trendTimes.value.shift()
    trendActual.value.shift()
    trendForecast.value.shift()
  }

  if (chartInstance) {
    chartInstance.setOption({
      xAxis: { data: trendTimes.value },
      series: [{ data: trendActual.value }, { data: trendForecast.value }],
    })
  }
}

// ─────────────────────────────────────────────
// 告警列表
// ─────────────────────────────────────────────
const alertList = ref([])
const alertListRef = ref(null)
const NORMAL_TYPE = 'Normal'

function pushAlerts(alerts) {
  if (!alerts || alerts.length === 0) return
  const now = new Date().toLocaleTimeString('zh-CN')
  const newItems = alerts.map(a => ({ ...a, time: now, _uid: ++_uidCounter }))
  alertList.value = [...newItems, ...alertList.value].slice(0, MAX_ALERTS)
  nextTick(() => { if (alertListRef.value) alertListRef.value.scrollTop = 0 })
}

// ─────────────────────────────────────────────
// WebSocket 消息处理
// ─────────────────────────────────────────────
function handleMessage(raw) {
  let data
  try { data = JSON.parse(raw) } catch { return }
  if (data.type !== 'realtime_update') return

  const bs = data.batch_stats || {}
  const total = bs.total || 0
  const normalCount = bs[NORMAL_TYPE] || 0
  const attackCount = total - normalCount

  stats.total   += total
  stats.normal  += normalCount
  stats.attack  += attackCount
  stats.batches += 1

  pushTrendPoint(data.timestamp, attackCount)
  pushAlerts(data.alerts || [])
}

// ─────────────────────────────────────────────
// WebSocket 生命周期
// ─────────────────────────────────────────────
function connectWS() {
  wsStatus.value = 'connecting'
  ws = new WebSocket(WS_URL)
  ws.onopen = () => {
    wsStatus.value = 'connected'
    ws._heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)
  }
  ws.onmessage = (event) => handleMessage(event.data)
  ws.onerror = (err) => console.warn('[SOC] WebSocket 错误:', err)
  ws.onclose = () => {
    wsStatus.value = 'disconnected'
    clearInterval(ws._heartbeat)
    reconnectTimer = setTimeout(connectWS, 5000)
  }
}

function disconnectWS() {
  clearTimeout(reconnectTimer)
  if (ws) {
    ws.onclose = null
    clearInterval(ws._heartbeat)
    ws.close()
    ws = null
  }
  wsStatus.value = 'disconnected'
}

function handleResize() { chartInstance?.resize() }

onMounted(() => {
  initChart()
  connectWS()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  disconnectWS()
  chartInstance?.dispose()
  chartInstance = null
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* ── 整体页面：明亮白底 ── */
.sop-dashboard {
  min-height: 100%;
  background: #f5f7fa;
  color: #303133;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 顶部状态栏 ── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #ffffff;
  border-bottom: 1px solid #ebeef5;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.brand { display: flex; align-items: center; gap: 10px; }
.brand-title { font-size: 16px; font-weight: 700; color: #303133; letter-spacing: 0.5px; }

.brand-dot {
  width: 10px; height: 10px; border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}
.dot-live  { background: #67c23a; }
.dot-dead  { background: #c0c4cc; animation: none; }

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(1.3); }
}

.top-bar-right { display: flex; align-items: center; gap: 10px; }

/* ── 仿真控制台 ── */
.sim-console {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
}
.sim-label { font-size: 12px; color: #606266; white-space: nowrap; }

/* ── 统计卡片行 ── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 0 20px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s, transform 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  transform: translateY(-2px);
}

.stat-icon {
  width: 48px; height: 48px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-body { flex: 1; min-width: 0; }
.stat-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.stat-value { font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; }
.stat-unit  { font-size: 11px; color: #c0c4cc; margin-top: 2px; }

/* ── 主体区域 ── */
.main-body {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 16px;
  padding: 0 20px 20px;
  flex: 1;
  min-height: 0;
}

/* ── 面板通用 ── */
.panel {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f2f3f5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  background: #fafafa;
}
.panel-title { font-size: 14px; font-weight: 600; color: #303133; }
.panel-sub   { font-size: 11px; color: #c0c4cc; }

/* ── 折线图 ── */
.chart-container { flex: 1; min-height: 300px; }

/* ── 告警列表 ── */
.panel-alerts { min-height: 0; }

.alert-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  border-left: 3px solid transparent;
  background: #fafafa;
  font-size: 12px;
  transition: background 0.2s;
  flex-wrap: nowrap;
}
.alert-item:hover { background: #f5f7fa; }

.alert-dos        { border-left-color: #f56c6c; }
.alert-bruteforce { border-left-color: #e6a23c; }

.alert-badge { flex-shrink: 0; }
.alert-ip {
  flex: 1; font-family: monospace; font-size: 11px; color: #409eff;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.alert-conf { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.conf-text  { font-size: 11px; color: #606266; white-space: nowrap; }
.alert-time { font-size: 10px; color: #c0c4cc; flex-shrink: 0; white-space: nowrap; }

.alert-empty {
  flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px;
}

/* ── 动画 ── */
.alert-slide-enter-active { transition: all 0.25s ease; }
.alert-slide-enter-from   { opacity: 0; transform: translateY(-8px); }
.alert-slide-leave-active { transition: all 0.15s ease; position: absolute; }
.alert-slide-leave-to     { opacity: 0; }

/* ── 滚动条 ── */
.alert-list::-webkit-scrollbar { width: 4px; }
.alert-list::-webkit-scrollbar-track { background: transparent; }
.alert-list::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
</style>
