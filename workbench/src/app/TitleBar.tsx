// Desktop toolbar adapted to Sentinel, following LovelyMiscLab's GPL workbench layout.
import {
  Activity,
  Boxes,
  Bug,
  Code2,
  FileText,
  History,
  LayoutGrid,
  Radar,
  Server,
  Settings,
  ShieldCheck,
  Sun,
  Moon,
  Monitor,
  Minus,
  Square,
  X,
} from "lucide-react";
import { useThemeStore, type ThemeMode } from "@/store/theme";
import { useViewStore, type View } from "@/store/view";
import { Button } from "@/components/ui/button";

const VIEW_META: Record<View, { label: string; icon: typeof LayoutGrid }> = {
  overview: { label: "安全态势", icon: LayoutGrid },
  assets: { label: "资产管理", icon: Server },
  intelligence: { label: "威胁情报", icon: Radar },
  events: { label: "安全事件", icon: Boxes },
  code: { label: "代码审计", icon: Code2 },
  runs: { label: "调查思维链", icon: History },
  results: { label: "调查结果", icon: FileText },
  settings: { label: "系统设置", icon: Settings },
};

export function TitleBar({
  sourceMode,
  modelMode,
  modelName,
  healthy,
  stats,
}: {
  sourceMode: string;
  modelMode: string;
  modelName: string;
  healthy: boolean;
  stats: { events: number; vulnerabilities: number; running: number };
}) {
  const { mode, setTheme } = useThemeStore();
  const view = useViewStore((state) => state.view);
  const CurrentIcon = VIEW_META[view].icon;
  const modelLabel =
    modelMode === "mock" ? "离线规则" : modelName || "外部模型";
  return (
    <header className="titlebar h-12 shrink-0 border-b bg-card">
      <div className="titlebar-brand">
        <ShieldCheck size={19} className="text-primary" />
        <strong>Double Pupil</strong>
        <span>Autonomous Security Workbench</span>
      </div>
      <div className="titlebar-divider" />
      <div className="titlebar-context">
        <CurrentIcon size={14} />
        <span>{VIEW_META[view].label}</span>
      </div>
      <div className="titlebar-telemetry" aria-label="工作区状态">
        <span className={healthy ? "healthy" : "pending"}>
          <i />
          {healthy ? "服务正常" : "连接中"}
        </span>
        <span>
          <Activity size={12} />
          {sourceMode === "live" ? "XDR 实时" : "演示数据"}
        </span>
        <span className="titlebar-stat">
          <Boxes size={12} />
          事件 {stats.events}
        </span>
        <span className="titlebar-stat">
          <Bug size={12} />
          漏洞 {stats.vulnerabilities}
        </span>
        {stats.running > 0 && (
          <span className="running">
            <i />
            调查中 {stats.running}
          </span>
        )}
        <span className="titlebar-model">AI · {modelLabel}</span>
      </div>
      <div className="titlebar-spacer" />
      <div className="no-drag flex items-center gap-2">
        <span className="text-muted-foreground">
          {mode === "light" ? (
            <Sun size={15} />
          ) : mode === "dark" ? (
            <Moon size={15} />
          ) : (
            <Monitor size={15} />
          )}
        </span>
        <select
          aria-label="外观主题"
          value={mode}
          onChange={(e) => setTheme(e.target.value as ThemeMode)}
        >
          <option value="system">跟随系统</option>
          <option value="light">日间</option>
          <option value="dark">夜间</option>
        </select>
        {[
          ["minimize", Minus],
          ["maximize", Square],
          ["close", X],
        ].map(([action, Icon]: any) => (
          <Button
            key={action}
            variant="ghost"
            size="icon"
            aria-label={action}
            onClick={() => window.desktop.windowControl(action)}
          >
            <Icon size={15} />
          </Button>
        ))}
      </div>
    </header>
  );
}
