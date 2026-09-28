import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bug,
  BrainCircuit,
  FileWarning,
  Play,
  Plus,
  ShieldCheck,
  X,
} from "lucide-react";
import { api, Data } from "@/lib/api";
import { Badge, Code, Empty } from "@/components/Common";
import { Button } from "@/components/ui/button";

export function CodeAudit({ run }: { run: (fn: () => Promise<any>) => void }) {
  const [projects, setProjects] = useState<Data[]>([]);
  const [id, setId] = useState("");
  const [scan, setScan] = useState<Data | null>(null);
  const [finding, setFinding] = useState<Data | null>(null);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [busy, setBusy] = useState(false);
  const [add, setAdd] = useState(false);
  const [name, setName] = useState("");
  const [source, setSource] = useState("git");
  const [path, setPath] = useState("");
  const [branch, setBranch] = useState("");

  const refresh = async () => {
    const rows = await api("/projects");
    setProjects(rows);
    if (!id && rows.length) setId(rows[0].id);
  };

  useEffect(() => {
    run(refresh);
  }, []);

  useEffect(() => {
    if (!id) return;
    let valid = true;
    setFinding(null);
    setQuery("");
    setSeverity("all");
    run(async () => {
      const result = await api("/projects/" + id + "/scan");
      if (valid) setScan(result);
    });
    return () => {
      valid = false;
    };
  }, [id]);

  const findings = (scan?.findings || []) as Data[];
  const visibleFindings = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((item) => {
      const severityMatches = severity === "all" || item.severity === severity;
      const text = [item.rule, item.type, item.cwe, item.file, item.function]
        .join(" ")
        .toLowerCase();
      return severityMatches && (!needle || text.includes(needle));
    });
  }, [findings, query, severity]);
  const highCount = findings.filter((item) =>
    ["critical", "high"].includes(item.severity),
  ).length;
  const affectedFiles = new Set(findings.map((item) => item.file)).size;

  const runScan = () =>
    run(async () => {
      setBusy(true);
      try {
        const result = await api("/projects/" + id + "/scan", "POST");
        setScan(result);
        setFinding(result.findings?.[0] || null);
      } finally {
        setBusy(false);
      }
    });

  return (
    <div className="audit-page">
      <header className="audit-header">
        <div>
          <span className="eyebrow">SAST + LLM CODE AUDIT</span>
          <h2>代码审计</h2>
          <p>规则扫描与大模型分批复核，审计快照持久化供调查关联</p>
        </div>
        <div className="flex gap-2">
          <select
            aria-label="代码项目"
            value={id}
            onChange={(e) => setId(e.target.value)}
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <Button size="sm" variant="outline" onClick={() => setAdd(true)}>
            <Plus size={14} />
            导入项目
          </Button>
          <Button size="sm" disabled={!id || busy} onClick={runScan}>
            <Play size={14} />
            {busy ? "AI 审计中…" : "运行扫描"}
          </Button>
        </div>
      </header>

      <section className="audit-metrics">
        <article>
          <Bug />
          <div>
            <span>漏洞总数</span>
            <strong>{findings.length}</strong>
          </div>
        </article>
        <article className="ai">
          <BrainCircuit />
          <div>
            <span>AI 发现 / 复核</span>
            <strong>
              {(scan?.ai_findings_count || 0) + (scan?.ai_confirmed_count || 0)}
            </strong>
            <small>
              {scan?.ai_audit?.status === "completed"
                ? scan.ai_audit.model
                : scan?.ai_audit?.status === "partial"
                  ? "部分完成"
                  : scan?.ai_audit?.status === "failed"
                    ? "审计失败"
                    : "等待扫描"}
            </small>
          </div>
        </article>
        <article className="risk">
          <AlertTriangle />
          <div>
            <span>高风险</span>
            <strong>{highCount}</strong>
          </div>
        </article>
        <article>
          <FileWarning />
          <div>
            <span>受影响文件</span>
            <strong>{affectedFiles}</strong>
          </div>
        </article>
        <article>
          <ShieldCheck />
          <div>
            <span>已扫描文件</span>
            <strong>{scan?.file_count || 0}</strong>
            <small>
              Python {scan?.python_files || 0} · PHP {scan?.php_files || 0}
            </small>
          </div>
        </article>
      </section>

      <div className="audit-layout">
        <section className="audit-findings">
          <div className="audit-toolbar">
            <div>
              <h3>漏洞清单</h3>
              <p>
                {scan
                  ? `${visibleFindings.length} / ${findings.length} 项发现 · ${scan.scanner}`
                  : "运行扫描后生成不可变证据快照"}
              </p>
            </div>
            <div className="flex gap-2">
              <input
                aria-label="搜索漏洞"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索规则、CWE、文件…"
              />
              <select
                aria-label="漏洞等级"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                <option value="all">全部风险</option>
                <option value="critical">严重</option>
                <option value="high">高危</option>
                <option value="medium">中危</option>
                <option value="low">低危</option>
              </select>
            </div>
          </div>
          {scan && (
            <div className="audit-risk-strip">
              <Badge value={scan.status} />
              <span className="audit-ai-state">
                <BrainCircuit size={12} /> AI 审计 ·{" "}
                {scan.ai_audit?.status || "未运行"}
                {scan.ai_audit?.chunks_analyzed
                  ? ` · ${scan.ai_audit.chunks_analyzed} 分块`
                  : ""}
              </span>
              <span>
                扫描快照 {String(scan.id || "").replace("scan-", "#")}
              </span>
              <span>{scan.created_at}</span>
            </div>
          )}
          <div className="audit-table-wrap">
            {scan ? (
              <table>
                <thead>
                  <tr>
                    <th>风险</th>
                    <th>漏洞 / 规则</th>
                    <th>位置</th>
                    <th>置信度</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleFindings.map((item) => (
                    <tr
                      key={item.id}
                      className={finding?.id === item.id ? "selected" : ""}
                      onClick={() => setFinding(item)}
                    >
                      <td>
                        <Badge value={item.severity} />
                      </td>
                      <td>
                        <strong>{item.type}</strong>
                        <small>
                          {item.rule} · {item.cwe} · {item.source}
                        </small>
                      </td>
                      <td className="audit-location">
                        {item.file}
                        <small>
                          第 {item.line} 行 ·{" "}
                          {item.kind === "AI Finding"
                            ? "AI 定位"
                            : `${item.function}()`}
                        </small>
                      </td>
                      <td>
                        <Badge value={item.confidence} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <Empty text="此项目尚未扫描，点击“运行扫描”开始代码审计" />
            )}
            {scan && visibleFindings.length === 0 && (
              <Empty text="没有符合当前筛选条件的漏洞" />
            )}
            {scan?.errors?.map((error: Data, index: number) => (
              <p key={index} className="p-3 text-xs text-destructive">
                {error.file}: {error.error}
              </p>
            ))}
          </div>
        </section>

        <aside className="audit-detail inspector">
          {finding ? (
            <>
              <div className="audit-detail-heading">
                <div>
                  <Badge value={finding.severity} />
                  <Badge value={finding.cwe} />
                </div>
                <h2>{finding.type}</h2>
                <p>
                  {finding.rule} · {finding.source}
                </p>
              </div>
              <div className="audit-detail-body">
                <dl className="details">
                  <dt>漏洞位置</dt>
                  <dd>
                    {finding.file}:{finding.line}
                  </dd>
                  <dt>所在函数</dt>
                  <dd>
                    {finding.kind === "AI Finding"
                      ? "AI 定位"
                      : `${finding.function}()`}
                  </dd>
                  <dt>置信度</dt>
                  <dd>
                    <Badge value={finding.confidence} />
                  </dd>
                  <dt>审计来源</dt>
                  <dd>{finding.source}</dd>
                </dl>
                {finding.ai_review && (
                  <div className="audit-ai-review">
                    <h3>
                      <BrainCircuit size={14} /> 大模型复核确认
                    </h3>
                    <p>{finding.ai_review.description}</p>
                    <small>
                      {finding.ai_review.model} · {finding.ai_review.confidence}
                    </small>
                  </div>
                )}
                <div>
                  <h3>问题描述</h3>
                  <p>{finding.description}</p>
                </div>
                <div>
                  <h3>漏洞代码</h3>
                  <div className="audit-code-preview">
                    <Code
                      code={finding.code}
                      start={finding.code_start || 1}
                      line={finding.line}
                    />
                  </div>
                </div>
                <div className="audit-fix">
                  <h3>修复建议</h3>
                  <p>{finding.fix}</p>
                </div>
                {finding.patch && (
                  <details>
                    <summary>查看修复示例</summary>
                    <div className="audit-patch-preview">
                      <Code code={finding.patch} />
                    </div>
                  </details>
                )}
                <small className="break-all">
                  文件 SHA-256 · {finding.file_sha256}
                </small>
              </div>
            </>
          ) : (
            <div className="audit-detail-empty">
              <ShieldCheck size={34} />
              <h2>选择一项漏洞</h2>
              <p>右侧仅展示与漏洞有关的代码片段、检测依据和修复建议。</p>
            </div>
          )}
        </aside>
      </div>

      {add && (
        <div className="modal-backdrop">
          <div role="dialog" aria-label="导入代码项目" className="modal">
            <div className="flex justify-between items-center">
              <h2>导入代码项目</h2>
              <Button variant="ghost" size="icon" onClick={() => setAdd(false)}>
                <X size={16} />
              </Button>
            </div>
            <label className="field-label">
              项目名称
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：生产 API"
              />
            </label>
            <label className="field-label">
              来源
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="git">公开 Git 仓库</option>
                <option value="local">本地目录</option>
                <option value="zip">ZIP 文件</option>
              </select>
            </label>
            {source !== "zip" && (
              <label className="field-label">
                {source === "git" ? "HTTPS 仓库地址" : "本地源码目录"}
                <input value={path} onChange={(e) => setPath(e.target.value)} />
                {source === "local" && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      run(async () => {
                        const selected = await window.desktop.chooseFolder();
                        if (selected) setPath(selected);
                      })
                    }
                  >
                    选择目录
                  </Button>
                )}
              </label>
            )}
            {source === "git" && (
              <label className="field-label">
                分支（可留空）
                <input
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                />
              </label>
            )}
            <p>
              本地目录支持用户 Documents、Desktop 及应用管理的代码库；ZIP 上限
              25 MB。
            </p>
            <Button
              disabled={!name || busy}
              onClick={() =>
                run(async () => {
                  setBusy(true);
                  try {
                    const project =
                      source === "zip"
                        ? await window.desktop.importZip(name)
                        : await api("/projects", "POST", {
                            name,
                            source,
                            path: source === "local" ? path : "",
                            git_url: source === "git" ? path : "",
                            branch,
                          });
                    if (project) {
                      await refresh();
                      setId(project.id);
                      setAdd(false);
                    }
                  } finally {
                    setBusy(false);
                  }
                })
              }
            >
              {busy
                ? "导入中…"
                : source === "zip"
                  ? "选择 ZIP 并导入"
                  : "导入项目"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
