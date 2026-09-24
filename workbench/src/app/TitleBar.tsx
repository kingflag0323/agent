// Desktop toolbar adapted to Sentinel, following LovelyMiscLab's GPL workbench layout.
import {
  ShieldCheck,
  Sun,
  Moon,
  Monitor,
  Minus,
  Square,
  X,
} from "lucide-react";
import { useThemeStore, type ThemeMode } from "@/store/theme";
import { Button } from "@/components/ui/button";
export function TitleBar() {
  const { mode, setTheme } = useThemeStore();
  return (
    <header className="titlebar flex h-12 shrink-0 items-center gap-3 border-b bg-card px-4">
      <ShieldCheck size={20} className="text-primary" />
      <strong className="text-sm tracking-wide">Double Pupil</strong>
      <span className="text-xs text-muted-foreground">
        Autonomous Security Workbench
      </span>
      <div className="grow" />
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
