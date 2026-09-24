# 协作开发

## 开发环境

使用 Python 3.12 和 Node.js 22。Windows 构建步骤见 README；应用前端必须在 Electron 中运行，浏览器不具备桌面 IPC 能力。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
cd workbench
npm ci
npm run build
cd ..
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
```

Windows PowerShell 测试：

```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## 分支与评审

从 `main` 建立 `feat/功能名称` 或 `fix/问题名称` 分支；提交后发起 Pull Request。说明触发条件、最终行为和验证结果。界面改动附日间/夜间截图；接口字段变化同步前端与契约测试。合并前检查 CI。仓库维护者可在 GitHub 设置保护 main 并要求评审；仓库本身的文件不会自动开启分支保护。

## 配置与数据

新工作区使用内置 Demo，不需要现场凭据。个人通过“设置”配置模型和 XDR；不要把密钥写入源码或提交 `.env`、用户数据库、抓包、原始客户 API 文档。API 契约测试使用仅含路径和方法的精简 fixture。现场验收与截图保留在本地，不属于协作仓库。

前端：`workbench/src`；Electron：`workbench/electron`；后端：`backend/app`；回归测试：`backend/tests`；Windows 打包：`scripts/build-workbench.ps1`。

项目沿用所复用 UI 的 GPL-3.0-only 许可，保留原作者声明；第三方组件以各自许可为准，详见 `THIRD_PARTY_NOTICES.md` 和 `workbench/UPSTREAM.md`。

本地完整工作区当前通过 45 项后端测试；仅含版本库内容的干净检出通过 41 项，另有 4 项依赖现场材料的检查自动跳过。CI 不连接现场 XDR、不调用付费模型、不扫描内网。
