import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  BackgroundVariant,
  type NodeProps,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  FileCode2,
  Download,
  Layers,
  Search,
  Network,
  CheckCircle2,
} from "lucide-react";
import { api, Data, fmt, labels } from "@/lib/api";
import { Badge, Code, Empty, Json } from "@/components/Common";
import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/store/theme";
function InvestigationNode({ data, selected }: NodeProps) {
  const d = data as Data;
  return (
    <div
      className={
        "investigation-node " +
        (selected ? "active " : "") +
        (d.sink ? "sink" : "")
      }
    >
      <Handle type="target" position={Position.Left} />
      <div className="node-cap">
        <FileCode2 size={14} />
        {d.role}
      </div>
      <strong>{d.label}</strong>
      <small>{d.location}</small>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { investigation: InvestigationNode };
export function Canvas({
  id,
  selectJob,
  run,
}: {
  id: string | null;
  selectJob: (id: string) => void;
  run: (fn: () => Promise<any>) => void;
}) {
  const theme = useThemeStore((s) => s.theme);
  const [jobs, setJobs] = useState<Data[]>([]),
    [job, setJob] = useState<Data>(),
    [selection, setSelection] = useState<Data | null>(null),
    [matchIndex, setMatchIndex] = useState(0),
    [tab, setTab] = useState("details");
  useEffect(() => {
    run(async () => setJobs(await api("/investigations")));
  }, [id]);
  useEffect(() => {
    setJob(undefined);
    setSelection(null);
    setMatchIndex(0);
    if (!id) return;
    let valid = true;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      const data = await api("/investigations/" + id);
      if (valid) {
        setJob(data);
        setJobs((previous) =>
          previous.map((item) =>
            item.id === data.id ? { ...item, status: data.status } : item,
          ),
        );
        if (
          ["running", "queued"].includes(data.status) ||
          data.remediation_pending
        )
          timer = setTimeout(() => run(refresh), 1000);
      }
    };
    run(refresh);
    return () => {
      valid = false;
      clearTimeout(timer);
    };
  }, [id]);
  const match = job?.correlation?.matches?.[matchIndex];
  const graph = useMemo(() => {
    if (!match) return { nodes: [], edges: [] };
    const data = [
      {
        role: "ATTACK ENTRY",
        label: (match.entry.method || "HTTP") + " " + match.entry.path,
        location: "XDR HTTP evidence",
        evidenceId: match.entry.evidence_id,
      },
      ...match.chain.map((n: Data, i: number) => ({
        role: i === match.chain.length - 1 ? "VULNERABLE SINK" : "CODE PATH",
        label: n.name + "()",
        location: n.file + ":" + n.line,
        sink: i === match.chain.length - 1,
        file: n.file,
        line: n.line,
      })),
    ];
    return {
      nodes: data.map((d: Data, i: number) => ({
        id: "n" + i,
        type: "investigation",
        position: { x: (i % 2) * 310, y: Math.floor(i / 2) * 195 },
        data: d,
      })),
      edges: data.slice(1).map((_: Data, i: number) => ({
        id: "e" + i,
        source: "n" + i,
        target: "n" + (i + 1),
        animated: true,
        style: { stroke: "var(--primary)", strokeWidth: 2 },
      })),
    };
  }, [match]);
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  useEffect(() => setNodes(graph.nodes), [graph, setNodes]);
  return (
    <div className="flex h-full min-h-0">
      <aside className="w-64 shrink-0 border-r bg-card flex flex-col">
        <div className="pane-heading">
          <Layers size={16} />
          <h2>调查与证据</h2>
        </div>
        <div className="p-3 border-b">
          <select
            aria-label="选择调查"
            className="w-full"
            value={id || ""}
            onChange={(e) => selectJob(e.target.value)}
          >
            <option value="">选择调查任务</option>
            {jobs.map((j) => (
              <option value={j.id} key={j.id}>
                {j.event.name} · {labels[j.status] || j.status}
              </option>
            ))}
          </select>
        </div>
        <div className="p-3 text-xs text-muted-foreground">
          EVIDENCE LIBRARY · {job?.evidence?.length || 0}
        </div>
        <div className="overflow-auto grow">
          {job?.evidence?.map((e: Data) => (
            <button
              className={
                "evidence-item " + (selection?.id === e.id ? "selected" : "")
              }
              key={e.id}
              onClick={() => {
                setSelection(e);
                setTab("details");
              }}
            >
              <span className="flex items-center gap-2">
                <Search size={13} />
                {e.title}
              </span>
              <small>
                {e.kind} · {e.source}
              </small>
            </button>
          ))}
          {!job && <Empty text="从事件列表启动调查，或选择已有任务" />}
        </div>
      </aside>
      <main className="min-w-0 flex-1 flex flex-col">
        <div className="pane-heading">
          <div>
            <h2>{job?.event.name || "Attack → Code 调查画布"}</h2>
            <p>{job ? job.id : "证据驱动的攻击路径与代码关联"}</p>
          </div>
          <div className="flex gap-2 items-center">
            {job && <Badge value={job.status} />}
            <Button
              size="sm"
              variant="outline"
              disabled={job?.status !== "completed" || job?.remediation_pending}
              onClick={() =>
                run(async () => {
                  await window.desktop.exportReport(job!.id, "markdown");
                })
              }
            >
              <Download size={14} />
              报告
            </Button>
          </div>
        </div>
        <div className="flex gap-2 px-4 py-2 border-b items-center text-xs">
          <Network size={14} className="text-primary" />
          <span>
            {job?.correlation?.summary ||
              "节点将随调查结果生成；可拖动、缩放和检查"}
          </span>
          {job?.correlation?.matches?.length > 1 && (
            <select
              value={matchIndex}
              onChange={(e) => {
                setMatchIndex(Number(e.target.value));
                setSelection(null);
              }}
            >
              {job?.correlation.matches.map((m: Data, i: number) => (
                <option key={i} value={i}>
                  {m.finding.file}:{m.finding.line}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="grow min-h-60 relative bg-background">
          {match ? (
            <ReactFlow
              key={id + "-" + matchIndex}
              nodes={nodes}
              onNodesChange={onNodesChange}
              edges={graph.edges}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              colorMode={theme}
              nodesDraggable={true}
              nodesConnectable={false}
              onNodeClick={(_, n) => {
                const d = n.data as Data;
                setSelection(
                  d.evidenceId
                    ? job!.evidence.find((e: Data) => e.id === d.evidenceId)
                    : {
                        ...d,
                        kind: "Code Context",
                        snippet: job!.evidence.find(
                          (e: Data) =>
                            ["Python AST", "PHP syntax"].includes(e.source) &&
                            e.content.file === d.file &&
                            e.content.line === d.line,
                        )?.content.code,
                      },
                );
                setTab("details");
              }}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
              <Controls showInteractive={false} />
              <MiniMap pannable zoomable nodeColor="var(--primary)" />
            </ReactFlow>
          ) : (
            <div className="empty-canvas">
              <Network size={42} />
              <h2>
                {job?.correlation
                  ? labels[job.correlation.verdict]
                  : job?.status === "running"
                    ? "正在收集证据与分析代码…"
                    : "等待调查结果"}
              </h2>
              <p>
                {job?.error ||
                  job?.correlation?.summary ||
                  "选择真实事件及对应代码仓库，启动 AI Investigation"}
              </p>
            </div>
          )}
        </div>
        <section className="run-console">
          <div className="flex items-center justify-between px-4 py-2 border-b text-xs">
            <strong>执行记录 / RUN CONSOLE</strong>
            <span>{job?.timeline?.length || 0} steps</span>
          </div>
          <div className="overflow-auto px-4 py-2 h-28">
            {job?.timeline?.map((step: Data, i: number) => (
              <div key={i} className="console-row">
                <CheckCircle2 size={12} />
                <span>{String(i + 1).padStart(2, "0")}</span>
                <strong>{step.agent || step.name}</strong>
                <span>{step.tool}</span>
                <span className="grow truncate">
                  {step.note || step.description || step.summary}
                </span>
                <Badge value={step.status} />
              </div>
            ))}
            {job?.warnings?.map((w: string, i: number) => (
              <p className="text-amber-600 text-xs" key={i}>
                {w}
              </p>
            ))}
          </div>
        </section>
      </main>
      <aside className="inspector w-[350px]">
        <div className="tabs">
          <button
            className={tab === "details" ? "active" : ""}
            onClick={() => setTab("details")}
          >
            检查器
          </button>
          <button
            className={tab === "review" ? "active" : ""}
            onClick={() => setTab("review")}
          >
            研判与复核
          </button>
        </div>
        <div className="p-4 space-y-4">
          {tab === "review" ? (
            <>
              <h2>AI Analysis</h2>
              <p>模型输出是未验证推断，静态关联不等于利用成功。</p>
              <Json value={job?.analysis || {}} />
              <h2>Skills / RAG 引用</h2>
              <Json value={job?.agent_context || {}} />
              <h2>自主修复</h2>
              <p>仅对资产中已明确授权且满足修复配方的真实目标执行。</p>
              <Button
                disabled={
                  job?.status !== "completed" || job?.remediation_pending
                }
                onClick={() =>
                  run(async () => {
                    const remediation = await api(
                      "/investigations/" + job!.id + "/repair",
                      "POST",
                    );
                    setJob({ ...job!, remediation });
                  })
                }
              >
                执行授权修复
              </Button>
              <Json value={job?.remediation || {}} />
              <h2>Evidence Reviewer</h2>
              <Json value={job?.review || {}} />
            </>
          ) : selection?.content ? (
            <>
              <Badge value={selection.kind} />
              <h2>{selection.title}</h2>
              <p className="break-all">{selection.provenance}</p>
              <small className="block break-all">
                SHA-256 · {selection.sha256}
              </small>
              <Json value={selection.content} />
            </>
          ) : match ? (
            <>
              <Badge value={match.finding.cwe} />
              <h2>{selection?.label || match.finding.type}</h2>
              <p>
                {match.finding.file}:{match.finding.line} · {match.finding.rule}
              </p>
              {selection?.kind === "Code Context" && (
                <p>
                  所选函数：{selection.file}:{selection.line}
                </p>
              )}
              <Code
                code={selection?.snippet || match.finding.code}
                start={
                  selection?.snippet ? selection.line : match.finding.code_start
                }
                line={
                  !selection?.snippet || selection.file === match.finding.file
                    ? match.finding.line
                    : undefined
                }
              />
              <h3>关联依据</h3>
              <ul className="reasons">
                {match.reasons.map((reason: string, i: number) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
              <h3>修复建议</h3>
              <p>{match.finding.fix}</p>
              <Code code={match.finding.patch} />
              <details>
                <summary>证据引用与边界</summary>
                <Json
                  value={{
                    evidence_ids: match.evidence_ids,
                    limitations: match.limitations,
                  }}
                />
              </details>
            </>
          ) : (
            <Empty text="点击节点或证据查看原始字段、代码及关联依据" />
          )}
        </div>
      </aside>
    </div>
  );
}
