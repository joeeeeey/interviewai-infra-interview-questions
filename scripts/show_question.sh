#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="${ROOT_DIR}/.candidate-progress"

show_step() {
  case "$1" in
    1) cat "${ROOT_DIR}/questions/Q1-service-overview.md" ;;
    2) cat "${ROOT_DIR}/questions/Q2-error-analysis.md" ;;
    3) cat "${ROOT_DIR}/questions/Q3-workflow-skill.md" ;;
    *)
      echo "Unsupported step: $1" >&2
      exit 1
      ;;
  esac
}

mode="${1:-next}"

case "$mode" in
  1|2|3)
    show_step "$mode"
    ;;
  next)
    step=1
    if [[ -f "${STATE_FILE}" ]]; then
      step="$(cat "${STATE_FILE}")"
    fi

    if [[ "$step" != "1" && "$step" != "2" && "$step" != "3" ]]; then
      step=1
    fi

    echo "[makrodnw] 当前题目: Q${step}"
    echo
    show_step "$step"

    if [[ "$step" -lt 3 ]]; then
      echo $((step + 1)) > "${STATE_FILE}"
      echo
      echo "[makrodnw] 下次执行 make makrodnw 将显示 Q$((step + 1))"
    else
      echo 3 > "${STATE_FILE}"
      echo
      echo "[makrodnw] 已到最后一题。可执行 make reset 重新从 Q1 开始。"
    fi
    ;;
  reset)
    echo 1 > "${STATE_FILE}"
    echo "[makrodnw] 已重置为 Q1"
    ;;
  all)
    show_step 1
    echo
    echo "-----"
    echo
    show_step 2
    echo
    echo "-----"
    echo
    show_step 3
    ;;
  *)
    echo "Usage: $0 [1|2|3|next|reset|all]" >&2
    exit 1
    ;;
esac
