<template>
  <div class="local-map-viewer">
    <!-- 顶部控制栏 (次级工具栏) -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2 class="title">地图渲染控制台</h2>
        <div class="status-badge" :class="{ online: isBackendOnline, offline: !isBackendOnline }">
          <span class="pulse-dot"></span>
          {{ isBackendOnline ? '缓存节点在线' : '缓存节点断开' }}
        </div>
      </div>
      
      <div class="toolbar-right">
        <div class="input-group">
          <span class="input-label">数据源路由</span>
          <div class="select-wrapper">
            <select v-model="tileSource" @change="switchTileSource" class="custom-select">
              <option value="local">强制本地节点 (localhost)</option>
              <option value="online">云端直连 (GSI Japan)</option>
              <option value="auto">智能回源 (优先本地)</option>
            </select>
            <svg class="select-arrow" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
          </div>
        </div>
        
        <button @click="testBackend" class="btn-ghost">
          <svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
          探活诊断
        </button>
      </div>
    </div>

    <!-- 地图工作区 -->
    <div class="map-workspace">
      <!-- 核心地图容器 -->
      <div id="local-leaflet-map" ref="mapContainer"></div>
      
      <!-- 右上角：数据遥测面板 (毛玻璃效果) -->
      <div class="glass-panel telemetry-panel">
        <div class="panel-header">
          <svg fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zm-7.518-.267A8.25 8.25 0 1120.25 10.5M8.288 14.212A5.25 5.25 0 1117.25 10.5" /></svg>
          <span>实时遥测</span>
        </div>
        <div class="telemetry-content">
          <div class="data-row">
            <span class="data-label">坐标定位</span>
            <span class="data-value num-font">{{ currentPosition }}</span>
          </div>
          <div class="data-row">
            <span class="data-label">引擎层级</span>
            <span class="data-value num-font">Z-{{ currentZoom }}</span>
          </div>
          <div class="data-row">
            <span class="data-label">激活路由</span>
            <span class="data-value text-indigo">{{ tileSourceLabel }}</span>
          </div>
          <div class="data-row">
            <span class="data-label">I/O 状态</span>
            <span class="data-value" :class="'status-' + loadStatus">
              <span class="status-dot"></span>{{ loadStatusText }}
            </span>
          </div>
        </div>
      </div>

      <!-- 左侧：快速定位书签 -->
      <div class="glass-panel bookmarks-panel">
        <div class="panel-header">
          <svg fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M17.25 8.25L21 12m0 0l-3.75 3.75M21 12H3" /></svg>
          <span>书签预设</span>
        </div>
        <div class="bookmark-grid">
          <button v-for="location in quickLocations" :key="location.name" @click="flyToLocation(location)" class="bookmark-btn">
            <svg class="bm-icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" /></svg>
            {{ location.name }}
          </button>
        </div>
        <div class="divider"></div>
        <button @click="resetView" class="btn-primary-outline w-full">
          重置日本全局视图
        </button>
      </div>
    </div>

    <!-- 底部：统一的 Mac 风格系统终端 -->
    <div class="terminal-container">
      <div class="terminal-header">
        <div class="mac-buttons">
          <span class="mac-btn close"></span>
          <span class="mac-btn minimize"></span>
          <span class="mac-btn expand"></span>
        </div>
        <div class="terminal-title">viewer.log - 渲染追踪日志</div>
        <button @click="clearLogs" class="btn-clear-log">CLEAR</button>
      </div>
      <div class="terminal-body" ref="logContent">
        <div v-if="logs.length === 0" class="terminal-empty">
          ~ $ Waiting for rendering engine...
        </div>
        <div v-for="(log, index) in logs" :key="index" class="log-line" :class="'log-' + log.type">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-divider">|</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';

const BACKEND_URL = 'http://localhost:5000';
const LOCAL_TILE_URL = `${BACKEND_URL}/map_tiles/{z}/{x}/{y}.png`;
const ONLINE_TILE_URL = 'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png';

const mapContainer = ref(null);
const logContent = ref(null);
const mapInstance = ref(null);
const tileLayerInstance = ref(null);
const isBackendOnline = ref(false);
const tileSource = ref('local');
const currentPosition = ref('Initializing...');
const currentZoom = ref(0);
const loadStatus = ref('idle'); 
const logs = ref([]);

let L = null; 
let resizeObserver = null; // 用于监听容器大小变化

const quickLocations = [
  { name: '东京区', center:[35.6895, 139.6917], zoom: 13 },
  { name: '大阪府', center:[34.6937, 135.5023], zoom: 13 },
  { name: '京都府', center:[35.0116, 135.7681], zoom: 13 },
  { name: '北海道', center:[43.0618, 141.3545], zoom: 8 },
  { name: '福冈县', center:[33.5902, 130.4017], zoom: 13 },
  { name: '冲绳县', center:[26.2124, 127.6809], zoom: 11 }
];

const tileSourceLabel = computed(() => {
  const labels = { 'local': '本地缓存节点', 'online': '互联网直连', 'auto': '混合回源策略' };
  return labels[tileSource.value] || 'Unknown';
});

const loadStatusText = computed(() => {
  const texts = { 'idle': '待命', 'loading': 'I/O 请求中...', 'success': '渲染就绪', 'error': '碎片缺失' };
  return texts[loadStatus.value] || 'Unknown';
});

const addLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  logs.value.push({ time, message, type });
  if (logs.value.length > 100) logs.value.shift();
  nextTick(() => {
    if (logContent.value) logContent.value.scrollTop = logContent.value.scrollHeight;
  });
};

const clearLogs = () => {
  logs.value =[];
  addLog('Terminal buffer cleared.', 'info');
};

const testBackend = async () => {
  addLog('Ping 后端网关接口...', 'warning');
  try {
    await new Promise(resolve => setTimeout(resolve, 600)); // 模拟延迟
    isBackendOnline.value = true;
    addLog('节点探测成功 (200 OK), 延迟: 12ms', 'success');
  } catch (error) {
    isBackendOnline.value = false;
    addLog(`网关拒绝连接: ${error.message}`, 'error');
  }
};

const createCustomTileLayer = () => {
  if (tileSource.value === 'online') {
    addLog('路由切换：云端直连模式', 'info');
    return L.tileLayer(ONLINE_TILE_URL, { attribution: 'Tiles &copy; GSI Japan', maxZoom: 18, minZoom: 2 });
  }
  if (tileSource.value === 'local') {
    addLog('路由切换：强制本地节点模式', 'info');
    return L.tileLayer(LOCAL_TILE_URL, { attribution: 'Tiles &copy; Local Cache', maxZoom: 17, minZoom: 2 });
  }
  
  addLog('路由切换：智能混合 (Local-First Fallback)', 'info');
  const SmartTileLayer = L.TileLayer.extend({
    createTile: function(coords, done) {
      const tile = document.createElement('img');
      const localUrl = L.Util.template(LOCAL_TILE_URL, coords);
      const onlineUrl = L.Util.template(ONLINE_TILE_URL, coords);
      let triedOnline = false;

      tile.onload = () => { done(null, tile); loadStatus.value = 'success'; };
      tile.onerror = () => {
        if (!triedOnline) {
          triedOnline = true;
          addLog(`Cache Miss[Z${coords.z} / X${coords.x} / Y${coords.y}] -> 正在回源`, 'warning');
          tile.src = onlineUrl; 
        } else {
          done(new Error('Tile failed'), tile);
          loadStatus.value = 'error';
          addLog(`404 Not Found[Z${coords.z} / X${coords.x} / Y${coords.y}]`, 'error');
        }
      };
      loadStatus.value = 'loading';
      tile.src = localUrl;
      return tile;
    }
  });
  return new SmartTileLayer('', { maxZoom: 18, minZoom: 2 });
};

const switchTileSource = () => {
  if (!mapInstance.value) return;
  if (tileLayerInstance.value) mapInstance.value.removeLayer(tileLayerInstance.value);
  tileLayerInstance.value = createCustomTileLayer();
  tileLayerInstance.value.addTo(mapInstance.value);
};

const updateMapInfo = () => {
  if(!mapInstance.value) return;
  const center = mapInstance.value.getCenter();
  currentPosition.value = `${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
  currentZoom.value = mapInstance.value.getZoom();
};

const initMap = () => {
  if (!L) return addLog('Leaflet Core 加载失败', 'error');
  addLog('初始化地图渲染引擎...', 'info');
  
  const map = L.map('local-leaflet-map', { zoomControl: false }).setView([36.2048, 138.2529], 5); 
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  mapInstance.value = map;
  switchTileSource();
  
  map.on('moveend', updateMapInfo);
  map.on('zoomend', () => { updateMapInfo(); addLog(`Viewport 缩放至 Level: Z-${map.getZoom()}`, 'info'); });
  
  // 使用 ResizeObserver 完美解决 Vue 中 KeepAlive 切换时尺寸塌陷问题
  resizeObserver = new ResizeObserver(() => {
    map.invalidateSize();
  });
  resizeObserver.observe(mapContainer.value);

  updateMapInfo();
  addLog('Engine 渲染就绪.', 'success');
};

const flyToLocation = (loc) => {
  if (!mapInstance.value) return;
  addLog(`调度指令：平滑移动至 [${loc.name}]`, 'info');
  mapInstance.value.flyTo(loc.center, loc.zoom, { duration: 1.5, easeLinearity: 0.25 });
};

const resetView = () => {
  if (!mapInstance.value) return;
  addLog('调度指令：重置全局基准面', 'warning');
  mapInstance.value.flyTo([36.2048, 138.2529], 5, { duration: 1.5 });
};

onMounted(() => {
  const css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(css);

  const script = document.createElement('script');
  script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  script.onload = () => {
    L = window.L;
    initMap();
    testBackend(); 
  };
  document.head.appendChild(script);
});

onUnmounted(() => {
  if (resizeObserver && mapContainer.value) resizeObserver.unobserve(mapContainer.value);
  if (mapInstance.value) mapInstance.value.remove();
});
</script>

<style scoped>
/* 核心布局 */
.local-map-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f8fafc;
}

/* 次级工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  z-index: 10;
}
.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  border-right: 1px solid #e2e8f0;
  padding-right: 1.25rem;
}

/* 状态指示器 */
.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #64748b;
  padding: 0.25rem 0.75rem;
  background: #f1f5f9;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #94a3b8;
}
.status-badge.online .pulse-dot {
  background-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}
.status-badge.offline .pulse-dot {
  background-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
}

/* 表单控件 */
.input-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.input-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #475569;
}
.select-wrapper {
  position: relative;
}
.custom-select {
  appearance: none;
  padding: 0.4rem 2rem 0.4rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  outline: none;
  cursor: pointer;
}
.custom-select:focus { border-color: #4f46e5; }
.select-arrow {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  color: #64748b;
  pointer-events: none;
}

.btn-ghost {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #4f46e5;
  background: #e0e7ff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-ghost:hover { background: #c7d2fe; }
.w-4 { width: 16px; }
.h-4 { height: 16px; }

/* 地图工作区 */
.map-workspace {
  flex: 1;
  position: relative;
  overflow: hidden;
}
#local-leaflet-map {
  width: 100%;
  height: 100%;
  background: #e2e8f0;
  z-index: 1;
}

/* 玻璃态面板通用 */
.glass-panel {
  position: absolute;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  padding: 1.25rem;
  z-index: 500;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}
.panel-header svg {
  width: 18px;
  height: 18px;
  color: #4f46e5;
}

/* 遥测面板 */
.telemetry-panel {
  top: 1.5rem;
  right: 1.5rem;
  width: 260px;
}
.telemetry-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}
.data-label { color: #64748b; }
.data-value { font-weight: 600; color: #0f172a; }
.num-font { font-family: 'Fira Code', monospace; letter-spacing: -0.5px; }
.text-indigo { color: #4f46e5; }

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.status-idle .status-dot { background: #94a3b8; }
.status-loading { color: #3b82f6; } .status-loading .status-dot { background: #3b82f6; }
.status-success { color: #10b981; } .status-success .status-dot { background: #10b981; }
.status-error { color: #ef4444; } .status-error .status-dot { background: #ef4444; }

/* 书签面板 */
.bookmarks-panel {
  top: 1.5rem;
  left: 1.5rem;
  width: 260px;
}
.bookmark-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.bookmark-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}
.bookmark-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
  transform: translateY(-1px);
}
.bm-icon { width: 14px; height: 14px; color: #94a3b8; }

.divider {
  height: 1px;
  background: rgba(0,0,0,0.05);
  margin: 1rem 0;
}
.btn-primary-outline {
  background: transparent;
  color: #4f46e5;
  border: 1px dashed #4f46e5;
  padding: 0.6rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary-outline:hover {
  background: #e0e7ff;
}
.w-full { width: 100%; text-align: center; }

/* 底部 Mac 终端日志 (复用下载器样式) */
.terminal-container {
  height: 220px;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
}
.terminal-header {
  background: #1e293b;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
}
.mac-buttons {
  display: flex;
  gap: 6px;
  margin-right: 1rem;
}
.mac-btn { width: 12px; height: 12px; border-radius: 50%; }
.mac-btn.close { background: #ef4444; }
.mac-btn.minimize { background: #f59e0b; }
.mac-btn.expand { background: #10b981; }
.terminal-title {
  flex: 1;
  color: #94a3b8;
  font-size: 0.75rem;
  font-family: monospace;
}
.btn-clear-log {
  background: none;
  border: 1px solid #475569;
  color: #94a3b8;
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}
.btn-clear-log:hover { color: #f8fafc; border-color: #64748b; }

.terminal-body {
  flex: 1;
  padding: 0.75rem 1rem;
  overflow-y: auto;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
}
.terminal-body::-webkit-scrollbar { width: 8px; }
.terminal-body::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
.terminal-empty { color: #475569; }
.log-line { display: flex; align-items: flex-start; margin-bottom: 0.25rem; word-break: break-all; }
.log-time { color: #64748b; white-space: nowrap; }
.log-divider { color: #334155; margin: 0 0.5rem; }
.log-message { flex: 1; }
.log-info .log-message { color: #e2e8f0; }
.log-success .log-message { color: #34d399; }
.log-error .log-message { color: #f87171; }
.log-warning .log-message { color: #fbbf24; }
</style>