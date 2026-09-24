import { useEffect, useMemo, useState } from "react";
import {
  FileCode2,
  Download,
  Layers,
  Search,
  Network,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";
import { api, Data, fmt, labels } from "@/lib/api";
import { Badge, Code, Empty, Json } from "@/components/Common";
import { Button } from "@/components/ui/button";
export function Canvas({
  id,
  selectJob,
  run,
}: {
  id: string | null;
  selectJob: (id: string) => void;
  run: (fn: () => Promise<any>) => void;
}) {
  const [jobs, setJobs] = useState<Data[]>([]),
    [job, setJob] = useState<Data>(),
    [selection, setSelection] = useState<Data | null>(null),
    [matchIndex, setMatchIndex] = useState(0),
    [tab, setTab] = useState("details");
  useEffect(() => {
    run(async () => {
      const rows = await api("/investigations");
      setJobs(rows);
      if (!id && rows.length) selectJob(rows[0].id);
    });
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
  const pathNodes = useMemo(() => {
    if (!match) return [];
    return [
      {
        role: "攻击入口",
        label: (match.entry.method || "HTTP") + " " + match.entry.path,
        location: "XDR HTTP 证据",
        evidenceId: match.entry.evidence_id,
      },
      ...match.chain.map((n: Data, i: number) => ({
        role: i === match.chain.length - 1 ? "漏洞位置" : "代码路径",
        label: n.name + "()",
        location: n.file + ":" + n.line,
        sink: i === match.chain.length - 1,
        file: n.file,
        line: n.line,
      })),
    ];
  }, [match]);

  const selectPathNode = (node: Data) => {
    setSelection(
      node.evidenceId
        ? job!.evidence.find((e: Data) => e.id === node.evidenceId)
        : {
            ...node,
            kind: "Code Context",
            snippet: job!.evidence.find(
              (e: Data) =>
                ["Python AST", "PHP syntax"].includes(e.source) &&
                e.content.file === node.file &&
                e.content.line === node.line,
            )?.content.code,
          },
    );
    setTab("details");
  };
  return (
    <div className="flex h-full min-h-0">
      <aside className="w-64 shrink-0 border-r bg-card flex flex-col">
        <div className="pane-heading">
          <Layers size={16} />
          <h2>调查思维链</h2>
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
            <h2>{job?.event.name || "调查过程与攻击代码关联"}</h2>
            <p>{job ? job.id : "执行节点、证据、攻击路径与代码位置统一呈现"}</p>
          </div>
          <div className="flex gap-2 items-center">
            {job && <Badge value={job.status} />}
            {["docx", "markdown", "json"].map((format) => (
              <Button
                key={format}
                size="sm"
                variant={format === "docx" ? "default" : "outline"}
                disabled={
                  job?.status !== "completed" || job?.remediation_pending
                }
                onClick={() =>
                  run(async () => {
                    await window.desktop.exportReport(job!.id, format);
                  })
                }
              >
                {format === "docx" && <Download size={14} />}
                {format === "docx"
                  ? "导出 Word"
                  : format === "markdown"
                    ? "MD"
                    : "JSON"}
              </Button>
            ))}
          </div>
        </div>
        <section className="chain-visual">
          <div className="chain-heading">
            <div>
              <span className="eyebrow">ATTACK TO CODE CORRELATION</span>
              <h2>
                <Network size={15} />
                攻击路径与漏洞定位
              </h2>
              <p>
                {job?.correlation?.summary || "等待智能体收集证据并关联代码"}
              </p>
            </div>
            {job?.correlation?.matches?.length > 1 && (
              <select
                aria-label="关联漏洞"
                value={matchIndex}
                onChange={(e) => {
                  setMatchIndex(Number(e.target.value));
                  setSelection(null);
                }}
              >
                {job?.correlation.matches.map((item: Data, index: number) => (
                  <option key={index} value={index}>
                    {item.finding.file}:{item.finding.line}
                  </option>
                ))}
              </select>
            )}
          </div>
          {match ? (
            <div className="attack-path">
              {pathNodes.map((node: Data, index: number) => (
                <div className="contents" key={index}>
                  {index > 0 && (
                    <span className="chain-arrow">
                      <ChevronRight size={18} />
                    </span>
                  )}
                  <button
                    className={`chain-node ${node.sink ? "sink" : ""} ${selection?.label === node.label ? "active" : ""}`}
                    onClick={() => selectPathNode(node)}
                  >
                    <span className="chain-step">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="chain-role">
                      <FileCode2 size={13} />
                      {node.role}
                    </span>
                    <strong>{node.label}</strong>
                    <small>{node.location}</small>
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="chain-empty">
              <Network size={28} />
              <div>
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
            </div>
          )}
        </section>
        <section className="investigation-timeline">
          <div className="timeline-heading">
            <div>
              <span className="eyebrow">AGENT EXECUTION</span>
              <h2>调查执行过程</h2>
            </div>
            <span>{job?.timeline?.length || 0} 个节点</span>
          </div>
          <div className="timeline-list">
            {job?.timeline?.map((step: Data, i: number) => (
              <article key={i} className="timeline-step investigation-step">
                <span className="timeline-step-number">
                  <CheckCircle2 size={14} />
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3>{step.agent || step.name}</h3>
                  <p>{step.note || step.description || step.summary}</p>
                  <small>
                    {step.tool}
                    {step.time ? ` · ${fmt(step.time)}` : ""}
                  </small>
                </div>
                <Badge value={step.status} />
              </article>
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
