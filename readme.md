# 🗾 日本地图瓦片下载系统 - 完整部署指南

## 📁 项目结构

```
your_project/
├── map_tile_downloader.py    # Python 后端（Flask API）
├── TileDownloader.vue         # Vue 前端组件
└── map_tiles/                 # 下载的瓦片存储目录（自动创建）
    ├── 5/
    ├── 6/
    ├── 7/
    └── 8/
```

## 🚀 快速开始

### 步骤 1: 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install flask flask-cors requests
```

### 步骤 2: 启动后端服务

```bash
python map_tile_downloader.py
```

你应该看到：
```
============================================================
🚀 日本地图瓦片下载服务已启动
============================================================
📁 瓦片保存目录: /your/path/map_tiles
🌐 API 服务地址: http://localhost:5000
🗺️  瓦片访问地址: http://localhost:5000/map_tiles/{z}/{x}/{y}.png
============================================================
```

### 步骤 3: 集成 Vue 前端

#### 方式 A: 在现有 Vue 3 项目中使用

将 `TileDownloader.vue` 复制到你的项目中：

```vue
<!-- 在你的页面中使用 -->
<template>
  <div>
    <TileDownloader />
  </div>
</template>

<script setup>
import TileDownloader from './components/TileDownloader.vue';
</script>
```

#### 方式 B: 快速创建新 Vue 项目

```bash
# 创建新项目
npm create vue@latest map-tile-app

# 进入项目
cd map-tile-app

# 安装依赖
npm install

# 将 TileDownloader.vue 放入 src/components/

# 修改 src/App.vue
# 然后启动开发服务器
npm run dev
```

## 🎯 使用流程

1. **启动后端**: 运行 Python 脚本
2. **访问前端**: 打开浏览器访问 Vue 应用
3. **配置下载**:
   - 选择区域（如"东京周边"）
   - 设置缩放级别（建议 5-8）
4. **开始下载**: 点击"开始下载"按钮
5. **查看进度**: 实时查看下载进度和日志

## 🗺️ 在你的地图应用中使用下载的瓦片

### 原始代码（从网络加载）

```javascript
L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', {
  attribution: 'Tiles &copy; GSI Japan',
  maxZoom: 18
}).addTo(map);
```

### 修改后（使用本地瓦片）

```javascript
L.tileLayer('http://localhost:5000/map_tiles/{z}/{x}/{y}.png', {
  attribution: 'Tiles &copy; GSI Japan (Cached)',
  maxZoom: 18
}).addTo(map);
```

### 高级：智能回退策略

```javascript
// 优先使用本地，失败后回退到在线
const CustomTileLayer = L.TileLayer.extend({
  createTile: function(coords, done) {
    const tile = document.createElement('img');
    
    // 先尝试本地
    const localUrl = `http://localhost:5000/map_tiles/${coords.z}/${coords.x}/${coords.y}.png`;
    
    tile.onload = () => done(null, tile);
    tile.onerror = () => {
      // 本地失败，使用在线源
      const onlineUrl = `https://cyberjapandata.gsi.go.jp/xyz/std/${coords.z}/${coords.x}/${coords.y}.png`;
      tile.src = onlineUrl;
    };
    
    tile.src = localUrl;
    return tile;
  }
});

new CustomTileLayer('', {
  attribution: 'Tiles &copy; GSI Japan',
  maxZoom: 18
}).addTo(map);
```

## 📊 瓦片大小参考（按缩放级别）

| 缩放级别 | 文件大小 | 文件数量 | 说明 |
|---------|---------|---------|------|
| 2 | 700 kB | - | 全球范围 |
| 3 | 2 MB | - | 全球范围 |
| 4 | 6.04 MB | - | 全球范围 |
| 5 | 21.8 MB | - | 全球范围 |
| 6 | 1.20 MB | - | 从此处开始仅日本地图（不含世界地图） |
| 7 | 2.88 MB | - | 日本地图 |
| 8 | 7.08 MB | - | 日本地图 |
| 9 | 13.7 MB | 1,482 个文件 | 日本地图 |
| 10 | 34.9 MB | 5,775 个文件 | 日本地图 |
| 11 | 93.1 MB | 22,797 个文件 | 日本地图 |
| 12 | 383 MB | 41,178 个文件 | 日本地图 |
| 13 | ~1.1 GB | ~123,534 个文件 | 日本地图（估算） |
| 14 | ~3.4 GB | ~370,602 个文件 | 日本地图（估算） |
| 15 | ~10.2 GB | ~1,111,806 个文件 | 日本地图（估算） |
| 16 | ~30.6 GB | ~3,335,418 个文件 | 日本地图（估算） |
| 17 | ~91.8 GB | ~10,006,254 个文件 | 日本地图（估算） |
| 18 | ~275.4 GB | ~30,018,762 个文件 | 日本地图（估算） |

**注意**:
- 缩放级别 2-5 包含全球地图数据
- 缩放级别 6-12 仅包含日本地图数据，因此文件大小相对较小
- 缩放级别 13-18 为估算值，按3倍增长率计算（实际可能因地图覆盖范围而异）
- 建议根据实际存储空间和使用需求选择合适的缩放级别范围

## 🔧 API 接口说明

### 1. 获取可用区域
```http
GET /api/regions
```

响应：
```json
{
  "regions": ["全日本", "关东", "关西", "北海道", "九州", "东京周边"]
}
```

### 2. 开始下载
```http
POST /api/download/start
Content-Type: application/json

{
  "region": "东京周边",
  "zoom_min": 5,
  "zoom_max": 8
}
```

### 3. 获取下载状态
```http
GET /api/download/status
```

响应：
```json
{
  "is_downloading": true,
  "progress": 45,
  "total": 500,
  "current": 225,
  "success": 200,
  "skip": 20,
  "fail": 5,
  "region": "东京周边",
  "logs": [...]
}
```

### 4. 获取存储统计
```http
GET /api/stats
```

### 5. 访问瓦片文件
```http
GET /map_tiles/{z}/{x}/{y}.png
```

## ⚠️ 注意事项

1. **存储空间**: 确保有足够的磁盘空间（建议至少 500MB）
2. **下载速度**: 受网络影响，日本服务器在中国访问可能较慢
3. **并发控制**: 默认 3 个并发，避免对服务器造成压力
4. **跨域问题**: 后端已配置 CORS，确保前后端正常通信
5. **端口占用**: 确保 5000 端口未被占用

## 🐛 常见问题

### 问题 1: CORS 错误
**解决**: 确保后端已安装 `flask-cors` 并正确启动

### 问题 2: 连接失败
**解决**: 检查后端是否运行，前端 API_BASE 地址是否正确

### 问题 3: 下载很慢
**解决**: 
- 减小缩放级别范围
- 选择较小的区域
- 检查网络连接

### 问题 4: 磁盘空间不足
**解决**: 删除不需要的缩放级别，或选择更小的区域

## 📦 生产环境部署建议

1. **使用 Nginx 反向代理**:
```nginx
location /map_tiles/ {
    alias /path/to/map_tiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

2. **使用 Gunicorn 运行 Flask**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 map_tile_downloader:app
```

3. **定期清理**: 设置定时任务清理过期瓦片

4. **监控磁盘**: 监控 `map_tiles/` 目录大小

## 🎉 完成！

现在你可以：
- ✅ 批量下载日本地图瓦片
- ✅ 本地缓存加速访问
- ✅ 实时监控下载进度
- ✅ 在任何 Leaflet 应用中使用

祝使用愉快！🗾