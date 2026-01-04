import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# ============================================
# 地图配置管理类
# ============================================

class JapanMapManager:
    """管理日本地图区域及本地瓦片服务"""
    
    def __init__(self, tiles_dir: str = "./map_tiles"):
        # 获取脚本所在目录
        script_dir = Path(__file__).parent.absolute()
        self.output_dir = script_dir / tiles_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    

    def get_local_stats(self):
        """获取本地已存在的瓦片统计"""
        zoom_levels = sorted([int(d.name) for d in self.output_dir.iterdir() 
                             if d.is_dir() and d.name.isdigit()])
        
        stats = []
        for z in zoom_levels:
            z_dir = self.output_dir / str(z)
            files = list(z_dir.rglob("*.png"))
            stats.append({
                "level": z,
                "count": len(files)
            })
        return stats

# ============================================
# Flask API 服务
# ============================================

app = Flask(__name__)
CORS(app)

# 初始化管理器
map_manager = JapanMapManager(tiles_dir="map_tiles")

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取本地瓦片库的状态"""
    return jsonify({
        "local_tiles": map_manager.get_local_stats(),
        "storage_path": str(map_manager.output_dir)
    })

@app.route('/map_tiles/<int:z>/<int:x>/<path:filename>')
def serve_tiles(z, x, filename):
    """
    提供本地瓦片文件服务
    访问路径示例: /map_tiles/5/28/12.png
    """
    # 构造子目录路径
    tile_subdir = os.path.join(str(map_manager.output_dir), str(z), str(x))
    return send_from_directory(tile_subdir, filename)

if __name__ == "__main__":    
    app.run(host='0.0.0.0', port=5000, debug=True)