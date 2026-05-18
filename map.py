import os
import time
import math
import json
import asyncio
import threading
import copy
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.parse import urljoin, urlsplit
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
            "stop_requested": False,
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
            if self.current_download.get("stop_requested"):
                return "cancelled", "已停止"

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
                if self.current_download.get("stop_requested"):
                    return "cancelled", f"已停止: {z}/{x}/{y}"
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
        self.current_download["stop_requested"] = False
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
            pending = {
                asyncio.create_task(self.download_single_tile_async(session, tile, semaphore, max_retries, retry_delay))
                for tile in tiles
            }
            for future in asyncio.as_completed(pending):
                result = await future
                
                # 更新状态
                status, message = result
                if status == "cancelled":
                    with self._lock:
                        self.current_download["total"] = self.current_download["current"]
                        self.current_download["progress"] = 100
                    self.add_log("⏹ 下载任务已停止", "warning")
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    break
                elif status == "skip" or status == "skip_404":
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
        
        if self.current_download.get("stop_requested"):
            self.add_log("⏹ 下载已终止，已保存文件会保留", "warning")
        else:
            self.add_log("✨ 下载完成!", "success")
            self.generate_metadata(region, zoom_min, zoom_max, total)
        self.current_download["is_downloading"] = False

    def request_stop(self):
        if self.current_download["is_downloading"]:
            self.current_download["stop_requested"] = True
            self.add_log("⏹ 已收到停止请求，正在收尾...", "warning")
            return True
        return False
    
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
# GSI DEM 下载器
# ============================================

class GsiDemDownloader:
    """日本国土地理院 DEM PNG 瓦片下载器（与 map_tiles 使用同一 XYZ 网格）"""

    def __init__(self, regions: Dict, output_dir: str = "./gsi_dem_cache"):
        self.base_url = "https://cyberjapandata.gsi.go.jp/xyz/dem_png/{z}/{x}/{y}.png"
        script_dir = Path(__file__).parent.absolute()
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.regions = regions
        self._lock = threading.Lock()
        self.current_download = {
            "is_downloading": False,
            "stop_requested": False,
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
        n = 2 ** zoom
        x = int((lng + 180) / 360 * n)
        lat_rad = math.radians(lat)
        y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
        return x, y

    def generate_tile_list(self, region: str, zoom_min: int, zoom_max: int) -> List[Dict]:
        if region not in self.regions:
            raise ValueError(f"未知区域: {region}. 可选: {list(self.regions.keys())}")

        zoom_min = max(0, min(14, int(zoom_min)))
        zoom_max = max(0, min(14, int(zoom_max)))
        if zoom_min > zoom_max:
            raise ValueError("DEM zoom_min 不能大于 zoom_max")

        bounds = self.regions[region]["bounds"]
        tiles = []
        for z in range(zoom_min, zoom_max + 1):
            x_min, y_max = self.lat_lng_to_tile(bounds[0][0], bounds[0][1], z)
            x_max, y_min = self.lat_lng_to_tile(bounds[1][0], bounds[1][1], z)
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tiles.append({"z": z, "x": x, "y": y})
        return tiles

    def add_log(self, message: str, log_type: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        with self._lock:
            self.current_download["logs"].append({
                "time": timestamp,
                "message": message,
                "type": log_type
            })

    async def download_single_tile_async(self, session, tile, semaphore, max_retries: int = 3, retry_delay: float = 1.0):
        async with semaphore:
            if self.current_download.get("stop_requested"):
                return "cancelled", "DEM 已停止"

            z, x, y = tile["z"], tile["x"], tile["y"]
            tile_path = self.output_dir / str(z) / str(x) / f"{y}.png"
            if tile_path.exists():
                return "skip", f"已存在 DEM: {z}/{x}/{y}"

            url = self.base_url.format(z=z, x=x, y=y)
            for attempt in range(max_retries + 1):
                if self.current_download.get("stop_requested"):
                    return "cancelled", f"DEM 已停止: {z}/{x}/{y}"
                try:
                    if attempt > 0:
                        await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 404:
                            return "skip_404", f"无 DEM: {z}/{x}/{y}"
                        if response.status != 200:
                            if attempt < max_retries:
                                continue
                            return "fail", f"DEM HTTP错误 {response.status}: {z}/{x}/{y}"

                        content = await response.read()
                        tile_path.parent.mkdir(parents=True, exist_ok=True)
                        tile_path.write_bytes(content)
                        return "success", f"成功 DEM: {z}/{x}/{y}"
                except (asyncio.TimeoutError, aiohttp.ClientError):
                    if attempt < max_retries:
                        continue
                    return "fail", f"DEM 下载失败: {z}/{x}/{y}"
                except Exception as e:
                    if attempt < max_retries:
                        continue
                    return "fail", f"DEM 错误: {z}/{x}/{y} - {str(e)}"

            return "fail", f"DEM 下载失败: {z}/{x}/{y}"

    async def download_tiles_async(self, region: str, zoom_min: int = 5, zoom_max: int = 12,
                                   max_concurrent: int = 120, max_retries: int = 3, retry_delay: float = 1.0):
        self.current_download["is_downloading"] = True
        self.current_download["stop_requested"] = False
        self.current_download["region"] = region
        self.current_download["logs"] = []

        self.add_log(f"⛰ 开始下载 {region} 的 GSI DEM", "info")
        self.add_log(f"📍 DEM 缩放级别: {zoom_min} - {zoom_max}（最高 14）", "info")

        try:
            tiles = self.generate_tile_list(region, zoom_min, zoom_max)
            total = len(tiles)
            self.current_download.update({
                "total": total,
                "current": 0,
                "success": 0,
                "skip": 0,
                "fail": 0,
                "progress": 0,
            })
            self.add_log(f"📊 共需下载 {total} 个 DEM 瓦片", "info")
            self.add_log(f"💾 保存路径: {self.output_dir.absolute()}", "info")

            connector = aiohttp.TCPConnector(limit=0)
            timeout = aiohttp.ClientTimeout(total=30)
            semaphore = asyncio.Semaphore(max_concurrent)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (GSI-DEM-downloader)'}
            ) as session:
                pending = {
                    asyncio.create_task(self.download_single_tile_async(session, tile, semaphore, max_retries, retry_delay))
                    for tile in tiles
                }
                for future in asyncio.as_completed(pending):
                    status, message = await future
                    if status == "cancelled":
                        with self._lock:
                            self.current_download["total"] = self.current_download["current"]
                            self.current_download["progress"] = 100
                        self.add_log("⏹ DEM 下载任务已停止", "warning")
                        for task in pending:
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        break
                    elif status in ("skip", "skip_404"):
                        self.current_download["skip"] += 1
                    elif status == "success":
                        self.current_download["success"] += 1
                    else:
                        self.current_download["fail"] += 1
                        self.add_log(message, "error")

                    with self._lock:
                        self.current_download["current"] += 1
                        self.current_download["progress"] = int((self.current_download["current"] / total) * 100) if total else 100

                    if self.current_download["current"] % 50 == 0 or self.current_download["current"] == total:
                        self.add_log(
                            f"⏳ DEM 进度: {self.current_download['current']}/{total} ({self.current_download['progress']}%) | "
                            f"✅ {self.current_download['success']} | "
                            f"⏭️ {self.current_download['skip']} | "
                            f"❌ {self.current_download['fail']}",
                            "info"
                        )

            if self.current_download.get("stop_requested"):
                self.add_log("⏹ DEM 下载已终止，已保存文件会保留", "warning")
            else:
                self.generate_metadata(region, zoom_min, zoom_max, total)
                self.add_log("✨ DEM 下载完成!", "success")
        except Exception as e:
            self.add_log(f"DEM 下载任务失败: {str(e)}", "error")
        finally:
            self.current_download["is_downloading"] = False

    def request_stop(self):
        if self.current_download["is_downloading"]:
            self.current_download["stop_requested"] = True
            self.add_log("⏹ 已收到 DEM 停止请求，正在收尾...", "warning")
            return True
        return False

    def download_tiles_api(self, region: str, zoom_min: int = 5, zoom_max: int = 12,
                           max_workers: int = 120, max_retries: int = 3, retry_delay: float = 1.0):
        asyncio.run(self.download_tiles_async(region, zoom_min, zoom_max, max_workers, max_retries, retry_delay))

    def generate_metadata(self, region: str, zoom_min: int, zoom_max: int, total_tiles: int):
        metadata = {
            "region": region,
            "zoom_levels": {"min": zoom_min, "max": zoom_max},
            "total_tiles": total_tiles,
            "download_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tile_source": "日本国土地理院 (GSI Japan) DEM PNG",
            "base_url": self.base_url,
            "directory_structure": "gsi_dem_cache/{z}/{x}/{y}.png"
        }
        metadata_path = self.output_dir / f"metadata_{region}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        self.add_log(f"📄 DEM 元数据已保存: metadata_{region}.json", "success")

    def get_stats(self):
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
# PLATEAU 3D Tiles 下载器
# ============================================

class PlateauDownloader:
    """递归下载 PLATEAU 3D Tiles 数据集（tileset.json + 子tileset + b3dm/glb）"""

    def __init__(self, output_dir: str = "./plateau_tiles"):
        script_dir = Path(__file__).parent.absolute()
        self.output_dir = script_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # dataset_id -> {status, files, bytes, errors, ...}
        self.downloads: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _sanitize_id(dataset_id: str) -> str:
        """防止路径遍历，只保留字母数字和 _ - ."""
        return "".join(c for c in dataset_id if c.isalnum() or c in "_-.")

    def dataset_dir(self, dataset_id: str) -> Path:
        return self.output_dir / self._sanitize_id(dataset_id)

    def is_local(self, dataset_id: str) -> bool:
        d = self.dataset_dir(dataset_id)
        return (d / "tileset.json").exists() and (d / ".complete").exists()

    def list_local(self) -> List[Dict]:
        """列出本地已下载的数据集（含大小）"""
        results = []
        if not self.output_dir.exists():
            return results
        for d in self.output_dir.iterdir():
            if not d.is_dir():
                continue
            root = d / "tileset.json"
            complete_marker = d / ".complete"
            if not root.exists() or not complete_marker.exists():
                continue
            try:
                size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                count = sum(1 for _ in d.rglob("*") if _.is_file())
                content_count = sum(
                    1 for f in d.rglob("*")
                    if f.is_file() and f.suffix.lower() in {".b3dm", ".glb"}
                )
            except Exception:
                size, count, content_count = 0, 0, 0
            if content_count == 0:
                continue
            results.append({
                "dataset_id": d.name,
                "size_mb": round(size / 1024 / 1024, 2),
                "files": count,
                "content_files": content_count,
            })
        return results

    def get_status_snapshot(self) -> Dict:
        with self._lock:
            return copy.deepcopy(self.downloads)

    def _collect_uris(self, node: Dict, parent_url: str, out: List[str]):
        """递归从 tile node 收集所有 content URI（解析为绝对 URL）"""
        if "content" in node and isinstance(node["content"], dict):
            uri = node["content"].get("uri") or node["content"].get("url")
            if uri and not uri.startswith("data:"):
                out.append(urljoin(parent_url, uri))
        for child in node.get("children") or []:
            self._collect_uris(child, parent_url, out)

    @staticmethod
    def _url_to_relpath(url: str, base_url: str) -> str:
        """把 URL 转成相对 base 的本地路径"""
        if url.startswith(base_url):
            rel = url[len(base_url):]
            return rel.split("?")[0]
        return urlsplit(url).path.lstrip("/").split("?")[0]

    async def _fetch_one(
        self,
        session: aiohttp.ClientSession,
        url: str,
        base_url: str,
        dataset_dir: Path,
        sem: asyncio.Semaphore,
        sub_uri_lists: List[List[str]],
        dataset_id: str,
        max_retries: int = 3,
    ):
        async with sem:
            rel = self._url_to_relpath(url, base_url)
            if not rel:
                return
            out_path = dataset_dir / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # 已下载：如果是 json 还要解析子节点
            if out_path.exists():
                if url.endswith(".json"):
                    try:
                        ts = json.loads(out_path.read_bytes())
                        uris: List[str] = []
                        if "root" in ts:
                            self._collect_uris(ts["root"], url, uris)
                        sub_uri_lists.append(uris)
                    except Exception:
                        pass
                return

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        await asyncio.sleep(1.0 * (2 ** (attempt - 1)))
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            out_path.write_bytes(data)
                            with self._lock:
                                st = self.downloads.get(dataset_id)
                                if st is not None:
                                    st["files"] += 1
                                    st["bytes"] += len(data)
                            if url.endswith(".json"):
                                try:
                                    ts = json.loads(data)
                                    uris = []
                                    if "root" in ts:
                                        self._collect_uris(ts["root"], url, uris)
                                    sub_uri_lists.append(uris)
                                except Exception:
                                    pass
                            return
                        elif resp.status == 404:
                            break
                except (asyncio.TimeoutError, aiohttp.ClientError):
                    continue
                except Exception:
                    continue

            with self._lock:
                st = self.downloads.get(dataset_id)
                if st is not None:
                    st["errors"] += 1

    async def download_async(
        self,
        dataset_id: str,
        root_url: str,
        max_concurrent: int = 60,
    ):
        dataset_dir = self.dataset_dir(dataset_id)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        base_url = root_url.rsplit("/", 1)[0] + "/"

        with self._lock:
            self.downloads[dataset_id] = {
                "status": "downloading",
                "files": 0,
                "bytes": 0,
                "errors": 0,
                "depth": 0,
                "queue_size": 0,
                "started_at": time.time(),
                "completed_at": None,
                "url": root_url,
                "error_msg": None,
            }

        sem = asyncio.Semaphore(max_concurrent)
        timeout = aiohttp.ClientTimeout(total=120)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(root_url) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"根 tileset.json 拉取失败: HTTP {resp.status}")
                    root_data = await resp.read()

                root_path = dataset_dir / "tileset.json"
                root_path.write_bytes(root_data)
                with self._lock:
                    self.downloads[dataset_id]["files"] = 1
                    self.downloads[dataset_id]["bytes"] = len(root_data)

                root_ts = json.loads(root_data)
                queue: List[str] = []
                if "root" in root_ts:
                    self._collect_uris(root_ts["root"], root_url, queue)

                downloaded = {root_url}
                depth = 0

                while queue:
                    depth += 1
                    with self._lock:
                        self.downloads[dataset_id]["depth"] = depth
                        self.downloads[dataset_id]["queue_size"] = len(queue)

                    sub_uri_lists: List[List[str]] = []
                    tasks = []
                    for u in queue:
                        if u in downloaded:
                            continue
                        downloaded.add(u)
                        tasks.append(self._fetch_one(
                            session, u, base_url, dataset_dir, sem,
                            sub_uri_lists, dataset_id
                        ))
                    if not tasks:
                        break
                    await asyncio.gather(*tasks)

                    new_queue: List[str] = []
                    for uris in sub_uri_lists:
                        for u in uris:
                            if u not in downloaded:
                                new_queue.append(u)
                    queue = new_queue

            with self._lock:
                errors = self.downloads.get(dataset_id, {}).get("errors", 0)
                self.downloads[dataset_id]["status"] = "done" if errors == 0 else "failed"
                self.downloads[dataset_id]["completed_at"] = time.time()
                snapshot = copy.deepcopy(self.downloads[dataset_id])

            complete_marker = dataset_dir / ".complete"
            if errors == 0:
                complete_marker.write_text(
                    json.dumps({
                        "dataset_id": dataset_id,
                        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "files": snapshot.get("files", 0),
                        "bytes": snapshot.get("bytes", 0),
                        "errors": errors,
                    }, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            elif complete_marker.exists():
                complete_marker.unlink()
        except Exception as e:
            complete_marker = dataset_dir / ".complete"
            if complete_marker.exists():
                complete_marker.unlink()
            with self._lock:
                self.downloads[dataset_id]["status"] = "failed"
                self.downloads[dataset_id]["error_msg"] = str(e)
                self.downloads[dataset_id]["completed_at"] = time.time()

    def start_download(self, dataset_id: str, url: str, max_concurrent: int = 60):
        from threading import Thread
        def run():
            asyncio.run(self.download_async(dataset_id, url, max_concurrent))
        Thread(target=run, daemon=True).start()


# ============================================
# Flask API 服务
# ============================================

app = Flask(__name__)
CORS(app)  # 允许跨域

# 初始化下载器
downloader = JapanMapTileDownloader(output_dir="map_tiles")
dem_downloader = GsiDemDownloader(regions=downloader.regions, output_dir="gsi_dem_cache")
plateau_downloader = PlateauDownloader(output_dir="plateau_tiles")

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

@app.route('/api/download/stop', methods=['POST'])
def stop_download():
    """请求停止当前普通瓦片下载任务"""
    if downloader.request_stop():
        return jsonify({"message": "停止请求已发送"})
    return jsonify({"message": "当前没有进行中的下载任务", "not_running": True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取下载统计"""
    try:
        return jsonify(downloader.get_stats())
    except Exception:
        return jsonify({"stats": [], "total_files": 0, "total_size_mb": 0.0})

@app.route('/api/dem/download/start', methods=['POST'])
def start_dem_download():
    """开始批量下载 GSI DEM"""
    data = request.json or {}
    region = data.get('region', '东京周边')
    zoom_min = data.get('zoom_min', 5)
    zoom_max = data.get('zoom_max', 12)
    max_concurrent = data.get('max_concurrent', 120)
    max_retries = data.get('max_retries', 3)
    retry_delay = data.get('retry_delay', 1.0)

    if dem_downloader.current_download["is_downloading"]:
        return jsonify({"error": "已有 DEM 下载任务在进行中"}), 400

    from threading import Thread
    thread = Thread(
        target=dem_downloader.download_tiles_api,
        args=(region, zoom_min, zoom_max, max_concurrent, max_retries, retry_delay)
    )
    thread.start()

    return jsonify({
        "message": "DEM 下载已开始",
        "region": region,
        "max_concurrent": max_concurrent,
        "max_retries": max_retries,
        "retry_delay": retry_delay
    })

@app.route('/api/dem/download/status', methods=['GET'])
def get_dem_status():
    """获取 DEM 下载状态"""
    return jsonify(dem_downloader.current_download)

@app.route('/api/dem/download/stop', methods=['POST'])
def stop_dem_download():
    """请求停止当前 DEM 下载任务"""
    if dem_downloader.request_stop():
        return jsonify({"message": "DEM 停止请求已发送"})
    return jsonify({"message": "当前没有进行中的 DEM 下载任务", "not_running": True})

@app.route('/api/dem/stats', methods=['GET'])
def get_dem_stats():
    """获取 DEM 缓存统计"""
    try:
        return jsonify(dem_downloader.get_stats())
    except Exception:
        return jsonify({"stats": [], "total_files": 0, "total_size_mb": 0.0})

@app.route('/map_tiles/<path:filename>')
def serve_tiles(filename):
    """提供瓦片文件服务"""
    return send_from_directory(downloader.output_dir, filename)


# -------- PLATEAU 3D Tiles 路由 --------

@app.route('/api/plateau/download', methods=['POST'])
def plateau_download_start():
    """启动一个 PLATEAU 数据集的递归下载"""
    data = request.json or {}
    dataset_id = data.get('dataset_id')
    url = data.get('url')
    if not dataset_id or not url:
        return jsonify({"error": "dataset_id 和 url 必填"}), 400

    existing = plateau_downloader.downloads.get(dataset_id)
    if existing and existing.get("status") == "downloading":
        return jsonify({
            "status": "already_running",
            "dataset_id": dataset_id,
            "progress": existing,
        })

    plateau_downloader.start_download(dataset_id, url)
    return jsonify({"status": "started", "dataset_id": dataset_id})


@app.route('/api/plateau/status', methods=['GET'])
def plateau_status():
    """所有 PLATEAU 下载任务的实时状态"""
    return jsonify({"downloads": plateau_downloader.get_status_snapshot()})


@app.route('/api/plateau/local', methods=['GET'])
def plateau_local():
    """本地已下载的 PLATEAU 数据集列表"""
    try:
        return jsonify({"datasets": plateau_downloader.list_local()})
    except Exception:
        return jsonify({"datasets": []})


@app.route('/plateau_tiles/<path:filename>')
def serve_plateau(filename):
    """本地 PLATEAU 3D Tiles 静态服务（供 Cesium 加载）"""
    return send_from_directory(plateau_downloader.output_dir, filename)


# -------- GSI DEM 缓存代理 --------
# 国土地理院 DEM 服务在中国不稳定（TLS 握手频繁失败），
# 走 Flask 后端：本地有就直接返，没有就重试拉取并落盘。
import struct
import urllib.request
import urllib.error
import zlib
from flask import Response

GSI_DEM_CACHE = dem_downloader.output_dir
_dem_inflight = {}  # tile key -> threading.Event（避免同一瓦片并发重复拉取）
_dem_inflight_lock = threading.Lock()


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _solid_png(width: int, height: int, channels: int, color: bytes) -> bytes:
    """生成标准 8-bit PNG，用 256x256 占位图规避 Safari/WebGL 对 1x1/灰度 PNG 的兼容问题。"""
    color_type = 6 if channels == 4 else 2
    row = b"\x00" + color * width
    raw = row * height
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0),
    )
    png += _png_chunk(b"IDAT", zlib.compress(raw, level=9))
    png += _png_chunk(b"IEND", b"")
    return png


_TRANSPARENT_RGBA_PNG = _solid_png(256, 256, 4, b"\x00\x00\x00\x00")
_GSI_DEM_NODATA_PNG = _solid_png(256, 256, 3, b"\x80\x00\x00")


def _png_response(data: bytes, *, cache_seconds: int = 3600) -> Response:
    resp = Response(data, mimetype='image/png')
    resp.headers['Cache-Control'] = f'public, max-age={cache_seconds}'
    return resp


@app.route('/map_tiles_3d/<int:z>/<int:x>/<int:y>.png')
def serve_tiles_3d(z, x, y):
    """3D 场景专用本地影像瓦片：缺瓦片时返回透明图，避免 Cesium 反复等待 404。"""
    tile_path = downloader.output_dir / str(z) / str(x) / f"{y}.png"
    if tile_path.exists():
        return send_from_directory(downloader.output_dir, f"{z}/{x}/{y}.png")
    return _png_response(_TRANSPARENT_RGBA_PNG)


def _fetch_dem_tile(z, x, y, max_retries=3):
    """同步拉取一个 DEM 瓦片，带重试，写入缓存目录。返回 cache_path 或 None。"""
    cache_path = GSI_DEM_CACHE / str(z) / str(x) / f"{y}.png"
    if cache_path.exists():
        return cache_path

    key = f"{z}/{x}/{y}"
    # 同瓦片并发去重：第二个请求等待第一个完成
    with _dem_inflight_lock:
        ev = _dem_inflight.get(key)
        if ev is not None:
            wait_ev = ev
        else:
            wait_ev = None
            _dem_inflight[key] = threading.Event()

    if wait_ev is not None:
        wait_ev.wait(timeout=30)
        return cache_path if cache_path.exists() else None

    try:
        url = f"https://cyberjapandata.gsi.go.jp/xyz/dem_png/{z}/{x}/{y}.png"
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    time.sleep(0.6 * (2 ** (attempt - 1)))
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Cesium-GSI-DEM-cache)'},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        body = resp.read()
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_bytes(body)
                        return cache_path
            except urllib.error.HTTPError as he:
                if he.code == 404:
                    return None  # 海上/无数据，直接返 None，前端解释成 404
                continue
            except Exception:
                continue
        return None
    finally:
        with _dem_inflight_lock:
            ev = _dem_inflight.pop(key, None)
            if ev is not None:
                ev.set()


@app.route('/gsi-dem/<int:z>/<int:x>/<int:y>.png')
def serve_gsi_dem(z, x, y):
    """GSI DEM 瓦片：本地缓存命中即返；否则重试拉取并缓存，失败时返回 no-data PNG。"""
    if z > 14 or z < 0:
        return _png_response(_GSI_DEM_NODATA_PNG)
    p = _fetch_dem_tile(z, x, y)
    if p is None or not p.exists():
        return _png_response(_GSI_DEM_NODATA_PNG)
    return send_from_directory(GSI_DEM_CACHE, f"{z}/{x}/{y}.png")


@app.route('/gsi-dem-local/<int:z>/<int:x>/<int:y>.png')
def serve_gsi_dem_local(z, x, y):
    """3D 场景专用 DEM：只读本地缓存，缺失时返回 GSI no-data PNG，避免 404 与 Safari 纹理异常。"""
    if z > 14 or z < 0:
        return _png_response(_GSI_DEM_NODATA_PNG)
    p = GSI_DEM_CACHE / str(z) / str(x) / f"{y}.png"
    if not p.exists():
        return _png_response(_GSI_DEM_NODATA_PNG)
    return send_from_directory(GSI_DEM_CACHE, f"{z}/{x}/{y}.png")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
