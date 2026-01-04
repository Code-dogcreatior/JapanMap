<template>
  <div class="local-map-viewer">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <div class="control-left">
        <h1 class="title">🗾 本地地图查看器</h1>
        <div class="status-indicator" :class="{ online: isBackendOnline, offline: !isBackendOnline }">
          <span class="dot"></span>
          <span class="text">{{ isBackendOnline ? '后端已连接' : '后端离线' }}</span>
        </div>
      </div>
      
      <div class="control-right">
        <div class="input-group">
          <label>瓦片源：</label>
          <select v-model="tileSource" @change="switchTileSource">
            <option value="local">本地瓦片 (localhost:5000)</option>
            <option value="online">在线瓦片 (GSI Japan)</option>
            <option value="auto">自动 (本地优先)</option>
          </select>
        </div>
        
        <button @click="testBackend" class="btn-test">
          🔍 测试连接
        </button>
      </div>
    </div>

    <!-- 地图容器 -->
    <div class="map-container">
      <div id="local-leaflet-map" ref="mapContainer"></div>
      
      <!-- 右侧：地图信息悬浮面板 -->
      <div class="info-panel">
        <div class="info-item">
          <span class="info-label">当前位置：</span>
          <span class="info-value">{{ currentPosition }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">缩放级别：</span>
          <span class="info-value">{{ currentZoom }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">瓦片源：</span>
          <span class="info-value">{{ tileSourceLabel }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">加载状态：</span>
          <span class="info-value" :class="'status-' + loadStatus">{{ loadStatusText }}</span>
        </div>
      </div>

      <!-- 左侧：快速导航悬浮面板 -->
      <div class="nav-panel">
        <h3>快速导航</h3>
        <div class="nav-grid">
          <button 
            v-for="location in quickLocations" 
            :key="location.name"
            @click="flyToLocation(location)"
            class="nav-btn"
          >
            <span class="nav-icon">{{ location.icon }}</span>
            <span class="nav-text">{{ location.name }}</span>
          </button>
        </div>
        <div class="divider"></div>
        <button @click="resetView" class="nav-btn reset">
          🇯🇵 重置全局视图
        </button>
      </div>
    </div>

    <!-- 底部日志终端 -->
    <div class="log-panel">
      <div class="log-header">
        <h3>📋 系统日志</h3>
        <button @click="clearLogs" class="btn-clear">清除日志</button>
      </div>
      <div class="log-content" ref="logContent">
        <div v-if="logs.length === 0" class="log-empty">
          > 等待系统操作...
        </div>
        <div 
          v-for="(log, index) in logs" 
          :key="index"
          class="log-entry"
          :class="'log-' + log.type"
        >
          <span class="log-time">[{{ log.time }}]</span>
          <span class="log-arrow">➜</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';

// --- 配置常量 ---
const BACKEND_URL = 'http://localhost:5000';
// 假设后端瓦片格式，根据实际情况调整
const LOCAL_TILE_URL = `${BACKEND_URL}/map_tiles/{z}/{x}/{y}.png`;
// 日本国土地理院在线地图源
const ONLINE_TILE_URL = 'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png';

// --- 响应式状态 ---
const mapContainer = ref(null);
const logContent = ref(null);
const mapInstance = ref(null);
const tileLayerInstance = ref(null);
const isBackendOnline = ref(false);
const tileSource = ref('local'); // 'local' | 'online' | 'auto'
const currentPosition = ref('未初始化');
const currentZoom = ref(0);
const loadStatus = ref('idle'); // 'idle' | 'loading' | 'success' | 'error'
const logs = ref([]);

let L = null; // Leaflet 实例占位

// --- 快速导航数据 ---
const quickLocations = [
  { name: '东京', icon: '🗼', center: [35.6895, 139.6917], zoom: 13 },
  { name: '大阪', icon: '🏯', center: [34.6937, 135.5023], zoom: 13 },
  { name: '京都', icon: '⛩️', center: [35.0116, 135.7681], zoom: 13 },
  { name: '北海道', icon: '❄️', center: [43.0618, 141.3545], zoom: 8 },
  { name: '福冈', icon: '🍜', center: [33.5902, 130.4017], zoom: 13 },
  { name: '冲绳', icon: '🏝️', center: [26.2124, 127.6809], zoom: 11 }
];

// --- 计算属性 ---
const tileSourceLabel = computed(() => {
  const labels = {
    'local': '本地服务器',
    'online': '互联网源',
    'auto': '智能混合'
  };
  return labels[tileSource.value] || '未知';
});

const loadStatusText = computed(() => {
  const texts = {
    'idle': '就绪',
    'loading': '请求中...',
    'success': '加载完成',
    'error': '加载失败'
  };
  return texts[loadStatus.value] || '未知';
});

// --- 日志系统 ---
const addLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  logs.value.push({ time, message, type });
  
  // 保持日志数量在合理范围
  if (logs.value.length > 100) logs.value.shift();
  
  // 自动滚动
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight;
    }
  });
};

const clearLogs = () => {
  logs.value = [];
  addLog('日志控制台已清空', 'info');
};

// --- 后端交互 ---
const testBackend = async () => {
  addLog('正在 Ping 后端接口...', 'warning');
  try {
    // 这里模拟测试，实际应请求真实的健康检查接口
    // const response = await fetch(`${BACKEND_URL}/health`);
    // 为了演示效果，这里使用 setTimeout 模拟
    await new Promise(resolve => setTimeout(resolve, 800));
    
    // 假设连接成功
    const success = true; 
    
    if (success) {
      isBackendOnline.value = true;
      addLog('后端服务连接成功 (200 OK)', 'success');
    } else {
      throw new Error('Connection refused');
    }
  } catch (error) {
    isBackendOnline.value = false;
    addLog(`后端连接失败: ${error.message}`, 'error');
  }
};

// --- 地图核心逻辑 ---

// 创建自定义瓦片层（含回退逻辑）
const createCustomTileLayer = () => {
  if (tileSource.value === 'online') {
    addLog('切换至：纯在线模式', 'info');
    return L.tileLayer(ONLINE_TILE_URL, {
      attribution: 'Tiles &copy; GSI Japan',
      maxZoom: 18,
      minZoom: 2
    });
  }
  
  if (tileSource.value === 'local') {
    addLog('切换至：纯本地模式', 'info');
    return L.tileLayer(LOCAL_TILE_URL, {
      attribution: 'Tiles &copy; Localhost',
      maxZoom: 17,
      minZoom: 2
    });
  }
  
  // 自动模式：尝试本地，失败则加载在线
  addLog('切换至：智能混合模式 (Local First)', 'info');
  
  const SmartTileLayer = L.TileLayer.extend({
    createTile: function(coords, done) {
      const tile = document.createElement('img');
      const localUrl = L.Util.template(LOCAL_TILE_URL, coords);
      const onlineUrl = L.Util.template(ONLINE_TILE_URL, coords);
      
      let triedOnline = false;

      // 成功加载回调
      tile.onload = () => {
        done(null, tile);
        loadStatus.value = 'success';
      };

      // 错误处理回调
      tile.onerror = () => {
        if (!triedOnline) {
          triedOnline = true;
          addLog(`本地缺失 [${coords.z}/${coords.x}/${coords.y}] -> 尝试在线获取`, 'warning');
          tile.src = onlineUrl; // 尝试在线地址
        } else {
          done(new Error('Tile load failed'), tile);
          loadStatus.value = 'error';
          addLog(`瓦片加载彻底失败 [${coords.z}/${coords.x}/${coords.y}]`, 'error');
        }
      };

      loadStatus.value = 'loading';
      tile.src = localUrl; // 默认先试本地
      return tile;
    }
  });
  
  return new SmartTileLayer('', { maxZoom: 18, minZoom: 2 });
};

const switchTileSource = () => {
  if (!mapInstance.value) return;
  
  if (tileLayerInstance.value) {
    mapInstance.value.removeLayer(tileLayerInstance.value);
  }
  
  tileLayerInstance.value = createCustomTileLayer();
  tileLayerInstance.value.addTo(mapInstance.value);
};

const updateMapInfo = () => {
  if(!mapInstance.value) return;
  const center = mapInstance.value.getCenter();
  currentPosition.value = `${center.lat.toFixed(5)}, ${center.lng.toFixed(5)}`;
  currentZoom.value = mapInstance.value.getZoom();
};

const initMap = () => {
  if (!L) {
    addLog('Leaflet 库尚未加载完成', 'error');
    return;
  }
  
  addLog('正在初始化 Leaflet 地图容器...', 'info');
  
  const map = L.map('local-leaflet-map', {
    zoomControl: false 
  }).setView([36.2048, 138.2529], 5); 
  
  L.control.zoom({ position: 'bottomright' }).addTo(map);

  mapInstance.value = map;
  
  // 初始化图层
  switchTileSource();
  
  // Events
  map.on('moveend', updateMapInfo);
  map.on('zoomend', () => {
    updateMapInfo();
    addLog(`用户缩放地图至级别: ${map.getZoom()}`, 'info');
  });
  
  // -------------------------------------------------
  // 👇【关键修复】在这里添加这段代码 👇
  // -------------------------------------------------
  setTimeout(() => {
    map.invalidateSize(); // 强制 Leaflet 重新计算容器大小
    addLog('已校正地图容器尺寸', 'info');
  }, 200); // 延时 200ms 确保 DOM 渲染完毕
  // -------------------------------------------------

  updateMapInfo();
  addLog('地图初始化完成', 'success');
};
const flyToLocation = (loc) => {
  if (!mapInstance.value) return;
  addLog(`导航指令: 飞往 ${loc.name}`, 'info');
  mapInstance.value.flyTo(loc.center, loc.zoom, {
    duration: 1.5,
    easeLinearity: 0.25
  });
};

const resetView = () => {
  if (!mapInstance.value) return;
  addLog('导航指令: 重置全局视图', 'warning');
  mapInstance.value.flyTo([36.2048, 138.2529], 5, { duration: 1.5 });
};

// --- 生命周期 ---
onMounted(() => {
  // 动态注入 Leaflet 资源 (为了演示方便，实际项目中建议 npm install leaflet)
  const css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(css);

  const script = document.createElement('script');
  script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  script.onload = () => {
    L = window.L;
    initMap();
    testBackend(); // 初始测试连接
  };
  document.head.appendChild(script);
});

onUnmounted(() => {
  if (mapInstance.value) {
    mapInstance.value.remove();
  }
});
</script>

<style scoped>
/* 基础重置 */
.local-map-viewer {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  background-color: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #333;
}

/* 顶部控制栏 */
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 64px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  box-shadow: 0 2px 10px rgba(79, 70, 229, 0.2);
  z-index: 10;
}

.control-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.5px;
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.85rem;
  backdrop-filter: blur(4px);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ccc;
  transition: background-color 0.3s;
}

.status-indicator.online .dot {
  background-color: #34d399; /* Green */
  box-shadow: 0 0 8px #34d399;
}

.status-indicator.offline .dot {
  background-color: #f87171; /* Red */
}

/* 顶部右侧控件 */
.control-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

select {
  padding: 6px 12px;
  border-radius: 6px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #4b5563;
  outline: none;
  cursor: pointer;
  font-weight: 500;
}

.btn-test {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.6);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-test:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: white;
}

/* 地图主容器 */
.map-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #e5e7eb;
}

#local-leaflet-map {
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* 悬浮面板通用样式 */
.info-panel, .nav-panel {
  position: absolute;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  z-index: 500; /* Leaflet default is 400 */
  border: 1px solid rgba(255,255,255,0.5);
}

/* 右侧信息面板 */
.info-panel {
  top: 20px;
  right: 20px;
  min-width: 220px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  color: #6b7280;
}

.info-value {
  font-weight: 600;
  color: #111827;
  font-feature-settings: "tnum";
}

.status-idle { color: #6b7280; }
.status-loading { color: #3b82f6; }
.status-success { color: #10b981; }
.status-error { color: #ef4444; }

/* 左侧导航面板 */
.nav-panel {
  top: 20px;
  left: 20px;
  width: 240px;
}

.nav-panel h3 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 8px;
}

.nav-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.nav-btn {
  display: flex;
  align-items: center;
  justify-content: center; /* 居中内容 */
  gap: 6px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #4b5563;
  font-size: 0.9rem;
}

.nav-btn:hover {
  background: #f9fafb;
  border-color: #d1d5db;
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.divider {
  height: 1px;
  background: #f3f4f6;
  margin: 12px 0;
}

.nav-btn.reset {
  width: 100%;
  background: #4f46e5;
  color: white;
  border: none;
  font-weight: 600;
}

.nav-btn.reset:hover {
  background: #4338ca;
  transform: translateY(-1px);
}

/* 底部日志面板 */
.log-panel {
  height: 200px;
  background: #1e1e1e;
  display: flex;
  flex-direction: column;
  border-top: 1px solid #333;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #252526;
  border-bottom: 1px solid #333;
}

.log-header h3 {
  margin: 0;
  color: #e5e7eb;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.btn-clear {
  background: transparent;
  color: #9ca3af;
  border: 1px solid #4b5563;
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-clear:hover {
  color: white;
  border-color: white;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

/* 滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 8px;
}
.log-content::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 4px;
}
.log-content::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.log-empty {
  color: #6b7280;
  font-style: italic;
}

.log-entry {
  display: flex;
  gap: 8px;
}

.log-time {
  color: #6b7280;
  min-width: 65px;
}

.log-arrow {
  color: #4b5563;
}

.log-info .log-message { color: #d1d5db; }
.log-success .log-message { color: #34d399; }
.log-warning .log-message { color: #fbbf24; }
.log-error .log-message { color: #f87171; }
</style>