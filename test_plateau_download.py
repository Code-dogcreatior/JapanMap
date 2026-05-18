"""测试单个 PLATEAU dataset 的完整下载时间和大小

递归遍历 tileset.json，解析所有子 tileset.json 和 .b3dm 引用，并发下载。
"""
import asyncio
import aiohttp
import json
import time
from pathlib import Path
from urllib.parse import urljoin

# 测试目标：东京千代田区 LOD1（PLATEAU 2023 数据）
TILESET_URL = (
    "https://assets.cms.plateau.reearth.io/assets/0e/e5948a-e95c-4e31-be85-1f8c066ed996/"
    "13101_chiyoda-ku_pref_2023_citygml_1_op_bldg_3dtiles_13101_chiyoda-ku_lod1/tileset.json"
)
OUTPUT_DIR = Path(__file__).parent / "plateau_test" / "13101_chiyoda-ku_lod1"
CONCURRENT = 120

ROOT_BASE = TILESET_URL.rsplit("/", 1)[0] + "/"

stats = {"files": 0, "bytes": 0, "errors": 0, "json_count": 0, "b3dm_count": 0}


def url_to_relpath(url):
    if url.startswith(ROOT_BASE):
        return url[len(ROOT_BASE):]
    return None


def collect_uris(node, parent_url, out):
    """BFS 收集 tile 节点中所有 content URI（解析为绝对 URL）"""
    if "content" in node and "uri" in node["content"]:
        uri = node["content"]["uri"]
        if not uri.startswith("data:"):
            out.append(urljoin(parent_url, uri))
    for child in node.get("children", []):
        collect_uris(child, parent_url, out)


async def fetch_and_save(session, url, sem, sub_uri_lists):
    async with sem:
        rel = url_to_relpath(url)
        if rel is None:
            return
        out_path = OUTPUT_DIR / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists():
            return

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    stats["errors"] += 1
                    return
                data = await resp.read()
                out_path.write_bytes(data)
                stats["files"] += 1
                stats["bytes"] += len(data)

                if url.endswith(".json"):
                    stats["json_count"] += 1
                    try:
                        ts = json.loads(data)
                        uris = []
                        if "root" in ts:
                            collect_uris(ts["root"], url, uris)
                        sub_uri_lists.append(uris)
                    except Exception:
                        pass
                elif url.endswith(".b3dm") or url.endswith(".glb"):
                    stats["b3dm_count"] += 1
        except Exception:
            stats["errors"] += 1


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()
    sem = asyncio.Semaphore(CONCURRENT)
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1) 拉取根 tileset.json
        async with session.get(TILESET_URL) as resp:
            root_data = await resp.read()
        rel = url_to_relpath(TILESET_URL)
        (OUTPUT_DIR / rel).write_bytes(root_data)
        stats["files"] += 1
        stats["bytes"] += len(root_data)
        stats["json_count"] += 1

        root_ts = json.loads(root_data)
        queue = []
        if "root" in root_ts:
            collect_uris(root_ts["root"], TILESET_URL, queue)

        downloaded = {TILESET_URL}
        depth = 0
        while queue:
            depth += 1
            sub_uri_lists = []
            tasks = []
            for url in queue:
                if url in downloaded:
                    continue
                downloaded.add(url)
                tasks.append(fetch_and_save(session, url, sem, sub_uri_lists))

            if not tasks:
                break

            print(f"[Depth {depth}] 并发下载 {len(tasks):>4} 个文件 ... 累计 {stats['bytes']/1024/1024:>7.2f} MB")
            await asyncio.gather(*tasks)

            new_queue = []
            for uris in sub_uri_lists:
                for u in uris:
                    if u not in downloaded:
                        new_queue.append(u)
            queue = new_queue

    elapsed = time.time() - start
    mb = stats["bytes"] / 1024 / 1024
    print(f"\n=========== 测试结果 ===========")
    print(f"目标:           Tokyo 千代田区 LOD1")
    print(f"总文件数:       {stats['files']}")
    print(f"  - tileset.json: {stats['json_count']}")
    print(f"  - b3dm/glb:     {stats['b3dm_count']}")
    print(f"  - 其他:         {stats['files'] - stats['json_count'] - stats['b3dm_count']}")
    print(f"总大小:         {mb:.2f} MB ({stats['bytes']:,} bytes)")
    print(f"总耗时:         {elapsed:.1f} 秒")
    print(f"平均速度:       {mb/elapsed:.2f} MB/s")
    print(f"并发数:         {CONCURRENT}")
    print(f"BFS 深度:       {depth}")
    print(f"错误数:         {stats['errors']}")
    print(f"输出目录:       {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
