import { useEffect, useState } from "react";
import { api, Data, fmt } from "@/lib/api";
import { Badge, Empty } from "@/components/Common";
import { Button } from "@/components/ui/button";
export function Intelligence({
  run,
}: {
  run: (fn: () => Promise<any>) => void;
}) {
  const [data, setData] = useState<Data>({ items: [], sync: [], total: 0 }),
    [q, setQ] = useState(""),
    [provider, setProvider] = useState(""),
    [page, setPage] = useState(1),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<Data>(),
    [notice, setNotice] = useState("");
  const refresh = async () =>
    setData(
      await api(
        "/intelligence?q=" +
          encodeURIComponent(q) +
          "&provider=" +
          provider +
          "&page=" +
          page,
      ),
    );
  useEffect(() => {
    run(refresh);
  }, [q, provider, page]);
  useEffect(() => {
    const t = setInterval(() => run(refresh), 30000);
    return () => clearInterval(t);
  }, [q, provider, page]);
  return (
    <div className="h-full flex flex-col">
      <div className="pane-heading">
        <div>
          <h1>威胁情报</h1>
          <p>公开漏洞动态 · 本地持久化 · 按来源日期排序</p>
        </div>
        <Button
          disabled={busy}
          onClick={() =>
            run(async () => {
              setBusy(true);
              try {
                const r = await api("/intelligence/sync", "POST");
                setNotice(
                  r.status === "completed"
                    ? "同步完成，" + r.count + " 条记录入库"
                    : r.error,
                );
                await refresh();
              } finally {
                setBusy(false);
              }
            })
          }
        >
          {busy ? "同步中…" : "立即同步"}
        </Button>
      </div>
      <div className="px-5 py-3 border-b flex gap-3">
        <input
          className="grow"
          placeholder="搜索 CVE、厂商、产品或漏洞描述"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
        <select
          aria-label="情报来源"
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value);
            setPage(1);
          }}
        >
          <option value="">全部来源</option>
          <option value="cisa">CISA KEV</option>
          <option value="nvd">NVD 最新发布</option>
        </select>
      </div>
      <div className="px-5 py-2 text-xs text-muted-foreground border-b">
        {notice ||
          "CISA 为已被利用漏洞收录动态，NVD 为 CVE 发布动态；不代表本机资产已受影响。API 与定时计划在设置中配置。"}
        {data.sync.map((s: Data) => (
          <span key={s.id} className="ml-3">
            {s.id.toUpperCase()} · 最近成功 {fmt(s.last_success)} · {s.status}
            {s.error ? " · " + s.error : ""}
          </span>
        ))}
      </div>
      <div className="flex flex-1 min-h-0">
        <main className="overflow-auto flex-1 p-5">
          <table>
            <thead>
              <tr>
                <th>CVE / 漏洞</th>
                <th>来源</th>
                <th>等级</th>
                <th>日期</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((r: Data) => (
                <tr
                  key={r.id}
                  className={selected?.id === r.id ? "selected" : ""}
                  onClick={() => setSelected(r)}
                >
                  <td>
                    <strong>{r.cve}</strong>
                    <small>{r.title}</small>
                  </td>
                  <td>
                    {r.provider.toUpperCase()}
                    {r.known_exploited && <small>已知被利用</small>}
                  </td>
                  <td>
                    <Badge value={r.severity} />
                    {r.score != null && <small>CVSS {r.score}</small>}
                  </td>
                  <td>
                    {r.date.slice(0, 10)}
                    <small>{r.date_kind}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.items.length && (
            <Empty text="尚无情报记录，点击立即同步，或在设置中启用定时更新" />
          )}
          <div className="flex gap-3 items-center mt-4">
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              上一页
            </Button>
            <span>
              第 {page} 页 · {data.total} 条
            </span>
            <Button
              variant="outline"
              disabled={page * 30 >= data.total}
              onClick={() => setPage(page + 1)}
            >
              下一页
            </Button>
          </div>
        </main>
        {selected && (
          <aside className="inspector w-[370px] p-5 space-y-4">
            <h2>{selected.cve}</h2>
            <strong>{selected.title}</strong>
            <p>{selected.description}</p>
            <p>
              {selected.vendor} {selected.product}
            </p>
            <h3>处置建议</h3>
            <p>
              {selected.action ||
                "查看原始公告与厂商修复说明，结合资产版本判断。"}
            </p>
            <h3>来源地址</h3>
            {selected.references.map((u: string) => (
              <p key={u} className="break-all text-xs select-text">
                {u}
              </p>
            ))}
            <p className="text-xs">入库时间：{fmt(selected.fetched_at)}</p>
          </aside>
        )}
      </div>
    </div>
  );
}
