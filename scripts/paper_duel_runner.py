#!/usr/bin/env python3
"""Compatibility shim; the crypto duel runner is owned by xiaobi."""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path("/workspace/hermes-workspaces/xiaobi/scripts/paper_duel_runner.py")

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
