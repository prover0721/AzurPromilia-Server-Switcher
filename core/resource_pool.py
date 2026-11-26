# -*- coding: utf-8 -*-
"""Resource sharing (NTFS hard links) and CN channel SDK hot-switching."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.models import BACKUPS_DIR, BUILTIN_CN_SOURCES_DIR, SOURCES_DIR

SHARED_RES_RELPATHS = [
    Path("AzurPromilia_Data") / "StreamingAssets" / ".res",
    Path("AzurPromilia_Data") / ".res",
]

DEFAULT_SHARED_PACKAGES = [
    "default_package",
    "raw_streaming_package",
    "raw_base_package",
    "raw_nostreaming_package",
    "static_package",
]


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


def get_ntfs_link_info(path: Path) -> Tuple[int, int]:
    """Return (link_count, file_index) on Windows NTFS; falls back to os.stat."""
    if os.name != "nt":
        st = path.stat()
        return (st.st_nlink, st.st_ino)
    kernel32 = ctypes.windll.kernel32
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    FILE_SHARE_DELETE = 0x00000004
    OPEN_EXISTING = 3
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    handle = kernel32.CreateFileW(
        str(path),
        0,  # query metadata only without locking file content
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        st = path.stat()
        return (st.st_nlink, st.st_ino)
    try:
        info = _BY_HANDLE_FILE_INFORMATION()
        ok = kernel32.GetFileInformationByHandle(handle, ctypes.byref(info))
        if not ok:
            st = path.stat()
            return (st.st_nlink, st.st_ino)
        file_index = (info.nFileIndexHigh << 32) | info.nFileIndexLow
        return (int(info.nNumberOfLinks), int(file_index))
    finally:
        kernel32.CloseHandle(handle)


@dataclass
class LinkAuditResult:
    """Summary of NTFS hard-link health and disk savings."""

    total_files: int = 0
    linked_files: int = 0
    logical_bytes: int = 0
    unique_physical_bytes: int = 0

    @property
    def saved_bytes(self) -> int:
        return max(0, self.logical_bytes - self.unique_physical_bytes)

    @property
    def saved_gb(self) -> float:
        return round(self.saved_bytes / (1024 ** 3), 2)

    @property
    def logical_gb(self) -> float:
        return round(self.logical_bytes / (1024 ** 3), 2)


def is_game_running(game_root: Optional[Path] = None) -> bool:
    """Check whether AzurPromilia.exe is currently running."""
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq AzurPromilia.exe", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "azurpromilia.exe" in proc.stdout.lower()
    except Exception:
        return False


def _copy_tree_overwrite(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def resolve_source_dir(server_id: str, sources_dir: Path = SOURCES_DIR) -> Optional[Path]:
    """Return the cached or built-in source directory for a CN server, if complete."""
    for base_root in (sources_dir, BUILTIN_CN_SOURCES_DIR):
        base = base_root / server_id
        if (base / "app_config.dat").is_file() and (base / "Plugins_mj_sdk").is_dir():
            return base
    return None


def get_source_status(server_id: str, sources_dir: Path = SOURCES_DIR) -> bool:
    """Return True if channel source files have been cached or bundled for server_id."""
    return resolve_source_dir(server_id, sources_dir) is not None


def get_backup_status(server_id: str, backups_dir: Path = BACKUPS_DIR) -> bool:
    """Return True if at least one backup exists for server_id."""
    base = backups_dir / server_id
    return base.is_dir() and any(base.iterdir())


def extract_channel_source(
    game_root: Path,
    server_id: str,
    sources_dir: Path = SOURCES_DIR,
    log: Optional[Callable[[str], None]] = None,
) -> Path:
    """Extract channel config and mj_sdk plugins from a live installation into local cache."""
    app_cfg = game_root / "mj_sdk" / "res" / "app_config.dat"
    sdk_dir = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    if not app_cfg.is_file() or not sdk_dir.is_dir():
        raise FileNotFoundError(f"未在 {game_root} 中找到完整的 mj_sdk 渠道文件")

    has_bl = (sdk_dir / "BLPlatform64").is_dir()
    if server_id == "bilibili" and not has_bl:
        raise ValueError("当前目录缺少 BLPlatform64，不是完整的 B 服客户端，无法提取为 B 服源。")
    if server_id == "official" and has_bl:
        raise ValueError("当前目录仍包含 BLPlatform64，不是纯净官服客户端，无法提取为官服源。")

    dest = sources_dir / server_id
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(app_cfg, dest / "app_config.dat")
    _copy_tree_overwrite(sdk_dir, dest / "Plugins_mj_sdk")
    if log:
        log(f"[+] 已提取并缓存 [{server_id}] 渠道源配置与登录组件 -> {dest}")
    return dest


def backup_channel_files(
    game_root: Path,
    server_id: str,
    backups_dir: Path = BACKUPS_DIR,
    log: Optional[Callable[[str], None]] = None,
) -> Path:
    """Create a safety backup of current channel config and mj_sdk plugins."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir / server_id / stamp
    dest.mkdir(parents=True, exist_ok=True)

    app_cfg = game_root / "mj_sdk" / "res" / "app_config.dat"
    sdk_dir = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    if app_cfg.is_file():
        shutil.copy2(app_cfg, dest / "app_config.dat")
    if sdk_dir.is_dir():
        _copy_tree_overwrite(sdk_dir, dest / "Plugins_mj_sdk")
    if log:
        log(f"[+] 已创建 [{server_id}] 原生备份 -> {dest}")
    return dest


def switch_cn_channel(
    game_root: Path,
    current_server: str,
    target_server: str,
    sources_dir: Path = SOURCES_DIR,
    backups_dir: Path = BACKUPS_DIR,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """Hot-switch between CN channels (e.g., official <-> bilibili) in the same game_root."""
    if is_game_running(game_root):
        raise RuntimeError("检测到 AzurPromilia.exe 正在运行，请先关闭游戏再执行切换。")

    target_src = resolve_source_dir(target_server, sources_dir)
    if not target_src:
        raise FileNotFoundError(
            f"尚未缓存 [{target_server}] 的渠道源。请先导入一次 [{target_server}] 客户端目录以提取源。"
        )

    if current_server in ("official", "bilibili") and not get_source_status(current_server, sources_dir):
        extract_channel_source(game_root, current_server, sources_dir, log=log)

    if current_server in ("official", "bilibili") and not get_backup_status(current_server, backups_dir):
        backup_channel_files(game_root, current_server, backups_dir, log=log)

    dst_cfg = game_root / "mj_sdk" / "res" / "app_config.dat"
    dst_cfg.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target_src / "app_config.dat", dst_cfg)

    dst_sdk = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    _copy_tree_overwrite(target_src / "Plugins_mj_sdk", dst_sdk)
    if log:
        log(f"[√] 已完成渠道热切换: {current_server} -> {target_server}")


def link_shared_resources(
    source_game_root: Path,
    target_game_root: Path,
    packages: Optional[List[str]] = None,
    overwrite: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[int, int]:
    """Hard-link heavy .res asset files from source_game_root into target_game_root.

    Returns (linked_count, skipped_count).
    """
    if is_game_running(target_game_root):
        raise RuntimeError("检测到游戏正在运行，请先关闭游戏再同步硬链接资源。")

    src_drive = os.path.splitdrive(str(source_game_root.resolve()))[0].lower()
    dst_drive = os.path.splitdrive(str(target_game_root.resolve()))[0].lower()
    if src_drive != dst_drive:
        raise ValueError(
            f"跨盘符无法建立 NTFS 硬链接（源在 {src_drive}，目标在 {dst_drive}）。请将外服壳目录放在同一磁盘分区。"
        )

    pkg_filter = set(packages or DEFAULT_SHARED_PACKAGES)
    linked = 0
    skipped = 0

    for rel_res in SHARED_RES_RELPATHS:
        src_base = source_game_root / rel_res
        dst_base = target_game_root / rel_res
        if not src_base.is_dir():
            continue

        for pkg_dir in src_base.iterdir():
            if not pkg_dir.is_dir() or pkg_dir.name not in pkg_filter:
                continue
            for root, _, files in os.walk(pkg_dir):
                rel_sub = Path(root).relative_to(src_base)
                target_dir = dst_base / rel_sub
                target_dir.mkdir(parents=True, exist_ok=True)
                for fname in files:
                    src_file = Path(root) / fname
                    dst_file = target_dir / fname
                    if dst_file.exists():
                        if not overwrite:
                            skipped += 1
                            continue
                        dst_file.unlink()
                    os.link(src_file, dst_file)
                    linked += 1

    if log:
        log(f"[√] 硬链接资源池同步完成：新建链接 {linked} 个文件，保留已有/跳过 {skipped} 个文件")
    return linked, skipped


def unlink_to_independent(
    target_game_root: Path,
    log: Optional[Callable[[str], None]] = None,
) -> int:
    """Break NTFS hard links in target_game_root by copying shared files into independent copies."""
    if is_game_running(target_game_root):
        raise RuntimeError("检测到游戏正在运行，请先关闭游戏再解除硬链接。")

    broken = 0
    for rel_res in SHARED_RES_RELPATHS:
        base = target_game_root / rel_res
        if not base.is_dir():
            continue
        for root, _, files in os.walk(base):
            for fname in files:
                fpath = Path(root) / fname
                nlink, _ = get_ntfs_link_info(fpath)
                if nlink > 1:
                    tmp = fpath.with_suffix(fpath.suffix + ".tmp_copy")
                    shutil.copy2(fpath, tmp)
                    fpath.unlink()
                    tmp.rename(fpath)
                    broken += 1
    if log:
        log(f"[√] 已解除 {broken} 个硬链接文件为独立副本，可安全执行官方更新")
    return broken


def audit_resource_links(game_roots: List[Path]) -> LinkAuditResult:
    """Audit NTFS hard-link count and compute unique physical bytes across managed directories."""
    result = LinkAuditResult()
    seen_inodes: set[Tuple[str, int]] = set()

    for root_path in game_roots:
        if not root_path.is_dir():
            continue
        drive = os.path.splitdrive(str(root_path.resolve()))[0].lower()
        for rel_res in SHARED_RES_RELPATHS:
            base = root_path / rel_res
            if not base.is_dir():
                continue
            for root, _, files in os.walk(base):
                for fname in files:
                    fpath = Path(root) / fname
                    try:
                        size = fpath.stat().st_size
                        nlink, file_idx = get_ntfs_link_info(fpath)
                    except OSError:
                        continue
                    result.total_files += 1
                    result.logical_bytes += size
                    if nlink > 1:
                        result.linked_files += 1
                    key = (drive, file_idx)
                    if key not in seen_inodes:
                        seen_inodes.add(key)
                        result.unique_physical_bytes += size
    return result
