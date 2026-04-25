<template>
  <div class="tile-downloader-app">
    <div class="page-layout">

      <!-- 左侧：控制中枢 -->
      <aside class="sidebar">
        <div class="card control-panel">
          <div class="card-header">
            <svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
            </svg>
            <h2>任务配置</h2>
          </div>

          <div class="form-body">
            <!-- 区域选择 -->
            <div class="form-group">
              <label>目标采集区域</label>
              <div class="select-wrapper">
                <select v-model="config.region" :disabled="isDownloading" class="form-control custom-select">
                  <option v-for="region in regions" :key="region.name" :value="region.name">
                    {{ region.name }}
                  </option>
                </select>
                <svg class="select-arrow" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
              </div>
            </div>

            <!-- 缩放级别 -->
            <div class="form-group">
              <label>瓦片层级范围 (Zoom Level)</label>
              <div class="zoom-range">
                <div class="input-wrapper">
                  <span class="input-prefix">MIN</span>
                  <input type="number" v-model.number="config.zoomMin" :disabled="isDownloading" min="0" max="18" class="form-control pl-10" />
                </div>
                <span class="zoom-separator">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="16"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
                </span>
                <div class="input-wrapper">
                  <span class="input-prefix">MAX</span>
                  <input type="number" v-model.number="config.zoomMax" :disabled="isDownloading" min="0" max="18" class="form-control pl-10" />
                </div>
              </div>
              <div class="hint-box">
                <svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                推荐: 5–8 级 (宏观) / 9–12 级 (精细)
              </div>
            </div>

            <!-- 预估信息 -->
            <div class="estimation-box" v-if="estimatedTiles > 0">
              <div class="est-row">
                <span class="est-label">预估瓦片数</span>
                <strong class="est-value">{{ estimatedTiles.toLocaleString() }}</strong>
              </div>
              <div class="est-row">
                <span class="est-label">约占存储</span>
                <span class="est-value est-dim">~{{ Math.round(estimatedTiles * 15 / 1024) }} MB</span>
              </div>
              <div class="est-warning" v-if="estimatedTiles > 10000">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="13"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                任务量大，将占用较长时间与存储
              </div>
            </div>

            <!-- 操作按钮 -->
            <button v-if="!isDownloading" @click="startDownload" class="btn btn-primary btn-block" :disabled="!canStartDownload">
              <svg class="btn-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              部署下载任务
            </button>
            <button v-else class="btn btn-downloading btn-block" disabled>
              <span class="spinner"></span>
              引擎采集中...
            </button>
          </div>

          <!-- 进度模块 -->
          <div v-if="downloadStatus.is_downloading" class="progress-module">
            <div class="progress-header">
              <span class="progress-title">总体进度</span>
              <span class="progress-percent">{{ downloadStatus.progress }}%</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" :style="{ width: downloadStatus.progress + '%' }"></div>
            </div>
            <div class="progress-detail">
              {{ downloadStatus.current.toLocaleString() }} / {{ downloadStatus.total.toLocaleString() }} 瓦片
            </div>
            <div class="status-metrics">
              <div class="metric metric-success">
                <span class="metric-val">{{ downloadStatus.success.toLocaleString() }}</span>
                <span class="metric-label">已保存</span>
              </div>
              <div class="metric metric-skip">
                <span class="metric-val">{{ downloadStatus.skip.toLocaleString() }}</span>
                <span class="metric-label">已命中</span>
              </div>
              <div class="metric metric-fail">
                <span class="metric-val">{{ downloadStatus.fail.toLocaleString() }}</span>
                <span class="metric-label">失败</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧：数据看板 + 终端 -->
      <main class="main-content">
        <!-- 存储洞察 -->
        <div class="card dashboard-card">
          <div class="card-header space-between">
            <div class="flex-center">
              <svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
              </svg>
              <h2>缓存数据洞察</h2>
            </div>
            <button @click="loadStats" class="btn-icon-only" title="刷新数据">
              <svg fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="18" height="18"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
            </button>
          </div>

          <div v-if="stats.total_files > 0" class="dashboard-body">
            <div class="kpi-row">
              <div class="kpi-box">
                <span class="kpi-title">总存储用量</span>
                <span class="kpi-value text-indigo">{{ stats.total_size_mb }}<small>MB</small></span>
              </div>
              <div class="kpi-box">
                <span class="kpi-title">瓦片文件总数</span>
                <span class="kpi-value">{{ stats.total_files.toLocaleString() }}<small>个</small></span>
              </div>
            </div>
            <div class="levels-breakdown">
              <div class="level-row" v-for="level in stats.stats" :key="level.level">
                <div class="level-badge">Z{{ level.level }}</div>
                <div class="level-bar-container">
                  <div class="level-bar" :style="{ width: Math.max((level.count / stats.total_files) * 100, 2) + '%' }"></div>
                </div>
                <div class="level-stats">
                  <span class="l-count">{{ level.count.toLocaleString() }}</span>
                  <span class="l-size">{{ level.size_mb }} MB</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <div class="empty-circle">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" /></svg>
            </div>
            <p>暂无缓存数据，配置任务后开始下载</p>
          </div>
        </div>

        <!-- 终端日志 -->
        <div class="terminal-card">
          <div class="terminal-header">
            <div class="mac-buttons">
              <span class="mac-btn mac-close"></span>
              <span class="mac-btn mac-min"></span>
              <span class="mac-btn mac-max"></span>
            </div>
            <div class="terminal-title">system.log — 下载引擎控制台</div>
          </div>
          <div class="terminal-body" ref="logContainer">
            <div v-if="logs.length === 0" class="terminal-empty">
              ~ $ Waiting for engine to start...
            </div>
            <div v-for="(log, index) in logs" :key="index" class="log-line" :class="'log-' + log.type">
              <span class="log-time">{{ log.time }}</span>
              <span class="log-divider">│</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { api, estimateTileCount } from '../services/api.js';
import { useLog } from '../composables/useLog.js';

const regions = ref([]); // [{ name, bounds }]
const regionBoundsMap = computed(() =>
  Object.fromEntries(regions.value.map(r => [r.name, r.bounds]))
);
const config = ref({
  region: '',
  zoomMin: 5,
  zoomMax: 8
});

const downloadStatus = ref({
  is_downloading: false,
  progress: 0,
  total: 0,
  current: 0,
  success: 0,
  skip: 0,
  fail: 0,
  region: '',
  logs: []
});

const stats = ref({
  stats: [],
  total_files: 0,
  total_size_mb: 0
});

const logContainer = ref(null);
const { logs, addLog: addLocalLog } = useLog(logContainer);

const isDownloading = computed(() => downloadStatus.value.is_downloading);

const estimatedTiles = computed(() => {
  const bounds = regionBoundsMap.value[config.value.region];
  return estimateTileCount(bounds, config.value.zoomMin, config.value.zoomMax);
});

const canStartDownload = computed(() =>
  config.value.region && config.value.zoomMin <= config.value.zoomMax && !isDownloading.value
);

let statusInterval = null;
let lastHeartbeatTs = 0;
let lastProgressKey = '';

const loadRegions = async () => {
  try {
    const data = await api.getRegions();
    const list = Array.isArray(data.regions) ? data.regions : [];
    regions.value = list;
    if (list.length > 0) config.value.region = list[0].name;
  } catch (error) {
    regions.value = [];
    addLocalLog(`引擎连接失败，请验证核心服务状态: ${error.message}`, 'error');
  }
};

const startDownload = async () => {
  try {
    await api.startDownload({
      region: config.value.region,
      zoom_min: config.value.zoomMin,
      zoom_max: config.value.zoomMax
    });
    addLocalLog(`任务指令已下发，区域=${config.value.region}，调度中...`, 'success');
    lastHeartbeatTs = 0;
    lastProgressKey = '';
    startStatusPolling();
  } catch (error) {
    addLocalLog(`调度异常: ${error.message}`, 'error');
  }
};

const loadStatus = async () => {
  try {
    const data = await api.getDownloadStatus();
    downloadStatus.value = data;

    if (data.logs && data.logs.length > logs.value.length) {
      const newEntries = data.logs.slice(logs.value.length);
      newEntries.forEach(entry => addLocalLog(entry.message || entry, entry.type || 'info'));
    }

    if (data.is_downloading) {
      const progressKey = `${data.current}/${data.total}/${data.success}/${data.skip}/${data.fail}`;
      const now = Date.now();
      if (progressKey !== lastProgressKey || now - lastHeartbeatTs >= 5000) {
        addLocalLog(
          `下载中: ${data.current}/${data.total} (${data.progress}%) | 成功 ${data.success} | 跳过 ${data.skip} | 失败 ${data.fail}`,
          'info'
        );
        lastProgressKey = progressKey;
        lastHeartbeatTs = now;
      }
    }

    if (!data.is_downloading && statusInterval) {
      stopStatusPolling();
      loadStats();
    }
  } catch (error) {
    addLocalLog(`同步引擎状态失败: ${error.message}`, 'error');
  }
};

const loadStats = async () => {
  try {
    const data = await api.getStats();
    stats.value = data;
  } catch (error) {
    addLocalLog(`统计数据加载失败: ${error.message}`, 'error');
  }
};

const startStatusPolling = () => {
  if (statusInterval) return;
  statusInterval = setInterval(loadStatus, 1000);
};

const stopStatusPolling = () => {
  if (statusInterval) {
    clearInterval(statusInterval);
    statusInterval = null;
  }
};

onMounted(() => {
  loadRegions();
  loadStats();
  loadStatus();
});

onUnmounted(() => {
  stopStatusPolling();
});
</script>

<style scoped>
* { box-sizing: border-box; }

/* ── 顶层容器：全高，flex 列，padding ── */
.tile-downloader-app {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 1.25rem 1.5rem;
  background: var(--bg-color, #f8fafc);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--text-main, #0f172a);
}

/* ── 双栏网格：左侧固定 360px，右侧 1fr，填满剩余高度 ── */
.page-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 1.25rem;
}

/* ── 左侧边栏可独立滚动 ── */
.sidebar {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ── 右侧主区：flex 列，终端自动填满 ── */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  min-height: 0;
}

/* ── 通用卡片 ── */
.card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.02);
  overflow: hidden;
}

.card-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.card-header .icon {
  width: 18px;
  height: 18px;
  color: var(--primary, #4f46e5);
  flex-shrink: 0;
}
.card-header h2 {
  margin: 0;
  font-size: 0.975rem;
  font-weight: 600;
  color: #1e293b;
}
.flex-center { display: flex; align-items: center; gap: 0.5rem; }
.space-between { display: flex; justify-content: space-between; align-items: center; }

/* ── 表单 ── */
.form-body { padding: 1.25rem; }
.form-group { margin-bottom: 1.25rem; }
.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.form-control {
  width: 100%;
  padding: 0.55rem 0.9rem;
  font-size: 0.9rem;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  transition: border-color 0.15s, box-shadow 0.15s;
  appearance: none;
}
.form-control:focus {
  outline: none;
  border-color: var(--primary, #4f46e5);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.12);
}
.form-control:disabled {
  background: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}
.select-wrapper { position: relative; }
.select-arrow {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  color: #94a3b8;
  pointer-events: none;
}
.zoom-range { display: flex; align-items: center; gap: 0.6rem; }
.input-wrapper { position: relative; flex: 1; }
.input-prefix {
  position: absolute;
  left: 0.7rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.7rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.05em;
}
.pl-10 { padding-left: 2.6rem; }
.zoom-separator { color: #94a3b8; }
.hint-box {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* ── 预估块 ── */
.estimation-box {
  background: #f8fafc;
  border: 1px dashed #c7d2fe;
  border-radius: 8px;
  padding: 0.875rem 1rem;
  margin-bottom: 1.25rem;
}
.est-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.3rem;
}
.est-label { font-size: 0.8rem; color: #64748b; }
.est-value { font-size: 1rem; font-weight: 700; color: #0f172a; }
.est-dim { font-size: 0.85rem; font-weight: 500; color: #475569; }
.est-warning {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #d97706;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* ── 按钮 ── */
.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.7rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}
.btn-block { width: 100%; }
.btn-primary {
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  color: #fff;
  box-shadow: 0 4px 10px -2px rgba(79,70,229,0.35);
}
.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #4338ca, #4f46e5);
  transform: translateY(-1px);
  box-shadow: 0 6px 14px -2px rgba(79,70,229,0.45);
}
.btn-primary:disabled {
  background: #cbd5e1;
  box-shadow: none;
  cursor: not-allowed;
}
.btn-icon { width: 18px; height: 18px; }
.btn-downloading {
  background: #f1f5f9;
  color: #4f46e5;
  border: 1px solid #c7d2fe;
}
.spinner {
  width: 16px; height: 16px;
  border: 2px solid #c7d2fe;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 进度模块 ── */
.progress-module {
  border-top: 1px solid #f1f5f9;
  padding: 1.25rem;
  background: #fafafa;
}
.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.82rem;
  font-weight: 500;
  color: #334155;
}
.progress-percent { color: var(--primary, #4f46e5); font-weight: 700; font-size: 0.9rem; }
.progress-bar-bg {
  width: 100%;
  height: 7px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 0.4rem;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5, #818cf8);
  border-radius: 999px;
  transition: width 0.4s ease;
}
.progress-detail {
  font-size: 0.72rem;
  color: #94a3b8;
  text-align: right;
  margin-bottom: 1rem;
  font-variant-numeric: tabular-nums;
}
.status-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
}
.metric {
  background: #fff;
  padding: 0.5rem 0.4rem;
  border-radius: 7px;
  border: 1px solid #e2e8f0;
  text-align: center;
}
.metric-label { display: block; font-size: 0.67rem; color: #94a3b8; margin-top: 0.2rem; }
.metric-val { font-size: 1.05rem; font-weight: 700; }
.metric-success .metric-val { color: #10b981; }
.metric-skip .metric-val { color: #f59e0b; }
.metric-fail .metric-val { color: #ef4444; }

/* ── 仪表盘 ── */
.dashboard-card { flex-shrink: 0; }
.btn-icon-only {
  background: none; border: none;
  color: #94a3b8; cursor: pointer;
  padding: 0.3rem; border-radius: 5px;
  transition: all 0.15s;
  display: flex; align-items: center;
}
.btn-icon-only:hover { background: #f1f5f9; color: #475569; }
.dashboard-body { padding: 1rem 1.25rem 1.25rem; }
.kpi-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.kpi-box {
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.kpi-title { font-size: 0.75rem; color: #64748b; font-weight: 500; }
.kpi-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1;
}
.kpi-value small { font-size: 0.75rem; font-weight: 500; color: #64748b; margin-left: 2px; }
.text-indigo { color: var(--primary, #4f46e5); }
.levels-breakdown { display: flex; flex-direction: column; gap: 0.55rem; }
.level-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.82rem; }
.level-badge {
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 700;
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  width: 36px;
  text-align: center;
  flex-shrink: 0;
}
.level-bar-container {
  flex: 1;
  height: 5px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}
.level-bar {
  height: 100%;
  background: linear-gradient(90deg, #818cf8, #4f46e5);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.level-stats { display: flex; flex-direction: column; align-items: flex-end; width: 72px; flex-shrink: 0; }
.l-count { font-weight: 600; color: #334155; font-size: 0.8rem; }
.l-size { font-size: 0.68rem; color: #94a3b8; }
.empty-state {
  padding: 2.5rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.875rem;
}
.empty-circle {
  width: 44px; height: 44px;
  background: #f1f5f9;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 0.875rem;
  color: #cbd5e1;
}
.empty-circle svg { width: 22px; height: 22px; }

/* ── 终端 ── */
.terminal-card {
  flex: 1;
  min-height: 180px;
  background: #0d1117;
  border-radius: 12px;
  border: 1px solid #1e293b;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.terminal-header {
  background: #161b22;
  padding: 0.6rem 1rem;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
}
.mac-buttons { display: flex; gap: 6px; margin-right: 1rem; }
.mac-btn { width: 11px; height: 11px; border-radius: 50%; }
.mac-close { background: #ef4444; }
.mac-min   { background: #f59e0b; }
.mac-max   { background: #10b981; }
.terminal-title { color: #484f58; font-size: 0.72rem; font-family: monospace; }
.terminal-body {
  flex: 1;
  padding: 0.875rem 1rem;
  overflow-y: auto;
  font-family: 'Fira Code', 'Cascadia Code', 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.65;
  min-height: 0;
}
.terminal-empty { color: #3d444d; }
.log-line {
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.15rem;
  word-break: break-all;
}
.log-time    { color: #3d444d; white-space: nowrap; min-width: 6.5rem; }
.log-divider { color: #21262d; margin: 0 0.5rem; flex-shrink: 0; }
.log-message { flex: 1; }
.log-info    .log-message { color: #adbac7; }
.log-success .log-message { color: #3fb950; }
.log-error   .log-message { color: #f85149; }
.log-warning .log-message { color: #d29922; }

/* ── 响应式 ── */
@media (max-width: 1024px) {
  .page-layout { grid-template-columns: 1fr; }
  .terminal-card { min-height: 240px; }
}
</style>
