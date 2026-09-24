# 开源调研与技术决策

调研日期：2026-09-20。首先搜索 AI SOC / Security Investigation / FastAPI / SAST，再对以下六个候选读取 README、实际许可证、目录结构、最近更新时间和近期 Issue/PR。GitHub 原始元信息及许可证保存在 `docs/research/`。Stars 仅记录，不作为选择依据。

| 候选 | License | 栈 / 复杂度 | 适配程度 | 选择 |
|---|---|---|---|---|
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | MIT | React/Vite/FastAPI/PostgreSQL；附带登录、邮件、容器部署 | API 分层和全栈测试可参考，但对本项目核心关联无直接实现 | 架构评估，不复制代码；SQLite 更适合本机 Demo |
| [dfir-iris/iris-web](https://github.com/dfir-iris/iris-web) | LGPL-3.0 | Python、事件协作、模块、Docker Compose | 事件管理成熟，但需要迁移其领域模型与部署体系 | 不作为基础；不复制代码 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | Python 状态图、持久化、依赖生态 | 适合复杂长任务，但本次有界只读调查不需要全部框架 | 保留可替换工作流接口；本版原生 asyncio 工作流 |
| [PyCQA/bandit](https://github.com/PyCQA/bandit) | Apache-2.0 | Python AST SAST，单进程 CLI，JSON 输出 | 直接提供可复核 SQL 拼接 / shell 调用发现，部署轻 | **实际集成**，安装发行包；没有复制或修改上游源码 |
| [semgrep/semgrep](https://github.com/semgrep/semgrep) | LGPL-2.1（仓库声明；规则/商业能力需另查） | 多语言扫描引擎，二进制与规则分发 | 更适合下一阶段 Java/JS，但增加 Windows 打包与规则维护成本 | 本版未安装、未声称支持；扫描接口可扩展 |
| [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | MIT | React/TypeScript 组件源码 | 最初网页技术栈可用，但用户后续明确要 Windows 原生程序 | 原网页原型已移除，不进入交付 |

## 质量观察

以下为调研时 GitHub API 快照，不承诺永久有效：

- FastAPI 模板 pushed_at 2026-09-18；近期 PR 涉及 Python <=3.13 异常语法兼容，直接搬最新模板会引入额外适配成本。
- IRIS pushed_at 2026-08-24；近期 Issue 包含报告模板 POST 重定向 405。复杂案例管理不是本次闭环必需。
- LangGraph pushed_at 2026-09-20；近期 Issue 涉及 RemoteGraph API key、SSE 游标；本机短流程可避免这类远程框架依赖。
- Bandit pushed_at 2026-08-29；近期 Issue 涉及 baseline 去重、部分 HTTP 调用检查覆盖。本版不用 baseline，将 nosec 忽略禁用，保留扫描错误。
- Semgrep pushed_at 2026-09-18；近期 Issue 包含扩展名大小写与 Python AST 特殊模式漏扫。多语言仍需专门用例验证。
- shadcn/ui pushed_at 2026-09-17；本次没有引入其代码或其构建体系。

未对已否决的完整平台执行 Build，避免调研吞噬开发时间；没有虚构“全部候选构建通过”。实际采用的依赖通过原生 UI、后端测试与 Windows 打包验证，具体见验收文档。

## 最终组合：原生桌面优先

用户明确要求 Windows 独立桌面软件后，采用 [PySide6 / Qt for Python](https://github.com/pyside/pyside-setup) 的 Qt Widgets。没有 QtWebEngine、Electron、浏览器或网页入口。图表、调用链与代码高亮使用 Qt 原生绘制；后端继续使用 FastAPI。PySide6/Qt 使用 LGPL-3.0 选项及相关第三方许可证，采用可替换动态 DLL 的目录发行，携带许可证及源码取得路径；详见 `THIRD_PARTY_NOTICES.md`。

统一数据层：SQLite；统一 API：FastAPI；统一调查：Planner → Evidence → Bandit/AST → Correlation → Provider → Reviewer → Report。自己的核心代码是 XDR 证据与代码可达漏洞候选之间的关联，而不是重新造扫描工具。
