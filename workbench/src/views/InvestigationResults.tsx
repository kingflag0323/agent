import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Crosshair,
  Download,
  FileCode2,
  FileText,
  Fingerprint,
  Network,
  Server,
  ShieldAlert,
} from "lucide-react";
import { api, Data, fmt } from "@/lib/api";
import { Badge, Empty, Json } from "@/components/Common";
import { Button } from "@/components/ui/button";

function sourceIp(job?: Data) {
  if (job?.event?.source_ip) return job.event.source_ip;
  for (const evidence of job?.evidence || []) {
    const stack = [evidence.content];
    while (stack.length) {
      const value = stack.pop();
      if (value && typeof value === "object") {
        if (!Array.isArray(value) && (value.srcIp || value.sourceIp))
          return value.srcIp || value.sourceIp;
        stack.push(...(Array.isArray(value) ? value : Object.values(value)));
      }
    }
  }
  return "来源地址未提供";
}

const confidenceLabels: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};
const attackLabels: Record<string, string> = {
  "SQL Injection": "SQL 注入",
  "Command Injection": "命令注入",
  "Code Injection": "代码注入",
};
const attackLabel = (value?: string) =>
  attackLabels[value || ""] || value || "未知类型";

export function InvestigationResults({
  id,
  selectJob,
  run,
}: {
  id: string | null;
  selectJob: (id: string) => void;
  run: (fn: () => Promise<any>) => void;
}) {
  const [jobs, setJobs] = useState<Data[]>([]);
  const [job, setJob] = useState<Data>();
  const [selectedEvidence, setSelectedEvidence] = useState<Data | null>(null);

  useEffect(() => {
    run(async () => {
      const rows = (await api("/investigations")).filter(
        (item: Data) => item.status === "completed",
      );
      setJobs(rows);
      if ((!id || !rows.some((item: Data) => item.id === id)) && rows.length)
        selectJob(rows[0].id);
    });
  }, []);

  useEffect(() => {
    if (!id) return;
    let valid = true;
    run(async () => {
      const result = await api("/investigations/" + id);
      if (valid) {
        setJob(result);
        setSelectedEvidence(null);
      }
    });
    return () => {
      valid = false;
    };
  }, [id]);

  const match = job?.correlation?.matches?.[0];
  const attackNodes = useMemo(() => {
    if (!job) return [];
    const nodes: Data[] = [
      {
        role: "攻击者",
        title: sourceIp(job),
        subtitle: attackLabel(job.event.attack_type),
        icon: Crosshair,
      },
      {
        role: "受攻击资产",
        title: job.event.asset_ip || job.event.asset,
        subtitle: job.event.asset,
        icon: Server,
      },
    ];
    if (match) {
      nodes.push({
        role: "攻击入口",
        title: `${match.entry.method || "HTTP"} ${match.entry.path}`,
        subtitle: "XDR 请求证据",
        icon: Network,
      });
      for (const [index, item] of match.chain.entries())
        nodes.push({
          role: index === match.chain.length - 1 ? "漏洞落点" : "代码调用",
          title: `${item.name}()`,
          subtitle: `${item.file}:${item.line}`,
          icon: index === match.chain.length - 1 ? ShieldAlert : FileCode2,
          sink: index === match.chain.length - 1,
        });
    }
    return nodes;
  }, [job, match]);

  const evidenceChain = useMemo(() => {
    if (!job) return [];
    const referenced = new Set(match?.evidence_ids || []);
    const picked: Data[] = [];
    const add = (item?: Data) => {
      if (item && !picked.some((current) => current.id === item.id))
        picked.push(item);
    };
    for (const title of [
      "安全事件",
      "关联告警 / HTTP 举证",
      "网络日志（时间/IP 关联）",
      "受影响资产",
    ])
      add(job.evidence.find((item: Data) => item.title === title));
    for (const item of job.evidence) if (referenced.has(item.id)) add(item);
    return picked.slice(0, 14);
  }, [job, match]);

  const exportReport = (format: string) =>
    run(async () => {
      await window.desktop.exportReport(job!.id, format);
    });

  return (
    <div className="results-page">
      <header className="results-header">
        <div>
          <span className="eyebrow">INVESTIGATION RESULT</span>
          <h1>调查结果</h1>
          <p>攻击链、证据链、漏洞定位和正式报告统一展示</p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={!job}
            onClick={() => exportReport("docx")}
          >
            <Download size={14} />
            导出 Word
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!job}
            onClick={() => exportReport("markdown")}
          >
            MD
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!job}
            onClick={() => exportReport("json")}
          >
            JSON
          </Button>
        </div>
      </header>

      <div className="results-layout">
        <aside className="result-list">
          <div className="result-list-heading">
            <FileText size={15} />
            已完成调查 <span>{jobs.length}</span>
          </div>
          <div className="result-list-scroll">
            {jobs.map((item) => (
              <button
                key={item.id}
                className={item.id === id ? "selected" : ""}
                onClick={() => selectJob(item.id)}
              >
                <span>
                  <Badge value={item.event.severity} />
                  {attackLabel(item.event.attack_type)}
                </span>
                <strong>{item.event.name}</strong>
                <small>
                  {item.event.asset_ip} · {fmt(item.completed_at)}
                </small>
              </button>
            ))}
          </div>
        </aside>

        <main className="result-document">
          {!job ? (
            <Empty text="完成调查后将在这里生成攻击链与证据链" />
          ) : (
            <>
              <section className="result-hero">
                <div>
                  <div className="flex gap-2 mb-2">
                    <Badge value={job.event.severity} />
                    <Badge value={job.correlation.verdict} />
                  </div>
                  <h2>{job.event.name}</h2>
                  <p>{job.correlation.summary}</p>
                </div>
                <div className="result-confidence">
                  <span>关联置信度</span>
                  <strong>
                    {confidenceLabels[job.correlation.confidence] ||
                      job.correlation.confidence}
                  </strong>
                  <small>
                    {match
                      ? `${job.correlation.matches.length} 个漏洞候选`
                      : "未建立代码关联"}
                  </small>
                </div>
              </section>

              <section className="result-facts">
                <article>
                  <span>攻击者来源</span>
                  <strong>{sourceIp(job)}</strong>
                </article>
                <article>
                  <span>目标资产</span>
                  <strong>{job.event.asset_ip || job.event.asset}</strong>
                </article>
                <article>
                  <span>攻击类型</span>
                  <strong>
                    {attackLabel(
                      job.correlation.attack_type || job.event.attack_type,
                    )}
                  </strong>
                </article>
                <article>
                  <span>代码快照</span>
                  <strong>
                    {String(job.snapshot || "未生成").slice(0, 14)}…
                  </strong>
                </article>
              </section>

              <section className="result-section">
                <div className="result-section-heading">
                  <div>
                    <span className="eyebrow">ATTACK PATH</span>
                    <h2>攻击者攻击链路</h2>
                  </div>
                  <small>从来源到漏洞代码的可核查路径</small>
                </div>
                <div className="result-attack-chain">
                  {attackNodes.map((node, index) => {
                    const Icon = node.icon;
                    return (
                      <div className="contents" key={`${node.role}-${index}`}>
                        {index > 0 && (
                          <span className="result-chain-arrow">
                            <ArrowRight size={16} />
                          </span>
                        )}
                        <article
                          className={`result-chain-node ${node.sink ? "sink" : ""}`}
                        >
                          <div>
                            <Icon size={15} />
                            <span>{node.role}</span>
                          </div>
                          <strong>{node.title}</strong>
                          <small>{node.subtitle}</small>
                        </article>
                      </div>
                    );
                  })}
                </div>
              </section>

              <section className="result-section">
                <div className="result-section-heading">
                  <div>
                    <span className="eyebrow">EVIDENCE CHAIN</span>
                    <h2>证据链</h2>
                  </div>
                  <small>
                    {evidenceChain.length} 项关键证据 · 可点击复核原文
                  </small>
                </div>
                <div className="result-evidence-chain">
                  {evidenceChain.map((item, index) => (
                    <button
                      key={item.id}
                      className={`result-evidence-step ${selectedEvidence?.id === item.id ? "selected" : ""}`}
                      onClick={() => setSelectedEvidence(item)}
                    >
                      <span className="result-evidence-index">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                    <span className="result-evidence-icon">
                        <Fingerprint size={15} />
                      </span>
                      <span className="result-evidence-copy">
                        <strong>{item.title}</strong>
                        <small>
                          {item.kind} · {item.source}
                        </small>
                        <code>
                          {item.id} · {item.sha256.slice(0, 16)}…
                        </code>
                      </span>
                      <Badge value={item.kind} />
                    </button>
                  ))}
                </div>
              </section>

              {match && (
                <section className="result-section result-vulnerability">
                  <div className="result-section-heading">
                    <div>
                      <span className="eyebrow">VULNERABILITY</span>
                      <h2>漏洞定位与修复</h2>
                    </div>
                    <Badge value={match.finding.cwe} />
                  </div>
                  <div className="result-vuln-grid">
                    <div>
                      <span>漏洞</span>
                      <strong>{match.finding.type}</strong>
                      <p>
                        {match.finding.file}:{match.finding.line} ·{" "}
                        {match.finding.rule}
                      </p>
                    </div>
                    <div>
                      <span>关联依据</span>
                      <ul>
                        {match.reasons.map((reason: string, index: number) => (
                          <li key={index}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span>修复建议</span>
                      <p>{match.finding.fix}</p>
                    </div>
                  </div>
                </section>
              )}
            </>
          )}
        </main>

        <aside className="result-evidence-inspector">
          <div className="result-list-heading">
            <Fingerprint size={15} />
            证据检查器
          </div>
          {selectedEvidence ? (
            <div className="result-evidence-detail">
              <Badge value={selectedEvidence.kind} />
              <h2>{selectedEvidence.title}</h2>
              <p>{selectedEvidence.source}</p>
              <dl className="details">
                <dt>证据 ID</dt>
                <dd>{selectedEvidence.id}</dd>
                <dt>采集时间</dt>
                <dd>{fmt(selectedEvidence.collected_at)}</dd>
                <dt>来源</dt>
                <dd>{selectedEvidence.provenance}</dd>
                <dt>SHA-256</dt>
                <dd>{selectedEvidence.sha256}</dd>
              </dl>
              <Json value={selectedEvidence.content} />
            </div>
          ) : (
            <Empty text="点击证据链节点查看原始证据、来源与哈希" />
          )}
        </aside>
      </div>
    </div>
  );
}
