<template>
  <div class="tile-downloader-app">
    <div class="container">
      <!-- 头部：现代 SaaS 导航栏风格 -->
      <header class="app-header">
        <div class="brand">
          <div class="logo-icon">
            <svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
          </div>
          <div>
            <h1>地图瓦片引擎 <span>Pro</span></h1>
            <p class="subtitle">日本国土地理院 (GSI) 高性能缓存节点</p>
          </div>
        </div>
      </header>

      <div class="main-layout">
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
                    <option v-for="region in regions" :key="region" :value="region">
                      {{ region }}
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
                  <svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                  推荐: 5-8 级 (宏观) / 9-12 级 (精细)
                </div>
              </div>

              <!-- 预估信息 -->
              <div class="estimation-box" v-if="estimatedTiles > 0">
                <div class="est-header">
                  <span>预估任务量</span>
                  <strong class="est-num">{{ estimatedTiles.toLocaleString() }}</strong> <span class="est-unit">瓦片</span>
                </div>
                <div class="est-warning" v-if="estimatedTiles > 1000">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="14"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                  预计将占用较长处理时间与存储空间
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

            <!-- 进度统计区域 -->
            <div v-if="downloadStatus.is_downloading" class="progress-module">
              <div class="progress-header">
                <span class="progress-title">总体进度</span>
                <span class="progress-percent">{{ downloadStatus.progress }}%</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" :style="{ width: downloadStatus.progress + '%' }"></div>
              </div>
              <div class="progress-detail">{{ downloadStatus.current }} / {{ downloadStatus.total }} 瓦片</div>

              <div class="status-metrics">
                <div class="metric metric-success">
                  <span class="metric-label">已保存</span>
                  <span class="metric-val">{{ downloadStatus.success }}</span>
                </div>
                <div class="metric metric-skip">
                  <span class="metric-label">已命中</span>
                  <span class="metric-val">{{ downloadStatus.skip }}</span>
                </div>
                <div class="metric metric-fail">
                  <span class="metric-label">失败</span>
                  <span class="metric-val">{{ downloadStatus.fail }}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右侧：数据看板与日志 -->
        <main class="main-content">
          <!-- 存储洞察模块 -->
          <div class="card dashboard-card">
            <div class="card-header space-between">
              <div class="flex-center">
                <svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                </svg>
                <h2>缓存数据洞察</h2>
              </div>
              <button @click="loadStats" class="btn-icon-only" title="刷新数据">
                <svg fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
              </button>
            </div>

            <div v-if="stats.total_files > 0" class="dashboard-grid">
              <div class="kpi-box">
                <span class="kpi-title">总存储用量</span>
                <span class="kpi-value text-indigo">{{ stats.total_size_mb }} <small>MB</small></span>
              </div>
              <div class="kpi-box">
                <span class="kpi-title">瓦片文件总数</span>
                <span class="kpi-value text-slate">{{ stats.total_files.toLocaleString() }} <small>个</small></span>
              </div>

              <div class="levels-breakdown">
                <div class="level-row" v-for="level in stats.stats" :key="level.level">
                  <div class="level-badge">Z{{ level.level }}</div>
                  <div class="level-bar-container">
                    <div class="level-bar" :style="{ width: Math.max((level.count / stats.total_files) * 100, 2) + '%' }"></div>
                  </div>
                  <div class="level-stats">
                    <span class="l-count">{{ level.count }}</span>
                    <span class="l-size">{{ level.size_mb }} MB</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <div class="empty-circle">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" /></svg>
              </div>
              <p>暂无缓存数据，请配置任务开始下载</p>
            </div>
          </div>

          <!-- 终端日志模块 -->
          <div class="terminal-card">
            <div class="terminal-header">
              <div class="mac-buttons">
                <span class="mac-btn close"></span>
                <span class="mac-btn minimize"></span>
                <span class="mac-btn expand"></span>
              </div>
              <div class="terminal-title">system.log - 下载引擎控制台</div>
            </div>
            <div class="terminal-body" ref="logContainer">
              <div v-if="logs.length === 0" class="terminal-empty">
                ~ $ Waiting for engine to start...
              </div>
              <div v-for="(log, index) in logs" :key="index" class="log-line" :class="'log-' + log.type">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-divider">|</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </main>
      </div>

      <!-- 开发指南 -->
      <div class="card integration-guide">
        <div class="card-header">
          <svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.25 9.75L16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
          </svg>
          <h2>集成指南</h2>
        </div>
        <div class="guide-grid">
          <div class="guide-step">
            <div class="step-num">01</div>
            <div class="step-content">
              <h3>环境初始化</h3>
              <p>确保后端引擎正常运行</p>
              <div class="code-block">
                <code>pip install flask flask-cors requests<br>python map_tile_downloader.py</code>
              </div>
            </div>
          </div>
          <div class="guide-step">
            <div class="step-num">02</div>
            <div class="step-content">
              <h3>任务调度</h3>
              <p>在上方面板配置目标参数，启动异步下载任务，引擎会自动跳过已缓存瓦片。</p>
            </div>
          </div>
          <div class="guide-step">
            <div class="step-num">03</div>
            <div class="step-content">
              <h3>前端接入 (Leaflet)</h3>
              <p>调用本地服务，实现离线/内网地图渲染。</p>
              <div class="code-block">
                <code>L.tileLayer('http://localhost:5000/map_tiles/{z}/{x}/{y}.png', {<br>&nbsp;&nbsp;attribution: 'Tiles &copy; GSI Japan',<br>&nbsp;&nbsp;maxZoom: 18<br>}).addTo(map);</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// [原封不动的脚本逻辑]
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';

const API_BASE = 'http://localhost:5000/api';

const regions = ref([]);
const config = ref({
  region: '东京周边',
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
  logs:[]
});

const stats = ref({
  stats:[],
  total_files: 0,
  total_size_mb: 0
});

const logs = ref([]);
const logContainer = ref(null);

const isDownloading = computed(() => downloadStatus.value.is_downloading);

const estimatedTiles = computed(() => {
  const zoomLevels = config.value.zoomMax - config.value.zoomMin + 1;
  return Math.pow(4, zoomLevels) * 10;
});

const canStartDownload = computed(() => {
  return config.value.zoomMin <= config.value.zoomMax && !isDownloading.value;
});

let statusInterval = null;

const loadRegions = async () => {
  try {
    const response = await fetch(`${API_BASE}/regions`);
    const data = await response.json();
    regions.value = data.regions;
  } catch (error) {
    console.error('加载区域失败:', error);
    addLocalLog('引擎连接失败，请验证核心服务状态', 'error');
  }
};

const startDownload = async () => {
  try {
    const response = await fetch(`${API_BASE}/download/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        region: config.value.region,
        zoom_min: config.value.zoomMin,
        zoom_max: config.value.zoomMax
      })
    });

    if (response.ok) {
      addLocalLog('任务指令已下发，调度中...', 'success');
      startStatusPolling();
    } else {
      const error = await response.json();
      addLocalLog(`调度异常: ${error.error}`, 'error');
    }
  } catch (error) {
    addLocalLog('调度核心无响应: ' + error.message, 'error');
  }
};

const loadStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/download/status`);
    const data = await response.json();
    downloadStatus.value = data;
    
    if (data.logs && data.logs.length > logs.value.length) {
      const newLogs = data.logs.slice(logs.value.length);
      logs.value = [...logs.value, ...newLogs];
      
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      });
    }

    if (!data.is_downloading && statusInterval) {
      stopStatusPolling();
      loadStats();
    }
  } catch (error) {
    console.error('同步引擎状态失败:', error);
  }
};

const loadStats = async () => {
  try {
    const response = await fetch(`${API_BASE}/stats`);
    const data = await response.json();
    stats.value = data;
  } catch (error) {
    console.error('统计加载失败:', error);
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

const addLocalLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  logs.value.push({ time, message, type });
  
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
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
/* 定义企业级设计系统色彩 */
:root {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --bg-color: #f8fafc;
  --surface: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  
  --success: #10b981;
  --success-bg: #d1fae5;
  --warning: #f59e0b;
  --warning-bg: #fef3c7;
  --danger: #ef4444;
  --danger-bg: #fee2e2;
}

* {
  box-sizing: border-box;
}

.tile-downloader-app {
  min-height: 100vh;
  background-color: #f8fafc;
  color: #0f172a;
  padding: 2rem 1rem;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
}

/* 灵活的居中处理 */
.flex-center {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.space-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 头部设计 */
.app-header {
  margin-bottom: 2.5rem;
}
.brand {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.logo-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
  color: white;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
}
.logo-icon svg {
  width: 28px;
  height: 28px;
}
.brand h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #0f172a;
}
.brand h1 span {
  font-size: 0.9rem;
  background: #e0e7ff;
  color: #4f46e5;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  vertical-align: middle;
  margin-left: 0.5rem;
}
.subtitle {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.95rem;
}

/* 布局网格 */
.main-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* 卡片通用基础 */
.card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.02);
  border: 1px solid #e2e8f0;
  overflow: hidden;
  margin-bottom: 1.5rem;
}
.card-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.card-header .icon {
  width: 20px;
  height: 20px;
  color: #4f46e5;
}
.card-header h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
}

/* 表单与输入 */
.form-body {
  padding: 1.5rem;
}
.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #475569;
  margin-bottom: 0.5rem;
}

.form-control {
  width: 100%;
  padding: 0.625rem 1rem;
  font-size: 0.95rem;
  color: #0f172a;
  background-color: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  transition: all 0.2s;
  appearance: none;
}
.form-control:focus {
  outline: none;
  border-color: #4f46e5;
  background-color: #fff;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
}
.form-control:disabled {
  background-color: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}

.select-wrapper {
  position: relative;
}
.select-arrow {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: #64748b;
  pointer-events: none;
}

/* 范围选择器 */
.zoom-range {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.input-wrapper {
  position: relative;
  flex: 1;
}
.input-prefix {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
}
.pl-10 {
  padding-left: 2.75rem;
}
.zoom-separator {
  color: #94a3b8;
}

.hint-box {
  margin-top: 0.625rem;
  font-size: 0.8rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* 预估信息块 */
.estimation-box {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}
.est-header {
  font-size: 0.875rem;
  color: #475569;
}
.est-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin-left: 0.5rem;
}
.est-unit {
  font-size: 0.75rem;
  color: #64748b;
}
.est-warning {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #d97706;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* 按钮设计 */
.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-block {
  width: 100%;
}
.btn-primary {
  background-color: #4f46e5;
  color: #ffffff;
  box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
}
.btn-primary:hover:not(:disabled) {
  background-color: #4338ca;
  transform: translateY(-1px);
}
.btn-primary:disabled {
  background-color: #94a3b8;
  box-shadow: none;
  cursor: not-allowed;
}
.btn-icon {
  width: 20px;
  height: 20px;
}
.btn-downloading {
  background-color: #f1f5f9;
  color: #4f46e5;
  border: 1px solid #cbd5e1;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #cbd5e1;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 进度面板 */
.progress-module {
  border-top: 1px solid #f1f5f9;
  padding: 1.5rem;
  background-color: #fafafa;
}
.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #334155;
}
.progress-percent {
  color: #4f46e5;
  font-weight: 700;
}
.progress-bar-bg {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}
.progress-bar-fill {
  height: 100%;
  background: #4f46e5;
  transition: width 0.3s ease;
}
.progress-detail {
  font-size: 0.75rem;
  color: #64748b;
  text-align: right;
  margin-bottom: 1.25rem;
}
.status-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}
.metric {
  background: white;
  padding: 0.5rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  text-align: center;
}
.metric-label {
  display: block;
  font-size: 0.7rem;
  color: #64748b;
  margin-bottom: 0.25rem;
}
.metric-val {
  font-size: 1rem;
  font-weight: 700;
}
.metric-success .metric-val { color: #10b981; }
.metric-skip .metric-val { color: #f59e0b; }
.metric-fail .metric-val { color: #ef4444; }

/* 仪表盘 */
.btn-icon-only {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s;
}
.btn-icon-only:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.dashboard-grid {
  padding: 1.5rem;
}
.kpi-box {
  background: #f8fafc;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #f1f5f9;
}
.kpi-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #475569;
}
.kpi-value {
  font-size: 1.5rem;
  font-weight: 700;
}
.text-indigo { color: #4f46e5; }
.text-slate { color: #0f172a; }

.levels-breakdown {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.level-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.85rem;
}
.level-badge {
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  width: 40px;
  text-align: center;
}
.level-bar-container {
  flex: 1;
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
}
.level-bar {
  height: 100%;
  background: #94a3b8;
  border-radius: 3px;
}
.level-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  width: 70px;
}
.l-count { font-weight: 500; color: #334155; }
.l-size { font-size: 0.7rem; color: #94a3b8; }

.empty-state {
  padding: 3rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.9rem;
}
.empty-circle {
  width: 48px;
  height: 48px;
  background: #f1f5f9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  color: #cbd5e1;
}
.empty-circle svg { width: 24px; height: 24px; }

/* 终端日志 */
.terminal-card {
  background: #0f172a;
  border-radius: 12px;
  box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
  overflow: hidden;
  height: 400px;
  display: flex;
  flex-direction: column;
}
.terminal-header {
  background: #1e293b;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
}
.mac-buttons {
  display: flex;
  gap: 6px;
  margin-right: 1rem;
}
.mac-btn {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.mac-btn.close { background: #ef4444; }
.mac-btn.minimize { background: #f59e0b; }
.mac-btn.expand { background: #10b981; }
.terminal-title {
  color: #94a3b8;
  font-size: 0.75rem;
  font-family: monospace;
}
.terminal-body {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
}
.terminal-empty { color: #475569; }
.log-line {
  display: flex;
  align-items: flex-start;
  margin-bottom: 0.25rem;
  word-break: break-all;
}
.log-time { color: #64748b; white-space: nowrap; }
.log-divider { color: #334155; margin: 0 0.5rem; }
.log-message { flex: 1; }
.log-info .log-message { color: #e2e8f0; }
.log-success .log-message { color: #34d399; }
.log-error .log-message { color: #f87171; }
.log-warning .log-message { color: #fbbf24; }

/* 集成指南 */
.integration-guide {
  margin-top: 2rem;
}
.guide-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  padding: 1.5rem;
}
.guide-step {
  display: flex;
  gap: 1rem;
}
.step-num {
  font-size: 1.5rem;
  font-weight: 800;
  color: #e2e8f0;
  line-height: 1;
}
.step-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}
.step-content p {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0 0 0.75rem 0;
}
.code-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 0.75rem;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.75rem;
  color: #0f172a;
  overflow-x: auto;
}

/* 响应式调整 */
@media (max-width: 1024px) {
  .main-layout { grid-template-columns: 1fr; }
  .guide-grid { grid-template-columns: 1fr; }
  .terminal-card { height: 350px; }
}
</style>