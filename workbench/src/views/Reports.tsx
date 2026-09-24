import { useEffect, useState } from "react";
import { api, Data, fmt } from "@/lib/api";
import { Badge, Empty, Json } from "@/components/Common";
import { Button } from "@/components/ui/button";
export function Reports({
  open,
  run,
}: {
  open: (id: string) => void;
  run: (fn: () => Promise<any>) => void;
}) {
  const [rows, setRows] = useState<Data[]>([]),
    [id, setId] = useState(""),
    [job, setJob] = useState<Data>();
  useEffect(() => {
    run(async () => {
      const rows = await api("/investigations");
      setRows(rows);
      if (rows.length && !id) setId(rows[0].id);
    });
  }, []);
  useEffect(() => {
    if (!id) return;
    let active = true;
    const refresh = async () => {
      const j = await api("/investigations/" + id);
      if (active) setJob(j);
    };
    run(refresh);
    const timer = setInterval(() => run(refresh), 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [id]);
  return (
    <div className="h-full flex">
      <aside className="w-72 border-r bg-card overflow-auto">
        <div className="pane-heading">
          <h2>调查思维链</h2>
        </div>
        {rows.map((j) => (
          <button
            className={"evidence-item " + (id === j.id ? "selected" : "")}
            key={j.id}
            onClick={() => setId(j.id)}
          >
            <strong>{j.event.name}</strong>
            <small>
              {j.project.name} · {fmt(j.created_at)}
            </small>
            <Badge value={j.status} />
          </button>
        ))}
      </aside>
      <main className="flex-1 overflow-auto p-6 space-y-5">
        <div className="flex justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">
              {job?.event.name || "调查过程"}
            </h1>
            <p className="text-muted-foreground text-sm">
              展示工具调用、节点状态、执行摘要与证据引用；不展示模型内部推理。
            </p>
          </div>
          <div className="flex gap-2 items-start">
            <Button variant="outline" disabled={!id} onClick={() => open(id)}>
              调查画布
            </Button>
            {["docx", "markdown", "json"].map((f) => (
              <Button
                key={f}
                variant={f === "docx" ? "default" : "outline"}
                disabled={job?.status !== "completed"}
                onClick={() => run(() => window.desktop.exportReport(id, f))}
              >
                {f === "docx" ? "导出 Word" : f === "markdown" ? "MD" : "JSON"}
              </Button>
            ))}
          </div>
        </div>
        {job ? (
          <>
            <div className="card">
              <Badge value={job.status} />
              <p className="mt-3">
                {job.correlation?.summary || job.error || "正在执行调查…"}
              </p>
              <small>
                {job.id} · {job.project.name}
              </small>
            </div>
            <div className="space-y-3">
              {job.timeline.map((node: Data, i: number) => (
                <section className="card flex gap-4" key={i}>
                  <div className="rounded-full bg-primary/10 text-primary w-10 h-10 flex shrink-0 items-center justify-center font-bold">
                    {i + 1}
                  </div>
                  <div className="grow">
                    <div className="flex justify-between">
                      <h2>{node.name}</h2>
                      <Badge value={node.status} />
                    </div>
                    <p className="my-2">{node.note}</p>
                    <small>
                      {node.tool} · {fmt(node.started_at)}
                      {node.finished_at ? " → " + fmt(node.finished_at) : ""}
                    </small>
                  </div>
                </section>
              ))}
            </div>
            <details className="card">
              <summary>模型辅助研判与复核结果</summary>
              <Json
                value={{
                  analysis: job.analysis,
                  review: job.review,
                  references: job.agent_context,
                }}
              />
            </details>
            <details className="card">
              <summary>证据引用（{job.evidence?.length || 0}）</summary>
              {job.evidence?.map((e: Data) => (
                <div key={e.id} className="border-b py-3">
                  <strong>{e.title}</strong>
                  <p className="text-xs break-all">
                    {e.id} · {e.kind} · {e.source} · SHA256 {e.sha256}
                  </p>
                </div>
              ))}
            </details>
          </>
        ) : (
          <Empty text="从事件页启动调查，随后在这里查看执行过程" />
        )}
      </main>
    </div>
  );
}
