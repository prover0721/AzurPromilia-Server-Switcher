# -*- coding: utf-8 -*-
"""Built-in community anti-blur (角色反虚化) patch manager with automatic backup & restore."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from core.models import BACKUPS_DIR, BUILTIN_ANTI_BLUR_DIR
from core.resource_pool import is_game_running


def resolve_anti_blur_root(candidate: Optional[Path] = None) -> Optional[Path]:
    """Resolve the built-in or provided folder containing AzurPromilia_Data."""
    target = candidate or BUILTIN_ANTI_BLUR_DIR
    if not target or not target.is_dir():
        return None
    if (target / "AzurPromilia_Data").is_dir():
        return target
    if target.name == "AzurPromilia_Data":
        return target.parent
    return None


def get_anti_blur_backup_dir(backups_dir: Path = BACKUPS_DIR) -> Path:
    return backups_dir / "anti_blur"


def has_anti_blur_backup(backups_dir: Path = BACKUPS_DIR) -> bool:
    bdir = get_anti_blur_backup_dir(backups_dir)
    return bdir.is_dir() and any(bdir.rglob("*"))


def is_builtin_anti_blur_ready() -> bool:
    return resolve_anti_blur_root(BUILTIN_ANTI_BLUR_DIR) is not None


def _list_patch_files(patch_root: Path) -> List[Path]:
    data_dir = patch_root / "AzurPromilia_Data"
    files: List[Path] = []
    for root, _, fnames in os.walk(data_dir):
        for fname in fnames:
            files.append((Path(root) / fname).relative_to(patch_root))
    return files


def apply_anti_blur_patch(
    game_root: Path,
    patch_dir: Optional[Path] = None,
    backups_dir: Path = BACKUPS_DIR,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[int, int]:
    """Apply built-in anti-blur patch files into game_root/AzurPromilia_Data with automatic backup.

    Returns (replaced_count, backed_up_count).
    """
    if is_game_running(game_root):
        raise RuntimeError("检测到游戏正在运行，请先关闭游戏再应用反虚化。")

    resolved_patch = resolve_anti_blur_root(patch_dir)
    if not resolved_patch:
        raise FileNotFoundError("未找到内置反虚化补丁资源 (assets/anti_blur_patch)。")

    rel_files = _list_patch_files(resolved_patch)
    if not rel_files:
        raise ValueError("反虚化补丁目录中没有可替换的文件。")

    backup_root = get_anti_blur_backup_dir(backups_dir)
    replaced = 0
    backed_up = 0

    for rel in rel_files:
        src = resolved_patch / rel
        dst = game_root / rel
        bak = backup_root / rel

        if dst.is_file() and not bak.exists():
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bak)
            backed_up += 1

        dst.parent.mkdir(parents=True, exist_ok=True)
        # Unlink first so any NTFS hard link to another server is broken safely instead of mutating shared inodes
        if dst.exists():
            dst.unlink()
        shutil.copy2(src, dst)
        replaced += 1

    if log:
        log(f"[√] 已应用内置反虚化：替换 {replaced} 个文件，新建原版备份 {backed_up} 个文件")
    return replaced, backed_up


def restore_anti_blur_backup(
    game_root: Path,
    backups_dir: Path = BACKUPS_DIR,
    log: Optional[Callable[[str], None]] = None,
) -> int:
    """Restore original files backed up before applying the anti-blur patch."""
    if is_game_running(game_root):
        raise RuntimeError("检测到游戏正在运行，请先关闭游戏再还原原版文件。")

    backup_root = get_anti_blur_backup_dir(backups_dir)
    if not backup_root.is_dir():
        raise FileNotFoundError("未找到反虚化原版备份。")

    restored = 0
    for root, _, fnames in os.walk(backup_root):
        for fname in fnames:
            bak_file = Path(root) / fname
            rel = bak_file.relative_to(backup_root)
            dst = game_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst.unlink()
            shutil.copy2(bak_file, dst)
            restored += 1

    if log:
        log(f"[√] 已还原 {restored} 个原版文件（恢复官方默认表现）")
    return restored
