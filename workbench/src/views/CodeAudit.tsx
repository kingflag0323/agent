import { useEffect, useState } from "react";
import { FolderOpen, FileCode2, Play, Plus, X } from "lucide-react";
import { api, Data } from "@/lib/api";
import { Badge, Code, Empty } from "@/components/Common";
import { Button } from "@/components/ui/button";
export function CodeAudit({ run }: { run: (fn: () => Promise<any>) => void }) {
  const [projects, setProjects] = useState<Data[]>([]),
    [id, setId] = useState(""),
    [files, setFiles] = useState<string[]>([]),
    [file, setFile] = useState(""),
    [code, setCode] = useState(""),
    [scan, setScan] = useState<Data | null>(null),
    [finding, setFinding] = useState<Data | null>(null),
    [busy, setBusy] = useState(false),
    [add, setAdd] = useState(false),
    [name, setName] = useState(""),
    [source, setSource] = useState("git"),
    [path, setPath] = useState(""),
    [branch, setBranch] = useState("");
  const refresh = async () => {
    const ps = await api("/projects");
    setProjects(ps);
    if (!id && ps.length) setId(ps[0].id);
  };
  useEffect(() => {
    run(refresh);
  }, []);
  useEffect(() => {
    if (!id) return;
    let valid = true;
    setFinding(null);
    setFile("");
    setCode("");
    run(async () => {
      const [fs, s] = await Promise.all([
        api("/projects/" + id + "/files"),
        api("/projects/" + id + "/scan"),
      ]);
      if (valid) {
        setFiles(fs.files);
        setScan(s);
        if (fs.files.length) setFile(fs.files[0]);
      }
    });
    return () => {
      valid = false;
    };
  }, [id]);
  useEffect(() => {
    if (!id || !file) return;
    let valid = true;
    run(async () => {
      const r = await api(
        "/projects/" + id + "/file?path=" + encodeURIComponent(file),
      );
      if (valid) setCode(r.content);
    });
    return () => {
      valid = false;
    };
  }, [id, file]);
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="pane-heading">
        <div>
          <h2>代码安全工作区</h2>
          <p>仓库、静态发现和不可变扫描证据</p>
        </div>
        <div className="flex gap-2">
          <select
            aria-label="代码项目"
            value={id}
            onChange={(e) => setId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <Button size="sm" variant="outline" onClick={() => setAdd(true)}>
            <Plus size={14} />
            导入项目
          </Button>
          <Button
            size="sm"
            disabled={!id || busy}
            onClick={() =>
              run(async () => {
                setBusy(true);
                try {
                  setScan(await api("/projects/" + id + "/scan", "POST"));
                  setFinding(null);
                } finally {
                  setBusy(false);
                }
              })
            }
          >
            <Play size={14} />
            {busy ? "扫描中…" : "运行扫描"}
          </Button>
        </div>
      </div>
      <div className="flex min-h-0 grow">
        <aside className="w-60 border-r bg-card overflow-auto">
          <div className="p-4 flex gap-2 items-center text-xs text-muted-foreground">
            <FolderOpen size={15} />
            SOURCE EXPLORER · {files.length}
          </div>
          {files.map((f) => (
            <button
              className={"file-item " + (file === f ? "selected" : "")}
              key={f}
              onClick={() => {
                setFile(f);
                setFinding(null);
              }}
            >
              <FileCode2 size={14} />
              <span>{f}</span>
            </button>
          ))}
        </aside>
        <div className="grow min-w-0 flex flex-col">
          <div className="p-3 border-b text-xs text-muted-foreground flex gap-3">
            <FileCode2 size={14} />
            {finding
              ? finding.file + " · 扫描证据快照"
              : file + " · 当前工作目录"}
          </div>
          <div className="grow min-h-0 overflow-auto">
            {file ? (
              <Code
                code={finding ? finding.code : code}
                start={finding?.code_start || 1}
                line={finding?.line}
              />
            ) : (
              <Empty text="选择源文件" />
            )}
          </div>
          <section className="border-t bg-card h-[280px] overflow-auto">
            <div className="px-4 py-3 flex justify-between">
              <h2>静态发现 · {scan?.findings?.length || 0}</h2>
              {scan && <Badge value={scan.status} />}
            </div>
            <table>
              <thead>
                <tr>
                  <th>规则 / 类型</th>
                  <th>风险</th>
                  <th>CWE</th>
                  <th>文件 / 行号</th>
                </tr>
              </thead>
              <tbody>
                {scan?.findings?.map((f: Data) => (
                  <tr
                    key={f.id}
                    onClick={() => {
                      setFile(f.file);
                      setFinding(f);
                    }}
                    className={finding?.id === f.id ? "selected" : ""}
                  >
                    <td>
                      {f.rule} · {f.type}
                    </td>
                    <td>
                      <Badge value={f.severity} />
                    </td>
                    <td>{f.cwe}</td>
                    <td>
                      {f.file}:{f.line}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {scan?.errors?.map((e: Data, i: number) => (
              <p key={i} className="p-2 text-destructive">
                {e.file}: {e.error}
              </p>
            ))}
            {!scan && <Empty text="尚未扫描此项目" />}
          </section>
        </div>
        <aside className="inspector w-72 p-4 space-y-4">
          <h2>Finding Inspector</h2>
          {finding ? (
            <>
              <Badge value="Static Finding" />
              <h3>{finding.type}</h3>
              <Badge value={finding.cwe} />
              <p className="text-xs break-all">
                {finding.rule} · {finding.file}:{finding.line}
              </p>
              <small>{finding.source}</small>
              <p>{finding.description}</p>
              <h3>修复建议</h3>
              <p>{finding.fix}</p>
              {finding.patch && <Code code={finding.patch} />}
              <small className="break-all block">
                SHA-256 · {finding.file_sha256}
              </small>
            </>
          ) : (
            <>
              <p>选中静态发现查看代码快照与修复建议。</p>
              <p>
                仓库只做静态读取，不执行代码、依赖或 hook。当前语义分析支持
                Python 与 PHP（有限语法和数据传播规则）。
              </p>
            </>
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
                        const p = await window.desktop.chooseFolder();
                        if (p) setPath(p);
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
                    const p =
                      source === "zip"
                        ? await window.desktop.importZip(name)
                        : await api("/projects", "POST", {
                            name,
                            source,
                            path: source === "local" ? path : "",
                            git_url: source === "git" ? path : "",
                            branch,
                          });
                    if (p) {
                      await refresh();
                      setId(p.id);
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
