import { useEffect, useState } from "react";
import { Activity, ShieldAlert, Server, Radar, RefreshCw, ArrowUpRight, Clock3, ShieldCheck } from "lucide-react";
import { api, fmt, Data } from "@/lib/api";
import { Badge, Empty } from "@/components/Common";
import { Button } from "@/components/ui/button";
const colors = ["#3b82f6", "#8b5cf6", "#14b8a6", "#f59e0b", "#f43f5e"];
const levels = [["critical", "严重", "#ef4444"], ["high", "高危", "#f59e0b"], ["medium", "中危", "#3b82f6"], ["low", "低危", "#14b8a6"], ["info", "信息", "#94a3b8"], ["unknown", "未知", "#64748b"]];
export function Overview({ openEvent, go, run }: { openEvent: (id: string) => void; go: (v: any) => void; run: (fn: () => Promise<any>) => void }) {
  const [d, setD] = useState<Data>();
  const [busy, setBusy] = useState(false);
  const refresh = () => api("/dashboard").then(setD);
  useEffect(() => { run(refresh); const t = setInterval(() => run(refresh), 15000); return () => clearInterval(t); }, []);
  if (!d) return <Empty text="正在读取安全态势…" />;
  const high = (d.severity.high || 0) + (d.severity.critical || 0);
  const ceiling = Math.max(4, Math.ceil(Math.max(0, ...d.trend.map((v: Data) => v.events)) / 4) * 4);
  const x = (i: number) => 44 + i * (628 / Math.max(1, d.trend.length - 1));
  const y = (n: number) => 184 - n / ceiling * 152;
  const points = (key: string) => d.trend.map((v: Data, i: number) => `${x(i)},${y(v[key])}`).join(" ");
  const types = [...d.types].sort((a: Data,b: Data) => b.value-a.value);
  const top = types.slice(0,5);
  if (types.length > 5) top.push({name:"其他类型", value:types.slice(5).reduce((s:number,v:Data)=>s+v.value,0)});
  let offset = 0;
  const segments = levels.map(([key,label,color]) => { const value = d.severity[key] || 0; const start=offset; offset+=value/Math.max(1,d.total)*100; return {key,label,color,value,start,size:offset-start}; });
  return <div className="page overview-page">
    <header className="overview-header">
      <div><div className="eyebrow">DOUBLE PUPIL / SECURITY OPERATIONS</div><h1>安全态势总览</h1><p>洞察威胁活动，从平台事件开始调查。</p></div>
      <div className="overview-actions"><span className="overview-source"><i className={d.mode === 'live' ? 'live' : ''}/>{d.mode === 'live' ? 'XDR 平台数据' : '演示数据'}</span><Button variant="outline" disabled={busy} onClick={()=>run(async()=>{setBusy(true);try{await api('/events/sync','POST');await refresh();}finally{setBusy(false);}})}><RefreshCw size={14} className={busy?'animate-spin':''}/>{busy?'同步中…':'同步 XDR'}</Button></div>
    </header>
    <div className="overview-scope"><Clock3 size={13}/>{d.mode === 'live' ? '最近 7 天 · 已同步事件' : '演示场景 · 已同步事件'}<span>今日统计以 UTC 为准</span></div>
    <div className="overview-metrics">
      {[["安全事件",d.total,Activity,"blue","当前数据源累计"],["高危与严重",high,ShieldAlert,"amber",d.total?`占已同步事件 ${Math.round(high/d.total*100)}%`:'暂无事件'],["事件关联主机",d.assets,Server,"teal","按事件主机 IP 去重"],["今日事件",d.today,Radar,"violet","UTC 当日新增记录"]].map(([title,value,Icon,tone,caption]:any)=><section className={`overview-metric ${tone}`} key={title}><div className="metric-top"><span>{title}</span><div className="metric-icon"><Icon size={19}/></div></div><strong>{Number(value).toLocaleString()}</strong><small>{caption}</small></section>)}
    </div>
    <div className="overview-charts">
      <section className="overview-panel trend-panel"><div className="overview-panel-heading"><div><h2>威胁活动趋势</h2><p>最近七天的事件变化</p></div><div className="chart-legend"><span><i style={{background:'#3b82f6'}}/>全部事件</span><span><i style={{background:'#f59e0b'}}/>高危与严重</span></div></div>
        <svg viewBox="0 0 704 220" className="overview-trend" role="img" aria-label="最近七天攻击趋势，蓝色为全部事件，橙色为高危与严重事件">
          <defs><linearGradient id="overview-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#3b82f6" stopOpacity=".2"/><stop offset="100%" stopColor="#3b82f6" stopOpacity=".01"/></linearGradient></defs>
          {[0,1,2,3,4].map(i=><g key={i}><line x1="44" x2="672" y1={y(i*ceiling/4)} y2={y(i*ceiling/4)} stroke="var(--border)" strokeDasharray="3 6"/><text x="29" y={y(i*ceiling/4)+4} textAnchor="end">{i*ceiling/4}</text></g>)}
          <polygon points={`44,184 ${points('events')} ${x(d.trend.length-1)},184`} fill="url(#overview-fill)"/>
          {['events','high'].map((key,k)=><g key={key}><polyline points={points(key)} fill="none" stroke={k?'#f59e0b':'#3b82f6'} strokeWidth="2.6" strokeLinejoin="round" strokeDasharray={k?'5 4':undefined}/>{d.trend.map((v:Data,i:number)=><circle key={i} cx={x(i)} cy={y(v[key])} r="3.5" fill="var(--card)" stroke={k?'#f59e0b':'#3b82f6'} strokeWidth="2"><title>{v.date} · {k?'高危与严重':'全部事件'} {v[key]} 起</title></circle>)}</g>)}
          {d.trend.map((v:Data,i:number)=><text key={v.date} x={x(i)} y="212" textAnchor="middle">{v.date}</text>)}
        </svg>
        <div className="trend-summary"><span>统计范围内共 <b>{d.total}</b> 起事件</span><span><i/>其中 <b>{high}</b> 起为高危或严重</span></div>
      </section>
      <section className="overview-panel risk-panel"><div className="overview-panel-heading"><div><h2>风险分布</h2><p>按平台事件等级统计</p></div><ShieldCheck size={19} className="text-muted-foreground"/></div><div className="risk-content"><div className="risk-ring"><svg viewBox="0 0 140 140" role="img" aria-label={`风险分布：${segments.map(s=>`${s.label}${s.value}起`).join('，')}`}><circle cx="70" cy="70" r="54" fill="none" stroke="var(--muted)" strokeWidth="13"/>{segments.filter(s=>s.value).map(s=><circle key={s.key} cx="70" cy="70" r="54" fill="none" stroke={s.color} strokeWidth="13" pathLength="100" strokeDasharray={`${s.size} ${100-s.size}`} strokeDashoffset={-s.start} transform="rotate(-90 70 70)"><title>{s.label}：{s.value} 起</title></circle>)}</svg><div><strong>{d.total}</strong><small>安全事件</small></div></div><div className="risk-legend">{segments.filter(s=>s.value||['critical','high','medium','low'].includes(s.key)).map(s=><div key={s.key}><span><i style={{background:s.color}}/>{s.label}</span><b>{s.value}</b><small>{d.total?Math.round(s.value/d.total*100):0}%</small></div>)}</div></div></section>
    </div>
    <div className="overview-bottom">
      <section className="overview-panel overview-events"><div className="overview-panel-heading"><div><h2>最近安全事件</h2><p>按平台发现时间排序</p></div><Button size="sm" variant="ghost" onClick={()=>go('events')}>全部事件<ArrowUpRight size={14}/></Button></div><div className="overview-table-wrap"><table><thead><tr><th>事件 / 攻击类型</th><th>风险等级</th><th>关联主机</th><th>发现时间</th><th><span className="sr-only">操作</span></th></tr></thead><tbody>{d.recent.map((e:Data)=><tr key={e.id} onClick={()=>openEvent(e.id)}><td><button className="event-title" onClick={ev=>{ev.stopPropagation();openEvent(e.id);}}>{e.name}</button><small className="event-category">{e.attack_type}</small></td><td><Badge value={e.severity}/></td><td className="host-cell">{e.asset_ip||'—'}</td><td className="time-cell">{fmt(e.time)}</td><td><ArrowUpRight size={15} className="text-muted-foreground"/></td></tr>)}</tbody></table>{!d.recent.length&&<Empty text="暂无安全事件，点击同步 XDR 获取平台数据。"/>}</div></section>
      <section className="overview-panel type-panel"><div className="overview-panel-heading"><div><h2>攻击类型</h2><p>平台分类描述与风险标签</p></div><span className="type-count">{types.length} 类</span></div><div className="type-list">{top.map((v:Data,i:number)=><div className="type-item" key={v.name}><div><span className="type-label"><i style={{background:colors[i%colors.length]}}/>{v.name}</span><strong>{v.value}<small> 起</small></strong></div><div className="type-track"><span style={{width:`${v.value/Math.max(1,d.total)*100}%`,background:colors[i%colors.length]}}/></div></div>)}{!top.length&&<Empty text="暂无攻击类型数据"/>}</div><div className="type-note">无可读分类的事件标注为未分类威胁。</div></section>
    </div>
  </div>;
}
