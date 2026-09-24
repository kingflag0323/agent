# Third-party software notices

**Scope:** Sentinel Workbench 0.2 uses Electron + React and a non-Qt Python sidecar. The combined distribution includes adapted LovelyMiscLab GPL-3.0 source; see `workbench/UPSTREAM.md` and `workbench/LICENSE`. Qt/PySide6 sections below apply only to the retained legacy Qt edition, not the Workbench runtime. Electron LICENSE and Chromium LICENSES.chromium.html are included at the distribution root; npm dependency notices are in `docs/licenses-workbench/`.

Sentinel includes unmodified open-source runtime packages. Our application code adds the XDR adapter, evidence snapshots, AST route/call indexing, attack-to-code correlation, bounded investigation workflow, native desktop UI, persistence, tests and packaging. No upstream SOC platform source was copied.

| Component | Upstream | License | Used for |
|---|---|---|---|
| FastAPI | https://github.com/fastapi/fastapi | MIT | Local HTTP API and validation integration |
| Starlette | https://github.com/Kludex/starlette | BSD-3-Clause | ASGI routing/lifecycle |
| Uvicorn | https://github.com/encode/uvicorn | BSD-3-Clause | Embedded loopback server |
| HTTPX / httpcore | https://github.com/encode/httpx | BSD-3-Clause | XDR and compatible LLM calls |
| Pydantic | https://github.com/pydantic/pydantic | MIT | Input schemas |
| Bandit | https://github.com/PyCQA/bandit | Apache-2.0 | Actual Python SAST scanning |
| PySide6 / Shiboken6 | https://github.com/pyside/pyside-setup | LGPL-3.0 option; also offered under GPL/commercial terms | Native Qt Python bindings |
| Qt Core, Gui, Widgets, Network, Test | https://code.qt.io/cgit/qt/qtbase.git | LGPL-3.0 option and applicable third-party notices | Native windows, painting, HTTP client, UI testing |
| Python / CPython | https://www.python.org/ | PSF license | Bundled Windows interpreter |
| SQLite | https://sqlite.org/ | Public domain | Local persistence |
| PyInstaller | https://github.com/pyinstaller/pyinstaller | GPL-2.0-or-later with distribution exception | Windows packaging / bootloader |

Full installed-package metadata and copied upstream notices are in `docs/dependencies*.json` and `docs/licenses/`. The packaged directory includes `licenses/` under `_internal` and a copy beside this notice. Runtime dependency versions are pinned in requirements lock files. Build tools and unused optional Qt modules are not claimed to be application functionality.

## Qt / PySide6 dynamic-library notice

This software uses Qt and PySide6 under the LGPL-3.0 option. The original copyright notices remain in the distributed libraries and license files. Copies of the GNU LGPLv3 and GPLv3 are included under `licenses/Qt-PySide6` (source checkout: `docs/licenses/Qt-PySide6`). The libraries have not been modified.

The Windows distribution is an **onedir** bundle, not a statically linked or onefile application. You may replace the compatible Qt/PySide6/Shiboken dynamic libraries in `_internal/PySide6` and `_internal/shiboken6`, and use the accompanying application source and build script to rebuild the application against a modified compatible library. No application term prohibits reverse engineering for debugging modifications to these LGPL libraries. Keep the executable and `_internal` directory together.

Corresponding upstream source for the distributed Qt/PySide6 6.11.2 release can be obtained from:

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/
- https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.11.2
- https://download.qt.io/official_releases/qt/6.11/6.11.2/single/
- https://code.qt.io/cgit/qt/qtbase.git/tag/?h=v6.11.2

Reproducible application build instructions are in README and `scripts/build-windows.ps1`. Official licensing information: https://doc.qt.io/qtforpython-6/licenses.html and https://www.qt.io/development/open-source-lgpl-obligations.

Windows system fonts are used from the operating system and are not copied into this distribution. Native figures and the Sentinel icon were drawn in project code, without third-party bitmap assets.

## PyCryptodome 3.23.0

用于平台授权码 AES-CBC 解析；BSD-2-Clause 与部分 Public Domain 代码。项目 https://github.com/Legrandin/pycryptodome ，许可原文见 docs/licenses/pycryptodome-LICENSE.txt。XDR 签名按用户提供协议独立实现，未将含未知许可的 SDK 源码打包分发。

## UI 设计参考（未复制源码或素材）

LovelyMiscLab — https://github.com/Tokeii0/LovelyMiscLab — GPL-3.0。参考窄导航栏、紧凑工具栏、蓝色强调色、节点画布和日夜主题的设计方式；以本项目原生 Qt Widgets 独立实现。没有分发该项目代码、图标或其他素材，也没有引入其 Tauri/React 运行时。

## Sentinel Workbench 0.2：实际源码复用（2026-09-22）

按用户要求，新 Workbench 已从“仅参考设计”改为复用 LovelyMiscLab 的 React 页面基础：index.css、LeftRail、theme store、button、utils。保留 workbench/LICENSE（GPL-3.0）及 workbench/UPSTREAM.md，组合发行提供 GPL-3.0 相应源码。本段取代此前关于该新版“未复制源码”的描述；旧 Qt 版记录保留供追溯。

Electron 44.4.3（MIT）与 Chromium 第三方许可随运行时保留；React、Zustand、React Flow、Lucide、Tailwind 及其他 npm 包的许可由 workbench 第三方许可目录收录。新发行包不包含 Qt/PySide6。

## Double Pupil 0.3 新增 SSH 基础

使用未修改的 Paramiko 4.0.0 (LGPL-2.1) 及其依赖，许可证收录于 docs/licenses，锁定版本见 backend/requirements.lock。上游 https://github.com/paramiko/paramiko 。自主修复配方、资产权限、审计与 RAG 为本项目新增代码。对应完整源代码随 Double-Pupil-source.zip 提供，可按 README 重建或替换依赖。

## Double Pupil 0.4

Tree-sitter / tree-sitter-php（MIT）提供 PHP 语法解析；python-docx（MIT）提供 OOXML Word 文档生成；lxml（BSD 等所附通知）提供 XML 基础。许可证见 docs/licenses，版本见 backend/requirements.lock。本项目新增 PHP 规则、资产拓扑/发现、情报持久化与定时同步、二级设置和执行节点展示。CISA KEV 数据源与官方镜像使用 CC0；NVD 数据引用 https://nvd.nist.gov/ 。实际情报缓存、用户 Pikachu 源码和密钥不包含在发行包中。
