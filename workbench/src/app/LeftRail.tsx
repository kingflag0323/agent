import {
  Boxes,
  Server,
  Radar,
  History,
  LayoutGrid,
  type LucideIcon,
  Package,
  Settings,
  Workflow,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useViewStore, type View } from "@/store/view";

type Item = { view: View; label: string; icon: LucideIcon };

const ITEMS: Item[] = [
  { view: "overview", label: "态势", icon: LayoutGrid },
  { view: "assets", label: "资产", icon: Server },
  { view: "intelligence", label: "威胁情报", icon: Radar },
  { view: "events", label: "事件", icon: Boxes },
  { view: "canvas", label: "调查画布", icon: Workflow },
  { view: "code", label: "代码", icon: Package },
  { view: "runs", label: "调查思维链", icon: History },
];
const SETTINGS: Item = { view: "settings", label: "设置", icon: Settings };

export function LeftRail() {
  const view = useViewStore((s) => s.view);
  const setView = useViewStore((s) => s.setView);

  const renderItem = ({ view: v, label, icon: Icon }: Item) => {
    const active = view === v;
    return (
      <button
        key={v}
        onClick={() => setView(v)}
        className={cn(
          "relative flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] transition-colors",
          active
            ? "bg-primary/10 font-medium text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
        )}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-r bg-primary" />
        )}
        <Icon className="h-5 w-5" />
        {label}
      </button>
    );
  };

  return (
    <div className="flex w-16 shrink-0 flex-col items-center gap-1 border-r border-border bg-card py-2">
      {ITEMS.map(renderItem)}
      <div className="flex-1" />
      {renderItem(SETTINGS)}
    </div>
  );
}
