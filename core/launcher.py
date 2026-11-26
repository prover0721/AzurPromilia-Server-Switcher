# -*- coding: utf-8 -*-
"""Game launching and quick directory access helpers."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from core.models import LaunchOptions


def launch_game(game_root: Path, options: Optional[LaunchOptions] = None) -> subprocess.Popen:
    """Launch AzurPromilia.exe directly with optional Unity command-line flags."""
    exe_path = game_root / "AzurPromilia.exe"
    if not exe_path.is_file():
        raise FileNotFoundError(f"未找到游戏主程序: {exe_path}")
    args = [str(exe_path)]
    if options:
        args.extend(options.build_args())
    return subprocess.Popen(args, cwd=str(game_root))


def open_directory(path: Path) -> None:
    """Open a local directory in Windows Explorer."""
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {path}")
    os.startfile(str(path))
