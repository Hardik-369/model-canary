#!/bin/bash
set -e

if [ ! -f "$MODEL_CANARY_CONFIG" ]; then
    echo "No config found at $MODEL_CANARY_CONFIG, initializing..."
    model-canary init --force /etc/model-canary
fi

exec "$@"
