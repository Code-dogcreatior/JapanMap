# mapdown 前端说明

`mapdown` 是 JapanMap 的 Vue 3 + Vite 前端。它负责地图瓦片下载控制、本地 2D 地图预览，以及 PLATEAU 3D Tiles 的 Cesium 展示。

## 功能页面

- 瓦片下载引擎：调用 Flask API 下载 GSI 标准地图瓦片和 GSI DEM 高度图，并显示进度、日志和缓存统计。
- 本地地图渲染：使用 Leaflet 渲染日本地图，支持本地缓存、GSI 在线源、优先本地后在线回源。
- 3D 地图：使用 Cesium 加载 PLATEAU 建筑 3D Tiles，在线 GSI 底图打底、本地 map_tiles 透明覆盖，支持目录筛选、本地缓存状态、数据集下载和 DEM 地形贴合。

## 本地开发启动

前端依赖根目录的 Flask 后端。请先在项目根目录启动：

```bash
python map.py
```

后端默认监听：

```text
http://localhost:5001
```

然后在 `mapdown` 目录启动前端：

```bash
npm install
npm run dev
```

Vite 默认访问地址通常是：

```text
http://localhost:5174
```

本项目不要求每次修改后运行 `npm run build`。本地开发以 `npm run dev` 为主。

也可以在项目根目录使用一键脚本同时启动前后端：

```bash
./start_map_all.sh
```

该脚本默认使用 conda `base` 启动后端，并在启动前释放 `5001` 和 `5174` 端口。

## 主要依赖

依赖由 `package.json` 管理：

- `vue`：页面和组件框架。
- `vite`：开发服务器与构建工具。
- `leaflet`：2D 地图渲染。
- `cesium`：3D 场景与 PLATEAU 3D Tiles 渲染。
- `vite-plugin-cesium`：Cesium 在 Vite 中的资源处理。

## Vite 代理

`vite.config.js` 已配置开发代理，前端可以直接请求相对路径：

```text
/api              -> http://localhost:5001
/map_tiles        -> http://localhost:5001
/map_tiles_3d     -> http://localhost:5001
/plateau_tiles    -> http://localhost:5001
/gsi-dem          -> http://localhost:5001
/gsi-dem-local    -> http://localhost:5001
/plateau-api      -> https://api.plateauview.mlit.go.jp
```

其中 `/plateau-api` 会去掉路径前缀后转发到 PLATEAU 官方 API，用于读取 3D Tiles 数据目录。

## 关键文件

```text
src/App.vue                         # 顶部导航和三个页面的切换入口
src/services/api.js                 # 后端 API 封装、瓦片 URL 常量、瓦片数量估算
src/components/download.vue         # GSI 影像瓦片和 DEM 下载控制台
src/components/LocalMapViewer.vue   # Leaflet 本地地图查看器
src/components/PlateauViewer.vue    # Cesium + PLATEAU 3D Tiles 查看器
src/composables/useLog.js           # 前端日志列表工具
```

## 后端接口依赖

下载页依赖：

```http
GET /api/regions
POST /api/download/start
POST /api/download/stop
GET /api/download/status
GET /api/stats
POST /api/dem/download/start
POST /api/dem/download/stop
GET /api/dem/download/status
GET /api/dem/stats
```

2D 地图页依赖：

```http
GET /api/stats
GET /map_tiles/{z}/{x}/{y}.png
```

3D 地图页依赖：

```http
GET /plateau-api/datacatalog/plateau-datasets?type=3DTiles&dataType=bldg
GET https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
POST /api/plateau/download
GET /api/plateau/status
GET /api/plateau/local
GET /plateau_tiles/{dataset_id}/tileset.json
GET /map_tiles_3d/{z}/{x}/{y}.png
GET /gsi-dem/{z}/{x}/{y}.png
GET /gsi-dem-local/{z}/{x}/{y}.png
```

## 常见问题

### 页面提示后端连接失败

确认根目录已经运行：

```bash
python map.py
```

并确认 `http://localhost:5001/api/stats` 可以访问。如果后端端口不是 `5001`，需要同步修改 `vite.config.js` 中的代理目标。

### 本地地图空白或大量缺瓦片

当前选择了本地缓存，但 `map_tiles/` 中还没有对应 zoom 和区域的瓦片。可以切到在线源，或者先在下载页下载对应区域。

### PLATEAU 数据目录加载失败

目录来自 PLATEAU 官方 API，经由 `/plateau-api` 代理访问。请检查网络连接、Vite 代理是否生效，以及浏览器控制台中的 HTTP 状态。

### 3D 地形显示为平面

Cesium 页面优先请求 `/gsi-dem/*`，后端会本地命中即返回，缺失时尝试回源 GSI DEM 并缓存。若网络失败或 GSI 无数据，会返回 no-data 高度图并退回局部平地。

### PLATEAU 数据集下载后仍未显示本地

后端只有在数据集下载完成并生成 `.complete` 标记后，`/api/plateau/local` 才会把它列为本地缓存。大数据集可能需要等待更久，也可能因网络错误导致状态为 failed。

## 开发注意

- 前端默认使用相对路径请求后端，开发时不要把 API 地址硬编码到组件里。
- `LocalMapViewer.vue` 的智能回源只影响 2D Leaflet 页面；3D 页面使用独立的 `/map_tiles_3d/*` 和 `/gsi-dem/*`。
- `PlateauViewer.vue` 中包含 Cesium Ion token。若后续使用需要 Ion 授权的资源，建议改为自己的 token 或环境变量。
- 高 zoom 瓦片、DEM 和 PLATEAU 数据都可能占用大量磁盘空间，前端只负责触发任务，实际缓存位于项目根目录。
