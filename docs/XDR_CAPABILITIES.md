# XDR 接口核对与实机状态

原始资料为工作目录中的三份“深信服XDR平台接口开放列表”HTML。三个文件 SHA-256 完全相同：

`b1b82dd1679b4bb46cb9bc489d4b15efbfe6d9738c2fe91d2dda9201db5f52dc`

内容是 Eolink 导出的 `projectJSON`，不是静态页面正文。提取结果为 `xdr-api.json`、`xdr-endpoints.json`、`xdr-api-extracted.txt`。共 **129 个接口**，涵盖大屏、事件、告警、日志、实体、SOAR 历史、工单、白名单、系统巡检、脆弱性、资产、风险主机等。保留原文档，不进行改写。

## 本版实现的只读能力

| 能力 | 方法及文档路径 | 用途 |
|---|---|---|
| 事件 | POST `/api/xdr/v1/incidents/list` | `uuIds` / 最近七天列表；读取 `data.item` |
| 事件举证 | GET `/api/xdr/v1/incidents/:uuid/proof` | 事件 `alertTimeLine`；兼容返回数组/对象 |
| 告警 | POST `/api/xdr/v1/alerts/list` | 仅按事件 `alertIds` 精确查询 |
| 告警举证 | GET `/api/xdr/v1/alerts/:uuid/proof` | HTTP `requestHead`、`requestBody` 等 |
| 网络日志 | POST `/api/xdr/v1/analysislog/networksecurity/list` | 资产目的 IP ±5 分钟；仅视为候选关联证据 |
| 安全日志 | POST `/api/xdr/v1/securitylog/list` | 适配器白名单能力；当前工作流没有日志 ID 时不调用 |
| 资产 | GET `/api/xdr/v1/incidents/:uuid/entities/host` | 事件主机实体代替未完整定义的资产列表 |
| IP / DNS / 文件 / 进程实体 | GET `/api/xdr/v1/incidents/:uuid/entities/{ip,dns,file,process}` | 均存在于文档；默认工作流只选 host/IP，其他为扩展只读工具 |

只读白名单在 `backend/app/xdr/adapter.py`。API 合同测试会核验路径与请求类型是否真实存在于输入文档。不实现封禁、隔离或处置动作。

## 已发现的文档局限

- 接口导出的 `authInfo.status=0` 且认证字段为空；无 token 获取、签名生成或认证交换协议。不能假设一个登录接口。
- 资产 `POST /assets/list` 的响应定义仅包含 `InvalidParameter`，没有完整成功结构。UI 明确标记，当前通过事件主机实体获取资产。
- 无独立 IOC 查询 / 威胁情报 lookup 接口：**Unsupported by current XDR API**。可读取 IP/DNS/file 实体已有 `intelligenceTag` 等，不能伪装成外部查询。
- 告警/网络日志中 `attackResult`、`attackState` 的成功/失败枚举存在端点间差异；事件列表、聚合接口的 severity/status 枚举也不同。保留原始字段；只按各自文档转换已实现的事件字段，不统一猜测攻击结果。
- POST 参数 `paramNotNull` 导出标记不应误当成“所有过滤器必填”，按字段描述和查询语义发送必要参数。现场还需联调。
- Live 同步最多最近 7 天 2000 事件；超过上限明确报错，不保存假装完整的部分结果。每次调查最多 10 条告警举证、50 条网络候选并提示截断。Dashboard 为本机已同步数据口径，不是声称上游全量。

## 实机探测（2026-09-20）

用户提供地址 `172.20.0.140`。

- HTTP 80：Connection refused。
- HTTPS 443：可建立网络连接，默认 TLS 校验报“不受信任的签发者”。
- 仅做无认证诊断时临时跳过证书校验，POST 文档事件列表接口，HTTP 200，JSON：`{"data":{},"message":"token.not.exist","code":"Unknown.GeneralError"}`。
- 未获得真实事件；**不声称真实 XDR 数据已接通**。
- 正式设置仍默认 `verify_tls=true`；已保存 `https://172.20.0.140`，Demo 模式开启。需要 API Token、现场认证 Header/Scheme 与可信证书。系统 sudo 密码不用于 XDR。

现场配置后，先点击“测试已保存的 XDR 配置”，再切换 Live 并同步。Live 失败直接显示错误，不会悄悄混入 Demo 数据。

## 补充认证材料（2026-09-21）

新材料确认 AK/SK HMAC-SHA256 请求签名及平台授权码本地解析，已实现且对照材料 SDK 测试。此前关于认证机制未知的记录仅描述首轮接口文档。补充材料仍无实际密钥/授权码与 CA，尚未通过现场鉴权。详见 [连接配置](XDR_CONNECTION_SETUP.md)。
