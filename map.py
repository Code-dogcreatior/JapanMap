import os
import time
import math
import json
import asyncio
import threading
from pathlib import Path
from typing import List, Dict, Tuple
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import aiohttp

# ============================================
# 地图瓦片下载器核心类
# ============================================

class JapanMapTileDownloader:
    """日本地图瓦片下载器"""
    
    def __init__(self, output_dir: str = "./map_tiles"):
        self.base_url = "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png"
        # 获取脚本所在目录
        script_dir = Path(__file__).parent.absolute()
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义区域边界 [南纬, 西经], [北纬, 东经]
        self.regions = {
            # 日本区域
"全日本": {"bounds": [[24, 122], [46, 149]]},

    # 修正：北纬扩展至37.2以包含栃木/群马北部（日光、那须等）
    "关东": {"bounds": [[34.8, 138.3], [37.2, 141.0]]},

    # 修正：西经扩至134.0（兵库西部），北纬扩至36.0（京都北部/福井边缘）
    "关西": {"bounds": [[33.3, 134.0], [36.0, 137.0]]},

    # 北海道保持原样即可，范围涵盖主岛
    "北海道": {"bounds": [[41.0, 139.0], [46.0, 146.5]]}, # 稍微修正东经以匹配您之前的查询

    # 九州范围合理
    "九州": {"bounds": [[30.9, 129.5], [34.0, 132.1]]},

    # 东京周边（首都圈核心）
    "东京周边": {"bounds": [[35.4, 139.2], [36.0, 140.0]]},

    # 城市级别（微调以确保不切断边缘）
    "大阪": {"bounds": [[34.4, 135.3], [34.9, 135.7]]},
    "名古屋": {"bounds": [[35.0, 136.7], [35.3, 137.1]]},
    "京都": {"bounds": [[34.9, 135.6], [35.15, 135.9]]},
    
    # 原“神奈川”实际只是横滨的范围
    "横滨": {"bounds": [[35.3, 139.5], [35.6, 139.7]]}, 
    
    "福冈": {"bounds": [[33.4, 130.2], [33.8, 130.6]]},
    "札幌": {"bounds": [[42.8, 141.1], [43.2, 141.6]]},
            
            # 全球区域
            "全球": {"bounds": [[-85, -180], [85, 180]]},
            # "亚洲": {"bounds": [[-10, 25], [80, 140]]},
           #  "欧洲": {"bounds": [[35, -10], [70, 40]]},
           #  "北美洲": {"bounds": [[7, -170], [80, -50]]},
            # "南美洲": {"bounds": [[12, -80], [-55, -30]]},
          #   "非洲": {"bounds": [[37, -18], [4, 51]]},
            # "大洋洲": {"bounds": [[-47, 110], [30, -120]]},
        }
        
        self.session = None
        self._lock = threading.Lock()

        # 下载状态追踪
        self.current_download = {
            "is_downloading": False,
            "progress": 0,
            "total": 0,
            "current": 0,
            "success": 0,
            "skip": 0,
            "fail": 0,
            "region": "",
            "logs": []
        }
    
    def lat_lng_to_tile(self, lat: float, lng: float, zoom: int) -> Tuple[int, int]:
        """经纬度转瓦片坐标"""
        n = 2 ** zoom
        x = int((lng + 180) / 360 * n)
        lat_rad = math.radians(lat)
        y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
        return x, y
    
    def generate_tile_list(self, region: str, zoom_min: int, zoom_max: int) -> List[Dict]:
        """生成需要下载的瓦片列表"""
        if region not in self.regions:
            raise ValueError(f"未知区域: {region}. 可选: {list(self.regions.keys())}")
        
        bounds = self.regions[region]["bounds"]
        tiles = []
        
        for z in range(zoom_min, zoom_max + 1):
            x_min, y_max = self.lat_lng_to_tile(bounds[0][0], bounds[0][1], z)
            x_max, y_min = self.lat_lng_to_tile(bounds[1][0], bounds[1][1], z)
            
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tiles.append({"z": z, "x": x, "y": y})
        
        return tiles
    
    async def download_single_tile_async(self, session, tile, semaphore, max_retries: int = 3, retry_delay: float = 1.0):
        """异步下载单个瓦片，带超时重试机制"""
        async with semaphore:  # 信号量控制并发数
            z, x, y = tile["z"], tile["x"], tile["y"]
            url = self.base_url.format(z=z, x=x, y=y)
            
            tile_path = self.output_dir / str(z) / str(x) / f"{y}.png"
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件已存在，跳过
            if tile_path.exists():
                return "skip", f"已存在: {z}/{x}/{y}"
            
            # 重试循环
            last_error = None
            for attempt in range(max_retries + 1):  # 总共尝试 max_retries + 1 次
                try:
                    # 使用指数退避策略，每次重试前等待时间递增
                    if attempt > 0:
                        wait_time = retry_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s...
                        await asyncio.sleep(wait_time)
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 404:
                            return "skip_404", f"跳过: {z}/{x}/{y}"
                        elif response.status != 200:
                            # HTTP错误也进行重试（除了404）
                            if attempt < max_retries:
                                last_error = f"HTTP错误 {response.status}"
                                continue
                            return "fail", f"HTTP错误 {response.status}: {z}/{x}/{y}"
                        
                        content = await response.read()
                        with open(tile_path, 'wb') as f:
                            f.write(content)
                        
                        # 如果之前有重试，记录重试信息
                        if attempt > 0:
                            return "success", f"成功(重试{attempt}次): {z}/{x}/{y}"
                        return "success", f"成功: {z}/{x}/{y}"
                        
                except asyncio.TimeoutError:
                    last_error = "超时"
                    if attempt < max_retries:
                        continue
                    return "fail", f"超时(重试{max_retries}次后失败): {z}/{x}/{y}"
                except aiohttp.ClientError as e:
                    last_error = f"连接错误: {str(e)}"
                    if attempt < max_retries:
                        continue
                    return "fail", f"连接错误(重试{max_retries}次后失败): {z}/{x}/{y} - {str(e)}"
                except Exception as e:
                    last_error = f"未知错误: {str(e)}"
                    if attempt < max_retries:
                        continue
                    return "fail", f"错误(重试{max_retries}次后失败): {z}/{x}/{y} - {str(e)}"
            
            # 所有重试都失败
            return "fail", f"失败(重试{max_retries}次): {z}/{x}/{y} - {last_error}"
    
    def add_log(self, message: str, log_type: str = "info"):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        with self._lock:
            self.current_download["logs"].append({
                "time": timestamp,
                "message": message,
                "type": log_type
            })
    
    async def download_tiles_async(self, region: str, zoom_min: int = 5, zoom_max: int = 8, 
                                 max_concurrent: int = 400, max_retries: int = 3, retry_delay: float = 1.0):
        """异步下载方法，带状态追踪和超时重试机制"""
        self.current_download["is_downloading"] = True
        self.current_download["region"] = region
        self.current_download["logs"] = []
        
        self.add_log(f"🗾 开始下载 {region} 的地图瓦片", "info")
        self.add_log(f"📍 缩放级别: {zoom_min} - {zoom_max}", "info")
        self.add_log(f"🔄 重试配置: 最大重试 {max_retries} 次，重试延迟 {retry_delay}s", "info")
        
        tiles = self.generate_tile_list(region, zoom_min, zoom_max)
        total = len(tiles)
        
        self.current_download["total"] = total
        self.current_download["current"] = 0
        self.current_download["success"] = 0
        self.current_download["skip"] = 0
        self.current_download["fail"] = 0
        
        self.add_log(f"📊 共需下载 {total} 个瓦片", "info")
        self.add_log(f"💾 保存路径: {self.output_dir.absolute()}", "info")
        
        # 创建连接器和信号量
        connector = aiohttp.TCPConnector(limit=0)  # 不限制连接数
        timeout = aiohttp.ClientTimeout(total=30)
        semaphore = asyncio.Semaphore(max_concurrent)
         
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            # 创建任务
            tasks = []
            for tile in tiles:
                task = self.download_single_tile_async(session, tile, semaphore, max_retries, retry_delay)
                tasks.append(task)
            
            # 并发执行并收集结果
            results = []
            for future in asyncio.as_completed(tasks):
                result = await future
                results.append(result)
                
                # 更新状态
                status, message = result
                if status == "skip" or status == "skip_404":
                    self.current_download["skip"] += 1
                elif status == "success":
                    self.current_download["success"] += 1
                elif status == "fail":
                    self.current_download["fail"] += 1
                    self.add_log(message, "error")
                
                with self._lock:
                    self.current_download["current"] += 1
                    self.current_download["progress"] = int((self.current_download["current"] / total) * 100)
                
                # 实时更新日志
                if self.current_download["current"] % 50 == 0 or self.current_download["current"] == total:
                    self.add_log(
                        f"⏳ 进度: {self.current_download['current']}/{total} ({self.current_download['progress']}%) | "
                        f"✅ {self.current_download['success']} | "
                        f"⏭️ {self.current_download['skip']} | "
                        f"❌ {self.current_download['fail']}",
                        "info"
                    )
        
        self.add_log("✨ 下载完成!", "success")
        self.generate_metadata(region, zoom_min, zoom_max, total)
        self.current_download["is_downloading"] = False
    
    def download_tiles_api(self, region: str, zoom_min: int = 5, zoom_max: int = 8, 
                          max_workers: int = 100, max_retries: int = 3, retry_delay: float = 1.0):
        """API版本的下载方法，带状态追踪和超时重试机制（同步包装器）"""
        # 使用 asyncio.run 启动异步下载
        asyncio.run(self.download_tiles_async(region, zoom_min, zoom_max, 
                                             max_concurrent=max_workers, 
                                             max_retries=max_retries, 
                                             retry_delay=retry_delay))
    
    def generate_metadata(self, region: str, zoom_min: int, zoom_max: int, total_tiles: int):
        """生成元数据文件"""
        metadata = {
            "region": region,
            "zoom_levels": {"min": zoom_min, "max": zoom_max},
            "total_tiles": total_tiles,
            "download_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tile_source": "日本国土地理院 (GSI Japan)",
            "base_url": self.base_url,
            "directory_structure": "map_tiles/{z}/{x}/{y}.png"
        }
        
        metadata_path = self.output_dir / f"metadata_{region}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self.add_log(f"📄 元数据已保存: metadata_{region}.json", "success")
    
    def get_stats(self):
        """获取已下载瓦片统计"""
        zoom_levels = sorted([int(d.name) for d in self.output_dir.iterdir() 
                             if d.is_dir() and d.name.isdigit()])
        
        total_files = 0
        total_size = 0
        stats = []
        
        for z in zoom_levels:
            z_dir = self.output_dir / str(z)
            files = list(z_dir.rglob("*.png"))
            size = sum(f.stat().st_size for f in files)
            total_files += len(files)
            total_size += size
            stats.append({
                "level": z,
                "count": len(files),
                "size_mb": round(size / 1024 / 1024, 2)
            })
        
        return {
            "stats": stats,
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }


# ============================================
# Flask API 服务
# ============================================

app = Flask(__name__)
CORS(app)  # 允许跨域

# 初始化下载器
downloader = JapanMapTileDownloader(output_dir="map_tiles")

@app.route('/api/regions', methods=['GET'])
def get_regions():
    """获取可用区域列表（含边界坐标，用于前端估算瓦片数）"""
    return jsonify({
        "regions": [
            {"name": name, "bounds": data["bounds"]}
            for name, data in downloader.regions.items()
        ]
    })

@app.route('/api/download/start', methods=['POST'])
def start_download():
    """开始下载"""
    data = request.json
    region = data.get('region', '东京周边')
    zoom_min = data.get('zoom_min', 5)
    zoom_max = data.get('zoom_max', 8)
    max_concurrent = data.get('max_concurrent', 200)  # 默认200并发
    max_retries = data.get('max_retries', 3)  # 默认重试3次
    retry_delay = data.get('retry_delay', 1.0)  # 默认重试延迟1秒
    
    if downloader.current_download["is_downloading"]:
        return jsonify({"error": "已有下载任务在进行中"}), 400
    
    # 在后台线程中执行下载
    from threading import Thread
    thread = Thread(target=downloader.download_tiles_api, 
                   args=(region, zoom_min, zoom_max, max_concurrent, max_retries, retry_delay))
    thread.start()
    
    return jsonify({
        "message": "下载已开始", 
        "region": region, 
        "max_concurrent": max_concurrent,
        "max_retries": max_retries,
        "retry_delay": retry_delay
    })

@app.route('/api/download/status', methods=['GET'])
def get_status():
    """获取下载状态"""
    return jsonify(downloader.current_download)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取下载统计"""
    return jsonify(downloader.get_stats())

@app.route('/map_tiles/<path:filename>')
def serve_tiles(filename):
    """提供瓦片文件服务"""
    return send_from_directory(downloader.output_dir, filename)

if __name__ == "__main__":    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
