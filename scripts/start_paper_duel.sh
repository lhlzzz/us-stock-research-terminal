#!/bin/bash
set -euo pipefail

# Compatibility entry point. Crypto duel ownership lives in xiaobi.
exec bash /workspace/hermes-workspaces/xiaobi/scripts/start_paper_duel.sh "$@"
