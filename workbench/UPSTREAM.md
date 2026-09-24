# Upstream and modifications

Based in part on Tokeii0/LovelyMiscLab, GPL-3.0:
https://github.com/Tokeii0/LovelyMiscLab
Reference commit: b234f00 (full revision in docs/UI_THEME.md).

Copied/adapted: src/index.css, src/app/LeftRail.tsx, src/store/theme.ts,
src/components/ui/button.tsx, src/lib/utils.ts. Preserve upstream LICENSE.
TitleBar follows upstream layout but replaces Tauri controls with Electron IPC.

Sentinel additions (2026-09-22): event/exposure overview, event inspector,
read-only XDR integration, evidence-driven React Flow investigation canvas,
code review and Bandit integration, settings, report export, system theme,
Electron isolated preload/main process and packaged Python sidecar.

Removed from scope: upstream crypto/forensics node engine, MCP, scripts,
auto-updater, template modules and Tauri/Rust application. No execution of
uploaded repository code. Existing backend algorithms and data model retained.

This combined Workbench distribution is provided under GPL-3.0-only, with
corresponding source and build scripts. Independent dependencies retain their
own licenses. This is not an official LovelyMiscLab release.

## Double Pupil 0.3

保留调查画布，新增资产 CRUD、SSH 修复授权、Skills/RAG 文档配置与修复审计页面。产品更名为 Double Pupil；上游归属和许可证不变。

## 0.4 新增

新增资产逻辑拓扑、明确范围的 TCP 资产发现、设置二级目录、漏洞情报页和调查执行节点；继续保留上游归属、主题组件和调查画布。
