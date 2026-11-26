# 蓝色星原：旅谣 — 全服资源共享与切换器 | AzurPromilia-Server-Switcher

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-green.svg)](#)
[![Latest Release](https://img.shields.io/github/v/release/prover0721/AzurPromilia-Server-Switcher?color=brightgreen&label=Release)](https://github.com/prover0721/AzurPromilia-Server-Switcher/releases/latest)

> **《蓝色星原：旅谣》（Azur Promilia）PC 端全服资源共享与一键切换启动器。**  
> **Cross-server resource sharing & one-click server switcher for *Azur Promilia* (PC).**  
>
> 只要本机有一份完整游戏资源（约 95GB），即可实现 **官服 ↔ B服 零额外空间秒切**，以及 **日服 / 韩服 / 台服 / 国际服** 通过 **NTFS 硬链接** 共享通用大资源！同时支持作为独立软件运行与挂载至 `GameHub`。  
> With a single full installation (~95GB), you can **hot-switch between CN Official & Bilibili servers with zero extra disk usage**, and share heavy game assets across **JP / KR / TW / Global** clients via **NTFS hard links**. Works both standalone and as a `GameHub` plugin.

---

## ⚠️ 免责声明 / Disclaimer

> [!CAUTION]
> 1. **非官方工具 / Unofficial Tool**：本项目仅为技术学习与交流之目的开发的开源工具，与《蓝色星原：旅谣》（Azur Promilia）官方著作权人、开发商及各区服运营发行方（上海蛮啾网络、哔哩哔哩、Yostar、NEXON、NIJIGEN 等）无任何官方合作或关联。This is an unofficial open-source project for educational and technical exchange only, with no affiliation to Manjuu, Bilibili, Yostar, NEXON, NIJIGEN, or any official publisher.
> 2. **责任完全豁免 / No Warranty**：本工具按“现状”（AS-IS）提供，作者及贡献者不对任何因使用或滥用本工具造成的后果承担责任。**包括但不限于游戏账号封禁/异常、文件损坏、存档丢失或硬件故障等，由此产生的一切风险与损失均由使用者自行完全承担，与本项目作者无关。** Provided AS-IS without warranty; all risks (including account penalties, file corruption, or data loss) are borne solely by the user.
> 3. **关于“角色反虚化”扩展功能 / About Anti-Blur Feature**：该功能所涉及的方法**来源于网络整理**，与游戏官方及本工具作者无关，工具仅提供自动备份与一键还原辅助；使用该功能产生的一切风险由使用者自行承担。The anti-blur method is sourced from public community guides; this tool only automates local backup and restoration. Use at your own risk.
> 4. **知情同意 / Acceptance**：使用、下载或传播本项目的任何内容即视为已充分知悉并完全同意本免责声明。By using or distributing this project, you agree to all terms above.

---

## 📥 下载与安装 / Download & Installation

1. 前往本仓库右侧 **[Releases 最新发布页面](https://github.com/prover0721/AzurPromilia-Server-Switcher/releases/latest)**；  
   Visit the **[Releases page](https://github.com/prover0721/AzurPromilia-Server-Switcher/releases/latest)**;
2. 下载压缩包 **`AzurPromilia-Server-Switcher-v1.0.0.zip`** 并解压到任意文件夹（内含已内置好的**官服 / B服双服源**与启动器）；  
   Download **`AzurPromilia-Server-Switcher-v1.0.0.zip`** and extract it (includes pre-bundled CN Official & Bilibili channel sources);
3. 确保电脑已安装 Python 3.11+ 及 `PySide6`、`PySide6-Fluent-Widgets`（或置于 `GameHub` 同级目录共用 `.venv`）；  
   Ensure Python 3.11+ with `PySide6` and `PySide6-Fluent-Widgets` is installed;
4. 双击 **`AzurPromiliaSwitcher.exe`** 即可启动可视化界面。  
   Double-click **`AzurPromiliaSwitcher.exe`** to launch the GUI.

---

## 🛠️ 详细使用教程 / Usage Guide

### 一、 首次定位游戏目录 / 1. Locate Game Directory
- 打开 **`AzurPromiliaSwitcher.exe`**，程序会自动通过 Windows 注册表与常见盘符定位本机已安装的《蓝色星原》；  
  Launch **`AzurPromiliaSwitcher.exe`** — it auto-detects installations via the Windows registry, running processes, and common drive paths;
- 若未自动识别或需要切换其他目录，点击右上角 **「手动选择目录」**，选中游戏安装目录或 `AzurPromilia_Game` 目录即可。  
  Or click **Select Directory** in the top-right corner to pick your `AzurPromilia_Game` folder manually.

### 二、 官服 ↔ B服 零空间秒切 / 2. CN Official ↔ Bilibili Hot-Switch (Zero Extra Disk)
1. 下载 Releases 完整压缩包的用户已自带官/B 双服源（`官:已就绪 / B:已就绪`）；  
   *(若你是通过 `git clone` 获取源码，因 `libcef.dll` 超过 GitHub 100MB 限制未包含在 Git 仓库中，可自行用另一区服客户端点击一次「提取当前服源」，或从 Releases 补全 `assets/cn_sources/`)*。  
   The Release ZIP bundles both CN Official and Bilibili sources. (If cloning via Git, `assets/cn_sources/` is excluded due to GitHub's 100MB limit on `libcef.dll` — extract once from a client or copy from the Release ZIP.)
2. 在主界面点击目标卡片（**官服 (蛮啾)** 或 **B服 (哔哩哔哩)**）；  
   Select the target card (**Official** or **Bilibili**);
3. 点击 **「切换 / 同步至 XX」**，等待 1~2 秒完成渠道配置与登录组件热切换（**切服前请先关闭游戏**）；  
   Click **Switch / Sync** (make sure the game is closed first);
4. 点击 **「启动当前区服」** 即可直接进入游戏（已自动附带 `-start=azurpromilia_launcher` 参数，无需再经过官方启动器）。  
   Click **Launch Current Server** to start `AzurPromilia.exe` directly with `-start=azurpromilia_launcher`.

### 三、 日服 / 韩服 / 台服 / 国际服 跨区资源共享 / 3. JP / KR / TW / Global Hard-Link Sharing
1. **同盘符安装壳目录 / Install Lightweight Shell on Same Drive**：在与国服主目录**同一个磁盘分区**（例如都在 `D:\` 盘）下，使用左侧 **「下载渠道与教程」** 页面提供的官方链接下载对应外服启动器并安装基础本体（**无需下载 95GB 完整资源**）；  
   Install the target overseas client's base shell on the **same NTFS drive** as your main client (no need to download the full ~95GB assets);
2. **绑定壳目录 / Bind Shell Directory**：回到 **「启动与区服管理」** 页，点击对应外服卡片（如 **日服 (JP)**），再点右上角 **「手动选择目录」** 选中该外服目录；  
   Select the overseas server card (e.g. **JP**) and bind its directory;
3. **建立硬链接共享池 / Link Shared Assets**：点击 **「切换 / 同步至 日服」**，工具会通过 Windows NTFS 硬链接把 `StreamingAssets/.res` 与 `AzurPromilia_Data/.res` 中的通用大文件零空间占用地映射到外服目录；  
   Click **Switch / Sync** to NTFS hard-link heavy `.res` bundles with zero extra disk usage;
4. **增量补齐语言包 / Incremental Language Pack**：首次进入外服时，游戏会自动增量下载少量该服独有的语言文字包与差异资源；以后在各服之间来回切换均无需重复下载；  
   On first launch, the client only downloads its region-specific language/text delta; switching back and forth afterwards requires no re-downloads;
5. **大版本更新前提示 / Pre-Update Protection**：更新前建议点击 **「更新前解除硬链接」**，更新完成后再重新同步。  
   Before major game updates, click **Unlink Before Update** to break hard links safely, then re-sync afterwards.

### 四、 其他实用功能 / 4. Additional Features
- **角色反虚化 / Anti-Blur**：一键应用并自动备份官方原版（自动解除硬链接防串改），支持随时点击 **「还原官方原版」** 恢复。One-click apply with automatic backup and one-click restore.
- **常用目录直达 / Quick Folders**：一键打开游戏根目录、截图目录（`Pictures\LSXY_PHOTO`）、日志目录。Quick access to game root, screenshots, and logs.
- **启动参数与账号快照 / Launch Flags & Profile Snapshots**：支持 `-popupwindow`、自定义分辨率，以及保存/切换 `HKCU\Software\manjuu\AzurPromilia` 本地配置快照。Supports borderless window, custom resolution, and local registry profile snapshots.
- **CLI 命令行**：
  - `python main.py --scan` — 扫描本机游戏目录 / Scan local installations
  - `python main.py --server official --launch` — 切换并直启 / Switch server and launch
  - `python main.py --audit` — 硬链接体检 / Audit NTFS hard links & saved space

---

## 🧩 接入 GameHub / GameHub Plugin Integration

本项目 `plugin/` 目录遵循 `GameHub` 插件规范，可通过 Windows 目录联接直接挂载到 `GameHub\games\azur_promilia`，在 `GameHub` 内直接调用换服、扫描与硬链接体检任务。  
The `plugin/` folder implements `GameHub`'s plugin spec (`manifest.json` + `runner.py`) and can be mounted via a Windows Junction at `GameHub\games\azur_promilia`.

## 📄 开源许可证 / License

本项目采用 [MIT License](LICENSE) 授权许可。Licensed under the [MIT License](LICENSE).

## 项目交接与变更记录 / Handover & Changelog

- **2026-11-26 | v1.0.0 正式发布 & 中英双语文档**
  - 完善中英双语 README、MIT 许可证与多层级免责声明；发布包含内置官/B 双服源的 `v1.0.0` 发行包。
- **2026-11-26 | 原创启动器面板重构 & 内置反虚化扩展**
  - 重构为“顶部 Hero 横幅 + 区服矩阵 + 2×2 状态概览方格”原创仪表盘布局，支持自由缩放与切行自适应；内置角色反虚化与自动备份还原。
- **2026-11-26 | 初始化工程与核心框架搭建**
  - 建立独立可开源仓库，同时通过 `plugin/` 适配 `GameHub` 插件规范。
