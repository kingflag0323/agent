export type Data = Record<string, any>;
declare global {
  interface Window {
    desktop: {
      request: (path: string, method?: string, body?: unknown) => Promise<any>;
      exportReport: (id: string, format: string) => Promise<boolean>;
      importZip: (name: string) => Promise<any>;
      importDocument: () => Promise<{ name: string; content: string } | null>;
      chooseFolder: () => Promise<string | null>;
      windowControl: (action: string) => Promise<void>;
      theme: (mode: string) => Promise<void>;
    };
  }
}
export async function api(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<any> {
  if (!window.desktop) throw Error("请使用独立桌面程序打开此工作台");
  return window.desktop.request(path, method, body);
}
export function errorText(e: unknown) {
  return e instanceof Error ? e.message : String(e);
}
export const labels: Record<string, string> = {
  verified: "验证通过",
  rolled_back: "已回滚",
  recovery_required: "待人工恢复",
  blocked: "条件不满足",
  not_applied: "未应用",
  critical: "严重",
  high: "高危",
  medium: "中危",
  low: "低危",
  info: "信息",
  open: "待处置",
  closed: "已关闭",
  investigating: "处理中",
  completed: "已完成",
  running: "运行中",
  queued: "排队中",
  failed: "失败",
  interrupted: "已中断",
  demo: "演示数据",
  live: "真实 XDR",
  likely_vulnerable_path: "找到可能被利用的代码路径",
  insufficient_evidence: "证据不足，未建立漏洞关联",
};
export const fmt = (v?: string) =>
  v ? new Date(v).toLocaleString("zh-CN", { hour12: false }) : "未提供";
