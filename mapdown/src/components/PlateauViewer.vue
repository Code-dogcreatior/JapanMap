<template>
  <div class="plateau-wrapper">
    <div ref="container" class="cesium-container"></div>

    <!-- 左侧控制面板 -->
    <aside class="side-panel">
      <div class="panel-head">
        <div class="head-badge">3D</div>
        <div>
          <div class="head-title">3D展示</div>
          <div class="head-sub">
            国土交通省 MLIT · 建物 3D Tiles · 本地 map_tiles
            <span v-if="terrainEnabled" class="terrain-badge on" title="GSI 国土地理院 DEM 地形已启用">⛰ GSI DEM</span>
            <span v-else class="terrain-badge off" title="使用平面椭球（山地建筑会浮空）">⛰ 平面</span>
          </div>
        </div>
      </div>

      <!-- 目录加载中 -->
      <div v-if="catalogLoading" class="catalog-status">
        <div class="mini-ring"></div>
        <span>正在加载数据目录...</span>
      </div>

      <!-- 目录加载失败 -->
      <div v-else-if="catalogError" class="catalog-err">
        <span>⚠ 目录加载失败</span>
        <button class="retry-btn" @click="fetchCatalog">重试</button>
      </div>

      <!-- 筛选与列表 -->
      <template v-else>
        <!-- 都道府県筛选 -->
        <div class="filter-group">
          <div class="section-label">都道府県</div>
          <select v-model="selectedPref" class="filter-select" @change="searchText = ''">
            <option value="">全都道府県 ({{ catalogs.length }})</option>
            <option v-for="p in prefList" :key="p.code" :value="p.code">
              {{ p.name }} ({{ p.count }})
            </option>
          </select>
        </div>

        <!-- 搜索框 -->
        <div class="filter-group">
          <div class="section-label">検索</div>
          <input
            v-model="searchText"
            class="filter-input"
            placeholder="城市 / 区市町村名..."
          />
        </div>

        <!-- LOD 筛选 -->
        <div class="lod-filter">
          <button
            v-for="opt in LOD_OPTS"
            :key="opt.v"
            :class="['lod-opt', { active: lodFilter === opt.v }]"
            @click="lodFilter = opt.v"
          >{{ opt.label }}</button>
        </div>

        <!-- 自动模式开关 -->
        <div class="auto-row">
          <label class="auto-toggle" :class="{ on: autoMount }">
            <input type="checkbox" v-model="autoMount" @change="autoMount && scheduleAutoMount()" />
            <span class="auto-dot"></span>
            <span class="auto-text">视口自动挂载</span>
          </label>
          <label class="auto-toggle" :class="{ on: autoDownload }">
            <input type="checkbox" v-model="autoDownload" />
            <span class="auto-dot"></span>
            <span class="auto-text">看到即下载</span>
          </label>
        </div>

        <!-- 数据列表 -->
        <div class="section-label">
          数据集
          <span class="count-badge">{{ visibleDatasets.length }}</span>
          <span class="local-count" v-if="localSet.size > 0">本地 {{ localSet.size }}</span>
        </div>
        <div class="dataset-list">
          <div
            v-for="d in visibleDatasets.slice(0, 40)"
            :key="d.id"
            :class="['dataset-item', { active: currentDataset?.id === d.id, loading: busy === d.id, mounted: mountedTilesets.has(d.id) }]"
            @click="!busy && loadDataset(d)"
          >
            <div class="ds-names">
              <span class="ds-city">{{ d.ward || d.city }}</span>
              <span class="ds-pref">{{ d.pref }}</span>
            </div>
            <div class="ds-tags">
              <span v-if="d.lod" :class="['lod-tag', 'lod' + d.lod]">LOD{{ d.lod }}</span>
              <span class="year-tag">{{ d.year }}</span>
              <!-- 状态/下载按钮 -->
              <span v-if="busy === d.id" class="spin-icon">↻</span>
              <span v-else-if="dsState(d) === 'local'" class="state-tag local" title="本地已缓存">✓</span>
              <span v-else-if="dsState(d) === 'downloading'" class="state-tag dl-progress" :title="`已下载 ${((downloadStatus[d.id]?.bytes || 0) / 1024 / 1024).toFixed(1)} MB`">
                <span class="dl-spinner"></span>
              </span>
              <button
                v-else
                class="dl-btn"
                @click.stop="downloadDataset(d)"
                title="下载到本地"
              >⬇</button>
            </div>
          </div>
          <div v-if="visibleDatasets.length > 40" class="list-hint">
            共 {{ visibleDatasets.length }} 个，已显示前 40 个，请缩小筛选范围
          </div>
          <div v-if="visibleDatasets.length === 0" class="list-empty">
            无匹配数据集
          </div>
        </div>
      </template>

      <!-- 操作按钮 -->
      <div class="ctrl-btns">
        <button class="ctrl-btn" @click="resetView" :disabled="!currentDataset || !!busy">↺ 重置视角</button>
        <button class="ctrl-btn" @click="toggleScene">⊞ {{ is3D ? '切换2D' : '切换3D' }}</button>
        <button
          class="ctrl-btn ctrl-btn-wide"
          :class="{ active: viewControlMode }"
          @click="toggleViewControlMode"
        >⌁ 视角模式 {{ viewControlMode ? '开' : '关' }}</button>
      </div>

      <!-- 已加载信息 -->
      <div v-if="currentDataset" class="info-box">
        <div class="info-row"><span>当前区域</span><b>{{ currentDataset.ward || currentDataset.city }}</b></div>
        <div class="info-row"><span>都道府県</span><b>{{ currentDataset.pref }}</b></div>
        <div class="info-row" v-if="currentDataset.lod">
          <span>精度</span>
          <b :class="['lod-tag', 'lod' + currentDataset.lod]">LOD{{ currentDataset.lod }}</b>
        </div>
        <div class="info-row"><span>年份</span><b>{{ currentDataset.year }}</b></div>
        <div class="info-row"><span>来源</span>
          <b v-if="localSet.has(currentDataset.id)" class="src-local">本地缓存</b>
          <b v-else class="src-remote">PLATEAU CDN</b>
        </div>
        <div class="info-row" v-if="downloadStatus[currentDataset.id]?.status === 'downloading'">
          <span>下载</span>
          <b>{{ ((downloadStatus[currentDataset.id].bytes || 0) / 1024 / 1024).toFixed(1) }} MB · {{ downloadStatus[currentDataset.id].files }} 文件</b>
        </div>
        <template v-if="snapDiagnostic">
          <div class="info-row diag-row"><span>建筑最低海拔</span><b>{{ formatMeters(snapDiagnostic.buildingMinHeight) }}</b></div>
          <div class="info-row diag-row"><span>DEM地形高度</span><b>{{ formatMeters(snapDiagnostic.terrainHeight) }}</b></div>
          <div class="info-row diag-row"><span>原始偏移</span><b>{{ formatMeters(snapDiagnostic.rawOffset) }}</b></div>
          <div class="info-row diag-row"><span>实际偏移</span><b>{{ formatMeters(snapDiagnostic.appliedOffset) }}</b></div>
          <div class="info-row diag-row"><span>DEM来源</span><b>{{ snapDiagnostic.terrainSource }}</b></div>
        </template>
      </div>

      <!-- 多挂载状态 -->
      <div v-if="autoMount && mountedTilesets.size > 0" class="mount-box">
        <span>视口已挂载</span>
        <b>{{ mountedTilesets.size }} / {{ MAX_MOUNTED }}</b>
      </div>

      <div class="tip-box">鼠标左键旋转 · 右键平移 · 双指缩放 · 视角模式/Shift/Option+双指调角度</div>
    </aside>

    <!-- 右上角标志 -->
    <div class="corner-badge">
      <span class="live-dot"></span>
      Project PLATEAU · MLIT Japan · 3D Tiles
    </div>

    <!-- 加载提示 -->
    <Transition name="fade">
      <div v-if="busy" class="load-toast">
        <div class="load-ring"></div>
        <span>正在加载 3D 建筑数据...</span>
      </div>
    </Transition>

    <!-- 错误提示 -->
    <Transition name="fade">
      <div v-if="errMsg" class="err-toast">
        <span>⚠ {{ errMsg }}</span>
        <button @click="errMsg = null">✕</button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, shallowRef, reactive, markRaw } from 'vue'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc5YzciLCJpZCI6NTc3MzMsImlhdCI6MTYyNzg0NTE4Mn0.XcKpgANiY19MC4bdFUXMVEBToBmqS8kuYpUlxJHYZxk'

const LOD_OPTS = [
  { v: '', label: '全部' },
  { v: 3, label: 'LOD3' },
  { v: 2, label: 'LOD2' },
  { v: 1, label: 'LOD1' },
]

// 各都道府県大致中心坐标（用于相机定位）
const PREF_CENTER = {
  '01': [141.35, 43.07], '02': [140.74, 40.82], '03': [141.15, 39.70],
  '04': [140.87, 38.27], '05': [140.10, 39.72], '06': [140.36, 38.92],
  '07': [140.47, 37.75], '08': [140.45, 36.34], '09': [139.88, 36.57],
  '10': [139.06, 36.39], '11': [139.65, 35.86], '12': [140.12, 35.61],
  '13': [139.69, 35.69], '14': [139.64, 35.45], '15': [138.88, 37.90],
  '16': [137.21, 36.70], '17': [136.63, 36.59], '18': [136.22, 36.07],
  '19': [138.57, 35.66], '20': [138.18, 36.65], '21': [136.72, 35.39],
  '22': [138.38, 34.98], '23': [136.91, 35.18], '24': [136.51, 34.73],
  '25': [135.87, 35.00], '26': [135.77, 35.01], '27': [135.50, 34.69],
  '28': [135.20, 34.69], '29': [135.83, 34.69], '30': [135.17, 34.23],
  '31': [133.97, 35.50], '32': [133.05, 35.47], '33': [133.93, 34.66],
  '34': [132.46, 34.40], '35': [131.47, 34.19], '36': [134.56, 34.07],
  '37': [134.04, 34.34], '38': [132.77, 33.84], '39': [133.53, 33.56],
  '40': [130.55, 33.61], '41': [130.30, 33.25], '42': [129.87, 32.74],
  '43': [130.74, 32.79], '44': [131.61, 33.24], '45': [131.42, 31.91],
  '46': [130.56, 31.56], '47': [127.68, 26.21],
}

// -------- State --------
const catalogs = ref([])
const catalogLoading = ref(false)
const catalogError = ref(false)
const selectedPref = ref('')
const searchText = ref('')
const lodFilter = ref('')

const container = ref(null)
const viewer = shallowRef(null)
const currentDataset = ref(null)
const busy = ref(null)
const errMsg = ref(null)
const is3D = ref(true)
const viewControlMode = ref(false)
const snapDiagnostic = ref(null)
let currentTileset = null

// 下载/本地缓存
const localSet = ref(new Set())                // dataset_id 集合：本地已下载
const downloadStatus = ref({})                 // dataset_id -> {status,files,bytes,errors,...}
const autoDownload = ref(false)                // 切换：加载即下载；默认关，避免误拉大体积 PLATEAU 数据
const autoMount = ref(false)                   // 切换：视口内自动挂载多个 tileset；默认关，避免相机移动触发大量远程加载
const terrainEnabled = ref(false)              // 真实地形是否就绪（异步加载）
let statusPollTimer = null

// 视口多挂载：dataset_id -> {tileset, dataset, mountedAt}
// 使用 reactive Map 让模板的 .size/.has 响应；tileset 对象用 markRaw 防止 Vue 深度跟踪
const mountedTilesets = reactive(new Map())
const MAX_MOUNTED = 4                          // 同时挂载上限（避免 GPU 爆显存/网络被远程 tileset 打满）
const BUILDING_HEIGHT_OFFSET_METERS = -0.5     // 自动贴合 DEM 后的微调；负数略微压入地面
const ESTIMATED_BUILDING_BASE_BELOW_CENTER_METERS = 35
const MAX_BUILDING_SNAP_OFFSET_METERS = 120    // 防止异常 DEM/boundingVolume 把模型移动到视野外
const TERRAIN_RENDER_MAX_LEVEL = 12            // 地形渲染用较低级别，贴地采样仍会单独取高精度 DEM
const DEM_SNAP_MAX_LEVEL = 14
const DEM_SNAP_MIN_LEVEL = 8
const tilesetCenterCache = new Map()           // dataset_id -> {lon,lat} （已加载过的中心）
const tilesetBoundsCache = new Map()           // dataset_id -> {west,south,east,north}，用于近距离视口稳定挂载
const demPixelCache = new Map()                // "z/x/y/px/py" -> {height,source} | null
let removeTrackpadZoomListeners = null

// -------- Computed --------
const prefList = computed(() => {
  const map = new Map()
  catalogs.value.forEach(d => {
    const entry = map.get(d.pref_code) || { code: d.pref_code, name: d.pref, count: 0 }
    entry.count++
    map.set(d.pref_code, entry)
  })
  return Array.from(map.values()).sort((a, b) => a.code.localeCompare(b.code))
})

const visibleDatasets = computed(() => {
  let list = catalogs.value
  if (selectedPref.value) list = list.filter(d => d.pref_code === selectedPref.value)
  if (lodFilter.value !== '') list = list.filter(d => d.lod === lodFilter.value)
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    list = list.filter(d =>
      (d.city || '').toLowerCase().includes(q) ||
      (d.ward || '').toLowerCase().includes(q) ||
      (d.pref || '').toLowerCase().includes(q)
    )
  }
  // 排序：LOD2（城市级覆盖最佳）> LOD1（基础体块）> LOD3 > LOD4（仅室内/地标，慎选）
  const lodWeight = (lod) => ({ 2: 4, 1: 3, 3: 2, 4: 1 }[lod] || 0)
  return list.slice().sort((a, b) => lodWeight(b.lod) - lodWeight(a.lod))
})

// -------- API --------
const CATALOG_CACHE_KEY = 'plateau:bldg-3dtiles-catalog:v1'

async function fetchCatalog() {
  catalogLoading.value = true
  catalogError.value = false
  try {
    try {
      const cached = localStorage.getItem(CATALOG_CACHE_KEY)
      if (cached) {
        const parsed = JSON.parse(cached)
        if (Array.isArray(parsed.datasets)) {
          catalogs.value = parsed.datasets
          return
        }
      }
    } catch (_) {
      localStorage.removeItem(CATALOG_CACHE_KEY)
    }

    const res = await fetch('/plateau-api/datacatalog/plateau-datasets?type=3DTiles&dataType=bldg')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()
    const datasets = (json.datasets || []).filter(d => d.url)
    catalogs.value = datasets
    try {
      localStorage.setItem(CATALOG_CACHE_KEY, JSON.stringify({
        savedAt: Date.now(),
        datasets,
      }))
    } catch (_) {}
  } catch (e) {
    console.error('PLATEAU catalog fetch failed:', e)
    catalogError.value = true
  } finally {
    catalogLoading.value = false
  }
}

// 拉取本地已下载列表（以及下载状态）
async function refreshLocal() {
  try {
    const res = await fetch('/api/plateau/local')
    if (res.ok) {
      const json = await res.json()
      const ids = (json.datasets || []).map(d => d.dataset_id)
      localSet.value = new Set(ids)
    }
  } catch (_) { /* 后端没起也允许：本地集合就是空 */ }
}

async function refreshStatus() {
  try {
    const res = await fetch('/api/plateau/status')
    if (res.ok) {
      const json = await res.json()
      downloadStatus.value = json.downloads || {}
    }
  } catch (_) {}
}

function startPolling() {
  if (statusPollTimer) return
  statusPollTimer = setInterval(async () => {
    await refreshStatus()
    await refreshLocal()
    const active = Object.values(downloadStatus.value).some(d => d.status === 'downloading')
    if (!active) stopPolling()
  }, 2000)
}

function stopPolling() {
  if (statusPollTimer) clearInterval(statusPollTimer)
  statusPollTimer = null
}

// 触发某数据集的后台下载（幂等）
async function downloadDataset(dataset) {
  if (!dataset || !dataset.url) return
  if (localSet.value.has(dataset.id)) return
  const cur = downloadStatus.value[dataset.id]
  if (cur && cur.status === 'downloading') return
  try {
    const res = await fetch('/api/plateau/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: dataset.id, url: dataset.url }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    startPolling()
  } catch (e) {
    errMsg.value = `下载请求失败：${e.message}（确认 Flask 后端已启动）`
    setTimeout(() => { errMsg.value = null }, 5000)
  }
}

// 数据集的当前展示状态（用于 UI 标签 / 颜色）
function dsState(dataset) {
  if (localSet.value.has(dataset.id)) return 'local'
  const s = downloadStatus.value[dataset.id]
  if (s) return s.status               // downloading | done | failed
  return 'remote'
}

// 实际加载用 URL：本地有就走本地代理，否则走 PLATEAU CDN
function effectiveUrl(dataset) {
  if (localSet.value.has(dataset.id)) {
    return `/plateau_tiles/${encodeURIComponent(dataset.id)}/tileset.json`
  }
  return dataset.url
}

// -------- Lifecycle --------
function createLocalMapImageryProvider() {
  return new Cesium.UrlTemplateImageryProvider({
    url: '/map_tiles_3d/{z}/{x}/{y}.png',
    minimumLevel: 2,
    maximumLevel: 16,
    credit: '本地 GSI map_tiles',
  })
}

function createOnlineMapImageryProvider() {
  return new Cesium.UrlTemplateImageryProvider({
    url: 'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png',
    minimumLevel: 2,
    maximumLevel: 18,
    credit: 'Tiles: GSI Japan',
  })
}

function currentCameraHeight() {
  if (!viewer.value) return 1000
  const camera = viewer.value.camera
  const ellipsoid = viewer.value.scene.globe.ellipsoid
  const carto = ellipsoid.cartesianToCartographic(camera.positionWC || camera.position)
  return Math.max(carto?.height || 1000, 1)
}

function applyTrackpadZoom(scaleDelta) {
  if (!viewer.value || !Number.isFinite(scaleDelta) || scaleDelta === 1) return
  const camera = viewer.value.camera
  const clampedScale = Cesium.Math.clamp(scaleDelta, 0.88, 1.14)
  const height = currentCameraHeight()
  const amount = Cesium.Math.clamp(
    height * Math.abs(clampedScale - 1) * 1.45,
    8,
    Math.max(20, height * 0.38)
  )
  if (clampedScale > 1) {
    camera.zoomIn(amount)
  } else {
    camera.zoomOut(amount)
  }
  viewer.value.scene.requestRender()
}

function applyTrackpadHeading(deltaDegrees) {
  if (!viewer.value || !Number.isFinite(deltaDegrees)) return
  const camera = viewer.value.camera
  const angle = Cesium.Math.clamp(Cesium.Math.toRadians(deltaDegrees) * 0.18, -0.018, 0.018)
  camera.setView({
    orientation: {
      heading: camera.heading + angle,
      pitch: camera.pitch,
      roll: 0,
    },
  })
  viewer.value.scene.requestRender()
}

function applyTrackpadTilt(deltaPixels) {
  if (!viewer.value || !Number.isFinite(deltaPixels)) return
  const camera = viewer.value.camera
  const delta = Cesium.Math.clamp(deltaPixels * 0.00045, -0.014, 0.014)
  const pitch = Cesium.Math.clamp(
    camera.pitch - delta,
    Cesium.Math.toRadians(-88),
    Cesium.Math.toRadians(-6)
  )
  camera.setView({
    orientation: {
      heading: camera.heading,
      pitch,
      roll: 0,
    },
  })
  viewer.value.scene.requestRender()
}

function normalizeWheelDelta(event) {
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1
  return {
    x: (event.deltaX || 0) * unit,
    y: (event.deltaY || 0) * unit,
  }
}

function isSidePanelEvent(event) {
  const path = typeof event.composedPath === 'function' ? event.composedPath() : []
  return path.some(el => el?.classList?.contains?.('side-panel'))
}

function installTrackpadZoom(containerEl) {
  if (!containerEl) return () => {}
  let lastGestureScale = 1
  let lastGestureRotation = 0
  let pointerInScene = false

  const onGestureStart = (event) => {
    lastGestureScale = event.scale || 1
    lastGestureRotation = event.rotation || 0
    event.preventDefault()
  }

  const onGestureChange = (event) => {
    const nextScale = event.scale || 1
    const scaleDelta = nextScale / (lastGestureScale || 1)
    lastGestureScale = nextScale
    applyTrackpadZoom(scaleDelta)

    const nextRotation = event.rotation || 0
    const rotationDelta = nextRotation - lastGestureRotation
    lastGestureRotation = nextRotation
    if (Math.abs(rotationDelta) > 0.05) applyTrackpadHeading(rotationDelta)

    event.preventDefault()
  }

  const onGestureEnd = (event) => {
    lastGestureScale = 1
    lastGestureRotation = 0
    event.preventDefault()
  }

  const stopCesiumWheel = (event) => {
    event.preventDefault()
    event.stopPropagation()
    if (typeof event.stopImmediatePropagation === 'function') event.stopImmediatePropagation()
  }

  const onWheel = (event) => {
    const eventTarget = event.target
    const fromScene = pointerInScene || eventTarget === containerEl || containerEl.contains(eventTarget)
    if (!fromScene || isSidePanelEvent(event)) return

    const { x, y } = normalizeWheelDelta(event)

    if (event.ctrlKey) {
      const scaleDelta = Math.exp(-y * 0.004)
      applyTrackpadZoom(scaleDelta)
      stopCesiumWheel(event)
      return
    }

    if (viewControlMode.value || event.shiftKey || event.altKey) {
      if (viewControlMode.value) {
        if (Math.abs(x) > 0.1) applyTrackpadHeading(x * 0.018)
        if (Math.abs(y) > 0.1) applyTrackpadTilt(y)
      } else if (event.altKey) {
        const headingSource = Math.abs(x) > 0.1 ? x : y
        if (Math.abs(headingSource) > 0.1) applyTrackpadHeading(headingSource * 0.018)
      } else {
        const headingSource = Math.abs(x) > 0.1 ? x : y
        if (Math.abs(headingSource) > 0.1) applyTrackpadHeading(headingSource * 0.018)
      }
      stopCesiumWheel(event)
    }
  }

  const onPointerEnter = () => { pointerInScene = true }
  const onPointerLeave = () => { pointerInScene = false }

  containerEl.addEventListener('gesturestart', onGestureStart, { passive: false })
  containerEl.addEventListener('gesturechange', onGestureChange, { passive: false })
  containerEl.addEventListener('gestureend', onGestureEnd, { passive: false })
  containerEl.addEventListener('pointerenter', onPointerEnter)
  containerEl.addEventListener('pointerleave', onPointerLeave)
  containerEl.addEventListener('mouseenter', onPointerEnter)
  containerEl.addEventListener('mouseleave', onPointerLeave)
  containerEl.addEventListener('wheel', onWheel, { passive: false, capture: true })
  viewer.value?.canvas?.addEventListener('wheel', onWheel, { passive: false, capture: true })
  window.addEventListener('wheel', onWheel, { passive: false, capture: true })

  return () => {
    containerEl.removeEventListener('gesturestart', onGestureStart)
    containerEl.removeEventListener('gesturechange', onGestureChange)
    containerEl.removeEventListener('gestureend', onGestureEnd)
    containerEl.removeEventListener('pointerenter', onPointerEnter)
    containerEl.removeEventListener('pointerleave', onPointerLeave)
    containerEl.removeEventListener('mouseenter', onPointerEnter)
    containerEl.removeEventListener('mouseleave', onPointerLeave)
    containerEl.removeEventListener('wheel', onWheel, { capture: true })
    viewer.value?.canvas?.removeEventListener('wheel', onWheel, { capture: true })
    window.removeEventListener('wheel', onWheel, { capture: true })
  }
}

function toggleViewControlMode() {
  viewControlMode.value = !viewControlMode.value
}

onMounted(async () => {
  const creditEl = document.createElement('div')
  creditEl.style.cssText = 'position:absolute;font-size:0;opacity:0;pointer-events:none;'
  container.value.appendChild(creditEl)

  const v = new Cesium.Viewer(container.value, {
    baseLayer: new Cesium.ImageryLayer(
      createOnlineMapImageryProvider()
    ),
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    baseLayerPicker: false,
    geocoder: false,
    animation: false,
    timeline: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    selectionIndicator: false,
    infoBox: false,
    creditContainer: creditEl,
  })
  v.imageryLayers.addImageryProvider(createLocalMapImageryProvider())
  v.scene.globe.depthTestAgainstTerrain = true
  v.scene.globe.maximumScreenSpaceError = 3
  v.scene.screenSpaceCameraController.inertiaSpin = 0.35
  v.scene.screenSpaceCameraController.inertiaTranslate = 0.35
  v.scene.screenSpaceCameraController.inertiaZoom = 0.28
  v.scene.fog.enabled = true
  v.scene.fog.density = 0.00018
  v.scene.requestRenderMode = false

  v.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(139.7671, 35.6812, 18000),
    orientation: {
      heading: Cesium.Math.toRadians(20),
      pitch: Cesium.Math.toRadians(-35),
      roll: 0,
    },
  })

  viewer.value = v
  removeTrackpadZoomListeners = installTrackpadZoom(container.value)
  fetchCatalog()
  refreshLocal()
  refreshStatus()

  // 加载本地/缓存的 GSI DEM 作为地形，map_tiles 会自动贴合在这层高度表面上。
  try {
    v.terrainProvider = createGsiDemTerrainProvider()
    terrainEnabled.value = true
    for (const { tileset } of mountedTilesets.values()) {
      if (tileset) await dropTilesetToGround(tileset)
    }
  } catch (e) {
    console.warn('GSI DEM 地形初始化失败:', e?.message || e)
  }

  // 视口自动挂载：相机停下时触发
  v.camera.moveEnd.addEventListener(() => {
    if (autoMount.value) scheduleAutoMount()
  })
})

onUnmounted(() => {
  if (removeTrackpadZoomListeners) {
    removeTrackpadZoomListeners()
    removeTrackpadZoomListeners = null
  }
  stopPolling()
  // 卸载所有挂载中的 tileset
  for (const { tileset } of mountedTilesets.values()) {
    try { viewer.value && viewer.value.scene.primitives.remove(tileset) } catch (_) {}
  }
  mountedTilesets.clear()
  if (viewer.value && !viewer.value.isDestroyed()) viewer.value.destroy()
  viewer.value = null
})

onDeactivated(() => {
  if (viewer.value && !viewer.value.isDestroyed()) viewer.value.useDefaultRenderLoop = false
})

onActivated(() => {
  if (viewer.value && !viewer.value.isDestroyed()) {
    viewer.value.useDefaultRenderLoop = true
    viewer.value.resize()
  }
})

// -------- GSI DEM 地形提供者 --------
// 解码 GSI PNG-encoded heightmap：
//   每像素 RGB → 24bit 有符号整数 v = (R<<16)|(G<<8)|B；高度 h = v / 100 米
//   无数据像素：(R,G,B) = (128, 0, 0)
function decodeGsiDemPng(img) {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 256
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0)
  const data = ctx.getImageData(0, 0, 256, 256).data
  const heights = new Float32Array(256 * 256)
  for (let i = 0; i < 256 * 256; i++) {
    const j = i * 4
    const r = data[j], g = data[j + 1], b = data[j + 2]
    if (r === 128 && g === 0 && b === 0) {
      heights[i] = 0
    } else {
      const v = (r << 16) + (g << 8) + b
      heights[i] = (v >= 0x800000 ? v - 0x1000000 : v) / 100
    }
  }
  return heights
}

function loadImageAnon(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image load failed'))
    img.src = url
  })
}

function createGsiDemTerrainProvider() {
  const tilingScheme = new Cesium.WebMercatorTilingScheme()
  const errorEvent = new Cesium.Event()
  const credit = new Cesium.Credit('国土地理院 DEM')
  const flatBuffer16x16 = new Float32Array(16 * 16)
  const geometryCache = new Map()

  return {
    tilingScheme,
    errorEvent,
    credit,
    hasWaterMask: false,
    hasVertexNormals: false,
    availability: undefined,
    get ready() { return true },
    get readyPromise() { return Promise.resolve(true) },

    getLevelMaximumGeometricError(level) {
      return Cesium.TerrainProvider.getEstimatedLevelZeroGeometricErrorForAHeightmap(
        tilingScheme.ellipsoid, 65, tilingScheme.getNumberOfXTilesAtLevel(0)
      ) / (1 << level)
    },

    getTileDataAvailable(x, y, level) {
      // GSI DEM 大致到 14 级；低级别也存在但可能是黑底
      return level <= TERRAIN_RENDER_MAX_LEVEL
    },

    loadTileDataAvailability() { return undefined },

    async requestTileGeometry(x, y, level) {
      // 太低/太高级别直接返平：避免无谓请求
      if (level < 4 || level > TERRAIN_RENDER_MAX_LEVEL) {
        return new Cesium.HeightmapTerrainData({
          buffer: flatBuffer16x16, width: 16, height: 16, childTileMask: 15,
        })
      }
      const cacheKey = `${level}/${x}/${y}`
      const cached = geometryCache.get(cacheKey)
      if (cached) return cached
      const url = `/gsi-dem/${level}/${x}/${y}.png`
      try {
        const img = await loadImageAnon(url)
        const heights = decodeGsiDemPng(img)
        const data = new Cesium.HeightmapTerrainData({
          buffer: heights, width: 256, height: 256, childTileMask: 15,
        })
        if (geometryCache.size > 512) geometryCache.clear()
        geometryCache.set(cacheKey, data)
        return data
      } catch (_) {
        // 海上 / 日本以外：返回全 0
        return new Cesium.HeightmapTerrainData({
          buffer: flatBuffer16x16, width: 16, height: 16, childTileMask: 15,
        })
      }
    },
  }
}


// -------- Actions --------
function tileHeaderMinimumHeight(tile) {
  const bv = tile?._header?.boundingVolume
  if (!bv) return null

  if (Array.isArray(bv.region) && Number.isFinite(bv.region[4])) {
    return bv.region[4]
  }

  // box/sphere 可能处在局部坐标或带 transform，不能直接当 ECEF 解析高度。
  return null
}

function collectMinimumHeightFromTiles(tile, state = { min: Number.POSITIVE_INFINITY, count: 0 }) {
  if (!tile || state.count > 3000) return state
  const h = tileHeaderMinimumHeight(tile)
  if (Number.isFinite(h)) state.min = Math.min(state.min, h)
  state.count++
  ;(tile.children || []).forEach(child => collectMinimumHeightFromTiles(child, state))
  return state
}

function getTilesetMinimumHeight(tileset) {
  const scanned = collectMinimumHeightFromTiles(tileset.root)
  if (Number.isFinite(scanned.min)) return scanned.min

  const bv = tileset.root?.boundingVolume
  if (bv && typeof bv.minimumHeight === 'number') return bv.minimumHeight

  const center = Cesium.Cartographic.fromCartesian(tileset.boundingSphere.center)
  return center.height - ESTIMATED_BUILDING_BASE_BELOW_CENTER_METERS
}

function lonLatToTilePixel(longitude, latitude, level) {
  const lon = Cesium.Math.toDegrees(longitude)
  const lat = Cesium.Math.toDegrees(latitude)
  const n = 2 ** level
  const xFloat = (lon + 180) / 360 * n
  const latRad = Cesium.Math.toRadians(lat)
  const yFloat = (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * n
  return {
    x: Math.floor(xFloat),
    y: Math.floor(yFloat),
    px: Math.min(255, Math.max(0, Math.floor((xFloat - Math.floor(xFloat)) * 256))),
    py: Math.min(255, Math.max(0, Math.floor((yFloat - Math.floor(yFloat)) * 256))),
  }
}

function decodeGsiDemPixel(img, px, py) {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, px, py, 1, 1, 0, 0, 1, 1)
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
  if (r === 128 && g === 0 && b === 0) return null
  const v = (r << 16) + (g << 8) + b
  return (v >= 0x800000 ? v - 0x1000000 : v) / 100
}

async function sampleLocalDemPixel(longitude, latitude) {
  for (let level = DEM_SNAP_MAX_LEVEL; level >= DEM_SNAP_MIN_LEVEL; level--) {
    const { x, y, px, py } = lonLatToTilePixel(longitude, latitude, level)
    const key = `${level}/${x}/${y}/${px}/${py}`
    if (demPixelCache.has(key)) return demPixelCache.get(key)
    try {
      const img = await loadImageAnon(`/gsi-dem/${level}/${x}/${y}.png`)
      const h = decodeGsiDemPixel(img, px, py)
      if (Number.isFinite(h)) {
        const result = { height: h, source: `DEM Z${level} ${x}/${y} (${px},${py})` }
        if (demPixelCache.size > 800) demPixelCache.clear()
        demPixelCache.set(key, result)
        return result
      }
      demPixelCache.set(key, null)
    } catch (_) {}
  }
  return null
}

function offsetLonLat(longitude, latitude, eastMeters, northMeters) {
  const earthRadius = 6378137
  const lat = latitude + northMeters / earthRadius
  const lon = longitude + eastMeters / (earthRadius * Math.max(Math.cos(latitude), 0.25))
  return { longitude: lon, latitude: lat }
}

async function sampleDemPatch(longitude, latitude, radiusMeters) {
  const radius = Cesium.Math.clamp((radiusMeters || 120) * 0.18, 25, 120)
  const offsets = [
    [0, 0],
    [radius, 0],
    [-radius, 0],
    [0, radius],
    [0, -radius],
    [radius * 0.7, radius * 0.7],
    [-radius * 0.7, radius * 0.7],
    [radius * 0.7, -radius * 0.7],
    [-radius * 0.7, -radius * 0.7],
  ]
  const samples = []
  let centerHeight = null
  for (const [east, north] of offsets) {
    const p = offsetLonLat(longitude, latitude, east, north)
    const dem = await sampleLocalDemPixel(p.longitude, p.latitude)
    if (dem && Number.isFinite(dem.height)) {
      if (east === 0 && north === 0) centerHeight = dem.height
      samples.push(dem.height)
    }
  }
  if (!samples.length) return null
  const sorted = samples.slice().sort((a, b) => a - b)
  const medianHeight = sorted[Math.floor(sorted.length / 2)]
  const terrainHeight = Number.isFinite(centerHeight) ? (centerHeight * 0.65 + medianHeight * 0.35) : medianHeight
  return {
    height: terrainHeight,
    source: `DEM patch median (${samples.length} samples, center ${(centerHeight ?? terrainHeight).toFixed(2)} m)`,
  }
}

async function sampleRenderedTerrain(longitude, latitude) {
  if (!viewer.value) return { height: 0, source: '无 viewer' }
  const dem = await sampleLocalDemPixel(longitude, latitude)
  if (dem) return dem

  try {
    const height = viewer.value.scene.globe.getHeight(new Cesium.Cartographic(longitude, latitude))
    if (Number.isFinite(height)) return { height, source: 'Cesium globe.getHeight' }
  } catch (_) {}

  try {
    const samples = [new Cesium.Cartographic(longitude, latitude)]
    const result = await Cesium.sampleTerrain(viewer.value.terrainProvider, 12, samples)
    if (Number.isFinite(result[0]?.height)) {
      return { height: result[0].height, source: 'Cesium sampleTerrain Z12' }
    }
  } catch (_) {}

  return { height: 0, source: '平面兜底' }
}

function applyVerticalOffset(tileset, longitude, latitude, offsetMeters) {
  const surface = Cesium.Cartesian3.fromRadians(longitude, latitude, 0)
  const target = Cesium.Cartesian3.fromRadians(longitude, latitude, offsetMeters)
  const translation = Cesium.Cartesian3.subtract(target, surface, new Cesium.Cartesian3())
  tileset.modelMatrix = Cesium.Matrix4.fromTranslation(translation)
}

function tuneTilesetForStableView(tileset, { auto = false } = {}) {
  if (!tileset) return
  tileset.show = true
  tileset.maximumScreenSpaceError = auto ? 16 : 10
  tileset.skipLevelOfDetail = false
  tileset.cullRequestsWhileMoving = false
  tileset.cullRequestsWhileMovingMultiplier = 0
  tileset.preloadWhenHidden = false
  tileset.preloadFlightDestinations = false
  tileset.dynamicScreenSpaceError = true
  tileset.dynamicScreenSpaceErrorDensity = 0.0018
  tileset.dynamicScreenSpaceErrorFactor = auto ? 10 : 6
  tileset.cacheBytes = auto ? 96 * 1024 * 1024 : 160 * 1024 * 1024
  tileset.maximumCacheOverflowBytes = auto ? 48 * 1024 * 1024 : 96 * 1024 * 1024
  tileset.immediatelyLoadDesiredLevelOfDetail = false
  tileset.loadSiblings = false
}

function clampSnapOffset(offsetMeters) {
  if (!Number.isFinite(offsetMeters)) return 0
  return Cesium.Math.clamp(
    offsetMeters,
    -MAX_BUILDING_SNAP_OFFSET_METERS,
    MAX_BUILDING_SNAP_OFFSET_METERS
  )
}

function formatMeters(value) {
  return Number.isFinite(value) ? `${value.toFixed(2)} m` : '-'
}

// 把 tileset 调整到地形附近
// - 真实地形开启时：采样 DEM 高度，把建筑最低端贴到该高度
// - 平面椭球模式下：用 root tile 的 boundingVolume.minimumHeight 把"整个 tileset 的最低点"放到 h=0
//   → 沿海建筑跟底图对齐；山上建筑会保留真实高差（看上去飘在平面地图上方，限制由平面 basemap 造成）
async function dropTilesetToGround(tileset, options = {}) {
  if (terrainEnabled.value) {
    if (!tileset.root || !tileset.boundingSphere) return
    const carto = Cesium.Cartographic.fromCartesian(tileset.boundingSphere.center)
    const tilesetMinHeight = getTilesetMinimumHeight(tileset)
    const terrain = await sampleDemPatch(
      carto.longitude,
      carto.latitude,
      tileset.boundingSphere.radius
    ) || await sampleRenderedTerrain(carto.longitude, carto.latitude)
    const rawOffset = terrain.height - tilesetMinHeight + BUILDING_HEIGHT_OFFSET_METERS
    const offset = clampSnapOffset(rawOffset)
    applyVerticalOffset(tileset, carto.longitude, carto.latitude, offset)
    if (options.recordDiagnostic) {
      snapDiagnostic.value = {
        lon: Cesium.Math.toDegrees(carto.longitude),
        lat: Cesium.Math.toDegrees(carto.latitude),
        buildingMinHeight: tilesetMinHeight,
        terrainHeight: terrain.height,
        terrainSource: terrain.source,
        rawOffset,
        appliedOffset: offset,
      }
      console.info('[贴地诊断]', snapDiagnostic.value)
    }
    return
  }

  const root = tileset.root
  if (!root || !tileset.boundingSphere) return

  let groundHeight = null
  const bv = root.boundingVolume
  if (bv && typeof bv.minimumHeight === 'number') {
    groundHeight = bv.minimumHeight
  } else {
    const carto = Cesium.Cartographic.fromCartesian(tileset.boundingSphere.center)
    groundHeight = Math.max(carto.height - 8, 0)
  }

  if (Math.abs(groundHeight) < 0.5) return

  const carto = Cesium.Cartographic.fromCartesian(tileset.boundingSphere.center)
  applyVerticalOffset(tileset, carto.longitude, carto.latitude, -groundHeight)
}

function flyToTileset(tileset, duration = 1.8) {
  const range = Cesium.Math.clamp(tileset.boundingSphere.radius * 2.5, 1500, 12000)
  viewer.value.camera.flyToBoundingSphere(tileset.boundingSphere, {
    duration,
    offset: new Cesium.HeadingPitchRange(
      Cesium.Math.toRadians(30),
      Cesium.Math.toRadians(-45),
      range
    ),
  })
}

async function loadDataset(dataset) {
  if (busy.value) return
  busy.value = dataset.id
  errMsg.value = null
  snapDiagnostic.value = null

  // 单选模式：把多挂载里旧的全部卸掉
  for (const { tileset } of mountedTilesets.values()) {
    try { viewer.value.scene.primitives.remove(tileset) } catch (_) {}
  }
  mountedTilesets.clear()
  currentTileset = null

  let tileset
  try {
    const url = effectiveUrl(dataset)
    tileset = await Cesium.Cesium3DTileset.fromUrl(url)
    tuneTilesetForStableView(tileset)
    viewer.value.scene.primitives.add(tileset)
    await dropTilesetToGround(tileset, { recordDiagnostic: true })
    cacheTilesetCenter(dataset.id, tileset)
    mountedTilesets.set(dataset.id, { tileset: markRaw(tileset), dataset, mountedAt: Date.now() })
    currentTileset = tileset
    currentDataset.value = dataset
  } catch (e) {
    console.error('PLATEAU tileset load error:', e)
    errMsg.value = `加载失败：${dataset.ward || dataset.city} — ${e.message}`
    setTimeout(() => { errMsg.value = null }, 6000)
    busy.value = null
    return
  }

  busy.value = null
  flyToTileset(tileset)

  // 自动下载：远程加载成功后顺手把数据下到本地
  if (autoDownload.value && !localSet.value.has(dataset.id)) {
    downloadDataset(dataset)
  }
}

function resetView() {
  if (!currentTileset || !viewer.value) return
  flyToTileset(currentTileset, 1.5)
}

// 缓存 tileset 的中心经纬度（用于视口检测）
function cacheTilesetCenter(id, tileset) {
  if (!tileset.boundingSphere) return
  const c = Cesium.Cartographic.fromCartesian(tileset.boundingSphere.center)
  const earthRadius = viewer.value?.scene.globe.ellipsoid.maximumRadius || 6378137
  const latBuffer = Cesium.Math.toDegrees(tileset.boundingSphere.radius / earthRadius)
  const lonBuffer = latBuffer / Math.max(Math.cos(c.latitude), 0.25)
  tilesetCenterCache.set(id, {
    lon: Cesium.Math.toDegrees(c.longitude),
    lat: Cesium.Math.toDegrees(c.latitude),
  })
  tilesetBoundsCache.set(id, {
    west: Cesium.Math.toDegrees(c.longitude) - lonBuffer,
    south: Cesium.Math.toDegrees(c.latitude) - latBuffer,
    east: Cesium.Math.toDegrees(c.longitude) + lonBuffer,
    north: Cesium.Math.toDegrees(c.latitude) + latBuffer,
  })
}

// 计算当前相机视口在地表的经纬度矩形（粗略）
function getViewportBounds() {
  const v = viewer.value
  if (!v) return null
  const rect = v.camera.computeViewRectangle(v.scene.globe.ellipsoid)
  if (!rect) return null
  return {
    west: Cesium.Math.toDegrees(rect.west),
    south: Cesium.Math.toDegrees(rect.south),
    east: Cesium.Math.toDegrees(rect.east),
    north: Cesium.Math.toDegrees(rect.north),
  }
}

// 给定 dataset，返回它的"代表点"经纬度（优先缓存，否则用 pref 中心兜底）
function datasetPoint(dataset) {
  const c = tilesetCenterCache.get(dataset.id)
  if (c) return c
  const p = PREF_CENTER[dataset.pref_code]
  return p ? { lon: p[0], lat: p[1] } : null
}

function rectIntersects(a, b) {
  return a.west <= b.east && a.east >= b.west && a.south <= b.north && a.north >= b.south
}

function datasetIntersectsViewport(dataset, bounds) {
  const rect = tilesetBoundsCache.get(dataset.id)
  if (rect) return rectIntersects(rect, bounds)
  const p = datasetPoint(dataset)
  return !!p && p.lon >= bounds.west && p.lon <= bounds.east &&
    p.lat >= bounds.south && p.lat <= bounds.north
}

// 视口自动挂载逻辑（相机停下时调用，加节流）
let autoMountTimer = null
function scheduleAutoMount() {
  if (autoMountTimer) clearTimeout(autoMountTimer)
  autoMountTimer = setTimeout(runAutoMount, 250)
}

async function runAutoMount() {
  if (!autoMount.value || !viewer.value) return
  const bounds = getViewportBounds()
  if (!bounds) return

  // 视口面积（度²）—— 太大就不自动挂载（比如俯瞰整个日本）
  const area = (bounds.east - bounds.west) * (bounds.north - bounds.south)
  if (area > 4) return  // 大于 ~2°×2° 不挂

  // 候选：当前筛选范围内 + 代表点落在视口
  const candidates = []
  for (const d of visibleDatasets.value) {
    if (datasetIntersectsViewport(d, bounds)) candidates.push(d)
  }
  if (candidates.length === 0 && mountedTilesets.size > 0 && currentCameraHeight() < 2500) return

  // 按 LOD 优先级，每个 city_code+ward_code 只取一个
  const byKey = new Map()
  const dsKey = (d) => `${d.city_code || ''}_${d.ward_code || ''}_${d.pref_code}`
  const lodWeight = (lod) => ({ 2: 4, 1: 3, 3: 2, 4: 1 }[lod] || 0)
  for (const d of candidates) {
    const k = dsKey(d)
    const cur = byKey.get(k)
    if (!cur || lodWeight(d.lod) > lodWeight(cur.lod)) byKey.set(k, d)
  }
  const targets = Array.from(byKey.values()).slice(0, MAX_MOUNTED)

  // 挂载：只补新目标，不按视口结果自动卸载；倾斜视角下 computeViewRectangle 不稳定，自动卸载会造成建筑闪消。
  for (const d of targets) {
    if (mountedTilesets.size >= MAX_MOUNTED) break
    if (mountedTilesets.has(d.id)) continue
    mountTileset(d)  // 不 await，并发挂
  }
}

async function mountTileset(dataset) {
  // 占位防并发同 id
  mountedTilesets.set(dataset.id, { tileset: null, dataset, mountedAt: Date.now() })
  try {
    const url = effectiveUrl(dataset)
    const tileset = await Cesium.Cesium3DTileset.fromUrl(url)
    tuneTilesetForStableView(tileset, { auto: true })
    viewer.value.scene.primitives.add(tileset)
    await dropTilesetToGround(tileset)
    cacheTilesetCenter(dataset.id, tileset)
    mountedTilesets.set(dataset.id, { tileset: markRaw(tileset), dataset, mountedAt: Date.now() })

    if (autoDownload.value && !localSet.value.has(dataset.id)) {
      downloadDataset(dataset)
    }
  } catch (e) {
    mountedTilesets.delete(dataset.id)
    console.warn('mountTileset 失败:', dataset.id, e.message)
  }
}

function toggleScene() {
  if (!viewer.value) return
  is3D.value = !is3D.value
  is3D.value ? viewer.value.scene.morphTo3D(1.0) : viewer.value.scene.morphTo2D(1.0)
}
</script>

<style scoped>
.plateau-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0d1117;
}

.cesium-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
}

/* ---- 侧面板 ---- */
.side-panel {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 252px;
  background: rgba(10, 14, 23, 0.9);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 13px;
  color: #e2e8f0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: calc(100dvh - 96px);
  overflow-y: auto;
}

.side-panel::-webkit-scrollbar { width: 3px; }
.side-panel::-webkit-scrollbar-track { background: transparent; }
.side-panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.panel-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.head-badge {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #7c3aed, #4f46e5);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.8rem;
  color: white;
  flex-shrink: 0;
}

.head-title { font-size: 0.9rem; font-weight: 700; color: #f1f5f9; letter-spacing: 0.08em; }
.head-sub { font-size: 0.62rem; color: #475569; margin-top: 1px; display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }

.terrain-badge {
  font-size: 0.58rem;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.terrain-badge.on  { background: rgba(16,185,129,0.15); color: #4ade80; border: 1px solid rgba(16,185,129,0.22); }
.terrain-badge.off { background: rgba(100,116,139,0.12); color: #64748b; border: 1px solid rgba(100,116,139,0.2); }

/* ---- 目录状态 ---- */
.catalog-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 0.75rem;
  padding: 8px 0;
}

.mini-ring {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(124,58,237,0.2);
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: rotate 0.8s linear infinite;
  flex-shrink: 0;
}

.catalog-err {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #fca5a5;
  font-size: 0.72rem;
  padding: 6px 8px;
  background: rgba(239,68,68,0.1);
  border-radius: 7px;
  border: 1px solid rgba(239,68,68,0.2);
}

.retry-btn {
  background: rgba(239,68,68,0.15);
  border: 1px solid rgba(239,68,68,0.25);
  color: #fca5a5;
  padding: 2px 8px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.68rem;
}

/* ---- 筛选 ---- */
.section-label {
  font-size: 0.65rem;
  font-weight: 600;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  display: flex;
  align-items: center;
  gap: 5px;
}

.count-badge {
  font-size: 0.6rem;
  background: rgba(124,58,237,0.2);
  color: #a78bfa;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 600;
}

.filter-group { display: flex; flex-direction: column; gap: 4px; }

.filter-select, .filter-input {
  width: 100%;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 7px;
  color: #94a3b8;
  font-size: 0.73rem;
  padding: 6px 8px;
  outline: none;
  transition: border-color 0.15s;
}

.filter-select:focus, .filter-input:focus {
  border-color: rgba(124,58,237,0.4);
  color: #cbd5e1;
}

.filter-select option { background: #1e293b; }
.filter-input::placeholder { color: #334155; }

/* ---- LOD 筛选 ---- */
.lod-filter {
  display: flex;
  gap: 4px;
}

.lod-opt {
  flex: 1;
  padding: 4px 0;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 6px;
  color: #475569;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.13s;
}

.lod-opt:hover { color: #94a3b8; background: rgba(255,255,255,0.07); }
.lod-opt.active { background: rgba(124,58,237,0.2); border-color: rgba(124,58,237,0.35); color: #c4b5fd; }

/* ---- 数据集列表 ---- */
.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  max-height: 200px;
}

.dataset-list::-webkit-scrollbar { width: 3px; }
.dataset-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

.dataset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  cursor: pointer;
  transition: all 0.12s;
  text-align: left;
  width: 100%;
  gap: 6px;
}

.dataset-item:hover:not(:disabled) {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.07);
}

.dataset-item.active {
  background: rgba(16,185,129,0.12);
  border-color: rgba(16,185,129,0.9);
  box-shadow: inset 0 0 0 1px rgba(16,185,129,0.45);
}

.dataset-item.loading { opacity: 0.65; }
.dataset-item:disabled { cursor: wait; }

.ds-names { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.ds-city { font-size: 0.76rem; font-weight: 600; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ds-pref { font-size: 0.6rem; color: #334155; }

.ds-tags { display: flex; align-items: center; gap: 3px; flex-shrink: 0; }

.lod-tag {
  font-size: 0.58rem;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  letter-spacing: 0.03em;
}

.lod-tag.lod2, .lod-opt-2 {
  background: rgba(34,197,94,0.12);
  color: #4ade80;
  border: 1px solid rgba(34,197,94,0.18);
}

.lod-tag.lod1 {
  background: rgba(251,191,36,0.12);
  color: #fbbf24;
  border: 1px solid rgba(251,191,36,0.18);
}

.year-tag {
  font-size: 0.58rem;
  color: #334155;
  font-weight: 500;
}

.spin-icon {
  font-size: 0.85rem;
  color: #7c3aed;
  animation: rotate 0.9s linear infinite;
  display: inline-block;
}

@keyframes rotate { to { transform: rotate(360deg); } }

.list-hint, .list-empty {
  font-size: 0.66rem;
  color: #334155;
  text-align: center;
  padding: 6px;
}

/* ---- 自动模式开关 ---- */
.auto-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 7px;
}

.auto-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  font-size: 0.72rem;
  color: #64748b;
  user-select: none;
}

.auto-toggle input { display: none; }

.auto-dot {
  width: 28px;
  height: 14px;
  background: rgba(255,255,255,0.08);
  border-radius: 7px;
  position: relative;
  transition: background 0.18s;
  flex-shrink: 0;
}

.auto-dot::after {
  content: '';
  position: absolute;
  width: 10px;
  height: 10px;
  background: #64748b;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: all 0.18s;
}

.auto-toggle.on .auto-dot { background: rgba(124,58,237,0.4); }
.auto-toggle.on .auto-dot::after {
  background: #c4b5fd;
  left: 16px;
}
.auto-toggle.on { color: #cbd5e1; }

/* ---- 数据集行的下载/状态 ---- */
.dataset-item.mounted {
  border-color: rgba(16,185,129,0.24);
}

.local-count {
  font-size: 0.6rem;
  background: rgba(16,185,129,0.15);
  color: #34d399;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 600;
  margin-left: auto;
}

.dl-btn {
  width: 18px;
  height: 18px;
  background: rgba(124,58,237,0.12);
  border: 1px solid rgba(124,58,237,0.22);
  color: #a78bfa;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.dl-btn:hover { background: rgba(124,58,237,0.22); color: #ddd6fe; }

.state-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 4px;
}

.state-tag.local {
  background: rgba(16,185,129,0.18);
  color: #4ade80;
  border: 1px solid rgba(16,185,129,0.25);
}

.state-tag.dl-progress {
  background: rgba(124,58,237,0.15);
  border: 1px solid rgba(124,58,237,0.25);
}

.dl-spinner {
  width: 9px;
  height: 9px;
  border: 1.5px solid rgba(124,58,237,0.2);
  border-top-color: #a78bfa;
  border-radius: 50%;
  animation: rotate 0.7s linear infinite;
}

/* ---- 加载来源 / 多挂载状态 ---- */
.src-local { color: #4ade80 !important; }
.src-remote { color: #94a3b8 !important; }

.mount-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 9px;
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.18);
  border-radius: 7px;
  font-size: 0.7rem;
}

.mount-box span { color: #475569; }
.mount-box b { color: #4ade80; font-weight: 600; }

/* ---- 控制按钮 ---- */
.ctrl-btns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}

.ctrl-btn {
  padding: 6px 4px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 7px;
  color: #475569;
  font-size: 0.71rem;
  cursor: pointer;
  transition: all 0.13s;
  font-weight: 500;
}

.ctrl-btn:hover:not(:disabled) { background: rgba(255,255,255,0.08); color: #94a3b8; }
.ctrl-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ---- 信息框 ---- */
.info-box {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 7px;
  padding: 8px 9px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.68rem;
}

.info-row span { color: #334155; }
.info-row b { color: #64748b; font-weight: 600; }
.info-row.diag-row {
  border-top: 1px solid rgba(255,255,255,0.04);
  padding-top: 4px;
}
.info-row.diag-row b {
  color: #34d399;
  font-family: 'Fira Code', monospace;
  font-size: 0.64rem;
}

.tip-box {
  font-size: 0.62rem;
  color: #1e293b;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 6px;
}

/* ---- 右上角标志 ---- */
.corner-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(10,14,23,0.82);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 20px;
  font-size: 0.68rem;
  color: #334155;
  z-index: 100;
  pointer-events: none;
}

.live-dot {
  width: 5px;
  height: 5px;
  background: #4ade80;
  border-radius: 50%;
  animation: blink 2.2s ease-in-out infinite;
}

@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.3; } }

/* ---- Toasts ---- */
.load-toast {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 18px;
  background: rgba(10,14,23,0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(124,58,237,0.28);
  border-radius: 22px;
  color: #c4b5fd;
  font-size: 0.78rem;
  z-index: 200;
  white-space: nowrap;
}

.load-ring {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(124,58,237,0.2);
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: rotate 0.7s linear infinite;
  flex-shrink: 0;
}

.err-toast {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 13px;
  background: rgba(127,29,29,0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 9px;
  color: #fca5a5;
  font-size: 0.75rem;
  z-index: 200;
  max-width: 480px;
}

.err-toast button {
  background: none;
  border: none;
  color: #fca5a5;
  cursor: pointer;
  padding: 0 2px;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.22s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
