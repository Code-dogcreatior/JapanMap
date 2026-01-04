<template>
  <div class="tile-downloader-app">
    <div class="container">
      <!-- 头部 -->
      <header class="app-header">
        <div class="header-content">
          <div class="logo">
            <span class="icon">🗾</span>
            <h1>日本地图瓦片下载器</h1>
          </div>
          <p class="subtitle">批量下载并缓存日本国土地理院地图瓦片</p>
        </div>
      </header>

      <div class="main-grid">
        <!-- 左侧：控制面板 -->
        <div class="card control-panel">
          <h2 class="card-title">
            <span class="icon">⚙️</span>
            下载配置
          </h2>

          <!-- 区域选择 -->
          <div class="form-group">
            <label>选择区域</label>
            <select v-model="config.region" :disabled="isDownloading" class="form-control">
              <option v-for="region in regions" :key="region" :value="region">
                {{ region }}
              </option>
            </select>
          </div>

          <!-- 缩放级别 -->
          <div class="form-group">
            <label>缩放级别范围</label>
            <div class="zoom-range">
              <div class="zoom-input">
                <span class="zoom-label">最小</span>
                <input 
                  type="number" 
                  v-model.number="config.zoomMin" 
                  :disabled="isDownloading"
                  min="0" 
                  max="18"
                  class="form-control"
                />
              </div>
              <span class="zoom-separator">—</span>
              <div class="zoom-input">
                <span class="zoom-label">最大</span>
                <input 
                  type="number" 
                  v-model.number="config.zoomMax" 
                  :disabled="isDownloading"
                  min="0" 
                  max="18"
                  class="form-control"
                />
              </div>
            </div>
            <p class="hint">推荐: 5-8 级（适中）, 9-12 级（详细）</p>
          </div>

          <!-- 预估信息 -->
          <div class="info-box" v-if="estimatedTiles > 0">
            <p><strong>预估瓦片数:</strong> {{ estimatedTiles }} 个</p>
            <p class="warning" v-if="estimatedTiles > 1000">
              ⚠️ 瓦片数量较多，下载需要时间
            </p>
          </div>

          <!-- 操作按钮 -->
          <div class="button-group">
            <button 
              v-if="!isDownloading"
              @click="startDownload" 
              class="btn btn-primary"
              :disabled="!canStartDownload"
            >
              <span class="icon">⬇️</span>
              开始下载
            </button>
            <button 
              v-else
              class="btn btn-secondary"
              disabled
            >
              <span class="spinner"></span>
              下载中...
            </button>
          </div>

          <!-- 进度条 -->
          <div v-if="downloadStatus.is_downloading" class="progress-section">
            <div class="progress-info">
              <span>下载进度</span>
              <span>{{ downloadStatus.current }} / {{ downloadStatus.total }}</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: downloadStatus.progress + '%' }"
              ></div>
            </div>
            <p class="progress-text">{{ downloadStatus.progress }}%</p>

            <div class="stats-grid">
              <div class="stat-item success">
                <span class="stat-icon">✅</span>
                <span class="stat-value">{{ downloadStatus.success }}</span>
                <span class="stat-label">成功</span>
              </div>
              <div class="stat-item skip">
                <span class="stat-icon">⏭️</span>
                <span class="stat-value">{{ downloadStatus.skip }}</span>
                <span class="stat-label">跳过</span>
              </div>
              <div class="stat-item fail">
                <span class="stat-icon">❌</span>
                <span class="stat-value">{{ downloadStatus.fail }}</span>
                <span class="stat-label">失败</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：日志和统计 -->
        <div class="right-column">
          <!-- 日志面板 -->
          <div class="card log-panel">
            <h2 class="card-title">
              <span class="icon">📋</span>
              下载日志
            </h2>
            <div class="log-container" ref="logContainer">
              <div v-if="logs.length === 0" class="log-empty">
                等待开始下载...
              </div>
              <div 
                v-for="(log, index) in logs" 
                :key="index" 
                class="log-item"
                :class="'log-' + log.type"
              >
                <span class="log-time">[{{ log.time }}]</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <!-- 统计面板 -->
          <div class="card stats-panel">
            <h2 class="card-title">
              <span class="icon">📊</span>
              存储统计
              <button @click="loadStats" class="btn-refresh">🔄</button>
            </h2>
            <div v-if="stats.total_files > 0" class="stats-content">
              <div class="stats-summary">
                <div class="summary-item">
                  <span class="summary-label">总瓦片数</span>
                  <span class="summary-value">{{ stats.total_files }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">总大小</span>
                  <span class="summary-value">{{ stats.total_size_mb }} MB</span>
                </div>
              </div>
              <div class="stats-levels">
                <div 
                  v-for="level in stats.stats" 
                  :key="level.level"
                  class="level-item"
                >
                  <span class="level-name">Level {{ level.level }}</span>
                  <span class="level-count">{{ level.count }} 个</span>
                  <span class="level-size">{{ level.size_mb }} MB</span>
                </div>
              </div>
            </div>
            <div v-else class="stats-empty">
              暂无已下载的瓦片
            </div>
          </div>
        </div>
      </div>

      <!-- 使用说明 -->
      <div class="card usage-guide">
        <h2 class="card-title">
          <span class="icon">📖</span>
          使用说明
        </h2>
        <div class="guide-content">
          <div class="guide-step">
            <h3>1️⃣ 启动后端服务</h3>
            <pre>pip install flask flask-cors requests
python map_tile_downloader.py</pre>
          </div>
          <div class="guide-step">
            <h3>2️⃣ 下载瓦片</h3>
            <p>选择区域和缩放级别，点击"开始下载"</p>
          </div>
          <div class="guide-step">
            <h3>3️⃣ 在 Leaflet 中使用本地瓦片</h3>
            <pre>L.tileLayer('http://localhost:5000/map_tiles/{z}/{x}/{y}.png', {
  attribution: 'Tiles &copy; GSI Japan',
  maxZoom: 18
}).addTo(map);</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';

// API 基础地址
const API_BASE = 'http://localhost:5000/api';

// 响应式数据
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
  logs: []
});

const stats = ref({
  stats: [],
  total_files: 0,
  total_size_mb: 0
});

const logs = ref([]);
const logContainer = ref(null);

// 计算属性
const isDownloading = computed(() => downloadStatus.value.is_downloading);

const estimatedTiles = computed(() => {
  // 简单估算瓦片数量（实际计算在后端）
  const zoomLevels = config.value.zoomMax - config.value.zoomMin + 1;
  return Math.pow(4, zoomLevels) * 10; // 粗略估计
});

const canStartDownload = computed(() => {
  return config.value.zoomMin <= config.value.zoomMax && !isDownloading.value;
});

// 定时器
let statusInterval = null;

// 方法
const loadRegions = async () => {
  try {
    const response = await fetch(`${API_BASE}/regions`);
    const data = await response.json();
    regions.value = data.regions;
  } catch (error) {
    console.error('加载区域失败:', error);
    addLocalLog('❌ 无法连接到后端服务，请确认 Python 服务已启动', 'error');
  }
};

const startDownload = async () => {
  try {
    const response = await fetch(`${API_BASE}/download/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        region: config.value.region,
        zoom_min: config.value.zoomMin,
        zoom_max: config.value.zoomMax
      })
    });

    if (response.ok) {
      addLocalLog('✅ 下载任务已启动', 'success');
      startStatusPolling();
    } else {
      const error = await response.json();
      addLocalLog(`❌ ${error.error}`, 'error');
    }
  } catch (error) {
    addLocalLog('❌ 启动下载失败: ' + error.message, 'error');
  }
};

const loadStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/download/status`);
    const data = await response.json();
    downloadStatus.value = data;
    
    // 更新日志（只添加新日志）
    if (data.logs && data.logs.length > logs.value.length) {
      const newLogs = data.logs.slice(logs.value.length);
      logs.value = [...logs.value, ...newLogs];
      
      // 自动滚动到底部
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      });
    }

    // 如果下载完成，停止轮询并刷新统计
    if (!data.is_downloading && statusInterval) {
      stopStatusPolling();
      loadStats();
    }
  } catch (error) {
    console.error('加载状态失败:', error);
  }
};

const loadStats = async () => {
  try {
    const response = await fetch(`${API_BASE}/stats`);
    const data = await response.json();
    stats.value = data;
  } catch (error) {
    console.error('加载统计失败:', error);
  }
};

const startStatusPolling = () => {
  if (statusInterval) return;
  statusInterval = setInterval(loadStatus, 1000); // 每秒轮询一次
};

const stopStatusPolling = () => {
  if (statusInterval) {
    clearInterval(statusInterval);
    statusInterval = null;
  }
};

const addLocalLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString('zh-CN');
  logs.value.push({ time, message, type });
  
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
};

// 生命周期
onMounted(() => {
  loadRegions();
  loadStats();
  loadStatus(); // 检查是否有正在进行的下载
});

onUnmounted(() => {
  stopStatusPolling();
});
</script>

<style scoped>
.tile-downloader-app {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.app-header {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.header-content {
  text-align: center;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.logo .icon {
  font-size: 2.5rem;
}

.logo h1 {
  margin: 0;
  font-size: 2rem;
  color: #333;
}

.subtitle {
  color: #666;
  margin: 0;
}

.main-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

.right-column {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  color: #333;
}

.card-title .icon {
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
}

.form-control:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.zoom-range {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.zoom-input {
  flex: 1;
}

.zoom-label {
  display: block;
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.zoom-separator {
  color: #999;
  margin-top: 1.5rem;
}

.hint {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #666;
}

.info-box {
  background: #e3f2fd;
  border: 2px solid #2196f3;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.info-box p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #1565c0;
}

.info-box .warning {
  color: #f57c00;
}

.button-group {
  display: flex;
  gap: 0.75rem;
}

.btn {
  flex: 1;
  padding: 0.875rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #999;
  color: white;
  cursor: not-allowed;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid #f0f0f0;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: #666;
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
  border-radius: 12px;
}

.progress-text {
  text-align: center;
  margin-top: 0.5rem;
  font-weight: 600;
  color: #667eea;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-top: 1rem;
}

.stat-item {
  text-align: center;
  padding: 0.75rem;
  border-radius: 8px;
  background: #f8f9fa;
}

.stat-item.success { border-left: 4px solid #4caf50; }
.stat-item.skip { border-left: 4px solid #ff9800; }
.stat-item.fail { border-left: 4px solid #f44336; }

.stat-icon {
  font-size: 1.5rem;
  display: block;
  margin-bottom: 0.25rem;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #333;
}

.stat-label {
  display: block;
  font-size: 0.85rem;
  color: #666;
  margin-top: 0.25rem;
}

.log-panel {
  flex: 1;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.log-container {
  flex: 1;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 1rem;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  max-height: 400px;
}

.log-empty {
  color: #666;
  text-align: center;
  padding: 2rem;
}

.log-item {
  margin-bottom: 0.5rem;
  padding: 0.25rem 0;
  display: flex;
  gap: 0.5rem;
}

.log-time {
  color: #888;
  flex-shrink: 0;
}

.log-message {
  flex: 1;
}

.log-info .log-message { color: #4fc3f7; }
.log-success .log-message { color: #66bb6a; }
.log-error .log-message { color: #ef5350; }
.log-warning .log-message { color: #ffb74d; }

.stats-panel .card-title {
  justify-content: space-between;
}

.btn-refresh {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.25rem;
  transition: transform 0.3s;
}

.btn-refresh:hover {
  transform: rotate(180deg);
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.summary-item {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}

.summary-label {
  display: block;
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.summary-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.stats-levels {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.level-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 0.9rem;
}

.level-name {
  font-weight: 600;
  color: #333;
  flex: 1;
}

.level-count {
  color: #666;
  margin: 0 1rem;
}

.level-size {
  color: #667eea;
  font-weight: 600;
}

.stats-empty {
  text-align: center;
  padding: 2rem;
  color: #999;
}

.usage-guide {
  margin-top: 2rem;
}

.guide-content {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.guide-step h3 {
  margin: 0 0 0.75rem 0;
  color: #667eea;
  font-size: 1.1rem;
}

.guide-step p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 0.9rem;
}

.guide-step pre {
  background: #1e1e1e;
  color: #4fc3f7;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.85rem;
  margin: 0.5rem 0;
}

@media (max-width: 1200px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
  
  .guide-content {
    grid-template-columns: 1fr;
  }
}
</style>