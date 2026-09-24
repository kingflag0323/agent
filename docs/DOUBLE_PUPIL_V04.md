# Double Pupil 0.4 — 资产拓扑、情报与 Pikachu 验证

## 导航与交互

- **态势**：只在指标卡统计当前数据源已同步的平台事件、风险、关联主机、当日事件及攻击类型，不把本地 SAST 发现混作 XDR 平台指标。Live 范围为接口同步的最近七天，非平台全历史总量；当日按 UTC 统计。
- **资产**：默认左侧列表 + 大区域资产拓扑。仅点击新增/编辑时打开登记表。连线表示环境逻辑分组，**不表示探测到物理网络链路**。支持标签、负责人、项目、Web URL 与部署前缀，以及既有 SSH 授权配置。
- **发现内网资产**：用户输入 IPv4/CIDR 与 TCP 端口，单次最大 /24、12 个端口，限定 RFC1918。异步任务最多 48 个并发 TCP 连接，按 IP 更新开放端口/最近发现，保留已有名称和代码绑定。不开口不等于离线；不做口令探测。关闭程序时中断，已发现记录保留。
- **威胁情报**：搜索 CVE/厂商/产品、按源筛选、分页、详情与原始参考地址。明确区分 CISA KEV 收录日期与 NVD CVE 发布日期，未提供 CVSS 时不伪造评分。
- **调查思维链**：调查列表与实际工具执行节点、状态、开始/完成时间、动作摘要、证据引用及复核结果。这里是可核查执行记录，不是模型内部推理。保留独立调查画布。
- **设置**：参考提供的二级目录布局，分别管理 AI 模型、XDR 平台、智能体执行、Skills/RAG/修复记录、工作/输出目录、代码扫描及情报源。一级“智能体”入口移除。

工作目录配置即时用于后续 Git/ZIP 导入与本地目录授权；已有项目不迁移，保留其已登记目录访问。报告目录用于原生保存对话框默认位置。只保存当前设置分区，避免其他分区的旧值覆盖新凭据。

## 威胁情报同步

- CISA 官方 JSON：`https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`。主站失败时使用 [CISA 官方 GitHub 镜像](https://github.com/cisagov/kev-data)；记录实际源 URL。数据许可 CC0。
- NVD CVE 2.0：`https://services.nvd.nist.gov/rest/json/cves/2.0`，按最近 1–30 天发布窗口分页，最多 10000 条/次。API Key 可选，只发送给 NVD 官方域名，读取配置不回显。
- 按 `来源:CVE` 幂等入库，重复同步不生成重复记录；失败显示错误、保留此前数据与最后成功时间，不伪装为更新完成。
- 同步间隔 1–168 小时；程序运行时执行，关闭期间不运行，重启补做过期/中断任务。新解压的干净 Demo 默认关闭自动联网，现场工作区单独配置启用。
- 微步专有漏洞订阅接口尚未对接，不将 IP 信誉接口冒充漏洞目录。可使用本版 CISA/NVD 作为请求中“类似平台”的数据源。

参考：[NVD API 文档](https://nvd.nist.gov/developers/vulnerabilities)、[CISA 镜像说明与许可证](https://github.com/cisagov/kev-data)。

## Pikachu 与 PHP

保留用户导入的 Pikachu 仓库；本机项目 ID 为 `proj-e0b86db1122e`，GitHub 快照为 `5e1e8d9…`。现场已确认 HTTP 服务为 `http://172.20.0.252:12348/`，部署前缀 `/`。

复用 Tree-sitter PHP 解析器，增加有限文件内 HTTP 输入 → 赋值 → SQL/命令危险调用规则。对唯一、静态包含的 SQL 包装函数补充源码跳转；无法解析的动态包含不猜测关联。新增规则不替代完整 PHP SAST/污点引擎，也不声称覆盖 Pikachu 全部漏洞类型。

当前源码扫描识别 111 个 PHP 文件、35 处 SQL/命令执行候选，包括：

| 类型 | HTTP 入口 / 参数 | 仓库位置 | 补充追溯 |
|---|---|---|---|
| SQL 注入 | `/vul/sqli/sqli_str.php` / `name` | `vul/sqli/sqli_str.php:29` | 输入第 26 行、拼接第 28 行、`inc/mysql.inc.php:19` |
| 命令注入 | `/vul/rce/rce_ping.php` / `ipaddress` | `vul/rce/rce_ping.php:26`、`:28` | 输入第 22 行，Windows/Linux 分支 |

线上测试只发送不存在用户名、单引号、恒假条件及零行 UNION 的读取请求，不写库、不提取账户数据、不执行系统命令。单引号响应出现 SQL 语法错误，而正确闭合的零行测试不出现该错误。HTTP 200 本身不是漏洞证明。

XDR 对此次测试生成了真实 SQL 注入告警，HTTP 举证与测试请求相符。平台事件主机为发起端 `172.16.125.188`，告警目的地址为 `172.20.0.252:12348`。资产归属和日志查询因此改用关联告警的结构化目的 IP，不使用可由请求者控制的 HTTP Host，也不把平台事件主机直接认作受害目标。

PHP 关联维持 medium 候选等级：仓库快照尚未与容器镜像内容进行哈希比对。SSH 自主修复仍只支持已有的特定 SQLite/Python 配方；本次没有对 Pikachu PHP 或 Docker 执行自动修改。

## Word 报告

调查思维链可直接导出 `.docx`、Markdown、JSON。DOCX 为 python-docx 生成的真实 OOXML 文件，包含事件、平台主机/告警目的地址、代码快照哈希、执行节点表、漏洞位置、关联依据、修复建议、模型辅助研判、限制及证据来源。大型单条原始证据截取前 12000 字并提示完整内容见 JSON。

原始现场报告可能包含流量举证，应存于用户工作区，不放入公开发行源码。发行验收样例使用隔离测试数据。

## 依赖与范围

新增 Tree-sitter 0.25.2、Tree-sitter PHP 0.24.1（MIT）、python-docx 1.2.0（MIT）、lxml 6.1.3（BSD 与所含依赖通知）。相应通知保存在 `docs/licenses/`，均支持 Windows 打包，无需 WSL/PHP 运行环境。

后端与 Windows 桌面验收结果以 `docs/workbench-delivery.json` 和 `docs/screenshots-double-pupil-v04/result.json` 为准；现场闭环摘要见 `docs/double-pupil-v04-live-check.json`。

## DeepSeek 正文输出兼容

AI 设置增加思考模式（自动/开启/关闭）。自动模式仅对官方 `api.deepseek.com` 显式关闭思考，以免输出额度全部消耗于思考而正文为空；其他兼容服务保持默认。请求使用有效 JSON 的有界证据上下文，发送前移除 Cookie 和 Authorization 等头部。只记录模型正文，不保存或展示内部 reasoning_content。输出截断会标记提示，不作为完整分析。

参考：[DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)。

## 态势页面更新

指标卡、事件趋势、风险环图、最近事件及攻击类型采用统一卡片布局，适配日间、夜间和窄窗口。类型名称优先读取平台分类描述；没有描述时使用风险标签或威胁定性，不猜测数字编码。无法识别时显示未分类威胁。已有缓存事件和事件详情均即时转换显示，无需重新同步。
