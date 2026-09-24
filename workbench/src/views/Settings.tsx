import { useEffect, useState } from "react";
import { Save, PlugZap } from "lucide-react";
import { api, Data } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Agents } from "@/views/Agents";
import { Empty } from "@/components/Common";
const secrets = ["token", "access_key", "secret_key", "auth_code", "api_key"];
const fields: Record<string, any[]> = {
  xdr: [
    ["mode", "数据模式", ["demo", "live"]],
    ["base_url", "Base URL"],
    ["auth_type", "认证方式", ["auth_code", "aksk", "token"]],
    ["auth_code", "平台授权码", "secret"],
    ["access_key", "Access Key", "secret"],
    ["secret_key", "Secret Key", "secret"],
    ["auth_header", "自定义认证 Header"],
    ["auth_scheme", "Token 前缀"],
    ["token", "Token", "secret"],
    ["verify_tls", "校验 TLS 证书", "bool"],
    ["ca_bundle", "自定义 CA 文件"],
    ["timeout", "超时（秒）", "number"],
  ],
  llm: [
    ["mode", "模型模式", ["mock", "compatible"]],
    ["base_url", "Base URL"],
    ["api_key", "API Key", "secret"],
    ["model", "模型名称"],
    ["temperature", "Temperature", "number"],
    ["timeout", "超时（秒）", "number"],
    ["max_tokens", "Max Tokens", "number"],
    ["thinking_mode", "DeepSeek 思考模式", ["auto", "disabled", "enabled"]],
  ],
  agent: [
    ["max_steps", "最大步骤", "number"],
    ["timeout", "超时（秒）", "number"],
    ["reviewer", "证据复核", "bool"],
    ["debug", "调试记录", "bool"],
  ],
  workspace: [
    ["working_directory", "代码工作目录"],
    ["report_directory", "报告输出目录"],
  ],
  ti: [
    ["enabled", "启用定时同步", "bool"],
    ["provider", "情报源", ["cisa", "nvd"]],
    ["api_key", "NVD API Key（CISA 无需密钥）", "secret"],
    ["interval_hours", "同步间隔（小时）", "number"],
    ["lookback_days", "NVD 回溯天数", "number"],
  ],
  audit: [
    ["max_files", "最大文件数", "number"],
    ["max_file_kb", "单文件 KB", "number"],
    ["timeout", "超时（秒）", "number"],
  ],
};
export function Settings({
  run,
  onSave,
}: {
  run: (fn: () => Promise<any>) => void;
  onSave: () => void;
}) {
  const [data, setData] = useState<Data>(),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [section, setSection] = useState("llm");
  function populate(d: Data) {
    const v = { ...d };
    for (const group of Object.keys(fields))
      for (const key of secrets)
        if (key + "_configured" in v[group]) v[group][key] = "";
    setData(v);
  }
  useEffect(() => {
    run(async () => populate(await api("/settings")));
  }, []);
  if (!data) return <Empty text="读取本机设置…" />;
  return (
    <div className="h-full flex flex-col">
      <div className="pane-heading">
        <div>
          <div className="eyebrow">WORKSPACE SETTINGS</div>
          <h1>设置</h1>
          <p>凭据保存在本机后台，读取时不会回显；空白保存保留已有值。</p>
        </div>
        <Button
          className={section === "resources" ? "hidden" : ""}
          disabled={busy}
          onClick={() =>
            run(async () => {
              setBusy(true);
              try {
                const body: Data = {};
                for (const [g, list] of Object.entries(fields).filter(
                  ([g]) => g === section,
                )) {
                  body[g] = {};
                  for (const [key] of list) body[g][key] = data[g][key];
                }
                populate({
                  ...(await api("/settings", "PUT", body)),
                  allowed_roots: data.allowed_roots,
                });
                setNotice("配置已保存");
                onSave();
              } finally {
                setBusy(false);
              }
            })
          }
        >
          <Save size={15} />
          保存配置
        </Button>
      </div>
      <div className="flex flex-1 min-h-0">
        <aside className="w-48 shrink-0 border-r p-3 space-y-1 bg-card">
          {[
            ["llm", "AI 模型"],
            ["xdr", "XDR 平台"],
            ["agent", "智能体执行"],
            ["resources", "Skills / RAG / 修复"],
            ["workspace", "工作与输出目录"],
            ["audit", "代码扫描"],
            ["ti", "威胁情报"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={
                "w-full text-left rounded px-3 py-3 text-sm " +
                (section === key
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-accent text-muted-foreground")
              }
              onClick={() => {
                setSection(key);
                setNotice("");
              }}
            >
              {label}
            </button>
          ))}
        </aside>
        <div className="flex-1 min-w-0 overflow-auto">
          {section === "resources" ? (
            <Agents run={run} />
          ) : (
            <div className="p-6">
              {notice && <div className="notice mb-4">{notice}</div>}
              <div>
                {Object.entries(fields)
                  .filter(([group]) => group === section)
                  .map(([group, list]) => (
                    <section className="card" key={group}>
                      <h2>
                        {
                          (
                            {
                              workspace: "工作与输出目录",
                              ti: "威胁情报数据源与定时同步",
                              xdr: "XDR 平台连接",
                              llm: "AI 模型",
                              agent: "智能体执行配置",
                              audit: "代码扫描",
                            } as Data
                          )[group]
                        }
                      </h2>
                      <div className="space-y-4 mt-5">
                        {list.map(([key, title, type]) => (
                          <label className="setting-row" key={key}>
                            <span>{title}</span>
                            {Array.isArray(type) ? (
                              <select
                                aria-label={group + "." + key}
                                value={data[group][key]}
                                onChange={(e) =>
                                  setData({
                                    ...data,
                                    [group]: {
                                      ...data[group],
                                      [key]: e.target.value,
                                    },
                                  })
                                }
                              >
                                {type.map((v) => (
                                  <option value={v} key={v}>
                                    {(
                                      {
                                        auto: "自动（DeepSeek 默认关闭思考）",
                                        disabled: "关闭思考，直接输出研判",
                                        enabled: "启用思考，需增加输出额度",
                                        cisa: "CISA KEV 已知被利用漏洞",
                                        nvd: "NVD 最新 CVE",
                                        demo: "Demo 合成数据",
                                        live: "Live 真实 XDR",
                                        auth_code: "平台授权码",
                                        aksk: "AK/SK 签名",
                                        token: "自定义 Token",
                                        mock: "Mock 离线模式",
                                        compatible: "OpenAI-compatible",
                                      } as Data
                                    )[v] || v}
                                  </option>
                                ))}
                              </select>
                            ) : type === "bool" ? (
                              <input
                                aria-label={group + "." + key}
                                type="checkbox"
                                checked={data[group][key]}
                                onChange={(e) =>
                                  setData({
                                    ...data,
                                    [group]: {
                                      ...data[group],
                                      [key]: e.target.checked,
                                    },
                                  })
                                }
                              />
                            ) : (
                              <input
                                aria-label={group + "." + key}
                                type={
                                  type === "secret"
                                    ? "password"
                                    : type === "number"
                                      ? "number"
                                      : "text"
                                }
                                step={key === "temperature" ? 0.1 : 1}
                                value={data[group][key] ?? ""}
                                placeholder={
                                  type === "secret"
                                    ? data[group][key + "_configured"]
                                      ? "已配置 · 留空保留"
                                      : "尚未配置"
                                    : ""
                                }
                                autoComplete="off"
                                onChange={(e) =>
                                  setData({
                                    ...data,
                                    [group]: {
                                      ...data[group],
                                      [key]:
                                        type === "number"
                                          ? Number(e.target.value)
                                          : e.target.value,
                                    },
                                  })
                                }
                              />
                            )}
                            {group === "workspace" && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  run(async () => {
                                    const p =
                                      await window.desktop.chooseFolder();
                                    if (p)
                                      setData({
                                        ...data,
                                        workspace: {
                                          ...data.workspace,
                                          [key]: p,
                                        },
                                      });
                                  })
                                }
                              >
                                选择目录
                              </Button>
                            )}
                          </label>
                        ))}
                      </div>
                      {group === "ti" && (
                        <p className="mt-4">
                          程序运行期间按计划同步并入库；关闭程序期间不运行，重新启动时补做过期同步。CISA
                          日期表示 KEV 收录，NVD
                          表示发布；微步专有订阅暂未对接。
                        </p>
                      )}
                      {group === "workspace" && (
                        <p className="mt-4">
                          代码工作目录用于后续 Git / ZIP
                          导入及本地目录授权，已有项目位置不迁移；报告输出目录作为原生保存对话框的默认路径。
                        </p>
                      )}
                      {["xdr", "llm"].includes(group) && (
                        <>
                          <p className="my-4">
                            {group === "xdr"
                              ? "只读事件与举证查询。授权码 / AKSK 模式独立签名。"
                              : "启用外部模型会将调查相关证据与代码片段发送到配置服务。"}
                          </p>
                          <Button
                            variant="outline"
                            disabled={busy}
                            onClick={() =>
                              run(async () => {
                                setBusy(true);
                                try {
                                  const r = await api(
                                    "/settings/test/" + group,
                                    "POST",
                                  );
                                  setNotice(r.message);
                                } finally {
                                  setBusy(false);
                                }
                              })
                            }
                          >
                            <PlugZap size={15} />
                            测试已保存配置
                          </Button>
                        </>
                      )}
                    </section>
                  ))}
              </div>
              {section === "workspace" && (
                <section className="card mt-4">
                  <h2>允许导入的本地目录</h2>
                  <pre className="text-xs mt-3 whitespace-pre-wrap">
                    {data.allowed_roots?.join("\n")}
                  </pre>
                </section>
              )}
            </div>
          )}{" "}
        </div>
      </div>
    </div>
  );
}
