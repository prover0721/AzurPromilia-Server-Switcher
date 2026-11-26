# -*- coding: utf-8 -*-
"""PySide6 + Fluent Widgets main window for AzurPromilia-Server-Switcher."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    FlowLayout,
    FluentIcon as FIF,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    SmoothScrollArea,
    SpinBox,
    StrongBodyLabel,
    SubtitleLabel,
    Theme,
    TitleLabel,
    setTheme,
    setThemeColor,
)

from core.account_profiles import apply_profile, list_profiles, save_profile
from core.anti_blur import (
    apply_anti_blur_patch,
    has_anti_blur_backup,
    is_builtin_anti_blur_ready,
    restore_anti_blur_backup,
)
from core.game_locator import discover_installations, inspect_installation
from core.launcher import launch_game, open_directory
from core.models import (
    APP_ICON_ICO,
    APP_ICON_PNG,
    GameInstallation,
    SERVER_CATALOG,
    SwitcherConfig,
)
from core.resource_pool import (
    audit_resource_links,
    extract_channel_source,
    get_backup_status,
    get_source_status,
    is_game_running,
    link_shared_resources,
    switch_cn_channel,
    unlink_to_independent,
)


DARK_STARRY_QSS = """
#switcherHome, #switcherGuide {
    background: transparent;
    border: none;
}
#switcherContainer {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #070d1a,
        stop: 0.5 #0d162b,
        stop: 1 #0a1222
    );
}
#heroBanner {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 rgba(23, 45, 84, 0.92),
        stop: 1 rgba(17, 28, 52, 0.92)
    );
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-radius: 14px;
}
#metricTile {
    background-color: rgba(15, 25, 46, 0.92);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 10px;
}
CardWidget {
    background-color: rgba(16, 26, 48, 0.90);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 12px;
}
TitleLabel, SubtitleLabel, StrongBodyLabel {
    color: #f1f5f9;
}
BodyLabel {
    color: #cbd5e1;
}
CaptionLabel {
    color: #94a3b8;
}
PlainTextEdit {
    background-color: rgba(8, 14, 28, 0.94);
    color: #cbd5e1;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 10px;
    padding: 8px;
    font-family: Consolas, "Microsoft YaHei UI", monospace;
    font-size: 12px;
}
"""


def _rounded_pixmap(path: Path, size: int = 60, radius: int = 14) -> QPixmap:
    src = QPixmap(str(path))
    if src.isNull():
        return QPixmap()
    scaled = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return out


class _WorkerSignals(QObject):
    log = Signal(str)
    finished = Signal(bool, str)
    audit_done = Signal(object)


class MetricTile(QFrame):
    """Compact 2x2 dashboard status tile."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metricTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        self.title_lbl = CaptionLabel(title, self)
        self.val_lbl = QLabel("-", self)
        self.val_lbl.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: 700;")
        self.sub_lbl = CaptionLabel("-", self)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)
        layout.addWidget(self.sub_lbl)

    def set_values(self, value: str, sub: str, color: str = "#38bdf8") -> None:
        self.val_lbl.setText(value)
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 700;")
        self.sub_lbl.setText(sub)


class ServerCard(CardWidget):
    """Clickable server selection card."""

    clicked_server = Signal(str)

    def __init__(self, server_id: str, parent=None):
        super().__init__(parent)
        self.server_id = server_id
        info = SERVER_CATALOG[server_id]
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(78)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.title_lbl = StrongBodyLabel(info["name"], self)
        self.badge_lbl = QLabel(info["badge"], self)
        self.badge_lbl.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.16); color: #7dd3fc; "
            "border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 6px; "
            "padding: 1px 7px; font-size: 11px; font-weight: 600;"
        )
        top_row.addWidget(self.title_lbl)
        top_row.addStretch(1)
        top_row.addWidget(self.badge_lbl)

        self.status_lbl = CaptionLabel("未配置", self)
        layout.addLayout(top_row)
        layout.addWidget(self.status_lbl)

        self._selected = False
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def set_status_text(self, text: str, active: bool = False) -> None:
        self.status_lbl.setText(text)
        if active:
            self.status_lbl.setStyleSheet("color: #38bdf8; font-weight: 600;")
        else:
            self.status_lbl.setStyleSheet("color: #94a3b8;")

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                "ServerCard { border: 2px solid #38bdf8; border-radius: 12px; "
                "background-color: rgba(24, 52, 88, 0.88); }"
            )
        else:
            self.setStyleSheet(
                "ServerCard { border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 12px; "
                "background-color: rgba(16, 26, 48, 0.85); }"
                "ServerCard:hover { border: 1px solid rgba(56, 189, 248, 0.45); }"
            )

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.clicked_server.emit(self.server_id)


class SwitcherMainWindow(FluentWindow):
    """Main Fluent GUI window with original launcher-dashboard layout."""

    def __init__(self):
        setTheme(Theme.DARK)
        setThemeColor("#38bdf8")
        super().__init__()

        self.setWindowTitle("蓝色星原：旅谣 — 全服资源共享与切换器")
        if APP_ICON_ICO.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON_ICO)))
        self.resize(1280, 880)
        self.setMinimumSize(620, 520)

        self.config = SwitcherConfig.load()
        self.installations: Dict[str, GameInstallation] = {}
        self.server_cards: Dict[str, ServerCard] = {}
        self.signals = _WorkerSignals()
        self.signals.log.connect(self._append_log)
        self.signals.finished.connect(self._on_worker_finished)
        self.signals.audit_done.connect(self._on_audit_done)

        self._build_ui()
        self.center_on_screen()
        self.refresh_detection(measure_size=False)

    def center_on_screen(self) -> None:
        """Center the window within the active screen's available geometry (excluding taskbar)."""
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        w = min(self.width(), max(640, geo.width() - 32))
        h = min(self.height(), max(480, geo.height() - 32))
        self.resize(w, h)
        cx = geo.x() + max(0, (geo.width() - w) // 2)
        cy = geo.y() + max(0, (geo.height() - h) // 2)
        self.move(cx, cy)

    def _build_ui(self) -> None:
        page = SmoothScrollArea(self)
        page.setObjectName("switcherHome")
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page.enableTransparentBackground()

        container = QWidget()
        container.setObjectName("switcherContainer")
        container.setStyleSheet(DARK_STARRY_QSS)
        page.setWidget(container)

        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(24, 18, 24, 16)
        root_layout.setSpacing(14)

        # Top Hero Banner
        hero = QFrame(container)
        hero.setObjectName("heroBanner")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 14, 18, 14)
        hero_layout.setSpacing(14)

        avatar_lbl = QLabel(hero)
        if APP_ICON_PNG.is_file():
            avatar_lbl.setPixmap(_rounded_pixmap(APP_ICON_PNG, size=58, radius=14))
        avatar_lbl.setFixedSize(58, 58)
        hero_layout.addWidget(avatar_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_top = QHBoxLayout()
        title_top.setSpacing(10)
        title_top.addWidget(TitleLabel("蓝色星原：旅谣", hero))
        self.hero_badge = QLabel("未定位", hero)
        self.hero_badge.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.18); color: #7dd3fc; "
            "border: 1px solid rgba(56, 189, 248, 0.40); border-radius: 8px; "
            "padding: 2px 10px; font-size: 12px; font-weight: 700;"
        )
        title_top.addWidget(self.hero_badge)
        title_top.addStretch(1)
        title_col.addLayout(title_top)
        hero_sub = CaptionLabel("全服资源共享与多端切换启动器 · 支持 官服 / B服 / 日服 / 韩服 / 台服 / 国际服", hero)
        hero_sub.setWordWrap(True)
        title_col.addWidget(hero_sub)
        hero_layout.addLayout(title_col, 1)

        self.btn_scan = PushButton(FIF.SYNC, "自动定位游戏", hero)
        self.btn_scan.clicked.connect(lambda: self.refresh_detection(measure_size=True))
        self.btn_pick_dir = PushButton(FIF.FOLDER, "手动选择目录", hero)
        self.btn_pick_dir.clicked.connect(self._pick_game_directory)
        hero_layout.addWidget(self.btn_scan)
        hero_layout.addWidget(self.btn_pick_dir)
        root_layout.addWidget(hero)

        # Body 2-column responsive dashboard (switches to stacked when narrow)
        self.body_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.body_row.setSpacing(16)

        # Left column: Server matrix + primary actions + paths + launch options
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        left_col.addWidget(SubtitleLabel("区服选择与共享池", container))
        grid = QGridLayout()
        grid.setSpacing(10)
        for idx, sid in enumerate(SERVER_CATALOG.keys()):
            card = ServerCard(sid, container)
            card.clicked_server.connect(self._on_select_server)
            self.server_cards[sid] = card
            grid.addWidget(card, idx // 3, idx % 3)
        left_col.addLayout(grid)

        # Action bar (distinct launcher semantics)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.btn_launch_current = PrimaryPushButton(FIF.PLAY, "启动当前区服", container)
        self.btn_launch_current.setMinimumHeight(42)
        self.btn_launch_current.clicked.connect(self._launch_current_server)
        self.btn_switch_sync = PushButton(FIF.SYNC, "切换 / 同步资源", container)
        self.btn_switch_sync.setMinimumHeight(42)
        self.btn_switch_sync.clicked.connect(self._switch_or_sync_target)
        self.btn_extract = PushButton(FIF.SAVE, "提取当前服源", container)
        self.btn_extract.setMinimumHeight(42)
        self.btn_extract.clicked.connect(self._extract_current_source)
        action_row.addWidget(self.btn_launch_current, 2)
        action_row.addWidget(self.btn_switch_sync, 2)
        action_row.addWidget(self.btn_extract, 1)
        left_col.addLayout(action_row)

        # Directory & quick links card
        info_card = CardWidget(container)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(5)
        self.lbl_active_server = StrongBodyLabel("当前主目录: 未定位", info_card)
        self.lbl_active_server.setWordWrap(True)
        self.lbl_install_dir = CaptionLabel("安装目录: -", info_card)
        self.lbl_install_dir.setWordWrap(True)
        self.lbl_game_dir = CaptionLabel("游戏根目录: -", info_card)
        self.lbl_game_dir.setWordWrap(True)
        self.lbl_version = CaptionLabel("游戏版本: -", info_card)
        self.lbl_version.setWordWrap(True)
        info_layout.addWidget(self.lbl_active_server)
        info_layout.addWidget(self.lbl_install_dir)
        info_layout.addWidget(self.lbl_game_dir)
        info_layout.addWidget(self.lbl_version)

        dir_btns = FlowLayout(needAni=False)
        dir_btns.setContentsMargins(0, 4, 0, 0)
        dir_btns.setHorizontalSpacing(8)
        dir_btns.setVerticalSpacing(6)
        self.btn_open_game = PushButton(FIF.FOLDER, "游戏根目录", info_card)
        self.btn_open_game.clicked.connect(self._open_game_root)
        self.btn_open_shots = PushButton(FIF.PHOTO, "截图目录", info_card)
        self.btn_open_shots.clicked.connect(lambda: self._open_indexed_dir("screenshot"))
        self.btn_open_logs = PushButton(FIF.DOCUMENT, "日志目录", info_card)
        self.btn_open_logs.clicked.connect(lambda: self._open_indexed_dir("gameLog"))
        dir_btns.addWidget(self.btn_open_game)
        dir_btns.addWidget(self.btn_open_shots)
        dir_btns.addWidget(self.btn_open_logs)
        info_layout.addLayout(dir_btns)
        left_col.addWidget(info_card)

        # Launch options & Profiles card
        opts_card = CardWidget(container)
        opts_layout = QVBoxLayout(opts_card)
        opts_layout.setContentsMargins(16, 12, 16, 12)
        opts_layout.setSpacing(8)
        opts_layout.addWidget(StrongBodyLabel("启动参数与本地账号快照", opts_card))

        launch_row = FlowLayout(needAni=False)
        launch_row.setContentsMargins(0, 0, 0, 0)
        launch_row.setHorizontalSpacing(8)
        launch_row.setVerticalSpacing(6)
        self.chk_popup = CheckBox("无边框窗口", opts_card)
        self.chk_popup.setChecked(self.config.launch_options.popupwindow)
        self.chk_res = CheckBox("指定分辨率", opts_card)
        self.chk_res.setChecked(self.config.launch_options.custom_resolution)
        self.spin_w = SpinBox(opts_card)
        self.spin_w.setRange(800, 7680)
        self.spin_w.setMinimumWidth(145)
        self.spin_w.setValue(self.config.launch_options.width)
        self.spin_h = SpinBox(opts_card)
        self.spin_h.setRange(600, 4320)
        self.spin_h.setMinimumWidth(145)
        self.spin_h.setValue(self.config.launch_options.height)
        launch_row.addWidget(self.chk_popup)
        launch_row.addWidget(self.chk_res)
        launch_row.addWidget(self.spin_w)
        launch_row.addWidget(CaptionLabel("×", opts_card))
        launch_row.addWidget(self.spin_h)
        opts_layout.addLayout(launch_row)

        prof_row = FlowLayout(needAni=False)
        prof_row.setContentsMargins(0, 0, 0, 0)
        prof_row.setHorizontalSpacing(8)
        prof_row.setVerticalSpacing(6)
        self.combo_profiles = ComboBox(opts_card)
        self.combo_profiles.setMinimumWidth(160)
        self.btn_save_prof = PushButton(FIF.ADD, "保存当前号快照", opts_card)
        self.btn_save_prof.clicked.connect(self._save_profile_snapshot)
        self.btn_apply_prof = PushButton(FIF.SYNC, "应用快照", opts_card)
        self.btn_apply_prof.clicked.connect(self._apply_profile_snapshot)
        prof_row.addWidget(CaptionLabel("账号快照:", opts_card))
        prof_row.addWidget(self.combo_profiles)
        prof_row.addWidget(self.btn_save_prof)
        prof_row.addWidget(self.btn_apply_prof)
        opts_layout.addLayout(prof_row)
        left_col.addWidget(opts_card)

        self.body_row.addLayout(left_col, 3)

        # Right column: 2x2 Status tiles + Anti-blur (built-in) + Hardlink tools + Logs
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        right_col.addWidget(SubtitleLabel("状态概览与工具箱", container))
        tiles_grid = QGridLayout()
        tiles_grid.setSpacing(10)
        self.tile_server = MetricTile("当前激活区服", container)
        self.tile_sources = MetricTile("国服渠道源 / 备份", container)
        self.tile_savings = MetricTile("共享池节省空间", container)
        self.tile_runtime = MetricTile("客户端运行状态", container)
        tiles_grid.addWidget(self.tile_server, 0, 0)
        tiles_grid.addWidget(self.tile_sources, 0, 1)
        tiles_grid.addWidget(self.tile_savings, 1, 0)
        tiles_grid.addWidget(self.tile_runtime, 1, 1)
        right_col.addLayout(tiles_grid)

        # Hardlink maintenance row
        link_card = CardWidget(container)
        link_layout = QHBoxLayout(link_card)
        link_layout.setContentsMargins(14, 10, 14, 10)
        link_layout.setSpacing(10)
        self.btn_audit = PushButton(FIF.SEARCH, "硬链接体检", link_card)
        self.btn_audit.clicked.connect(self._run_audit)
        self.btn_unlink = PushButton(FIF.BROOM, "更新前解除硬链接", link_card)
        self.btn_unlink.clicked.connect(self._unlink_target)
        link_layout.addWidget(self.btn_audit, 1)
        link_layout.addWidget(self.btn_unlink, 1)
        right_col.addWidget(link_card)

        # Built-in Anti-blur card (only Apply & Restore)
        blur_card = CardWidget(container)
        blur_layout = QVBoxLayout(blur_card)
        blur_layout.setContentsMargins(14, 12, 14, 12)
        blur_layout.setSpacing(8)
        blur_header = QHBoxLayout()
        blur_header.addWidget(StrongBodyLabel("角色反虚化", blur_card))
        blur_header.addStretch(1)
        self.lbl_blur_backup = QLabel("未备份原版", blur_card)
        self.lbl_blur_backup.setStyleSheet("color: #94a3b8; font-size: 12px;")
        blur_header.addWidget(self.lbl_blur_backup)
        blur_layout.addLayout(blur_header)

        blur_btns = QHBoxLayout()
        self.btn_apply_blur = PrimaryPushButton(FIF.CHECKBOX, "应用反虚化", blur_card)
        self.btn_apply_blur.clicked.connect(self._apply_anti_blur)
        self.btn_restore_blur = PushButton(FIF.HISTORY, "还原官方原版", blur_card)
        self.btn_restore_blur.clicked.connect(self._restore_anti_blur)
        blur_btns.addWidget(self.btn_apply_blur, 1)
        blur_btns.addWidget(self.btn_restore_blur, 1)
        blur_layout.addLayout(blur_btns)

        blur_warn = QLabel("⚠ 声明：内置反虚化方法来源于网络整理，与游戏官方及本工具无关，使用风险由使用者自行承担。", blur_card)
        blur_warn.setStyleSheet("color: #fbbf24; font-size: 11px;")
        blur_warn.setWordWrap(True)
        blur_layout.addWidget(blur_warn)
        right_col.addWidget(blur_card)

        self.log_box = PlainTextEdit(container)
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(PlainTextEdit.LineWrapMode.WidgetWidth)
        self.log_box.setPlaceholderText("操作日志将显示在这里...")
        self.log_box.setMinimumHeight(210)
        right_col.addWidget(self.log_box, 1)

        self.body_row.addLayout(right_col, 2)
        root_layout.addLayout(self.body_row)

        footer = CaptionLabel("个人开源制作 · 与游戏官方无关 | 仅作本地文件级资源链接与配置备份，请勿在游戏运行时切换", container)
        footer.setWordWrap(True)
        root_layout.addWidget(footer)

        self.addSubInterface(page, FIF.GAME, "启动与区服管理")
        self.addSubInterface(self._build_guide_page(), FIF.GLOBE, "下载渠道与教程")
        self.navigationInterface.setCollapsible(True)
        self._on_select_server(self.config.selected_target_server)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "body_row"):
            want_dir = (
                QBoxLayout.Direction.TopToBottom
                if self.width() < 980
                else QBoxLayout.Direction.LeftToRight
            )
            if self.body_row.direction() != want_dir:
                self.body_row.setDirection(want_dir)

    def _build_guide_page(self) -> SmoothScrollArea:
        guide_page = SmoothScrollArea(self)
        guide_page.setObjectName("switcherGuide")
        guide_page.setWidgetResizable(True)
        guide_page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        guide_page.enableTransparentBackground()

        wrap = QWidget()
        wrap.setObjectName("switcherContainer")
        wrap.setStyleSheet(DARK_STARRY_QSS)
        guide_page.setWidget(wrap)

        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(TitleLabel("各区服官方下载渠道与使用教程", wrap))
        layout.addWidget(CaptionLabel("请从以下官方渠道下载对应区服的 PC 启动器（切勿下载第三方不明安装包）", wrap))

        channels = [
            ("国服官方（蛮啾通行证）", "https://azurpromilia.manjuu.com/", "大陆官服 PC 客户端下载"),
            ("B服（哔哩哔哩游戏中心）", "https://game.bilibili.com/", "B 站渠道服 PC 客户端下载"),
            ("日服 (JP · Yostar)", "https://azurpromilia.jp/PCdownload", "日服官方 PC 启动器直链"),
            ("韩服 (KR · NEXON)", "https://azurpromilia.nexon.com/support/download", "韩服官方 PC 启动器下载"),
            ("台港澳服 (TW · NIJIGEN)", "https://azurpromilia.jimi-global.com/", "台港澳繁体中文官网"),
        ]
        dl_card = CardWidget(wrap)
        dl_layout = QVBoxLayout(dl_card)
        dl_layout.setContentsMargins(16, 14, 16, 14)
        dl_layout.setSpacing(10)
        dl_layout.addWidget(SubtitleLabel("官方下载入口", dl_card))

        for title, url, desc in channels:
            row = QHBoxLayout()
            col = QVBoxLayout()
            col.setSpacing(2)
            t_lbl = StrongBodyLabel(title, dl_card)
            d_lbl = CaptionLabel(f"{desc}  |  {url}", dl_card)
            d_lbl.setWordWrap(True)
            col.addWidget(t_lbl)
            col.addWidget(d_lbl)
            row.addLayout(col, 1)
            btn = PushButton(FIF.LINK, "打开官网", dl_card)
            btn.setFixedWidth(116)
            btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            row.addWidget(btn)
            dl_layout.addLayout(row)
        layout.addWidget(dl_card)

        tut_cn = CardWidget(wrap)
        tut_cn_l = QVBoxLayout(tut_cn)
        tut_cn_l.setContentsMargins(16, 14, 16, 14)
        tut_cn_l.setSpacing(6)
        tut_cn_l.addWidget(SubtitleLabel("教程一：官服 ↔ B服 零额外空间秒切", tut_cn))
        tut_cn_body = BodyLabel(
            "1. 准备主目录：确保电脑上已安装并下好一份完整国服（官服或 B服 均可）。\n"
            "2. 首次缓存渠道源：若尚未内置另一方渠道源，只需用其启动器下载基础小文件（无需下 95GB），"
            "在“启动与区服管理”页点击「手动选择目录」选中它并点「提取当前服源」，之后即可删除临时目录。\n"
            "3. 秒级互切：选中目标卡片（官服 / B服）→ 点「切换 / 同步资源」→ 点「启动当前区服」。",
            tut_cn,
        )
        tut_cn_body.setWordWrap(True)
        tut_cn_l.addWidget(tut_cn_body)
        layout.addWidget(tut_cn)

        tut_os = CardWidget(wrap)
        tut_os_l = QVBoxLayout(tut_os)
        tut_os_l.setContentsMargins(16, 14, 16, 14)
        tut_os_l.setSpacing(6)
        tut_os_l.addWidget(SubtitleLabel("教程二：日服 / 韩服 / 台服 跨区资源共享（省 95GB 硬盘）", tut_os))
        tut_os_body = BodyLabel(
            "1. 同盘符安装壳目录：在与国服主目录相同的磁盘分区（例如都在 D:\\ 盘）下，用外服官方启动器安装基础客户端（无需在游戏内下载几十 GB 大资源）。\n"
            "2. 绑定壳目录：回到主界面，点击对应外服卡片（如「日服 (JP)」），点击右上角「手动选择目录」选中该外服目录。\n"
            "3. 建立 NTFS 硬链接共享池：点击「切换 / 同步至 日服」，工具会自动将国服通用大资源零空间占用地链接过去。\n"
            "4. 增量补齐语言包：启动外服后，游戏仅需自动下载少量该服独有的语言文字与差异资源；以后来回切换无需重复下载。\n"
            "5. 大版本更新前建议：在右侧点击「更新前解除硬链接」，更新完毕后再重新同步即可。",
            tut_os,
        )
        tut_os_body.setWordWrap(True)
        tut_os_l.addWidget(tut_os_body)
        layout.addWidget(tut_os)
        layout.addStretch(1)
        return guide_page

    def _append_log(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)

    def _on_select_server(self, server_id: str) -> None:
        if server_id not in SERVER_CATALOG:
            server_id = "official"
        self.config.selected_target_server = server_id
        for sid, card in self.server_cards.items():
            card.set_selected(sid == server_id)
        name = SERVER_CATALOG[server_id]["short"]
        self.btn_switch_sync.setText(f"切换 / 同步至 {name}")
        self._refresh_profile_combo()

    def _active_cn_installation(self) -> Optional[GameInstallation]:
        if self.config.cn_game_root and self.config.cn_game_root in self.installations:
            return self.installations[self.config.cn_game_root]
        for inst in self.installations.values():
            if inst.detected_server in ("official", "bilibili"):
                return inst
        return next(iter(self.installations.values()), None)

    def _get_target_installation(self, server_id: str) -> Optional[GameInstallation]:
        saved = self.config.server_game_roots.get(server_id, "")
        if saved and saved in self.installations:
            return self.installations[saved]
        if server_id in ("official", "bilibili"):
            return self._active_cn_installation()
        return None

    def refresh_detection(self, measure_size: bool = False) -> None:
        saved_paths = [self.config.cn_game_root] + list(self.config.server_game_roots.values())
        found = discover_installations(extra_paths=saved_paths, measure_size=measure_size)
        self.installations = {inst.game_root: inst for inst in found}

        for inst in found:
            if inst.detected_server in ("official", "bilibili") and not self.config.cn_game_root:
                self.config.cn_game_root = inst.game_root
            if inst.detected_server in SERVER_CATALOG and inst.detected_server not in self.config.server_game_roots:
                self.config.server_game_roots[inst.detected_server] = inst.game_root
        self.config.save()

        cn_inst = self._active_cn_installation()
        if cn_inst:
            self.hero_badge.setText(cn_inst.server_display_name)
            self.lbl_active_server.setText(f"当前主目录区服: {cn_inst.server_display_name}")
            self.lbl_install_dir.setText(f"安装目录: {cn_inst.install_root}")
            self.lbl_game_dir.setText(f"游戏根目录: {cn_inst.game_root}")
            size_str = f" | 资源体积: {cn_inst.total_res_gb} GB" if measure_size else ""
            self.lbl_version.setText(f"版本: {cn_inst.version} ({cn_inst.source_tag}){size_str}")
            sdk_txt = "BLPlatform64 (B服)" if cn_inst.has_bl_platform else ("PCGameSDK" if cn_inst.has_sdk_dll else "未检测")
            self.tile_server.set_values(cn_inst.server_display_name, f"SDK: {sdk_txt}", "#38bdf8")
            self.btn_launch_current.setText(f"启动当前区服 ({SERVER_CATALOG.get(cn_inst.detected_server, {}).get('short', '游戏')})")
        else:
            self.hero_badge.setText("未定位")
            self.lbl_active_server.setText("未检测到本地游戏目录，请点击右上角手动选择")
            self.tile_server.set_values("未定位", "请手动选择目录", "#fbbf24")
            self.btn_launch_current.setText("启动当前区服")

        off_src = "已就绪" if get_source_status("official") else "待导入"
        bili_src = "已就绪" if get_source_status("bilibili") else "待导入"
        off_bak = "有备份" if get_backup_status("official") else "无备份"
        bili_bak = "有备份" if get_backup_status("bilibili") else "无备份"
        self.tile_sources.set_values(
            f"官:{off_src} / B:{bili_src}",
            f"备份 官:{off_bak} | B:{bili_bak}",
            "#34d399" if (get_source_status("official") and get_source_status("bilibili")) else "#fbbf24",
        )

        running = is_game_running()
        self.tile_runtime.set_values(
            "运行中" if running else "空闲可切换",
            "请勿在运行中切服" if running else "未检测到游戏进程",
            "#fbbf24" if running else "#34d399",
        )
        if not self.tile_savings.val_lbl.text() or self.tile_savings.val_lbl.text() == "-":
            self.tile_savings.set_values("待体检", "点击下方硬链接体检", "#94a3b8")

        if has_anti_blur_backup():
            self.lbl_blur_backup.setText("已备份原版 (可还原)")
            self.lbl_blur_backup.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 600;")
        else:
            self.lbl_blur_backup.setText("内置就绪" if is_builtin_anti_blur_ready() else "未就绪")
            self.lbl_blur_backup.setStyleSheet("color: #94a3b8; font-size: 12px;")

        for sid, card in self.server_cards.items():
            if sid in ("official", "bilibili"):
                if cn_inst and cn_inst.detected_server == sid:
                    card.set_status_text("当前激活", active=True)
                elif get_source_status(sid):
                    card.set_status_text("源已就绪（秒切）", active=True)
                else:
                    card.set_status_text("待导入一次源")
            else:
                if sid in self.config.server_game_roots and Path(self.config.server_game_roots[sid]).is_dir():
                    card.set_status_text("壳目录已绑定", active=True)
                else:
                    card.set_status_text("未绑定壳目录")

        self._refresh_profile_combo()

    def _pick_game_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择《蓝色星原》安装目录或 AzurPromilia_Game 目录")
        if not folder:
            return
        inst = inspect_installation(Path(folder), source_tag="manual", measure_size=True)
        if not inst:
            InfoBar.error("无效目录", "未在该目录下找到 AzurPromilia.exe", parent=self, position=InfoBarPosition.TOP)
            return
        target_sid = self.config.selected_target_server
        if inst.detected_server in ("official", "bilibili"):
            self.config.cn_game_root = inst.game_root
            self.config.server_game_roots[inst.detected_server] = inst.game_root
        else:
            self.config.server_game_roots[target_sid] = inst.game_root
        self.config.save()
        self.refresh_detection(measure_size=True)
        self._append_log(f"[+] 已绑定目录 ({inst.server_display_name}): {inst.game_root}")

    def _apply_anti_blur(self) -> None:
        inst = self._active_cn_installation()
        if not inst:
            InfoBar.warning("提示", "请先定位游戏目录", parent=self, position=InfoBarPosition.TOP)
            return
        try:
            replaced, _ = apply_anti_blur_patch(Path(inst.game_root), log=self._append_log)
            self.refresh_detection(measure_size=False)
            InfoBar.success("反虚化已生效", f"已替换 {replaced} 个文件并自动备份原版", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("应用失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def _restore_anti_blur(self) -> None:
        inst = self._active_cn_installation()
        if not inst:
            InfoBar.warning("提示", "请先定位游戏目录", parent=self, position=InfoBarPosition.TOP)
            return
        try:
            restored = restore_anti_blur_backup(Path(inst.game_root), log=self._append_log)
            InfoBar.success("已还原原版", f"已恢复 {restored} 个官方原始文件", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("还原失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def _extract_current_source(self) -> None:
        inst = self._active_cn_installation()
        if not inst:
            InfoBar.warning("提示", "请先定位游戏目录", parent=self, position=InfoBarPosition.TOP)
            return
        sid = inst.detected_server if inst.detected_server in ("official", "bilibili") else self.config.selected_target_server
        try:
            extract_channel_source(Path(inst.game_root), sid, log=self._append_log)
            self.refresh_detection(measure_size=False)
            InfoBar.success("提取成功", f"已缓存 [{SERVER_CATALOG.get(sid, {}).get('short', sid)}] 渠道源", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("提取失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def _save_launch_options(self) -> None:
        self.config.launch_options.popupwindow = self.chk_popup.isChecked()
        self.config.launch_options.custom_resolution = self.chk_res.isChecked()
        self.config.launch_options.width = self.spin_w.value()
        self.config.launch_options.height = self.spin_h.value()
        self.config.save()

    def _launch_current_server(self) -> None:
        self._save_launch_options()
        target = self.config.selected_target_server
        inst = self._get_target_installation(target) or self._active_cn_installation()
        if not inst:
            InfoBar.warning("未定位目录", "请先自动定位或手动选择《蓝色星原》游戏目录", parent=self, position=InfoBarPosition.TOP)
            return
        try:
            launch_game(Path(inst.game_root), self.config.launch_options)
            self._append_log(f"[▶] 已启动 {inst.server_display_name}: {inst.game_root}\\AzurPromilia.exe")
            InfoBar.success("已启动", f"正在启动 {inst.server_display_name}", parent=self, position=InfoBarPosition.TOP)
        except Exception as exc:
            InfoBar.error("启动失败", str(exc), parent=self, position=InfoBarPosition.TOP)

    def _switch_or_sync_target(self) -> None:
        self._save_launch_options()
        target = self.config.selected_target_server
        cn_inst = self._active_cn_installation()
        if not cn_inst:
            InfoBar.warning("未定位目录", "请先自动定位或手动选择《蓝色星原》游戏目录", parent=self, position=InfoBarPosition.TOP)
            return

        def _worker():
            try:
                if target in ("official", "bilibili"):
                    game_root = Path(cn_inst.game_root)
                    switch_cn_channel(
                        game_root,
                        cn_inst.detected_server,
                        target,
                        log=self.signals.log.emit,
                    )
                else:
                    shell_path = self.config.server_game_roots.get(target, "")
                    if not shell_path or not Path(shell_path).is_dir():
                        raise FileNotFoundError(
                            f"尚未绑定 [{SERVER_CATALOG[target]['short']}] 壳目录。请先选中该卡片并点击右上角“手动选择目录”绑定。"
                        )
                    link_shared_resources(Path(cn_inst.game_root), Path(shell_path), log=self.signals.log.emit)
                self.signals.finished.emit(True, f"已完成 {SERVER_CATALOG[target]['short']} 切换 / 同步")
            except Exception as exc:
                self.signals.finished.emit(False, str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_worker_finished(self, ok: bool, message: str) -> None:
        self.refresh_detection(measure_size=False)
        if ok:
            InfoBar.success("完成", message, parent=self, position=InfoBarPosition.TOP)
        else:
            self._append_log(f"[!] {message}")
            InfoBar.error("操作提示", message, parent=self, position=InfoBarPosition.TOP, duration=5000)

    def _run_audit(self) -> None:
        roots = [Path(p) for p in self.installations.keys()]
        if not roots:
            return
        self._append_log("[*] 正在扫描 NTFS 硬链接与物理空间占用，请稍候...")

        def _worker():
            res = audit_resource_links(roots)
            self.signals.audit_done.emit(res)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_audit_done(self, res) -> None:
        self.tile_savings.set_values(f"{res.saved_gb} GB", f"硬链接 {res.linked_files}/{res.total_files} 个", "#34d399")
        self._append_log(
            f"[√] 体检完成：总文件 {res.total_files} 个 | 硬链接 {res.linked_files} 个 | 逻辑总计 {res.logical_gb} GB | 已节省 {res.saved_gb} GB"
        )

    def _unlink_target(self) -> None:
        target = self.config.selected_target_server
        inst = self._get_target_installation(target)
        if not inst:
            InfoBar.warning("提示", "当前区服未绑定目录", parent=self, position=InfoBarPosition.TOP)
            return
        try:
            cnt = unlink_to_independent(Path(inst.game_root), log=self._append_log)
            InfoBar.success("已解除", f"已将 {cnt} 个硬链接恢复为独立文件", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def _open_game_root(self) -> None:
        inst = self._active_cn_installation()
        if inst:
            open_directory(Path(inst.game_root))

    def _open_indexed_dir(self, key: str) -> None:
        inst = self._active_cn_installation()
        if not inst or key not in inst.paths_index:
            InfoBar.warning("提示", "未在 _index/paths 中找到该目录", parent=self, position=InfoBarPosition.TOP)
            return
        p = Path(inst.paths_index[key])
        if not p.exists():
            InfoBar.warning("提示", f"目录尚未生成: {p}", parent=self, position=InfoBarPosition.TOP)
            return
        open_directory(p)

    def _refresh_profile_combo(self) -> None:
        sid = self.config.selected_target_server
        self.combo_profiles.clear()
        items = list_profiles(sid)
        self.combo_profiles.addItems(items if items else ["(暂无快照)"])

    def _save_profile_snapshot(self) -> None:
        sid = self.config.selected_target_server
        existing = list_profiles(sid)
        name = f"account_{len(existing) + 1}"
        try:
            out = save_profile(sid, name)
            self._refresh_profile_combo()
            self._append_log(f"[+] 已保存 [{sid}] 配置快照: {out.name}")
            InfoBar.success("已保存", f"快照 {name} 已创建", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("保存失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def _apply_profile_snapshot(self) -> None:
        sid = self.config.selected_target_server
        name = self.combo_profiles.currentText()
        if not name or name == "(暂无快照)":
            return
        try:
            apply_profile(sid, name)
            self._append_log(f"[√] 已应用 [{sid}] 配置快照: {name}")
            InfoBar.success("已应用", f"已切换至快照 {name}", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("应用失败", str(e), parent=self, position=InfoBarPosition.TOP)
