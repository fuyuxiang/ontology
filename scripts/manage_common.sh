#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
LOG_DIR="${RUN_DIR}/logs"
PID_DIR="${RUN_DIR}/pids"

BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
BACKEND_VENV_DIR="${BACKEND_DIR}/.venv"
BACKEND_VENV_PYTHON="${BACKEND_VENV_DIR}/bin/python"

BACKEND_PORT="${BACKEND_PORT:-8088}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
BACKEND_STARTUP_TIMEOUT="${BACKEND_STARTUP_TIMEOUT:-90}"
FRONTEND_STARTUP_TIMEOUT="${FRONTEND_STARTUP_TIMEOUT:-20}"

BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"
BACKEND_LOG_FILE="${LOG_DIR}/backend.log"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"
BACKEND_BOOTSTRAP_LOG_FILE="${LOG_DIR}/backend-bootstrap.log"
BACKEND_INSTALL_STAMP_FILE="${BACKEND_VENV_DIR}/.install-stamp"

ensure_runtime_dirs() {
  mkdir -p "${LOG_DIR}" "${PID_DIR}"
}

print_line() {
  printf '%s\n' "$*"
}

fail() {
  print_line "ERROR: $*" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || fail "Missing required command: ${command_name}"
}

require_base_commands() {
  require_command lsof
  require_command ps
  require_command python3
}

install_backend_dependencies() {
  print_line "Installing backend dependencies into ${BACKEND_VENV_DIR}..."
  : > "${BACKEND_BOOTSTRAP_LOG_FILE}"
  (
    cd "${BACKEND_DIR}"
    "${BACKEND_VENV_PYTHON}" -m pip install -e .
  ) >> "${BACKEND_BOOTSTRAP_LOG_FILE}" 2>&1 || {
    print_line "Backend dependency installation failed. Recent log output:"
    tail -n 60 "${BACKEND_BOOTSTRAP_LOG_FILE}" 2>/dev/null || true
    fail "Failed to install backend dependencies. Full log: ${BACKEND_BOOTSTRAP_LOG_FILE}"
  }
  touch "${BACKEND_INSTALL_STAMP_FILE}"
}

ensure_backend_environment() {
  local reinstall_required=1

  if [ ! -x "${BACKEND_VENV_PYTHON}" ]; then
    print_line "Creating backend virtual environment at ${BACKEND_VENV_DIR}..."
    python3 -m venv "${BACKEND_VENV_DIR}"
  fi

  if [ -f "${BACKEND_INSTALL_STAMP_FILE}" ] && [ "${BACKEND_INSTALL_STAMP_FILE}" -nt "${BACKEND_DIR}/pyproject.toml" ]; then
    reinstall_required=0
  fi

  if ! "${BACKEND_VENV_PYTHON}" -c "import rdflib, fastapi, uvicorn" >/dev/null 2>&1; then
    reinstall_required=1
  fi

  if [ "${reinstall_required}" -eq 1 ]; then
    install_backend_dependencies
  fi
}

pid_is_running() {
  local pid="$1"
  kill -0 "${pid}" >/dev/null 2>&1
}

read_pid_file() {
  local pid_file="$1"
  if [ -f "${pid_file}" ]; then
    tr -d '[:space:]' < "${pid_file}"
  fi
}

cleanup_stale_pid_file() {
  local pid_file="$1"
  local pid
  pid="$(read_pid_file "${pid_file}")"
  if [ -n "${pid}" ] && ! pid_is_running "${pid}"; then
    rm -f "${pid_file}"
  fi
}

port_pids() {
  local port="$1"
  lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null | sort -u
}

port_in_use() {
  local port="$1"
  [ -n "$(port_pids "${port}")" ]
}

pid_command() {
  local pid="$1"
  local command_text
  command_text="$(ps -p "${pid}" -o command= 2>/dev/null | sed 's/^[[:space:]]*//')"
  if [ -n "${command_text}" ]; then
    print_line "${command_text}"
    return 0
  fi
  lsof -a -p "${pid}" -d txt -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "${pid}" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

is_backend_process() {
  local pid="$1"
  local command_text
  local cwd_path
  command_text="$(pid_command "${pid}")"
  case "${command_text}" in
    *"-m app.cli serve"*|*"uvicorn"*"app.main:app"*|*"app.main:app"*)
      return 0
      ;;
  esac

  cwd_path="$(pid_cwd "${pid}")"
  case "${cwd_path}" in
    "${BACKEND_DIR}"|"${BACKEND_DIR}"/*)
      return 0
      ;;
  esac
  return 1
}

is_frontend_process() {
  local pid="$1"
  local command_text
  local cwd_path
  command_text="$(pid_command "${pid}")"
  case "${command_text}" in
    *"vite"*"--port ${FRONTEND_PORT}"*|*"vite"*"--strictPort"*|*"npm run dev"*)
      return 0
      ;;
  esac

  cwd_path="$(pid_cwd "${pid}")"
  case "${cwd_path}" in
    "${FRONTEND_DIR}"|"${FRONTEND_DIR}"/*)
      return 0
      ;;
  esac
  return 1
}

is_service_process() {
  local service_name="$1"
  local pid="$2"
  case "${service_name}" in
    backend)
      is_backend_process "${pid}"
      ;;
    frontend)
      is_frontend_process "${pid}"
      ;;
    *)
      return 1
      ;;
  esac
}

service_port() {
  case "$1" in
    backend) print_line "${BACKEND_PORT}" ;;
    frontend) print_line "${FRONTEND_PORT}" ;;
    *) return 1 ;;
  esac
}

service_pid_file() {
  case "$1" in
    backend) print_line "${BACKEND_PID_FILE}" ;;
    frontend) print_line "${FRONTEND_PID_FILE}" ;;
    *) return 1 ;;
  esac
}

service_log_file() {
  case "$1" in
    backend) print_line "${BACKEND_LOG_FILE}" ;;
    frontend) print_line "${FRONTEND_LOG_FILE}" ;;
    *) return 1 ;;
  esac
}

service_url() {
  case "$1" in
    backend) print_line "http://127.0.0.1:${BACKEND_PORT}" ;;
    frontend) print_line "http://127.0.0.1:${FRONTEND_PORT}" ;;
    *) return 1 ;;
  esac
}

wait_for_port() {
  local port="$1"
  local attempts="${2:-20}"
  local current=0
  while [ "${current}" -lt "${attempts}" ]; do
    if port_in_use "${port}"; then
      return 0
    fi
    sleep 1
    current=$((current + 1))
  done
  return 1
}

wait_for_pid_exit() {
  local pid="$1"
  local attempts="${2:-10}"
  local current=0
  while [ "${current}" -lt "${attempts}" ]; do
    if ! pid_is_running "${pid}"; then
      return 0
    fi
    sleep 1
    current=$((current + 1))
  done
  return 1
}

verify_started_service() {
  local service_name="$1"
  local port
  local pid_file
  local pid
  port="$(service_port "${service_name}")"
  pid_file="$(service_pid_file "${service_name}")"
  pid="$(read_pid_file "${pid_file}")"

  if [ -z "${pid}" ] || ! pid_is_running "${pid}"; then
    print_line "${service_name} process is not running after startup."
    return 1
  fi

  if ! port_in_use "${port}"; then
    print_line "${service_name} port ${port} is not listening after startup."
    return 1
  fi

  sleep 1
  if ! pid_is_running "${pid}" || ! port_in_use "${port}"; then
    print_line "${service_name} exited too soon after startup."
    return 1
  fi

  return 0
}

describe_port_conflict() {
  local service_name="$1"
  local port
  local pid
  local matched_ours=1
  port="$(service_port "${service_name}")"

  print_line "${service_name} port ${port} is already in use."
  for pid in $(port_pids "${port}"); do
    if is_service_process "${service_name}" "${pid}"; then
      matched_ours=0
      print_line "  PID ${pid}: $(pid_command "${pid}") [managed-service]"
    else
      print_line "  PID ${pid}: $(pid_command "${pid}") [external-process]"
    fi
  done
  return "${matched_ours}"
}

ensure_frontend_dependencies() {
  require_command npm
  if [ ! -x "${FRONTEND_DIR}/node_modules/.bin/vite" ]; then
    fail "Frontend dependencies are missing. Run: cd frontend && npm install"
  fi
}

start_backend() {
  cleanup_stale_pid_file "${BACKEND_PID_FILE}"
  ensure_backend_environment
  if port_in_use "${BACKEND_PORT}"; then
    if describe_port_conflict backend; then
      fail "Refusing to start backend because port ${BACKEND_PORT} is occupied by another process."
    fi
    print_line "Backend already running at $(service_url backend)"
    return 0
  fi

  print_line "Starting backend on port ${BACKEND_PORT}..."
  (
    cd "${BACKEND_DIR}"
    nohup env ONTOLOGY_HOST="${BACKEND_HOST}" ONTOLOGY_PORT="${BACKEND_PORT}" \
      "${BACKEND_VENV_PYTHON}" -m app.cli serve --port "${BACKEND_PORT}" > "${BACKEND_LOG_FILE}" 2>&1 &
    echo "$!" > "${BACKEND_PID_FILE}"
  )

  if ! wait_for_port "${BACKEND_PORT}" "${BACKEND_STARTUP_TIMEOUT}"; then
    print_line "Backend failed to listen on port ${BACKEND_PORT}. Recent log output:"
    tail -n 40 "${BACKEND_LOG_FILE}" 2>/dev/null || true
    fail "Backend start failed."
  fi

  if ! verify_started_service backend; then
    print_line "Backend failed health checks. Recent log output:"
    tail -n 40 "${BACKEND_LOG_FILE}" 2>/dev/null || true
    fail "Backend start failed."
  fi

  print_line "Backend started: $(service_url backend)"
}

start_frontend() {
  cleanup_stale_pid_file "${FRONTEND_PID_FILE}"
  ensure_frontend_dependencies

  if port_in_use "${FRONTEND_PORT}"; then
    if describe_port_conflict frontend; then
      fail "Refusing to start frontend because port ${FRONTEND_PORT} is occupied by another process."
    fi
    print_line "Frontend already running at $(service_url frontend)"
    return 0
  fi

  print_line "Starting frontend on port ${FRONTEND_PORT}..."
  (
    cd "${FRONTEND_DIR}"
    nohup ./node_modules/.bin/vite --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" --strictPort \
      > "${FRONTEND_LOG_FILE}" 2>&1 &
    echo "$!" > "${FRONTEND_PID_FILE}"
  )

  if ! wait_for_port "${FRONTEND_PORT}" "${FRONTEND_STARTUP_TIMEOUT}"; then
    print_line "Frontend failed to listen on port ${FRONTEND_PORT}. Recent log output:"
    tail -n 40 "${FRONTEND_LOG_FILE}" 2>/dev/null || true
    fail "Frontend start failed."
  fi

  if ! verify_started_service frontend; then
    print_line "Frontend failed health checks. Recent log output:"
    tail -n 40 "${FRONTEND_LOG_FILE}" 2>/dev/null || true
    fail "Frontend start failed."
  fi

  print_line "Frontend started: $(service_url frontend)"
}

stop_pid() {
  local pid="$1"
  if ! pid_is_running "${pid}"; then
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  if wait_for_pid_exit "${pid}" 10; then
    return 0
  fi

  kill -9 "${pid}" >/dev/null 2>&1 || true
  wait_for_pid_exit "${pid}" 5 || true
}

stop_service_by_pid_file() {
  local service_name="$1"
  local pid_file
  local pid
  pid_file="$(service_pid_file "${service_name}")"
  cleanup_stale_pid_file "${pid_file}"
  pid="$(read_pid_file "${pid_file}")"
  if [ -n "${pid}" ]; then
    print_line "Stopping ${service_name} PID ${pid}..."
    stop_pid "${pid}"
    rm -f "${pid_file}"
  fi
}

stop_service_by_port() {
  local service_name="$1"
  local port
  local pid
  local any_stopped=1
  port="$(service_port "${service_name}")"

  for pid in $(port_pids "${port}"); do
    if is_service_process "${service_name}" "${pid}"; then
      print_line "Stopping ${service_name} listener PID ${pid} on port ${port}..."
      stop_pid "${pid}"
      any_stopped=0
    else
      print_line "Skipping PID ${pid} on port ${port}; it does not look like the managed ${service_name} process."
    fi
  done

  return "${any_stopped}"
}

stop_backend() {
  stop_service_by_pid_file backend
  stop_service_by_port backend || true
  rm -f "${BACKEND_PID_FILE}"
  if port_in_use "${BACKEND_PORT}"; then
    fail "Backend port ${BACKEND_PORT} is still occupied after stop."
  fi
  print_line "Backend stopped."
}

stop_frontend() {
  stop_service_by_pid_file frontend
  stop_service_by_port frontend || true
  rm -f "${FRONTEND_PID_FILE}"
  if port_in_use "${FRONTEND_PORT}"; then
    fail "Frontend port ${FRONTEND_PORT} is still occupied after stop."
  fi
  print_line "Frontend stopped."
}

print_status_summary() {
  print_line ""
  print_line "Services:"
  print_line "  Backend : $(service_url backend)"
  print_line "  Frontend: $(service_url frontend)"
  print_line "Logs:"
  print_line "  Backend : ${BACKEND_LOG_FILE}"
  print_line "  Backend bootstrap: ${BACKEND_BOOTSTRAP_LOG_FILE}"
  print_line "  Frontend: ${FRONTEND_LOG_FILE}"
}
