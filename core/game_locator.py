# -*- coding: utf-8 -*-
"""Auto-detection and inspection of Azur Promilia PC installations."""
from __future__ import annotations

import json
import os
import re
import string
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from core.models import GameInstallation

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None


UNINSTALL_REG_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") if winreg else None,
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall") if winreg else None,
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") if winreg else None,
]

COMMON_SUBPATHS = [
    "AzurPromilia",
    "AzurPromilia bilibili",
    "AzurPromilia_Game",
    r"game\AzurPromilia",
    r"game\AzurPromilia bilibili",
    r"Games\AzurPromilia",
    r"Games\AzurPromilia bilibili",
    r"Program Files\AzurPromilia",
    r"Program Files\Manjuu\AzurPromilia",
]


def resolve_game_root(candidate: Path) -> Optional[Path]:
    """Resolve either an install root or a game root to the folder containing AzurPromilia.exe."""
    if not candidate or not candidate.exists():
        return None
    if (candidate / "AzurPromilia.exe").is_file():
        return candidate
    nested = candidate / "AzurPromilia_Game"
    if (nested / "AzurPromilia.exe").is_file():
        return nested
    return None


def _find_launcher_exe(install_root: Path) -> str:
    if not install_root.is_dir():
        return ""
    for child in sorted(install_root.iterdir(), reverse=True):
        if child.is_dir() and re.match(r"^\d+(\.\d+)+$", child.name):
            exe = child / "launcher.exe"
            if exe.is_file():
                return str(exe)
    direct = install_root / "launcher.exe"
    return str(direct) if direct.is_file() else ""


def _resolve_index_paths(game_root: Path) -> Dict[str, str]:
    paths_file = game_root / "_index" / "paths"
    if not paths_file.is_file():
        return {}
    try:
        raw = json.loads(paths_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

    user_home = str(Path.home())
    local_app = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    temp_dir = tempfile.gettempdir()

    def _expand(template: str) -> str:
        out = (
            template.replace("{user}", user_home)
            .replace("{local_appdata}", local_app)
            .replace("{temp}", temp_dir)
            .replace("{game}", str(game_root))
        )
        return os.path.normpath(out)

    resolved: Dict[str, str] = {}
    for key in ("gameLog", "cache", "crashLog", "screenshot"):
        items = raw.get(key)
        if isinstance(items, list) and items and isinstance(items[0], dict) and "path" in items[0]:
            resolved[key] = _expand(str(items[0]["path"]))
    return resolved


def _fast_dir_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    stack = [str(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    return total


def detect_server_from_files(game_root: Path, install_root: Optional[Path] = None) -> str:
    """Identify which server a game_root currently belongs to (SDK files take priority over folder name)."""
    plugins_sdk = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    if (plugins_sdk / "BLPlatform64").is_dir():
        return "bilibili"

    name_hint = f"{install_root.name if install_root else ''} {game_root.name}".lower()
    if any(k in name_hint for k in ("_jp", " jp", "japan", "日服")):
        return "jp"
    if any(k in name_hint for k in ("_kr", " kr", "korea", "韩服")):
        return "kr"
    if any(k in name_hint for k in ("_tw", " tw", "taiwan", "台服")):
        return "tw"
    if any(k in name_hint for k in ("_en", " global", "国际服")):
        return "en"

    if (plugins_sdk / "union_pcsdk.dll").is_file() or (game_root / "mj_sdk" / "res" / "app_config.dat").is_file():
        return "official"
    if any(k in name_hint for k in ("bilibili", "bili", "b服")):
        return "bilibili"
    return "unknown"


def inspect_installation(path: Path, source_tag: str = "manual", measure_size: bool = True) -> Optional[GameInstallation]:
    """Inspect a candidate path and build a GameInstallation descriptor."""
    game_root = resolve_game_root(path)
    if not game_root:
        return None

    install_root = game_root.parent if game_root.name.lower() == "azurpromilia_game" else game_root
    version = "未知"
    version_name = ""
    ver_file = game_root / "_index" / "version"
    if ver_file.is_file():
        try:
            ver_data = json.loads(ver_file.read_text(encoding="utf-8"))
            version = str(ver_data.get("version", "未知"))
            version_name = str(ver_data.get("versionName", ""))
        except Exception:
            pass

    plugins_sdk = game_root / "AzurPromilia_Data" / "Plugins" / "mj_sdk"
    has_app_config = (game_root / "mj_sdk" / "res" / "app_config.dat").is_file()
    has_bl_platform = (plugins_sdk / "BLPlatform64").is_dir()
    has_sdk_dll = (plugins_sdk / "PCGameSDK.dll").is_file() or (plugins_sdk / "union_pcsdk.dll").is_file()

    streaming_bytes = _fast_dir_size(game_root / "AzurPromilia_Data" / "StreamingAssets" / ".res") if measure_size else 0
    persistent_bytes = _fast_dir_size(game_root / "AzurPromilia_Data" / ".res") if measure_size else 0

    return GameInstallation(
        install_root=str(install_root),
        game_root=str(game_root),
        launcher_exe=_find_launcher_exe(install_root),
        version=version,
        version_name=version_name,
        detected_server=detect_server_from_files(game_root, install_root),
        has_app_config=has_app_config,
        has_bl_platform=has_bl_platform,
        has_sdk_dll=has_sdk_dll,
        streaming_res_bytes=streaming_bytes,
        persistent_res_bytes=persistent_bytes,
        paths_index=_resolve_index_paths(game_root),
        source_tag=source_tag,
    )


def _scan_registry() -> List[tuple[Path, str]]:
    found: List[tuple[Path, str]] = []
    if not winreg:
        return found
    for entry in UNINSTALL_REG_PATHS:
        if not entry:
            continue
        hive, subkey = entry
        try:
            with winreg.OpenKey(hive, subkey) as root_key:
                count = winreg.QueryInfoKey(root_key)[0]
                for i in range(count):
                    try:
                        name = winreg.EnumKey(root_key, i)
                        with winreg.OpenKey(root_key, name) as item_key:
                            display_name = ""
                            install_loc = ""
                            try:
                                display_name = str(winreg.QueryValueEx(item_key, "DisplayName")[0])
                            except OSError:
                                pass
                            try:
                                install_loc = str(winreg.QueryValueEx(item_key, "InstallLocation")[0])
                            except OSError:
                                pass
                            combined = f"{display_name} {install_loc}".lower()
                            if install_loc and ("azurpromilia" in combined or "蓝色星原" in combined):
                                found.append((Path(install_loc), "registry"))
                    except OSError:
                        continue
        except OSError:
            continue
    return found


def _scan_running_processes() -> List[tuple[Path, str]]:
    found: List[tuple[Path, str]] = []
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process -Name 'AzurPromilia','launcher' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout.splitlines():
            p = line.strip()
            if p and "azurpromilia" in p.lower():
                exe_path = Path(p)
                if exe_path.name.lower() == "azurpromilia.exe":
                    found.append((exe_path.parent, "process"))
                elif exe_path.name.lower() == "launcher.exe":
                    found.append((exe_path.parent.parent, "process"))
    except Exception:
        pass
    return found


def _scan_common_drives() -> List[tuple[Path, str]]:
    found: List[tuple[Path, str]] = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        if not drive.exists():
            continue
        for sub in COMMON_SUBPATHS:
            cand = drive / sub
            if cand.exists():
                found.append((cand, "disk"))
    return found


def discover_installations(extra_paths: Optional[List[str]] = None, measure_size: bool = True) -> List[GameInstallation]:
    """Discover all Azur Promilia PC installations via registry, processes, common paths, and saved paths."""
    candidates: List[tuple[Path, str]] = []
    candidates.extend(_scan_registry())
    candidates.extend(_scan_running_processes())
    candidates.extend(_scan_common_drives())
    for raw in extra_paths or []:
        if raw:
            candidates.append((Path(raw), "saved"))

    seen_roots: set[str] = set()
    results: List[GameInstallation] = []
    for cand, tag in candidates:
        resolved = resolve_game_root(cand)
        if not resolved:
            continue
        norm = os.path.normcase(os.path.normpath(str(resolved)))
        if norm in seen_roots:
            continue
        seen_roots.add(norm)
        info = inspect_installation(resolved, source_tag=tag, measure_size=measure_size)
        if info:
            results.append(info)
    return results
