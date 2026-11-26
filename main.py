# -*- coding: utf-8 -*-
"""CLI and GUI entrypoint for AzurPromilia-Server-Switcher."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.game_locator import discover_installations
from core.launcher import launch_game
from core.models import SERVER_CATALOG, SwitcherConfig
from core.resource_pool import (
    audit_resource_links,
    extract_channel_source,
    link_shared_resources,
    switch_cn_channel,
)


def _run_cli(args: argparse.Namespace) -> int:
    cfg = SwitcherConfig.load()
    saved = [cfg.cn_game_root] + list(cfg.server_game_roots.values())
    found = discover_installations(extra_paths=saved, measure_size=args.scan)

    if args.scan:
        if not found:
            print("[!] 未检测到本地《蓝色星原》游戏目录。")
            return 1
        for inst in found:
            print(
                f"- [{inst.server_display_name}] 版本={inst.version} | 来源={inst.source_tag} | "
                f"资源={inst.total_res_gb}GB | 路径={inst.game_root}"
            )
        return 0

    if args.extract:
        if not found:
            print("[!] 未检测到游戏目录。")
            return 1
        extract_channel_source(Path(found[0].game_root), args.extract, log=print)
        return 0

    if args.audit:
        res = audit_resource_links([Path(i.game_root) for i in found])
        print(
            f"总文件={res.total_files}, 硬链接={res.linked_files}, "
            f"逻辑={res.logical_gb}GB, 已节省={res.saved_gb}GB"
        )
        return 0

    if args.server:
        target = args.server
        if target not in SERVER_CATALOG:
            print(f"[!] 未知区服: {target}，可选: {', '.join(SERVER_CATALOG.keys())}")
            return 1
        cn_inst = next((i for i in found if i.detected_server in ("official", "bilibili")), None)
        if not cn_inst:
            print("[!] 未定位到国服主目录，请先打开界面手动选择目录。")
            return 1

        if target in ("official", "bilibili"):
            if cn_inst.detected_server != target:
                switch_cn_channel(Path(cn_inst.game_root), cn_inst.detected_server, target, log=print)
            launch_root = Path(cn_inst.game_root)
        else:
            shell = cfg.server_game_roots.get(target, "")
            if not shell or not Path(shell).is_dir():
                print(f"[!] 尚未绑定 [{target}] 壳目录。")
                return 1
            launch_root = Path(shell)
            link_shared_resources(Path(cn_inst.game_root), launch_root, log=print)

        if args.launch:
            launch_game(launch_root, cfg.launch_options)
            print(f"[▶] 已启动 {SERVER_CATALOG[target]['short']}")
        return 0

    return -1


def main() -> int:
    parser = argparse.ArgumentParser(description="蓝色星原：旅谣 — 全服资源共享与切换器")
    parser.add_argument("--scan", action="store_true", help="扫描并打印本机检测到的游戏目录")
    parser.add_argument("--server", type=str, help="切换到指定区服 (official/bilibili/jp/kr/tw/en)")
    parser.add_argument("--launch", action="store_true", help="切换后直接启动游戏")
    parser.add_argument("--extract", type=str, help="从当前游戏目录提取指定区服渠道源")
    parser.add_argument("--audit", action="store_true", help="执行 NTFS 硬链接健康检查")
    args = parser.parse_args()

    cli_rc = _run_cli(args)
    if cli_rc >= 0:
        return cli_rc

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from core.models import APP_ICON_ICO
    from ui.main_window import SwitcherMainWindow

    app = QApplication(sys.argv)
    if APP_ICON_ICO.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON_ICO)))
    win = SwitcherMainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
