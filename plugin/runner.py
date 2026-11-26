# -*- coding: utf-8 -*-
"""GameHub plugin runner for AzurPromilia-Server-Switcher."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SWITCHER_ROOT = Path(__file__).resolve().parent.parent
if str(SWITCHER_ROOT) not in sys.path:
    sys.path.insert(0, str(SWITCHER_ROOT))

from core.game_locator import discover_installations
from core.launcher import launch_game
from core.models import SwitcherConfig
from core.resource_pool import audit_resource_links, switch_cn_channel


def run_task(task_id: str, config: dict, log_func, is_stopped_func) -> bool:
    """Execute a GameHub task by delegating to AzurPromilia-Server-Switcher core."""
    if is_stopped_func():
        log_func("[!] 用户中止", "warning")
        return False

    if task_id == "open_switcher_gui":
        main_py = SWITCHER_ROOT / "main.py"
        subprocess.Popen([sys.executable, str(main_py)], cwd=str(SWITCHER_ROOT))
        log_func("[+] 已启动《蓝色星原》可视化换服器窗口", "success")
        return True

    sw_cfg = SwitcherConfig.load()
    saved = [sw_cfg.cn_game_root] + list(sw_cfg.server_game_roots.values())
    found = discover_installations(extra_paths=saved, measure_size=(task_id == "scan_installations"))

    if not found:
        log_func("[!] 未检测到本机《蓝色星原》游戏目录，请先打开换服器界面手动选择。", "error")
        return False

    if task_id == "scan_installations":
        for inst in found:
            log_func(
                f"[*] [{inst.server_display_name}] 版本={inst.version} | 体积={inst.total_res_gb}GB | {inst.game_root}",
                "info",
            )
        return True

    if task_id == "audit_hardlinks":
        res = audit_resource_links([Path(i.game_root) for i in found])
        log_func(
            f"[√] 总文件 {res.total_files} | 硬链接 {res.linked_files} | 逻辑 {res.logical_gb}GB | 已节省 {res.saved_gb}GB",
            "success",
        )
        return True

    if task_id in ("switch_official_launch", "switch_bilibili_launch"):
        target = "official" if task_id == "switch_official_launch" else "bilibili"
        cn_inst = next((i for i in found if i.detected_server in ("official", "bilibili")), None)
        if not cn_inst:
            log_func("[!] 未找到国服主目录。", "error")
            return False
        game_root = Path(cn_inst.game_root)
        try:
            switch_cn_channel(
                game_root,
                cn_inst.detected_server,
                target,
                log=lambda m: log_func(m, "info"),
            )
            if config.get("auto_launch", True):
                launch_game(game_root, sw_cfg.launch_options)
                log_func(f"[▶] 已切换并启动 {target}", "success")
            return True
        except Exception as exc:
            log_func(f"[!] 操作失败: {exc}", "error")
            return False

    log_func(f"[!] 未知任务: {task_id}", "warning")
    return False
