import { useCallback, useEffect, useState } from "react";
import { X, ShieldCheck } from "lucide-react";
import { LeftRail } from "@/app/LeftRail";
import { TitleBar } from "@/app/TitleBar";
import { useViewStore, type View } from "@/store/view";
import { api, errorText } from "@/lib/api";
import { Overview } from "@/views/Overview";
import { Events } from "@/views/Events";
import { Assets } from "@/views/Assets";
import { Intelligence } from "@/views/Intelligence";
import { Canvas } from "@/views/Canvas";
import { CodeAudit } from "@/views/CodeAudit";
import { Settings } from "@/views/Settings";
import { Reports } from "@/views/Reports";
export default function App() {
  const { view, setView } = useViewStore();
  const [event, setEvent] = useState<string | null>(null),
    [job, setJob] = useState<string | null>(null),
    [error, setError] = useState(""),
    [mode, setMode] = useState(""),
    [model, setModel] = useState("");
  const run = useCallback((fn: () => Promise<any>) => {
    void fn().catch((e) => setError(errorText(e)));
  }, []);
  const refresh = () =>
    run(async () => {
      const s = await api("/settings");
      setMode(s.xdr.mode);
      setModel(s.llm.mode);
    });
  useEffect(refresh, []);
  const openEvent = (id: string) => {
    setEvent(id);
    setView("events");
  };
  const openJob = (id: string) => {
    setJob(id);
    setView("canvas");
  };
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-background text-foreground">
      <TitleBar />
      <div className="flex min-h-0 flex-1">
        <LeftRail />
        <div className="grow min-w-0 relative">
          {view === "overview" && (
            <Overview openEvent={openEvent} go={setView} run={run} />
          )}{" "}
          {view === "events" && (
            <Events
              selected={event}
              onSelect={setEvent}
              onJob={openJob}
              run={run}
            />
          )}{" "}
          {view === "canvas" && (
            <Canvas id={job} selectJob={setJob} run={run} />
          )}{" "}
          {view === "assets" && <Assets run={run} />}
          {view === "intelligence" && <Intelligence run={run} />}
          {view === "code" && <CodeAudit run={run} />}{" "}
          {view === "runs" && <Reports open={openJob} run={run} />}{" "}
          {view === "settings" && <Settings run={run} onSave={refresh} />}
        </div>
      </div>
      <footer className="statusbar">
        <span className="flex items-center gap-2">
          <ShieldCheck size={12} />
          {mode === "live" ? "LIVE XDR" : "DEMO WORKSPACE"} · 资产 · 关联分析 ·
          授权修复
        </span>
        <span>
          {model === "mock" ? "Mock · 离线规则模式" : "外部模型"}　|　事件 →
          Evidence → Code
        </span>
      </footer>
      {error && (
        <div role="alert" className="error-toast">
          <span>{error}</span>
          <button aria-label="关闭提示" onClick={() => setError("")}>
            <X size={17} />
          </button>
        </div>
      )}
    </div>
  );
}
