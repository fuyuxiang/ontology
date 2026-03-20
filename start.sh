#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "${ROOT_DIR}/scripts/manage_common.sh"

ensure_runtime_dirs
require_base_commands

start_backend
start_frontend
print_status_summary
