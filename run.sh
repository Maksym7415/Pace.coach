#!/bin/bash
# Run Shoe Tracker backend
# Usage: ./run.sh
# Ensure .venv is activated or use: source .venv/bin/activate && python -m src.api.app

cd "$(dirname "$0")"
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
python -m src.api.app
