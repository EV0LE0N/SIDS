<template>
  <div class="sop-dashboard">

    <!-- ===== 顶部状态栏 ===== -->
    <div class="top-bar">
      <div class="brand">
        <span class="brand-dot" :class="wsStatus === 'connected' ? 'dot-live' : 'dot-dead'"></span>
        <span class="brand-title">安全运营中心 · SOC</span>
      </div>
      <div class="top-bar-right">
        <!-- 被动雷达开关（替代原有攻击选择沙盘） -->
        <div class="radar-switch">
          <span class="radar-label">📡 全路段雷达监测</span>
          <el-switch
            v-model="radarActive"
            active-text="运行"
            inactive-text="待机"
            :loading="radarLoading"
            active-color="#67c23a"
            @change="handleRadarToggle"
          />
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

    <!-- ===== 主体区域：上下两行布局 ===== -->
    <div class="main-body">

      <!-- 上行：折线图（宽） + 饼图 -->
      <div class="top-row">
        <!-- 左：攻击趋势折线图 -->
        <div class="panel panel-chart">
          <div class="panel-header">
            <span class="panel-title">📈 实时攻击频次</span>
            <span class="panel-sub">基于微批窗口的攻击条数统计</span>
          </div>
          <div ref="chartRef" class="chart-container"></div>
        </div>

        <!-- 右：攻击类型分布饼图 -->
        <div class="panel panel-pie">
          <div class="panel-header">
            <span class="panel-title">🎯 攻击类型分布</span>
            <span class="panel-sub">实时占比统计</span>
          </div>
          <div ref="pieChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 下行： DoS预警 + BruteForce预警 + 告警列表 -->
      <div class="bottom-row">
        <!-- DoS 洪峰预警榜 -->
        <div class="threat-board threat-dos">
          <div class="tb-header">
            <span class="tb-icon">🔴</span>
            <span class="tb-title">DoS 洪峰预警</span>
            <span class="tb-sub">高危受击节点 Top 3</span>
          </div>
          <div class="tb-body">
            <div v-if="predictedTargets.DoS.length === 0" class="tb-empty">暂无高危节点</div>
            <div
              v-for="(node, idx) in predictedTargets.DoS"
              :key="'dos-' + node.ip"
              class="tb-row"
              :class="`tb-level-${node.level.toLowerCase()}`"
            >
              <span class="tb-rank">{{ idx + 1 }}</span>
              <span class="tb-ip">{{ node.ip }}</span>
              <el-tag :type="node.level === 'Danger' ? 'danger' : 'warning'" size="small" effect="dark" class="tb-tag">
                {{ node.level === 'Danger' ? '⚠ 洪峰' : node.level === 'Warning' ? '↑ 升温' : '◉ 观察' }}
              </el-tag>
              <el-button type="danger" size="small" text class="tb-action" @click="blockByIp(node.ip)">封禁 ⚡</el-button>
            </div>
          </div>
        </div>

        <!-- BruteForce 爆破预警榜 -->
        <div class="threat-board threat-bf">
          <div class="tb-header">
            <span class="tb-icon">🟠</span>
            <span class="tb-title">BruteForce 爆破预警</span>
            <span class="tb-sub">高危受击节点 Top 3</span>
          </div>
          <div class="tb-body">
            <div v-if="predictedTargets.BruteForce.length === 0" class="tb-empty">暂无高危节点</div>
            <div
              v-for="(node, idx) in predictedTargets.BruteForce"
              :key="'bf-' + node.ip"
              class="tb-row"
              :class="`tb-level-${node.level.toLowerCase()}`"
            >
              <span class="tb-rank">{{ idx + 1 }}</span>
              <span class="tb-ip">{{ node.ip }}</span>
              <el-tag :type="node.level === 'Danger' ? 'danger' : 'warning'" size="small" effect="dark" class="tb-tag">
                {{ node.level === 'Danger' ? '⚠ 爆发' : node.level === 'Warning' ? '↑ 升温' : '◉ 观察' }}
              </el-tag>
              <el-button type="danger" size="small" text class="tb-action" @click="blockByIp(node.ip)">封禁 ⚡</el-button>
            </div>
          </div>
        </div>

        <!-- 实时高危告警列表 -->
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
                <div class="alert-left">
                  <el-tag
                    :type="alert.attack_type === 'DoS' ? 'danger' : 'warning'"
                    size="small"
                    effect="dark"
                    class="alert-badge"
                  >{{ alert.attack_type }}</el-tag>
                  <span class="alert-ip">{{ alert.ip }}</span>
                </div>
                <div class="alert-right">
                  <div class="alert-conf">
                    <el-progress
                      :percentage="+(alert.confidence * 100).toFixed(1)"
                      :color="alert.attack_type === 'DoS' ? '#f56c6c' : '#e6a23c'"
                      :show-text="false"
                      :stroke-width="6"
                      style="width: 70px"
                    />
                    <span class="conf-text">{{ (alert.confidence * 100).toFixed(1) }}%</span>
                  </div>
                  <el-button
                    type="danger"
                    size="small"
                    text
                    class="handle-btn"
                    @click="blockByIp(alert.ip)"
                  >
                    一键封禁 ⚡
                  </el-button>
                </div>
              </div>
            </transition-group>

            <div v-if="alertList.length === 0" class="alert-empty">
              <el-empty description="当前无高危事件" :image-size="60" />
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, onActivated, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// ─────────────────────────────────────────────
// 常量配置
// ─────────────────────────────────────────────
const WS_URL = 'ws://localhost:8000/ws/alerts'
const API_BASE = 'http://localhost:8000/api'
const MAX_TREND_POINTS = 30
const MAX_ALERTS = 50

// ─────────────────────────────────────────────
// 被动雷达开关（替代原有仿真沙盘）
// ─────────────────────────────────────────────
const radarActive = ref(false)
const radarLoading = ref(false)

async function handleRadarToggle(active) {
  radarLoading.value = true
  try {
    if (active) {
      await axios.post(`${API_BASE}/simulator/start`)
      ElMessage.success('📡 雷达已启动，正在监测全路段真实流量...')
    } else {
      await axios.post(`${API_BASE}/simulator/stop`)
      ElMessage.info('⏹ 雷达已关闭')
    }
  } catch (e) {
    ElMessage.error(`操作失败：${e.response?.data?.detail || e.message}`)
    radarActive.value = !active
  } finally {
    radarLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 一键封禁（直接调 API，不跳页面）
// ─────────────────────────────────────────────
async function blockByIp(ip) {
  try {
    await ElMessageBox.confirm(
      `确认封禁节点 ${ip} 吗？封禁后可在「探针资产管理」页面解封。`,
      '⚡ 一键封禁',
      { type: 'warning', confirmButtonText: '立即封禁', cancelButtonText: '取消' }
    )
    const res = await axios.post(`${API_BASE}/assets/block-by-ip`, { ip })
    if (res.data.already_blocked) {
      ElMessage.warning(`${ip} 已处于封禁状态`)
    } else {
      ElMessage.success(`🔒 已封禁：${res.data.message}`)
    }
  } catch (e) {
    if (e === 'cancel' || e?.toString?.().includes('cancel')) return
    ElMessage.error(`封禁失败：${e.response?.data?.detail || e.message}`)
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
// 攻击类型分布（饼图数据）
// ─────────────────────────────────────────────
const pieData = reactive({ Normal: 0, DoS: 0, BruteForce: 0 })

// ─────────────────────────────────────────────
// 折线图
// ─────────────────────────────────────────────
const chartRef = ref(null)
let chartInstance = null

const trendTimes = ref([])
const trendActual = ref([])

function initChart() {
  if (!chartRef.value) return
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
      data: ['实测攻击频次'],
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
    ],
  }
}

function pushTrendPoint(timestamp, attackCount) {
  const label = new Date(timestamp * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
  trendTimes.value.push(label)
  trendActual.value.push(attackCount)

  if (trendTimes.value.length > MAX_TREND_POINTS) {
    trendTimes.value.shift()
    trendActual.value.shift()
  }

  if (chartInstance) {
    chartInstance.setOption({
      xAxis: { data: trendTimes.value },
      series: [{ data: trendActual.value }],
    })
  }
}

// ─────────────────────────────────────────────
// 杀伤链早期探测：节点级预警状态
// ─────────────────────────────────────────────
const predictedTargets = reactive({
  DoS: [],
  BruteForce: [],
})

// ─────────────────────────────────────────────
// 饼图
// ─────────────────────────────────────────────
const pieChartRef = ref(null)
let pieChartInstance = null

function initPieChart() {
  if (!pieChartRef.value) return
  pieChartInstance = echarts.init(pieChartRef.value)
  pieChartInstance.setOption(buildPieOption())
}

function buildPieOption() {
  return {
    backgroundColor: '#ffffff',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'horizontal',
      bottom: 8,
      textStyle: { color: '#606266', fontSize: 12 },
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data: [
        { value: pieData.Normal, name: 'Normal', itemStyle: { color: '#67c23a' } },
        { value: pieData.DoS, name: 'DoS', itemStyle: { color: '#f56c6c' } },
        { value: pieData.BruteForce, name: 'BruteForce', itemStyle: { color: '#e6a23c' } },
      ],
    }],
  }
}

function updatePieChart() {
  if (!pieChartInstance) return
  pieChartInstance.setOption({
    series: [{
      data: [
        { value: pieData.Normal, name: 'Normal', itemStyle: { color: '#67c23a' } },
        { value: pieData.DoS, name: 'DoS', itemStyle: { color: '#f56c6c' } },
        { value: pieData.BruteForce, name: 'BruteForce', itemStyle: { color: '#e6a23c' } },
      ],
    }],
  })
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

  // 更新饼图累计
  pieData.Normal += (bs.Normal || 0)
  pieData.DoS += (bs.DoS || 0)
  pieData.BruteForce += (bs.BruteForce || 0)
  updatePieChart()

  pushTrendPoint(data.timestamp, attackCount)

  // 更新节点级杀伤链预警
  if (data.predicted_targets) {
    predictedTargets.DoS = data.predicted_targets.DoS || []
    predictedTargets.BruteForce = data.predicted_targets.BruteForce || []
  }

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

function handleResize() {
  chartInstance?.resize()
  pieChartInstance?.resize()
}

onMounted(() => {
  initChart()
  initPieChart()
  connectWS()
  window.addEventListener('resize', handleResize)
})

// keep-alive 激活时：ECharts 画布可能因隐藏期间尺寸失准，强制 resize
onActivated(() => {
  nextTick(() => {
    chartInstance?.resize()
    pieChartInstance?.resize()
  })
})

onBeforeUnmount(() => {
  disconnectWS()
  chartInstance?.dispose()
  chartInstance = null
  pieChartInstance?.dispose()
  pieChartInstance = null
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* ── 整体页面：明亮白底 ── */
.sop-dashboard {
  height: 100%;
  overflow: hidden;
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

.top-bar-right { display: flex; align-items: center; gap: 14px; }

/* ── 雷达开关 ── */
.radar-switch {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}
.radar-label { font-size: 13px; color: #303133; font-weight: 500; white-space: nowrap; }

/* ── 统计卡片行 ── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 0 20px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  transition: box-shadow 0.25s, transform 0.25s;
}
.stat-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.10);
  transform: translateY(-3px);
}

.stat-icon {
  width: 50px; height: 50px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-body { flex: 1; min-width: 0; }
.stat-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.stat-value { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; }
.stat-unit  { font-size: 11px; color: #c0c4cc; margin-top: 2px; }

/* ── 主体区域：上下两行布局 ── */
.main-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0 20px 20px;
  flex: 1;
  min-height: 0;
}

/* ── 上行：折线图（2份） + 饼图（1份） ── */
.top-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 14px;
  flex: 1.2;
  min-height: 0;
}

/* ── 下行： DoS榜 + BruteForce榜 + 告警列表 ── */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1.2fr;
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.threat-board {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
}
.threat-dos { border-top: 3px solid #f56c6c; }
.threat-bf  { border-top: 3px solid #e6a23c; }

.tb-header {
  padding: 10px 14px;
  background: #fafafa;
  border-bottom: 1px solid #f2f3f5;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.tb-icon  { font-size: 16px; }
.tb-title { font-size: 13px; font-weight: 600; color: #303133; }
.tb-sub   { font-size: 11px; color: #c0c4cc; margin-left: auto; }

.tb-body {
  padding: 6px 10px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tb-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fafafa;
  font-size: 12px;
  transition: background 0.2s, box-shadow 0.2s;
  border-left: 3px solid transparent;
}
.tb-row:hover { background: #f0f2f5; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

.tb-level-danger  { border-left-color: #f56c6c; background: #fff0f0; }
.tb-level-warning { border-left-color: #e6a23c; background: #fffbe6; }
.tb-level-watch   { border-left-color: #909399; }

.tb-rank {
  width: 20px; height: 20px;
  border-radius: 50%;
  background: #ebeef5;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #606266;
  flex-shrink: 0;
}
.tb-level-danger .tb-rank  { background: #f56c6c; color: #fff; }
.tb-level-warning .tb-rank { background: #e6a23c; color: #fff; }

.tb-ip {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 11px; color: #409eff;
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.tb-tag { flex-shrink: 0; }
.tb-action { font-size: 11px !important; padding: 2px 6px !important; flex-shrink: 0; }

.tb-empty {
  padding: 16px;
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
}

/* ── 面板通用 ── */
.panel {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
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
.panel-title { font-size: 14px; font-weight: 600; color: '#303133'; }
.panel-sub   { font-size: 11px; color: #c0c4cc; }

/* ── 图表容器 ── */
.chart-container { flex: 1; min-height: 280px; }

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
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  border-left: 3px solid transparent;
  background: #fafafa;
  font-size: 12px;
  transition: background 0.2s, box-shadow 0.2s;
}
.alert-item:hover {
  background: #f0f2f5;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.alert-dos        { border-left-color: #f56c6c; }
.alert-bruteforce { border-left-color: #e6a23c; }

.alert-left { display: flex; align-items: center; gap: 8px; }
.alert-right { display: flex; align-items: center; gap: 8px; }

.alert-badge { flex-shrink: 0; }
.alert-ip {
  font-family: 'SF Mono', 'Consolas', monospace; font-size: 11px; color: #409eff;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.alert-conf { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.conf-text  { font-size: 11px; color: #606266; white-space: nowrap; }

.handle-btn { font-size: 11px !important; padding: 2px 6px !important; }

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
