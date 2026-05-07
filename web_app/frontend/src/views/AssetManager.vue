<template>
  <div class="asset-manager">

    <!-- ===== 页面标题与搜索栏 ===== -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title"><Monitor class="title-icon" /> 终端节点管理</h2>
        <span class="page-desc">运行中 {{ activeNodes.length }} · 已封禁 {{ blockedNodes.length }}</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索 IP / 节点名 / 用户..."
          :prefix-icon="Search"
          clearable
          style="width: 260px"
          @input="fetchNodes"
        />
      </div>
    </div>

    <!-- ===== 双表格区域 ===== -->
    <div class="tables-area">

      <!-- 正常运行节点表格 -->
      <div class="table-section">
        <div class="section-header">
          <span class="section-title"><CircleCheckFilled class="section-icon" color="#67c23a" /> 运行中节点</span>
          <el-tag type="success" size="small" effect="plain">{{ activeNodes.length }} 个</el-tag>
        </div>
        <div class="table-wrapper">
          <el-table
            :data="activeNodes"
            style="width: 100%"
            stripe
            :header-cell-style="{ background: '#fafafa', color: '#303133', fontWeight: 600 }"
            v-loading="tableLoading"
            height="100%"
          >
            <el-table-column prop="id" label="节点 ID" width="90" />
            <el-table-column prop="node_name" label="节点名称" min-width="160" />
            <el-table-column prop="ip_address" label="IP 地址" width="150">
              <template #default="{ row }">
                <span class="mono-text">{{ row.ip_address }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="location" label="部署地点" width="100" />
            <el-table-column prop="owner" label="用户" width="80" />
            <el-table-column label="操作" width="160" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="danger" size="small" text @click="toggleBlock(row)">
                  封禁
                </el-button>
                <el-button type="primary" size="small" text @click="openEditDialog(row)">
                  编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 已封禁节点表格 -->
      <div class="table-section section-blocked">
        <div class="section-header">
          <span class="section-title"><CircleCloseFilled class="section-icon" color="#f56c6c" /> 已封禁节点</span>
          <el-tag type="danger" size="small" effect="plain">{{ blockedNodes.length }} 个</el-tag>
        </div>
        <div class="table-wrapper">
          <el-table
            :data="blockedNodes"
            style="width: 100%"
            stripe
            :header-cell-style="{ background: '#fff5f5', color: '#303133', fontWeight: 600 }"
            v-loading="tableLoading"
            height="100%"
          >
            <el-table-column prop="id" label="节点 ID" width="90" />
            <el-table-column prop="node_name" label="节点名称" min-width="160" />
            <el-table-column prop="ip_address" label="IP 地址" width="150">
              <template #default="{ row }">
                <span class="mono-text blocked-ip">{{ row.ip_address }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="location" label="部署地点" width="100" />
            <el-table-column prop="owner" label="用户" width="80" />
            <el-table-column label="操作" width="120" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="success" size="small" text @click="toggleBlock(row)">
                  解封
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="blockedNodes.length === 0 && !tableLoading" class="empty-blocked">
            <span>暂无封禁节点</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 编辑弹窗 ===== -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑节点信息"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="节点 ID">
          <el-input :model-value="editForm.id" disabled />
        </el-form-item>
        <el-form-item label="节点名称">
          <el-input v-model="editForm.node_name" />
        </el-form-item>
        <el-form-item label="用户">
          <el-input v-model="editForm.owner" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const API_BASE = 'http://localhost:8000/api'

// ─────────────────────────────────────────────
// 表格数据与搜索
// ─────────────────────────────────────────────
const allNodes = ref([])
const tableLoading = ref(false)
const searchKeyword = ref('')

// 计算属性：自动分离为正常节点和已封禁节点
const activeNodes = computed(() => allNodes.value.filter(n => n.status === 'active'))
const blockedNodes = computed(() => allNodes.value.filter(n => n.status === 'blocked'))

async function fetchNodes() {
  tableLoading.value = true
  try {
    const params = {}
    if (searchKeyword.value) params.keyword = searchKeyword.value
    // 不传 status 筛选，全量拉取后前端分离
    const res = await axios.get(`${API_BASE}/assets/nodes`, { params })
    allNodes.value = res.data.nodes
  } catch (e) {
    ElMessage.error('加载节点数据失败')
  } finally {
    tableLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 封禁/解封
// ─────────────────────────────────────────────
async function toggleBlock(row) {
  const action = row.status === 'active' ? 'block' : 'unblock'
  const actionText = row.status === 'active' ? '封禁' : '解封'

  try {
    await ElMessageBox.confirm(
      `确认要${actionText}节点 ${row.id}（${row.node_name}）吗？`,
      `${actionText}确认`,
      { type: 'warning' }
    )

    await axios.post(`${API_BASE}/assets/nodes/${row.id}/${action}`)
    ElMessage.success(`${actionText}成功：${row.node_name}`)
    await fetchNodes()
  } catch (e) {
    if (e !== 'cancel' && !e?.toString?.().includes('cancel')) {
      ElMessage.error(`${actionText}失败`)
    }
  }
}

// ─────────────────────────────────────────────
// 编辑弹窗
// ─────────────────────────────────────────────
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = reactive({ id: '', node_name: '', owner: '' })

function openEditDialog(row) {
  editForm.id = row.id
  editForm.node_name = row.node_name
  editForm.owner = row.owner
  editDialogVisible.value = true
}

async function submitEdit() {
  editLoading.value = true
  try {
    await axios.put(`${API_BASE}/assets/nodes/${editForm.id}`, {
      node_name: editForm.node_name,
      owner: editForm.owner,
    })
    ElMessage.success('编辑成功')
    editDialogVisible.value = false
    await fetchNodes()
  } catch (e) {
    ElMessage.error('编辑失败')
  } finally {
    editLoading.value = false
  }
}

// ─────────────────────────────────────────────
// 初始化 + keep-alive 重新激活时刷新
// ─────────────────────────────────────────────
onMounted(() => {
  if (route.query.keyword) {
    searchKeyword.value = route.query.keyword
  }
  fetchNodes()
})

// 从 SOC 大屏切回来时自动刷新数据（可能有新的封禁操作）
onActivated(() => {
  fetchNodes()
})
</script>

<style scoped>
.asset-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
}

/* ── 页面标题栏 ── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  flex-shrink: 0;
}

.header-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 18px; font-weight: 700; color: #303133; margin: 0; }
.page-desc { font-size: 13px; color: #909399; }

.header-right { display: flex; align-items: center; gap: 10px; }

/* ── 双表格区域 ── */
.tables-area {
  flex: 1;
  display: flex;
  flex-direction: row;
  gap: 14px;
  min-height: 0;
  min-width: 0;
}

.table-section {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

/* 正常节点表格占更多空间 */
.table-section:first-child { flex: 1.6; }
/* 封禁节点表格 */
.table-section.section-blocked { flex: 1; }

.section-header {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f2f3f5;
  background: #fafafa;
  border-radius: 10px 10px 0 0;
  flex-shrink: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.table-wrapper {
  flex: 1;
  padding: 8px 12px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mono-text {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  color: #409eff;
}

.blocked-ip {
  color: #f56c6c;
  text-decoration: line-through;
}

.empty-blocked {
  padding: 24px;
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
}

.title-icon {
  width: 24px;
  height: 24px;
  margin-right: 10px;
  vertical-align: -4px;
  color: #a3b8d0;
}
.section-icon {
  width: 18px;
  height: 18px;
  margin-right: 6px;
  vertical-align: -3px;
}

</style>
