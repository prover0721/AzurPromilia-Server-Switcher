# -*- coding: utf-8 -*-
"""Local Windows registry snapshot manager for multi-account / settings isolation."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

from core.models import PROFILES_DIR

MANJUU_REG_KEY = r"HKCU\Software\manjuu\AzurPromilia"


def list_profiles(server_id: str, profiles_dir: Path = PROFILES_DIR) -> List[str]:
    """List saved registry profile names for a given server."""
    folder = profiles_dir / server_id
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.reg") if p.is_file())


def save_profile(server_id: str, profile_name: str, profiles_dir: Path = PROFILES_DIR) -> Path:
    """Export current HKCU\\Software\\manjuu\\AzurPromilia registry key to a .reg snapshot."""
    clean_name = "".join(c for c in profile_name if c.isalnum() or c in ("-", "_", ".")).strip()
    if not clean_name:
        raise ValueError("配置快照名称不能为空")
    folder = profiles_dir / server_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{clean_name}.reg"

    proc = subprocess.run(
        ["reg.exe", "export", MANJUU_REG_KEY, str(target), "/y"],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"导出注册表配置失败: {proc.stderr.strip() or proc.stdout.strip()}")
    return target


def apply_profile(server_id: str, profile_name: str, profiles_dir: Path = PROFILES_DIR) -> None:
    """Import a saved .reg snapshot back into HKCU\\Software\\manjuu\\AzurPromilia."""
    target = profiles_dir / server_id / f"{profile_name}.reg"
    if not target.is_file():
        raise FileNotFoundError(f"未找到配置快照: {target}")
    proc = subprocess.run(
        ["reg.exe", "import", str(target)],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"导入注册表配置失败: {proc.stderr.strip() or proc.stdout.strip()}")
