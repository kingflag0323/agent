import { useEffect, useState } from "react";
import { api, Data, fmt, labels } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Json, Empty } from "@/components/Common";
export function Agents({ run }: { run: (fn: () => Promise<any>) => void }) {
  const [tab, setTab] = useState("skills"),
    [rows, setRows] = useState<Data[]>([]),
    [draft, setDraft] = useState<Data>({
      name: "",
      content: "",
      enabled: true,
    }),
    [query, setQuery] = useState(""),
    [hits, setHits] = useState<any>(),
    [selected, setSelected] = useState(""),
    [notice, setNotice] = useState("");
  const refresh = async () =>
    setRows(
      await api(
        tab === "repairs" ? "/remediations" : "/agent/resources/" + tab,
      ),
    );
  useEffect(() => {
    setSelected("");
    setNotice("");
    setDraft({ name: "", content: "", enabled: true });
    setHits(undefined);
    run(refresh);
  }, [tab]);
  return (
    <div className="h-full flex flex-col">
      <div className="pane-heading">
        <div>
          <h1>智能体配置</h1>
          <p>Skills · 本地 RAG · 自主修复记录</p>
        </div>
        <div className="flex gap-2">
          {[
            ["skills", "Skills"],
            ["knowledge", "RAG 知识库"],
            ["repairs", "修复记录"],
          ].map(([k, l]) => (
            <Button
              key={k}
              variant={tab === k ? "default" : "outline"}
              onClick={() => setTab(k)}
            >
              {l}
            </Button>
          ))}
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <aside className="w-72 border-r overflow-auto bg-card">
          {rows.map((r) => (
            <button
              key={r.id}
              className={
                "evidence-item " + (selected === r.id ? "selected" : "")
              }
              onClick={() => {
                setSelected(r.id);
                setDraft(r);
                setNotice("");
              }}
            >
              <strong>{r.name || r.file || r.id}</strong>
              <small>
                {tab === "repairs"
                  ? labels[r.status] || r.status
                  : r.enabled
                    ? "已启用"
                    : "已停用"}{" "}
                · {fmt(r.updated_at || r.created_at)}
              </small>
            </button>
          ))}
          {!rows.length && <Empty text="尚无记录" />}
        </aside>
        <main className="flex-1 overflow-auto p-6 space-y-4">
          {tab === "repairs" ? (
            <>
              <h2>修复执行审计</h2>
              <p>
                查看配方、差异、文件哈希、备份位置、验证输出与回滚状态。没有授权资产时不会发起
                SSH 写入。
              </p>
              <Json
                value={selected ? draft : { message: "选择一条执行记录" }}
              />
            </>
          ) : (
            <>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelected("");
                    setDraft({ name: "", content: "", enabled: true });
                    setNotice("");
                  }}
                >
                  新建
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    run(async () => {
                      const d = await window.desktop.importDocument();
                      if (d) {
                        setSelected("");
                        setDraft({ ...d, enabled: true });
                        setNotice("已读取文件，保存后加入知识配置");
                      }
                    })
                  }
                >
                  从文件导入
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                {tab === "skills"
                  ? "导入 SKILL.md 或文本规范。启用的 Skills 作为调查参考传给模型（最多 5 份，每份前 6000 字），不执行附带脚本，也不能修改 SSH 权限。"
                  : "导入 Markdown / TXT / JSON 知识文档，按中英文关键词分块检索；调查自动引用前 5 个相关片段。当前为本地词法 RAG，无需向量服务。"}
              </p>
              <label className="flex flex-col gap-1">
                名称
                <input
                  aria-label="名称"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <label className="flex flex-col gap-1">
                内容
                <textarea
                  aria-label="内容"
                  className="font-mono text-sm"
                  rows={13}
                  value={draft.content}
                  onChange={(e) =>
                    setDraft({ ...draft, content: e.target.value })
                  }
                />
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) =>
                    setDraft({ ...draft, enabled: e.target.checked })
                  }
                />
                启用该文档
              </label>
              <div className="flex gap-2">
                <Button
                  onClick={() =>
                    run(async () => {
                      const saved = await api(
                        "/agent/resources/" +
                          tab +
                          (selected ? "/" + selected : ""),
                        selected ? "PUT" : "POST",
                        {
                          name: draft.name,
                          content: draft.content,
                          enabled: draft.enabled,
                        },
                      );
                      setDraft(saved);
                      setSelected(saved.id);
                      await refresh();
                      setNotice("已保存；下一次调查生效");
                    })
                  }
                >
                  保存配置
                </Button>
                {selected && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      run(async () => {
                        await api(
                          "/agent/resources/" + tab + "/" + selected,
                          "DELETE",
                        );
                        setSelected("");
                        setDraft({ name: "", content: "", enabled: true });
                        await refresh();
                      })
                    }
                  >
                    删除文档
                  </Button>
                )}
              </div>
              {notice && <p role="status">{notice}</p>}
              {draft.sha256 && (
                <p className="text-xs break-all text-muted-foreground">
                  SHA-256 · {draft.sha256}
                </p>
              )}
              {tab === "knowledge" && (
                <section className="border-t pt-4 space-y-3">
                  <h2>检索测试</h2>
                  <div className="flex gap-2">
                    <input
                      className="grow"
                      placeholder="例如 SQL 注入 参数化查询"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                    <Button
                      variant="outline"
                      onClick={() =>
                        run(async () =>
                          setHits(
                            await api(
                              "/agent/search?q=" + encodeURIComponent(query),
                            ),
                          ),
                        )
                      }
                    >
                      检索
                    </Button>
                  </div>
                  {hits && <Json value={hits} />}
                </section>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
