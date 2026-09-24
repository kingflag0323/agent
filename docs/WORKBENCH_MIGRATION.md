# Workbench 迁移交付说明

2026-09-22，按用户“不要 Qt，使用 GitHub 页面修改”的要求，将窗口切换为 Electron + React，页面基于 LovelyMiscLab 源码二次开发。原项目的 Tauri/Rust 外壳未复用，以避免当前构建环境额外引入 Rust/MSVC 工具链。独立 exe 加载本地打包页面，用户无需浏览器或访问网站。

复用与许可列表见 workbench/UPSTREAM.md；相应源码和构建脚本随发行提供。后端复用 FastAPI/SQLite、XDR 适配器、Evidence、Bandit/AST、关联与报告。数据目录维持原路径；切换前进行了 SQLite 备份。旧 Qt 程序保留为回退，不应与新版同时使用同一数据库。

主题选择在 Electron 本机资料目录的 localStorage 保存。后端凭据仍只在用户数据目录 SQLite 中，不复制到 Renderer、静态资源或发布包。主进程以随机令牌连接本机后台，Renderer 只经预加载白名单调用 API。

本次迁移不增加任意脚本节点或执行代码功能。拖动节点只改变当前画布布局，不修改已有调查证据与调用边。
