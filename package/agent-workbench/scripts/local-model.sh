#!/usr/bin/env bash
set -euo pipefail
if ! command -v llama-server >/dev/null; then
  echo 'Install a current CUDA-enabled llama.cpp build on the desktop, with llama-server on PATH.' >&2
  exit 1
fi
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo 'Usage: scripts/local-model.sh /path/to/Qwen3.8-27B-IQ3_S.gguf' >&2
  exit 1
fi
# One generation and quantized KV are initial settings for a 16GB 4080 SUPER.
# Actual model/runtime compatibility and memory use must pass the GPU smoke test.
exec llama-server --model "$1" --alias qwen3.8-27b \
  --jinja --no-context-shift \
  --ctx-size 36864 --parallel 1 --n-gpu-layers 99 \
  --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 \
  --host 127.0.0.1 --port 8081
