#!/bin/bash
# Run Coach App backend (FastAPI)
# Usage: ./run.sh

cd "$(dirname "$0")/backend"
if [ -d "../.venv" ]; then
  source ../.venv/bin/activate
elif [ -d ".venv" ]; then
  source .venv/bin/activate
fi
python -m src.main
