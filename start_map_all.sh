#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="5001"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
CONDA_ENV="${CONDA_ENV:-base}"

BACKEND_PID=""
FRONTEND_PID=""

free_port() {
  local port="$1"
  local name="$2"
  local pids

  pids="$(lsof -ti tcp:"${port}" || true)"
  if [ -z "${pids}" ]; then
    echo "[OK] ${name} port ${port} is free."
    return
  fi

  echo "[WARN] ${name} port ${port} is occupied by PID(s): ${pids}"
  echo "[INFO] Stopping process(es) on port ${port}..."
  kill ${pids} 2>/dev/null || true
  sleep 1

  pids="$(lsof -ti tcp:"${port}" || true)"
  if [ -n "${pids}" ]; then
    echo "[WARN] Force stopping PID(s): ${pids}"
    kill -9 ${pids} 2>/dev/null || true
    sleep 1
  fi

  pids="$(lsof -ti tcp:"${port}" || true)"
  if [ -n "${pids}" ]; then
    echo "[ERROR] Could not free ${name} port ${port}. Remaining PID(s): ${pids}"
    exit 1
  fi

  echo "[OK] ${name} port ${port} has been freed."
}

cleanup() {
  echo
  echo "[INFO] Shutting down JapanMap services..."
  if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${BACKEND_PID}" ] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}

start_backend() {
  echo "[1/2] Starting Flask backend on http://localhost:${BACKEND_PORT}"
  if command -v conda >/dev/null 2>&1; then
    conda run -n "${CONDA_ENV}" python "${BASE_DIR}/map.py" &
  else
    echo "[WARN] conda command not found. Falling back to system python."
    python "${BASE_DIR}/map.py" &
  fi
  BACKEND_PID="$!"
}

start_frontend() {
  echo "[2/2] Starting Vite frontend on http://localhost:${FRONTEND_PORT}"
  cd "${BASE_DIR}/mapdown"
  npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" --strictPort &
  FRONTEND_PID="$!"
}

trap cleanup INT TERM EXIT

echo "============================================================"
echo "JapanMap local startup"
echo "Backend port:  ${BACKEND_PORT}"
echo "Frontend port: ${FRONTEND_PORT}"
echo "Conda env:     ${CONDA_ENV}"
echo "============================================================"

free_port "${BACKEND_PORT}" "Backend"
free_port "${FRONTEND_PORT}" "Frontend"

start_backend
start_frontend

echo
echo "[READY] Backend:  http://localhost:${BACKEND_PORT}"
echo "[READY] Frontend: http://localhost:${FRONTEND_PORT}"
echo "[INFO] Press Ctrl+C to stop both services."
echo

while true; do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "[ERROR] Backend process exited."
    exit 1
  fi
  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    echo "[ERROR] Frontend process exited."
    exit 1
  fi
  sleep 2
done
