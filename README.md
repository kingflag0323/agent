# Double Pupil — XDR × AI Investigation × Code

**Windows 独立桌面程序，基于 LovelyMiscLab 的 React 页面二次开发，以 Electron 承载。新版不使用 Qt。** 双击 `DoublePupil.exe` 即可启动：内嵌页面和 Python 后台随程序启动，无需浏览器、外置 Python、Node、数据库或 WSL。

本版 **0.4** 新增资产拓扑与内网发现、二级设置目录、定时漏洞情报、调查执行节点和 Word 报告，并以已导入的 Pikachu PHP 靶场验证。保留调查画布。详见 [0.4 使用说明](docs/DOUBLE_PUPIL_V04.md)；SSH 范围见 [修复边界](docs/DOUBLE_PUPIL.md)。

## 打开程序

- 桌面入口：**Double Pupil**。
- 安装目录：`%LOCALAPPDATA%\Programs\DoublePupil`。
- 便携版：`release/DoublePupil/`；保留整个目录，不能只复制 exe。
- 发行压缩包：`release/Double-Pupil-Windows-x64.zip`。
- 相应源码：`release/Double-Pupil-source.zip`。
- 数据继续使用 `%LOCALAPPDATA%\Sentinel\data\sentinel.db`；原有 XDR 授权码、项目、事件与调查记录保留。
- 新解压的程序不附带密钥。当前这台电脑已有 Live XDR 配置；干净数据目录默认 Demo。
- 旧 Qt 版保留为回退，不要与新版同时使用同一数据库。历史验收与部署记录仅在现场工作区保留。

## 界面与核心流程

复用上游的窄导航栏、React Button、样式变量和主题状态，并修改为统一安全调查工作台：

1. **态势**：当前数据源已同步的平台事件、风险、关联主机与攻击类型。
2. **事件**：搜索 / 风险筛选 / 分页 → 事件检查器 → 选择对应源码项目 → AI Investigation。
3. **调查画布**：证据库 + 可缩放/平移的 React Flow 调用链 + 代码/证据检查器 + 执行记录。点击节点查看代码快照，点击证据查看来源、哈希和原始字段。
4. **代码**：本地 / ZIP / 公开 Git 导入、文件树、真实 Bandit 扫描、漏洞行、快照和修复建议。
5. **调查思维链**：展示实际执行节点、工具、时间、状态与引用，支持 Word / Markdown / JSON 导出。
6. **资产**：默认拓扑与列表，点击新增才登记；支持内网 TCP 发现、标签、源码/Web 服务绑定和 SSH 授权。
7. **威胁情报**：CISA / NVD 漏洞动态，定期持久化、筛选和检索。
8. **设置**：二级目录分开配置模型、XDR、智能体、Skills/RAG、工作/输出目录、扫描和情报 API/计划。

右上角 **日间 / 夜间 / 跟随系统**，自动保存；图形画布、代码、证据及表单同步适配。系统模式通过媒体颜色变化和 Electron 原生主题同步更新。页面只加载打包的本地资源，不从 GitHub 在线加载。

## 五分钟演示

现场推荐：资产中的 **Pikachu Docker 靶场** → 事件中本次 SQL 注入告警 → 选择 `pikachu` → **AI Investigation**。靶场地址 `http://172.20.0.252:12348/`。

隔离 Demo 回归：设置 XDR 为 Demo → 事件中 SQL 注入攻击 → 选择 `Shop API · 演示项目` → **AI Investigation**。

真实静态分析得到：`GET /api/user → user_controller → get_user → find_user → repository.py:6`，规则 `B608 / CWE-89`。画布可查看证据与函数快照，右侧给出参数化 SQL 修复建议。

负例：健康检查 `/api/health` 必须显示 **证据不足，未建立漏洞关联**。命令注入例：`/api/diagnostic → shell=True → CWE-78`。

演示事件始终标注 Demo Fact；Bandit 扫描实际执行。默认 LLM 是 Mock，不会声称已调用真实模型。选择真实事件时应绑定资产实际部署的仓库，不能将演示项目当作生产代码。

## XDR 现场连接

`https://172.20.0.140` 已以用户提供的授权码通过 HMAC-SHA256 鉴权。2026-09-21 已同步近七天 7 条真实事件，抽样读取事件举证、4 条告警、1 个资产成功。TLS 校验按用户提供配置关闭；可在设置中配置可信 CA 后开启。

XDR 仅调用文档内的只读事件、告警、网络日志与实体接口；不执行处置动作。原始连接材料、会话 Cookie 和密钥不进入发行包或源码包。

## 技术边界

- FastAPI + SQLite + Bandit + Python AST；现有证据、工作流、关联和报告实现继续复用。
- Python 后端打包为 `sentinel-backend.exe`，仅监听随机回环端口；每次启动使用随机会话令牌。
- Electron Renderer 使用 sandbox / contextIsolation，禁用 Node Integration；预加载只公开受限 API。主进程验证调用来源与 API 白名单，拦截外部导航。Renderer 不能调用任意 URL、命令或读取任意文件。
- 本地目录仍受后端允许根目录约束；ZIP 有穿越、符号链接、数量与容量检查。
- 支持 Python 直接路由与可解析导入，以及 PHP 文件入口、有限赋值传播与静态 SQL 包装函数；其他语言可浏览。调用可达性不是完整污点证明，静态风险与 HTTP 状态码不证明利用成功。
- 单机单用户 Demo；未做多租户/生产级认证与 Windows 代码签名。

## 开源复用与许可证

上游：[Tokeii0/LovelyMiscLab](https://github.com/Tokeii0/LovelyMiscLab)，**GPL-3.0**。

实际复用并修改：`index.css`、`LeftRail.tsx`、`store/theme.ts`、`components/ui/button.tsx`、`lib/utils.ts`。保留 `workbench/LICENSE` 与 `workbench/UPSTREAM.md`，组合 Workbench 发行采用 GPL-3.0-only 并提供相应源码。未使用上游 Rust 取证引擎、MCP、脚本执行或自动更新模块。

我们新增：事件检查器、XDR/后端 IPC、调查节点画布、资产管理、Skills/RAG 检索、受约束 SSH 修复、代码审计、模型/连接配置、报告导出、系统主题和独立 Electron + Python 打包。Electron/Chromium 和其他第三方许可证随包保留，详见 `THIRD_PARTY_NOTICES.md` 与 `docs/licenses-workbench/`。

## 源码构建

Windows 需要 Python 3.12、Node.js 22 及 npm；运行已打包程序无需这些工具。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock -r scripts\requirements-build.txt
powershell -ExecutionPolicy Bypass -File scripts\build-workbench.ps1 -Python .\.venv\Scripts\python.exe
```

前端单独检查：`cd workbench; npm ci; npm run build`。输出仅用于桌面打包，普通浏览器没有受限 IPC 桥，不能操作本机后台。

Linux 后端验证：`PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q`。

Windows 实际安装包验收脚本：`scripts/test-workbench-windows.py`（本机测试目录与路径，需 playwright；通过 CDP 测试 Electron 内嵌页面，不需要另外安装浏览器）。测试使用独立 Demo 数据，不覆盖真实 XDR 配置。

## 进一步资料

- `docs/XDR_CAPABILITIES.md`：接口及合同边界。
- `docs/XDR_CONNECTION_SETUP.md`：鉴权材料与现场结果。
- `docs/OPEN_SOURCE_RESEARCH.md`：初始候选比较。
- `workbench/UPSTREAM.md`：本次上游复用及修改范围。
- `docs/workbench-delivery.json`：最终发行验收、哈希与大小。

## 团队协作

分支、开发检查与配置约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。仓库不包含现场抓包、原始客户接口文档、密钥、数据库、构建目录或安装包；API 契约测试使用精简 fixture。GitHub Actions 检查后端测试和前端生产构建。
