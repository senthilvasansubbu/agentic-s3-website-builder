#!/usr/bin/env bash

set -euo pipefail

PORT="${PORT:-8000}"
APP_ENTRY="${APP_ENTRY:-app.py}"
APP_MODULE="${APP_MODULE:-app:app}"
LOG_FILE="${LOG_FILE:-logs/server-local-${PORT}.log}"
PID_FILE="${PID_FILE:-.server-${PORT}.pid}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ ! -f "${APP_ENTRY}" ]]; then
  echo "Error: ${APP_ENTRY} not found in ${REPO_ROOT}" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is not installed or not on PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "${LOG_FILE}")"

echo "[1/4] Stopping existing app-related processes (if any)..."
pkill -f "python3 app.py" >/dev/null 2>&1 || true
pkill -f "uvicorn app:app" >/dev/null 2>&1 || true

echo "[2/4] Releasing any listener on port ${PORT}..."
PORT_PIDS="$(ss -ltnp 2>/dev/null | awk -v port=":${PORT}" '$4 ~ port"$" {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)"

if [[ -n "${PORT_PIDS}" ]]; then
  echo "Found listener PID(s) on ${PORT}: ${PORT_PIDS}"
  kill ${PORT_PIDS} >/dev/null 2>&1 || true

  for _ in $(seq 1 8); do
    sleep 1
    if ! ss -ltnp 2>/dev/null | grep -qE ":${PORT}\\b"; then
      break
    fi
  done

  if ss -ltnp 2>/dev/null | grep -qE ":${PORT}\\b"; then
    echo "Port ${PORT} is still busy. Force-stopping remaining listener(s)..."
    kill -9 ${PORT_PIDS} >/dev/null 2>&1 || true
  fi
fi

if ss -ltnp 2>/dev/null | grep -qE ":${PORT}\\b"; then
  echo "Error: port ${PORT} is still in use after cleanup" >&2
  ss -ltnp 2>/dev/null | grep -E ":${PORT}\\b" >&2 || true
  exit 1
fi

echo "[3/4] Starting server on http://0.0.0.0:${PORT} ..."
nohup python3 -m uvicorn "${APP_MODULE}" --host 0.0.0.0 --port "${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${PID_FILE}"

echo "[4/4] Validating startup..."
for _ in $(seq 1 20); do
  if ss -ltnp 2>/dev/null | grep -qE ":${PORT}\\b"; then
    echo "Server started successfully."
    echo "PID: ${SERVER_PID}"
    echo "URL: http://localhost:${PORT}"
    echo "Log: ${LOG_FILE}"
    echo "PID file: ${PID_FILE}"
    exit 0
  fi
  sleep 1
done

echo "Error: server did not start within expected time" >&2
echo "Last 40 log lines:" >&2
tail -n 40 "${LOG_FILE}" >&2 || true
exit 1
