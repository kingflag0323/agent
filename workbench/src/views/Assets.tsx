import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, Data, fmt } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Json } from "@/components/Common";
import { useThemeStore } from "@/store/theme";
const blank: Data = {
  name: "",
  host: "",
  owner: "",
  environment: "test",
  description: "",
  project_id: "",
  web_path: "/",
  web_url: "",
  tags: [],
  ssh_port: 22,
  ssh_user: "",
  key_path: "",
  fingerprint: "",
  remote_root: "",
  allowed_files: [],
  verify_argv: [],
  auto_repair: false,
};
export function Assets({ run }: { run: (fn: () => Promise<any>) => void }) {
  const [rows, setRows] = useState<Data[]>([]),
    [projects, setProjects] = useState<Data[]>([]),
    [draft, setDraft] = useState<Data>({ ...blank }),
    [id, setId] = useState(""),
    [query, setQuery] = useState(""),
    [editor, setEditor] = useState(false),
    [files, setFiles] = useState(""),
    [tags, setTags] = useState(""),
    [argv, setArgv] = useState('["python3","-m","pytest","-q"]'),
    [notice, setNotice] = useState<any>(),
    [deleting, setDeleting] = useState(false),
    [discover, setDiscover] = useState(false),
    [cidr, setCidr] = useState("172.20.0.252/32"),
    [portText, setPortText] = useState("22,80,443,8080,8081,3306"),
    [discovery, setDiscovery] = useState<Data>(),
    [busy, setBusy] = useState(false);
  const theme = useThemeStore((s) => s.theme);
  const refresh = async () => {
    setRows(await api("/assets"));
    setProjects(await api("/projects"));
  };
  useEffect(() => {
    run(refresh);
  }, []);
  useEffect(() => {
    if (!discovery || !["queued", "running"].includes(discovery.status)) return;
    const t = setTimeout(
      () =>
        run(async () => {
          const d = await api("/assets/discovery/" + discovery.id);
          setDiscovery(d);
          await refresh();
        }),
      1000,
    );
    return () => clearTimeout(t);
  }, [discovery]);
  const edit = (a?: Data) => {
    const d = { ...blank, ...a };
    setId(a?.id || "");
    setDraft(d);
    setFiles(d.allowed_files.join("\n"));
    setTags(d.tags.join(", "));
    setArgv(
      JSON.stringify(
        d.verify_argv.length
          ? d.verify_argv
          : ["python3", "-m", "pytest", "-q"],
      ),
    );
    setNotice(undefined);
    setDeleting(false);
    setEditor(true);
  };
  const selected = rows.find((a) => a.id === id);
  const filtered = rows.filter((a) =>
    [a.name, a.host, a.owner, ...(a.tags || [])]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const graph = useMemo(() => {
    const environments = [
      ...new Set(filtered.map((a) => a.environment || "未分组")),
    ];
    const nodes: any[] = [];
    const edges: any[] = [];
    let top = 0;
    for (const env of environments) {
      const group = filtered.filter((a) => (a.environment || "未分组") === env);
      const groupId = "group-" + env;
      nodes.push({
        id: groupId,
        type: "input",
        sourcePosition: Position.Right,
        position: { x: 25, y: top + 40 },
        data: { label: env + " · 逻辑分组" },
        style: {
          background: "var(--card)",
          color: "var(--foreground)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          width: 160,
        },
      });
      group.forEach((a, i) => {
        nodes.push({
          id: a.id,
          type: "output",
          targetPosition: Position.Left,
          position: {
            x: 300 + (i % 2) * 260,
            y: top + Math.floor(i / 2) * 110,
          },
          data: {
            label: (
              <div className="text-left">
                <strong>{a.name}</strong>
                <div className="text-xs mt-1">{a.host}</div>
                <div className="text-[10px] mt-1 opacity-70">
                  {a.observed_ports?.length
                    ? "TCP " + a.observed_ports.join(" / ")
                    : "已登记 · 未探测"}
                  {a.project_id ? " · 已绑定源码" : ""}
                </div>
              </div>
            ),
          },
          style: {
            background: a.id === id ? "var(--accent)" : "var(--card)",
            color: "var(--foreground)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            width: 220,
          },
        });
        edges.push({
          id: "e-" + a.id,
          source: groupId,
          target: a.id,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "var(--primary)" },
        });
      });
      top += Math.max(1, Math.ceil(group.length / 2)) * 110 + 75;
    }
    return { nodes, edges };
  }, [rows, query, id]);
  const save = () =>
    run(async () => {
      setBusy(true);
      try {
        const body: Data = {};
        Object.keys(blank).forEach((k) => (body[k] = draft[k] ?? blank[k]));
        body.allowed_files = files
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean);
        body.tags = tags
          .split(/[,，]/)
          .map((s) => s.trim())
          .filter(Boolean);
        body.verify_argv = JSON.parse(argv);
        const a = await api(
          "/assets" + (id ? "/" + id : ""),
          id ? "PUT" : "POST",
          body,
        );
        await refresh();
        setId(a.id);
        setEditor(false);
        setNotice({ message: "资产已保存" });
      } finally {
        setBusy(false);
      }
    });
  return (
    <div className="h-full flex">
      <aside className="w-64 shrink-0 border-r bg-card flex flex-col">
        <div className="pane-heading">
          <h2>资产列表</h2>
          <span className="text-xs">{rows.length}</span>
        </div>
        <div className="p-3">
          <input
            className="w-full"
            placeholder="搜索名称 / IP / 标签"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="overflow-auto">
          {filtered.map((a) => (
            <button
              key={a.id}
              className={"evidence-item " + (id === a.id ? "selected" : "")}
              onClick={() => {
                setId(a.id);
                setEditor(false);
                setDeleting(false);
                setNotice(undefined);
              }}
            >
              <strong>{a.name}</strong>
              <small>
                {a.host} · {a.environment}
              </small>
              {a.tags?.length > 0 && <small>{a.tags.join(" · ")}</small>}
            </button>
          ))}
        </div>
      </aside>
      <main className="flex-1 min-w-0 flex flex-col">
        <div className="pane-heading">
          <div>
            <h1>{editor ? (id ? "编辑资产" : "资产登记") : "资产拓扑"}</h1>
            <p>
              {editor
                ? "登记资产、绑定源码及配置明确的修复范围"
                : "连线表示登记资产的环境分组，不代表实测网络链路；扫描只探测指定 TCP 端口。"}
            </p>
          </div>
          <div className="flex gap-2">
            {editor ? (
              <Button variant="outline" onClick={() => setEditor(false)}>
                返回拓扑
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => setDiscover(!discover)}
                >
                  发现内网资产
                </Button>
                <Button onClick={() => edit()}>新增资产</Button>
              </>
            )}
          </div>
        </div>
        {discover && !editor && (
          <section className="px-5 py-3 border-b space-y-2">
            <div className="flex gap-3 items-center">
              <label className="flex flex-col text-xs gap-1">
                目标 IPv4 / CIDR
                <input
                  aria-label="发现目标"
                  value={cidr}
                  onChange={(e) => setCidr(e.target.value)}
                />
              </label>
              <label className="flex flex-col text-xs gap-1 grow">
                TCP 端口（逗号分隔）
                <input
                  aria-label="发现端口"
                  value={portText}
                  onChange={(e) => setPortText(e.target.value)}
                />
              </label>
              <Button
                disabled={["queued", "running"].includes(discovery?.status)}
                onClick={() =>
                  run(async () => {
                    setDiscovery(
                      await api("/assets/discovery", "POST", {
                        cidr,
                        ports: portText.split(",").map((s) => Number(s.trim())),
                      }),
                    );
                  })
                }
              >
                开始发现并入库
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              仅允许 RFC1918 内网，单次最多 /24、12
              个端口；发现开放端口后登记资产，不尝试登录。没有响应不等于主机离线。
            </p>
            {discovery && (
              <p className="text-sm">
                {discovery.status} · 已检查 {discovery.checked}/
                {discovery.total} · 发现 {discovery.found.length} 台
                {discovery.error ? " · " + discovery.error : ""}
              </p>
            )}
          </section>
        )}
        {editor ? (
          <div className="overflow-auto p-6 space-y-5">
            <div className="grid grid-cols-2 gap-4">
              {[
                ["name", "资产名称"],
                ["host", "主机 IP / 域名"],
                ["owner", "负责人"],
                ["environment", "环境"],
                ["description", "资产说明"],
                ["web_path", "Web 部署前缀，例如 /pikachu"],
                ["web_url", "Web 服务地址，例如 http://172.20.0.252:12348"],
              ].map(([k, l]) => (
                <label key={k} className="flex flex-col gap-1 text-sm">
                  {l}
                  <input
                    aria-label={l}
                    value={draft[k]}
                    onChange={(e) =>
                      setDraft({ ...draft, [k]: e.target.value })
                    }
                  />
                </label>
              ))}
              <label className="flex flex-col gap-1 text-sm">
                关联代码项目
                <select
                  aria-label="资产代码项目"
                  value={draft.project_id}
                  onChange={(e) =>
                    setDraft({ ...draft, project_id: e.target.value })
                  }
                >
                  <option value="">未绑定</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                资产标签（逗号分隔）
                <input value={tags} onChange={(e) => setTags(e.target.value)} />
              </label>
            </div>
            <details className="card">
              <summary>SSH 与自主修复授权</summary>
              <p className="text-sm my-4">
                私钥仅保存在本机，登记路径不会上传密钥；主机指纹须先核实。当前自动配方仅支持特定
                SQLite 拼接查询，不支持 PHP 自动修改。
              </p>
              <div className="grid grid-cols-2 gap-4">
                {[
                  ["ssh_user", "SSH 用户"],
                  ["ssh_port", "SSH 端口"],
                  ["key_path", "本机私钥完整路径"],
                  ["fingerprint", "主机指纹 SHA256:…"],
                  ["remote_root", "远程代码根目录"],
                ].map(([k, l]) => (
                  <label key={k} className="flex flex-col gap-1 text-sm">
                    {l}
                    <input
                      value={draft[k]}
                      type={k === "ssh_port" ? "number" : "text"}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          [k]:
                            k === "ssh_port"
                              ? Number(e.target.value)
                              : e.target.value,
                        })
                      }
                    />
                  </label>
                ))}
              </div>
              <label className="flex flex-col gap-1 text-sm my-4">
                授权修复文件（每行一个 .py 相对路径）
                <textarea
                  rows={3}
                  value={files}
                  onChange={(e) => setFiles(e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                验证命令参数（JSON 数组）
                <input value={argv} onChange={(e) => setArgv(e.target.value)} />
              </label>
              <label className="flex items-center gap-2 mt-4 text-sm">
                <input
                  type="checkbox"
                  checked={draft.auto_repair}
                  onChange={(e) =>
                    setDraft({ ...draft, auto_repair: e.target.checked })
                  }
                />
                授权在上述范围内自主修复、验证及失败回滚
              </label>
            </details>
            <Button disabled={busy} onClick={save}>
              保存资产
            </Button>
          </div>
        ) : (
          <div className="flex-1 min-h-0 relative">
            <ReactFlow
              key={rows.length + "-" + query}
              nodes={graph.nodes}
              edges={graph.edges}
              fitView
              fitViewOptions={{ maxZoom: 1.1, padding: 0.25 }}
              colorMode={theme}
              nodesConnectable={false}
              nodesDraggable={false}
              onNodeClick={(_, n) => {
                if (!n.id.startsWith("group-")) {
                  setId(n.id);
                  setNotice(undefined);
                }
              }}
            >
              <Background />
              <Controls showInteractive={false} />
            </ReactFlow>
            {!rows.length && (
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="card text-center">
                  <h2>建立你的资产视图</h2>
                  <p>新增资产或扫描指定内网范围，发现结果会自动入库。</p>
                </div>
              </div>
            )}
            {selected && (
              <aside className="absolute top-4 right-4 w-72 card space-y-3 shadow-lg">
                <h2>{selected.name}</h2>
                <p>
                  {selected.host} · {selected.environment}
                </p>
                <p className="text-sm">
                  {selected.description || "未填写说明"}
                </p>
                <small>
                  源码：
                  {projects.find((p) => p.id === selected.project_id)?.name ||
                    "未绑定"}
                </small>
                <small>最近发现：{fmt(selected.last_seen)}</small>
                <p className="text-xs">
                  开放端口：{selected.observed_ports?.join(", ") || "未探测"}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => edit(selected)}>
                    编辑资产
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDeleting(!deleting)}
                  >
                    删除
                  </Button>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    run(async () =>
                      setNotice(await api("/assets/" + id + "/test", "POST")),
                    )
                  }
                >
                  测试 SSH 连接
                </Button>
                {deleting && (
                  <Button
                    size="sm"
                    onClick={() =>
                      run(async () => {
                        await api("/assets/" + id, "DELETE");
                        setId("");
                        setDeleting(false);
                        await refresh();
                      })
                    }
                  >
                    确认删除资产
                  </Button>
                )}
              </aside>
            )}
          </div>
        )}
        {notice && (
          <div className="px-5 py-2 border-t">
            <Json value={notice} />
          </div>
        )}
      </main>
    </div>
  );
}
