#!/usr/bin/env bash
# ============================================================
# GADA — Rental Market Analysis App
# Start script for the Streamlit application
# Usage: ./start.sh [--port PORT]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
APP_FILE="$SCRIPT_DIR/app/app.py"
PORT="${PORT:-8501}"

# Parse optional --port argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: ./start.sh [--port PORT]"
      exit 1
      ;;
  esac
done

echo "============================================"
echo " GADA — Rental Market Analysis"
echo " Starting Streamlit app on port $PORT ..."
echo "============================================"

# Check virtual environment exists
if [[ ! -d "$VENV_DIR" ]]; then
  echo "ERROR: Virtual environment not found at $VENV_DIR"
  echo "       Run: python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

# Check app file exists
if [[ ! -f "$APP_FILE" ]]; then
  echo "ERROR: App file not found at $APP_FILE"
  exit 1
fi

# Activate virtual environment (cross-platform: Git Bash / WSL / Linux / macOS)
if [[ -f "$VENV_DIR/Scripts/activate" ]]; then
  # Windows / Git Bash
  source "$VENV_DIR/Scripts/activate"
elif [[ -f "$VENV_DIR/bin/activate" ]]; then
  # Linux / macOS / WSL
  source "$VENV_DIR/bin/activate"
else
  echo "ERROR: Could not find activate script in $VENV_DIR"
  exit 1
fi

echo "Virtual environment activated."
echo "Launching: streamlit run app/app.py --server.port $PORT"
echo ""

streamlit run "$APP_FILE" --server.port "$PORT"
