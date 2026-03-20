#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

"${ROOT_DIR}/stop.sh"
"${ROOT_DIR}/start.sh"
