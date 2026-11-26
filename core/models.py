# -*- coding: utf-8 -*-
"""Data models, server definitions, and persistent configuration."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

APP_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_ROOT / "assets"
APP_ICON_ICO = ASSETS_DIR / "app_icon.ico"
APP_ICON_PNG = ASSETS_DIR / "app_icon.png"
BUILTIN_ANTI_BLUR_DIR = ASSETS_DIR / "anti_blur_patch"
BUILTIN_CN_SOURCES_DIR = ASSETS_DIR / "cn_sources"
DATA_DIR = APP_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
BACKUPS_DIR = DATA_DIR / "backups"
PROFILES_DIR = DATA_DIR / "profiles"
CONFIG_FILE = DATA_DIR / "switcher_config.json"


SERVER_CATALOG: Dict[str, dict] = {
    "official": {
        "id": "official",
        "name": "官服 (蛮啾)",
        "short": "官服",
        "group": "cn",
        "badge": "C000",
        "desc": "中国大陆官方服务器（蛮啾通行证）",
    },
    "bilibili": {
        "id": "bilibili",
        "name": "B服 (哔哩哔哩)",
        "short": "B服",
        "group": "cn",
        "badge": "BILI",
        "desc": "中国大陆 Bilibili 渠道服务器",
    },
    "jp": {
        "id": "jp",
        "name": "日服 (JP)",
        "short": "日服",
        "group": "overseas",
        "badge": "JP",
        "desc": "日本地区服务器（需独立壳目录 + 硬链接共享通用资源）",
    },
    "kr": {
        "id": "kr",
        "name": "韩服 (KR)",
        "short": "韩服",
        "group": "overseas",
        "badge": "KR",
        "desc": "韩国地区服务器（需独立壳目录 + 硬链接共享通用资源）",
    },
    "tw": {
        "id": "tw",
        "name": "台服 (TW)",
        "short": "台服",
        "group": "overseas",
        "badge": "TW",
        "desc": "港澳台地区服务器（需独立壳目录 + 硬链接共享通用资源）",
    },
    "en": {
        "id": "en",
        "name": "国际服 (Global)",
        "short": "国际服",
        "group": "overseas",
        "badge": "GL",
        "desc": "全球国际服务器（需独立壳目录 + 硬链接共享通用资源）",
    },
}


@dataclass
class GameInstallation:
    """Represents a detected or manually configured Azur Promilia PC installation."""

    install_root: str
    game_root: str
    launcher_exe: str = ""
    version: str = "未知"
    version_name: str = ""
    detected_server: str = "unknown"
    has_app_config: bool = False
    has_bl_platform: bool = False
    has_sdk_dll: bool = False
    streaming_res_bytes: int = 0
    persistent_res_bytes: int = 0
    paths_index: Dict[str, str] = field(default_factory=dict)
    source_tag: str = "manual"

    @property
    def total_res_gb(self) -> float:
        return round((self.streaming_res_bytes + self.persistent_res_bytes) / (1024 ** 3), 2)

    @property
    def server_display_name(self) -> str:
        info = SERVER_CATALOG.get(self.detected_server)
        return info["name"] if info else "未识别区服"


@dataclass
class LaunchOptions:
    """Optional command-line launch parameters for AzurPromilia.exe."""

    popupwindow: bool = False
    custom_resolution: bool = False
    width: int = 1920
    height: int = 1080
    extra_args: str = ""

    def build_args(self) -> List[str]:
        args: List[str] = ["-start=azurpromilia_launcher"]
        if self.popupwindow:
            args.append("-popupwindow")
        if self.custom_resolution and self.width > 0 and self.height > 0:
            args.extend(["-screen-width", str(self.width), "-screen-height", str(self.height)])
        if self.extra_args.strip():
            args.extend(self.extra_args.strip().split())
        return args


@dataclass
class SwitcherConfig:
    """Persistent configuration for the server switcher."""

    cn_game_root: str = ""
    server_game_roots: Dict[str, str] = field(default_factory=dict)
    primary_pool_server: str = "bilibili"
    launch_options: LaunchOptions = field(default_factory=LaunchOptions)
    selected_target_server: str = "official"
    anti_blur_patch_dir: str = ""

    def save(self, path: Path = CONFIG_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "SwitcherConfig":
        if not path.is_file():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            launch_raw = raw.get("launch_options") or {}
            launch_opts = LaunchOptions(
                popupwindow=bool(launch_raw.get("popupwindow", False)),
                custom_resolution=bool(launch_raw.get("custom_resolution", False)),
                width=int(launch_raw.get("width", 1920)),
                height=int(launch_raw.get("height", 1080)),
                extra_args=str(launch_raw.get("extra_args", "")),
            )
            return cls(
                cn_game_root=str(raw.get("cn_game_root", "")),
                server_game_roots=dict(raw.get("server_game_roots") or {}),
                primary_pool_server=str(raw.get("primary_pool_server", "bilibili")),
                launch_options=launch_opts,
                selected_target_server=str(raw.get("selected_target_server", "official")),
                anti_blur_patch_dir=str(raw.get("anti_blur_patch_dir", "")),
            )
        except Exception:
            return cls()
