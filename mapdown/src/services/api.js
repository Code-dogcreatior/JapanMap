const BASE = '/api';
export const LOCAL_TILE_URL = '/map_tiles/{z}/{x}/{y}.png';
export const ONLINE_TILE_URL = 'https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png';

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

export const api = {
  getRegions: () => request('/regions'),
  getStats: () => request('/stats'),
  getDownloadStatus: () => request('/download/status'),
  startDownload: (params) => request('/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  }),

  async ping() {
    const start = Date.now();
    await request('/stats');
    return Date.now() - start;
  },
};

// 根据区域边界和缩放范围计算瓦片总数
export function estimateTileCount(bounds, zoomMin, zoomMax) {
  if (!bounds || zoomMin > zoomMax) return 0;
  const [[minLat, minLon], [maxLat, maxLon]] = bounds;

  function lngToX(lng, z) {
    return Math.floor((lng + 180) / 360 * Math.pow(2, z));
  }
  function latToY(lat, z) {
    const r = lat * Math.PI / 180;
    return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * Math.pow(2, z));
  }

  let total = 0;
  for (let z = zoomMin; z <= zoomMax; z++) {
    const xMin = lngToX(minLon, z);
    const xMax = lngToX(maxLon, z);
    const yMin = latToY(maxLat, z); // 纬度越高 y 越小
    const yMax = latToY(minLat, z);
    total += (xMax - xMin + 1) * (yMax - yMin + 1);
  }
  return total;
}
