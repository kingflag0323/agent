import { useEffect, useState } from "react";
import {
  Search,
  Play,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { api, fmt, Data } from "@/lib/api";
import { Badge, Empty, Json } from "@/components/Common";
import { Button } from "@/components/ui/button";
export function Events({
  selected,
  onSelect,
  onJob,
  run,
}: {
  selected: string | null;
  onSelect: (id: string) => void;
  onJob: (id: string) => void;
  run: (fn: () => Promise<any>) => void;
}) {
  const [q, setQ] = useState(""),
    [severity, setSeverity] = useState(""),
    [page, setPage] = useState(1),
    [rows, setRows] = useState<Data>({ items: [], total: 0 }),
    [event, setEvent] = useState<Data>(),
    [projects, setProjects] = useState<Data[]>([]),
    [project, setProject] = useState(""),
    [proof, setProof] = useState<Data>(),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let valid = true;
    const t = setTimeout(
      () =>
        run(async () => {
          const d = await api(
            "/events?" +
              new URLSearchParams({ q, severity, page: String(page) }),
          );
          if (valid) setRows(d);
        }),
      150,
    );
    return () => {
      valid = false;
      clearTimeout(t);
    };
  }, [q, severity, page]);
  useEffect(() => {
    let valid = true;
    setEvent(undefined);
    setProof(undefined);
    if (selected)
      run(async () => {
        const [e, ps] = await Promise.all([
          api("/events/" + selected),
          api("/projects"),
        ]);
        if (valid) {
          setEvent(e);
          setProjects(ps);
          setProject(e.project_id || "");
        }
      });
    return () => {
      valid = false;
    };
  }, [selected]);
  return (
    <div className="flex h-full min-h-0">
      <section className="flex flex-col min-w-0 flex-1">
        <div className="pane-heading">
          <div>
            <h2>安全事件</h2>
            <p>选择事件，关联项目，启动调查</p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              run(async () => {
                await api("/events/sync", "POST");
                setRows(await api("/events?page=" + page));
              })
            }
          >
            <RefreshCw size={14} />
            同步
          </Button>
        </div>
        <div className="flex gap-2 p-4 border-b">
          <div className="relative grow">
            <Search
              size={15}
              className="absolute left-3 top-3 text-muted-foreground"
            />
            <input
              aria-label="搜索事件"
              className="w-full pl-9"
              placeholder="搜索事件、资产、攻击类型…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <select
            aria-label="风险筛选"
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setPage(1);
            }}
          >
            <option value="">全部风险</option>
            {["critical", "high", "medium", "low", "info"].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <div className="overflow-auto grow">
          <table>
            <thead>
              <tr>
                <th>事件 / 攻击类型</th>
                <th>风险</th>
                <th>资产</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {rows.items.map((e: Data) => (
                <tr
                  key={e.id}
                  className={selected === e.id ? "selected" : ""}
                  onClick={() => onSelect(e.id)}
                >
                  <td>
                    <div>{e.name}</div>
                    <small>{e.attack_type}</small>
                  </td>
                  <td>
                    <Badge value={e.severity} />
                  </td>
                  <td>{e.asset_ip}</td>
                  <td className="text-xs">{fmt(e.time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.items.length && <Empty text="没有匹配的事件" />}
        </div>
        <footer className="flex justify-between items-center p-3 border-t text-xs text-muted-foreground">
          <span>
            共 {rows.total} 条 · 第 {page} 页
          </span>
          <div className="flex gap-2">
            <Button
              aria-label="上一页"
              size="icon"
              variant="ghost"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft size={15} />
            </Button>
            <Button
              aria-label="下一页"
              size="icon"
              variant="ghost"
              disabled={page * 20 >= rows.total}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight size={15} />
            </Button>
          </div>
        </footer>
      </section>
      <aside className="inspector w-[390px]">
        {event ? (
          <>
            <div className="pane-heading">
              <h2>事件检查器</h2>
              <Badge value={event.source} />
            </div>
            <div className="p-5 space-y-5">
              <h2>{event.name}</h2>
              <div className="flex gap-2">
                <Badge value={event.severity} />
                <Badge value={event.status} />
              </div>
              <dl className="details">
                <dt>攻击类型</dt>
                <dd>{event.attack_type}</dd>
                <dt>受影响资产</dt>
                <dd>{event.asset_ip || event.asset}</dd>
                <dt>发现时间</dt>
                <dd>{fmt(event.time)}</dd>
                <dt>事件 ID</dt>
                <dd className="break-all">{event.external_id || event.id}</dd>
              </dl>
              <label className="field-label">
                关联代码项目
                <select
                  aria-label="关联代码项目"
                  className="w-full"
                  value={project}
                  onChange={(e) => setProject(e.target.value)}
                >
                  <option value="">请选择代码项目</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-xs">
                选择与目标资产部署对应的代码仓库；演示项目仅适用于演示事件。
              </p>
              <Button
                className="w-full"
                disabled={!project || busy}
                onClick={() =>
                  run(async () => {
                    setBusy(true);
                    try {
                      await api("/events/" + event.id + "/project", "PUT", {
                        project_id: project,
                      });
                      const j = await api("/investigations", "POST", {
                        event_id: event.id,
                        project_id: project,
                      });
                      onJob(j.id);
                    } finally {
                      setBusy(false);
                    }
                  })
                }
              >
                <Play size={15} />
                {busy ? "正在启动…" : "AI Investigation"}
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() =>
                  run(async () =>
                    setProof(await api("/events/" + event.id + "/evidence")),
                  )
                }
              >
                读取事件举证
              </Button>
              {proof && (
                <>
                  <h3>Evidence · {proof.evidence.length}</h3>
                  {proof.warnings?.map((w: string, i: number) => (
                    <p key={i} className="text-destructive">
                      {w}
                    </p>
                  ))}
                  <Json value={proof} />
                </>
              )}
              <details>
                <summary>原始事件字段</summary>
                <Json value={event.raw || event} />
              </details>
              {event.investigations?.map((j: Data) => (
                <Button
                  key={j.id}
                  className="w-full justify-between"
                  variant="outline"
                  onClick={() => onJob(j.id)}
                >
                  {j.id}
                  <Badge value={j.status} />
                </Button>
              ))}
            </div>
          </>
        ) : (
          <Empty text="从左侧选择事件，查看证据并启动代码关联调查" />
        )}
      </aside>
    </div>
  );
}
