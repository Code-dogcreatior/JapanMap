# JapanMap 本地地图缓存与 3D 展示工具

JapanMap 是一个面向本地开发和数据缓存的日本地图工具。项目由 Flask 后端和 Vue 3 + Vite 前端组成，可以批量下载日本国土地理院 GSI 影像瓦片、缓存 GSI DEM 高度图，并在前端用 Leaflet 和 Cesium 查看 2D/3D 地图与 PLATEAU 建筑 3D Tiles。

## 核心功能

- GSI 标准地图瓦片下载：按区域和 zoom 范围批量缓存到本地。
- GSI DEM 高度图下载与代理：支持批量缓存，也支持按需读取本地 DEM。
- 本地 2D 地图渲染：Leaflet 支持本地、在线、优先本地后回源三种瓦片来源。
- PLATEAU 3D 建筑查看：Cesium 加载 MLIT PLATEAU 3D Tiles，并支持下载到本地缓存。
- 本地静态服务：Flask 统一提供地图瓦片、DEM、PLATEAU 缓存文件和下载状态接口。

## 项目结构

```text
JapanMap/
├── map.py                    # 主后端：Flask API、GSI 瓦片/DEM 下载、PLATEAU 下载与静态服务
├── map_use.py                # 简化版本地瓦片统计与静态服务，可单独用于已有瓦片目录
├── mapdown/                  # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue
│   │   ├── services/api.js
│   │   └── components/
│   │       ├── download.vue
│   │       ├── LocalMapViewer.vue
│   │       └── PlateauViewer.vue
│   ├── package.json
│   └── vite.config.js
├── start_map_all.bat         # Windows 一键启动脚本，需要按本机 Python 路径调整
├── start_map_all.sh          # macOS/Linux 一键启动脚本，启动前会释放占用端口
├── requirements.txt          # Python 后端依赖清单
├── test_plateau_download.py  # PLATEAU 单数据集下载测试脚本
├── map_tiles/                # GSI 标准地图瓦片缓存，运行时生成，已忽略
├── gsi_dem_cache/            # GSI DEM 缓存，运行时生成，已忽略
└── plateau_tiles/            # PLATEAU 3D Tiles 缓存，运行时生成，已忽略
```

`map_tiles/`、`gsi_dem_cache/`、`plateau_tiles/` 会占用较多磁盘空间，已经在 `.gitignore` 中排除。

## 环境依赖

### Python 后端

后端主要依赖：

```bash
conda run -n base python -m pip install -r requirements.txt
```

如果不使用 conda，也可以在你当前项目适配的 Python 环境中运行：

```bash
python -m pip install -r requirements.txt
```

### 前端

前端依赖由 `mapdown/package.json` 管理，主要包括：

- Vue 3
- Vite
- Leaflet
- Cesium
- vite-plugin-cesium

首次运行前进入前端目录安装依赖：

```bash
cd mapdown
npm install
```

## 本地启动

需要同时启动后端和前端。推荐从两个终端分别运行。

### 1. 启动 Flask 后端

在项目根目录运行：

```bash
python map.py
```

默认服务地址：

```text
http://localhost:5001
```

后端会提供 API、瓦片静态服务、DEM 静态服务和 PLATEAU 本地缓存服务。

### 2. 启动 Vite 前端

在另一个终端运行：

```bash
cd mapdown
npm run dev
```

Vite 默认会输出本地访问地址，通常是：

```text
http://localhost:5174
```

`mapdown/vite.config.js` 已配置开发代理，前端请求 `/api`、`/map_tiles`、`/plateau_tiles`、`/gsi-dem*` 等路径时会转发到 Flask 后端。

### 3. Windows 可选启动脚本

Windows 下可以使用：

```bat
start_map_all.bat
```

注意脚本中的 `PY_EXE` 当前写死为：

```bat
D:\Anaconda\python.exe
```

如果你的 Python 不在这个位置，需要先修改脚本，或者让脚本回退到系统 `python`。

### 4. macOS/Linux 一键启动脚本

macOS 或 Linux 下可以使用：

```bash
./start_map_all.sh
```

脚本默认使用 conda `base` 启动后端，启动前会检查并释放以下端口：

```text
5001  # Flask 后端
5174  # Vite 前端
```

如需临时改前端端口或 conda 环境：

```bash
FRONTEND_PORT=5174 CONDA_ENV=base ./start_map_all.sh
```

## 前端页面

前端顶部有三个主要页面：

- 瓦片下载引擎：选择区域和 zoom 范围，下载 GSI 标准地图瓦片和 DEM 高度图。
- 本地地图渲染：使用 Leaflet 查看地图，支持本地缓存、GSI 在线源、智能回源。
- 3D 地图：使用 Cesium 查看 PLATEAU 建筑 3D Tiles，并可将数据集下载到本地。

## API 速览

### 区域与普通瓦片

```http
GET /api/regions
POST /api/download/start
POST /api/download/stop
GET /api/download/status
GET /api/stats
GET /map_tiles/{z}/{x}/{y}.png
GET /map_tiles_3d/{z}/{x}/{y}.png
```

`/map_tiles_3d/*` 面向 Cesium 3D 场景。本地缺少影像瓦片时会返回透明 PNG，避免 3D 场景反复等待 404。

启动普通瓦片下载示例：

```bash
curl -X POST http://localhost:5001/api/download/start \
  -H "Content-Type: application/json" \
  -d '{"region":"东京周边","zoom_min":5,"zoom_max":8}'
```

### DEM 高度图

```http
POST /api/dem/download/start
POST /api/dem/download/stop
GET /api/dem/download/status
GET /api/dem/stats
GET /gsi-dem/{z}/{x}/{y}.png
GET /gsi-dem-local/{z}/{x}/{y}.png
```

- `/gsi-dem/*` 会在本地未命中时尝试回源 GSI DEM 并写入缓存。
- `/gsi-dem-local/*` 只读本地缓存，缺失时直接返回 404，主要供 3D 场景使用。
- DEM zoom 在后端限制到最高 14。

启动 DEM 下载示例：

```bash
curl -X POST http://localhost:5001/api/dem/download/start \
  -H "Content-Type: application/json" \
  -d '{"region":"东京周边","zoom_min":5,"zoom_max":12}'
```

### PLATEAU 3D Tiles

```http
POST /api/plateau/download
GET /api/plateau/status
GET /api/plateau/local
GET /plateau_tiles/{dataset_id}/tileset.json
```

前端会通过 Vite 代理访问 PLATEAU 官方目录：

```text
/plateau-api/datacatalog/plateau-datasets?type=3DTiles&dataType=bldg
```

下载 PLATEAU 数据集示例：

```bash
curl -X POST http://localhost:5001/api/plateau/download \
  -H "Content-Type: application/json" \
  -d '{"dataset_id":"sample_dataset","url":"https://example.com/path/to/tileset.json"}'
```

实际 `url` 通常由前端从 PLATEAU 数据目录中获取。

## 数据目录与存储建议

- `map_tiles/{z}/{x}/{y}.png`：GSI 标准地图瓦片。
- `gsi_dem_cache/{z}/{x}/{y}.png`：GSI DEM PNG 高度图。
- `plateau_tiles/{dataset_id}/`：PLATEAU 3D Tiles 数据集。

存储量会随 zoom 和区域快速增长。建议先用小区域、低 zoom 验证流程，再下载大范围数据。PLATEAU 数据集体积差异较大，LOD 越高通常越占空间和显存。

## 潜在问题与排查

- 后端端口固定为 `5001`。如果手动启动时端口被占用，需要先释放端口或修改 `map.py` 与 Vite 代理配置；`start_map_all.sh` 会自动尝试释放默认端口。
- Vite 前端依赖后端代理。若页面提示接口连接失败，先确认 `python map.py` 已启动。
- GSI、PLATEAU 官方服务需要网络访问，国内网络环境下可能出现超时、TLS 握手失败或目录加载慢。
- 后端下载并发默认较高。普通瓦片默认从 API 读取 `max_concurrent`，代码默认值较大；网络不稳定或磁盘压力大时建议降低并发。
- `start_map_all.bat` 写死了 Windows Python 路径，跨机器使用前需要检查。
- `PlateauViewer.vue` 内含 Cesium Ion token。若未来接入需要 Ion 服务的资源，建议换成自己的 token 或改为环境变量。
- Python 依赖已写入 `requirements.txt`；如果后续新增第三方包，需要同步更新该文件。
- `map_use.py` 是简化服务，主应用请优先运行 `map.py`。
- 本项目偏本地工具形态，未包含鉴权、任务持久化、队列管理和生产级日志轮转。

## 常用操作

查看普通瓦片统计：

```bash
curl http://localhost:5001/api/stats
```

查看 DEM 统计：

```bash
curl http://localhost:5001/api/dem/stats
```

查看 PLATEAU 本地数据集：

```bash
curl http://localhost:5001/api/plateau/local
```

测试单个本地瓦片是否存在：

```text
http://localhost:5001/map_tiles/5/28/12.png
```
