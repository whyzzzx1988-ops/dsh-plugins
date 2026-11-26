#!/usr/bin/env python3
# DEPENDENCIES: Python stdlib only (>= 3.8).
"""从结构化 JSON 渲染应用可观测报告。

Skill 收集各层结论并输出一份 JSON；本脚本负责评分、校验并渲染最终报告，
避免由模型逐字手写长排版。

评分覆盖四个健康维度——应用、ECS、RDS（仅当应用带 RDS 时）、可用性——
加权成 0-100 的健康分并给出 A/B/C/D 分级。成本独立展示：只承载实际账单
金额和可选的优化说明，绝不参与健康分计算。

用法：
    python3 render_report.py --schema
    python3 render_report.py --validate --input data.json
    python3 render_report.py --input data.json --format md   --output report.md
    python3 render_report.py --input data.json --format html --output report.html
    cat data.json | python3 render_report.py --format md

币种为人民币（¥，国内站）。成本只展示实际账单金额，没有预估字段。
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from typing import Any

STATES = ("healthy", "degraded", "unavailable", "unknown")
CURRENCY = "CNY"

DIMENSIONS = ("application", "ecs", "rds", "availability")

WEIGHTS_WITH_RDS = {"application": 35, "ecs": 30, "rds": 25, "availability": 10}
WEIGHTS_NO_RDS = {"application": 45, "ecs": 45, "availability": 10}

SCHEMA_DOC = """
{
  "meta": {
    "generated_at": "2026-08-26 16:20 UTC+8",
    "app": "shop-api",
    "region": "cn-hangzhou",
    "region_label": "华东1（杭州）",
    "window": "1h",
    "topology": "ecs" | "ecs+rds",
    "data_source": "cloudmonitor" | "fallback"
  },
  "recent_action": null | {
    "time": "2026-09-09 11:20 UTC+8",
    "action": "restart shop-api",
    "verification": "recovered"
  },
  "layers": {
    "application": {
      "state": "healthy" | "degraded" | "unavailable" | "unknown",
      "score": 32, "max_score": 35,
      "evidence": "reachable, response 186 ms; app and Nginx healthy",
      "metrics": [
        {"name": "Reachability", "value": "200 OK", "threshold": "2xx/3xx", "trend": "stable"},
        {"name": "Response time", "value": "186 ms", "threshold": "<800 ms warn", "trend": "stable"},
        {"name": "Error rate", "value": "0.2%", "threshold": "<1% warn", "trend": "flat"}
      ],
      "detail": "one paragraph of plain-language analysis for this layer",
      "reason": "only when state is unknown: why it could not be determined"
    },
    "ecs": {
      "state": "healthy", "score": 27, "max_score": 30,
      "evidence": "1h avg CPU 31%, memory 44%, disk 15%",
      "metrics": [
        {"name": "CPU", "value": "31%", "threshold": "80/95", "trend": "stable"},
        {"name": "Memory", "value": "44%", "threshold": "80/95", "trend": "stable"},
        {"name": "Disk usage", "value": "15%", "threshold": "80/90", "trend": "flat"},
        {"name": "Disk IO", "value": "236 IOPS", "threshold": "vs 2280 limit", "trend": "low"},
        {"name": "Network out", "value": "0.24 Mbps", "threshold": "vs 100 Mbps", "trend": "low"}
      ],
      "detail": "..."
    },
    "rds": null | {
      "state": "degraded", "score": 18, "max_score": 25,
      "evidence": "active connections rose 12 -> 38; watch the pool",
      "metrics": [
        {"name": "Connections", "value": "38", "threshold": "vs 200 max", "trend": "rising"},
        {"name": "Slow SQL", "value": "3 / 1h", "threshold": "<10 warn", "trend": "up"},
        {"name": "Space usage", "value": "22%", "threshold": "80/90", "trend": "flat"},
        {"name": "Row-lock waits", "value": "0", "threshold": "0 ideal", "trend": "flat"}
      ],
      "detail": "..."
    },
    "availability": {
      "state": "healthy", "score": 10, "max_score": 10,
      "evidence": "ECS Running; RDS Running; EIP InUse; SG 80/443 open; no recent system events",
      "metrics": [
        {"name": "ECS status", "value": "Running", "threshold": "Running", "trend": "stable"},
        {"name": "RDS status", "value": "Running", "threshold": "Running", "trend": "stable"},
        {"name": "EIP status", "value": "InUse", "threshold": "InUse", "trend": "stable"},
        {"name": "Exposure", "value": "80/443 only", "threshold": "no 22/3306 to 0.0.0.0/0", "trend": "stable"}
      ],
      "detail": "..."
    }
  },
  "assessment": {
    "health_score": 87,
    "grade": "B", "grade_label": "Good",
    "one_liner": "App healthy; watch the RDS connection trend",
    "narrative": "one or two paragraphs summarizing the whole app's health",
    "previous": null | {"health_score": 72, "grade": "C"},
    "anomalies": [
      {"level": "warn" | "crit", "title": "RDS connections rising", "message": "...", "anchor": "rds"}
    ]
  },
  "cost": null | {
    "state": "healthy" | "unknown",
    "cycle": "2026-08",
    "currency": "CNY",
    "total": 12.40,
    "breakdown": [
      {"product": "ecs", "amount": 7.80},
      {"product": "rds", "amount": 4.60}
    ],
    "evaluation": "utilization-based note, e.g. CPU steady at 31% — right-sized",
    "suggestion": "optional optimization idea; never an estimate of spend",
    "reason": "only when state is unknown: e.g. no actual bill for this cycle yet"
  },
  "recommendations": {
    "immediate": ["..."],
    "short_term": ["..."],
    "long_term": ["..."]
  },
  "unknowns": ["item + why it could not be determined", "..."],
  "next_step": "optional: offer qianwenai-operate when a real fault is found"
}

说明：
- 每个 layer 的 state 必须是：healthy、degraded、unavailable、unknown 之一。
- health_score 等于各层 score 之和；grade 必须与之匹配
  （>=90 A / >=75 B / >=60 C / <60 D）。仅当应用带 RDS 时才给 RDS 打分，
  否则其权重重分配给应用和 ECS。
- 成本只承载实际账单金额，没有预估字段，不要凭空构造；成本绝不计入 health_score。
- 当账期尚无账单时，将 state 设为 "unknown" 并给出 reason，省略 total/breakdown。
- data_source：能拿到云监控 agent 趋势指标（尤其内存）时为 "cloudmonitor"；agent 缺失/异常、
  改用只读云助手瞬时快照或有指标降级时为 "fallback"，降级层的证据里注明「瞬时值、无趋势」，
  两条路径都拿不到的指标标 unknown。
- previous：可选。存在最近一次 observe 结果时填写上次的 health_score/grade，报告标题展示分数变化。
"""


def _state_ok(s: Any) -> bool:
    return isinstance(s, str) and s in STATES


def _grade_for(score: Any) -> str:
    if not isinstance(score, (int, float)):
        return "?"
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _delta_text(assessment: dict) -> str:
    prev = assessment.get("previous")
    if not isinstance(prev, dict):
        return ""
    ps = prev.get("health_score")
    cur = assessment.get("health_score")
    if not isinstance(ps, (int, float)) or not isinstance(cur, (int, float)):
        return ""
    pg = (prev.get("grade") or _grade_for(ps)).upper()
    cg = (assessment.get("grade") or _grade_for(cur)).upper()
    return f"（上次 {pg} {ps} → {cg} {cur}）"


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["[root] top-level JSON must be an object"]

    layers = data.get("layers")
    has_rds = False
    if not isinstance(layers, dict):
        errors.append("[required] layers{} is missing")
        layers = {}
    else:
        for name in ("application", "ecs", "availability"):
            layer = layers.get(name)
            if not isinstance(layer, dict):
                errors.append(f"[required] layers.{name} is missing")
                continue
            if not _state_ok(layer.get("state")):
                errors.append(f"[enum] layers.{name}.state must be one of {STATES}")
            if layer.get("state") == "unknown" and not (layer.get("reason") or "").strip():
                errors.append(f"[rule] layers.{name} is unknown but has no reason")
            if not isinstance(layer.get("score"), (int, float)):
                errors.append(f"[required] layers.{name}.score must be a number")
        rds = layers.get("rds")
        if rds is not None:
            has_rds = True
            if not isinstance(rds, dict) or not _state_ok(rds.get("state")):
                errors.append(f"[enum] layers.rds.state must be one of {STATES}")
            elif not isinstance(rds.get("score"), (int, float)):
                errors.append("[required] layers.rds.score must be a number")

    assessment = data.get("assessment")
    if not isinstance(assessment, dict):
        errors.append("[required] assessment{} is missing")
    else:
        for key in ("health_score", "grade", "grade_label", "one_liner", "narrative"):
            v = assessment.get(key)
            if v is None or (isinstance(v, str) and not v.strip()):
                errors.append(f"[required] assessment.{key} must not be empty")

        score = assessment.get("health_score")
        grade = assessment.get("grade")
        if isinstance(score, (int, float)) and isinstance(grade, str):
            expected = _grade_for(score)
            if grade.upper() != expected:
                errors.append(
                    f"[logic] grade={grade} does not match health_score={score}; "
                    f"expected {expected} (>=90 A / >=75 B / >=60 C / <60 D)"
                )

        if isinstance(score, (int, float)) and isinstance(layers, dict):
            names = ("application", "ecs", "rds", "availability") if has_rds \
                else ("application", "ecs", "availability")
            total = 0
            ok = True
            for name in names:
                s = (layers.get(name) or {}).get("score")
                if isinstance(s, (int, float)):
                    total += s
                else:
                    ok = False
            if ok and abs(total - score) > 0.5:
                errors.append(
                    f"[logic] health_score={score} must equal the sum of layer scores ({total})"
                )

        one_liner = (assessment.get("one_liner") or "").strip().lower()
        if isinstance(score, (int, float)) and score < 60 and one_liner:
            for kw in ("all normal", "everything is fine", "no issues", "running normally", "healthy"):
                if kw in one_liner:
                    errors.append(
                        f"[logic] health_score={score} is below 60 but one_liner suggests a normal status"
                    )
                    break

    cost = data.get("cost")
    if cost is not None:
        if not isinstance(cost, dict):
            errors.append("[type] cost must be an object or null")
        else:
            st = cost.get("state")
            if st not in ("healthy", "unknown"):
                errors.append("[enum] cost.state must be healthy or unknown")
            blob = json.dumps(cost, ensure_ascii=False).lower()
            if "estimate" in blob or "预估" in blob:
                errors.append("[rule] cost must be the ACTUAL billed amount only; no estimate")
            if st == "unknown":
                if not (cost.get("reason") or "").strip():
                    errors.append("[rule] cost is unknown but has no reason")
            else:
                if not isinstance(cost.get("total"), (int, float)):
                    errors.append("[required] cost.total must be a number when state is healthy")
                cur = cost.get("currency")
                if cur and cur != CURRENCY:
                    errors.append(f"[rule] cost.currency should be {CURRENCY} on this site")
    return errors


_BADGE = {
    "healthy": "🟢 正常",
    "degraded": "🟡 可用但有风险",
    "unavailable": "🔴 不可用",
    "unknown": "⚪ 无法判断",
}
_GRADE_ICON = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}
_LAYER_LABEL = {"application": "应用", "ecs": "ECS", "rds": "RDS",
                "availability": "可用性"}
_STATE_ZH = {"healthy": "正常", "degraded": "可用但有风险",
             "unavailable": "不可用", "unknown": "无法判断"}


def _money(amount: Any, currency: str = CURRENCY) -> str:
    sym = "$" if currency == "USD" else "¥"
    try:
        return f"{sym}{float(amount):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _ordered_layers(layers: dict):
    for name in ("application", "ecs", "rds", "availability"):
        layer = layers.get(name)
        if isinstance(layer, dict):
            yield name, layer


def render_md(data: dict) -> str:
    meta = data.get("meta", {}) or {}
    layers = data.get("layers", {}) or {}
    assessment = data.get("assessment", {}) or {}
    cost = data.get("cost")
    rec = data.get("recommendations", {}) or {}
    out: list[str] = []

    grade = (assessment.get("grade") or "?").upper()
    icon = _GRADE_ICON.get(grade, "")
    out.append(f"# 可观测报告 — {meta.get('app', 'application')}")
    out.append("")
    delta = _delta_text(assessment)
    out.append(f"{icon} **{assessment.get('health_score', '?')} / 100** · "
               f"{grade} {assessment.get('grade_label', '')}{delta} · "
               f"{assessment.get('one_liner', '')}".strip())
    out.append("")
    if assessment.get("narrative"):
        out.append(assessment["narrative"])
        out.append("")

    out.append("## 分维度评分")
    out.append("")
    out.append("| 维度 | 评级 | 得分 | 状态 | 证据 |")
    out.append("|---|---|---|---|---|")
    for name, layer in _ordered_layers(layers):
        st = layer.get("state", "unknown")
        out.append(
            f"| {_LAYER_LABEL.get(name, name)} "
            f"| {_BADGE.get(st, st).split(' ')[0]} "
            f"| {layer.get('score', '?')}/{layer.get('max_score', '?')} "
            f"| {_STATE_ZH.get(st, st)} | {(layer.get('evidence') or layer.get('reason') or '').replace('|', '/')} |"
        )
    out.append("")

    anomalies = assessment.get("anomalies") or []
    if anomalies:
        out.append("## 异常")
        for a in anomalies:
            mark = "🔴" if a.get("level") == "crit" else "🟠"
            anchor = a.get("anchor")
            title = a.get("title", "")
            title = f"[{title}](#{anchor})" if anchor else f"**{title}**"
            out.append(f"- {mark} {title}: {a.get('message', '')}")
        out.append("")

    for name, layer in _ordered_layers(layers):
        out.append(f'<a id="{name}"></a>')
        out.append("")
        out.append(f"## {_LAYER_LABEL.get(name, name)}")
        st = layer.get("state", "unknown")
        out.append(f"{_BADGE.get(st, st)} · {layer.get('score', '?')}/{layer.get('max_score', '?')}")
        metrics = layer.get("metrics") or []
        if metrics:
            out.append("")
            out.append("| 指标 | 数值 | 阈值 | 趋势 |")
            out.append("|---|---|---|---|")
            for m in metrics:
                out.append(f"| {m.get('name', '')} | {m.get('value', '')} | "
                           f"{m.get('threshold', '')} | {m.get('trend', '')} |")
        if layer.get("detail"):
            out.append("")
            out.append(layer["detail"])
        out.append("")

    if isinstance(cost, dict):
        out.append("## 成本（实际账单）")
        if cost.get("state") == "unknown":
            out.append(f"- {_BADGE['unknown']} — {cost.get('reason', '当前账期暂无实际账单')}")
        else:
            cur = cost.get("currency", CURRENCY)
            out.append(f"- 账期 {cost.get('cycle', '')}：**{_money(cost.get('total'), cur)}** {cur}")
            for row in cost.get("breakdown", []) or []:
                out.append(f"  - {row.get('product', '?')}: {_money(row.get('amount'), cur)}")
        if cost.get("evaluation"):
            out.append(f"- 评价：{cost['evaluation']}")
        if cost.get("suggestion"):
            out.append(f"- 建议：{cost['suggestion']}")
        out.append("")

    buckets = [("immediate", "立即"), ("short_term", "短期"), ("long_term", "长期")]
    if any(rec.get(k) for k, _ in buckets):
        out.append("## 建议")
        for key, label in buckets:
            items = rec.get(key) or []
            if items:
                out.append(f"**{label}**")
                out += [f"- {i}" for i in items]
        out.append("")

    unknowns = data.get("unknowns") or []
    if unknowns:
        out.append("## 未知 / 无法判断")
        out += [f"- {u}" for u in unknowns]
        out.append("")

    ra = data.get("recent_action")
    if isinstance(ra, dict) and ra.get("action"):
        v = f"（{ra['verification']}）" if ra.get("verification") else ""
        out.append(f"> 最近一次运维：{ra.get('time', '')} {ra['action']}{v}")
        out.append("")

    if data.get("next_step"):
        out.append(f"> 下一步：{data['next_step']}")
        out.append("")

    ctx = " · ".join(str(x) for x in (
        meta.get("region_label") or meta.get("region"),
        f"窗口 {meta.get('window')}" if meta.get("window") else None,
        f"数据源 {meta.get('data_source')}" if meta.get("data_source") else None,
        meta.get("generated_at"),
    ) if x)
    if ctx:
        out.append(f"_数据时间：{ctx}_")
    return "\n".join(out).rstrip() + "\n"


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=False)


_COLOR = {"healthy": "#00b894", "degraded": "#e17055",
          "unavailable": "#d63031", "unknown": "#636e72"}

CSS = """
  :root { --bg:#f5f6fa; --card:#fff; --text:#2d3436; --muted:#636e72; --border:#dfe6e9;
          --green:#00b894; --green-bg:#e6faf3; --orange:#e17055; --red:#d63031; --accent:#6c5ce7; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--text); line-height:1.6; padding:24px 16px; }
  .container { max-width:960px; margin:0 auto; }
  .header { background:linear-gradient(135deg,#6c5ce7,#a29bfe); color:#fff; text-align:center;
            padding:36px 24px; border-radius:12px 12px 0 0; }
  .header h1 { font-size:24px; font-weight:700; margin-bottom:10px; }
  .header .score { font-size:40px; font-weight:800; }
  .header .meta { font-size:13px; opacity:.9; display:flex; gap:20px; justify-content:center;
                  flex-wrap:wrap; margin-top:10px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px;
          padding:24px 28px; margin-bottom:18px; }
  .card:first-of-type { border-radius:0 0 12px 12px; }
  .section-title { font-size:17px; font-weight:700; margin-bottom:14px; padding-bottom:8px;
                   border-bottom:2px solid var(--accent); display:flex; align-items:center; gap:8px; }
  table { width:100%; border-collapse:collapse; margin:10px 0; font-size:14px; }
  th,td { padding:9px 12px; border:1px solid var(--border); text-align:left; }
  th { background:#f8f9fa; font-weight:600; color:var(--muted); }
  .ta-c { text-align:center; }
  .rating { display:inline-block; padding:2px 10px; border-radius:10px; font-size:12px; font-weight:700; }
  .rating-a { background:var(--green-bg); color:#00a376; }
  .rating-b { background:#fff8e1; color:#f39c12; }
  .rating-c { background:#fff3e0; color:#e17055; }
  .rating-d { background:#ffeaea; color:#d63031; }
  .badge { display:inline-block; padding:2px 8px; border-radius:10px; color:#fff; font-size:12px; }
  .highlight { border-left:3px solid var(--green); background:#f0faf6; padding:11px 15px;
               border-radius:0 8px 8px 0; margin:10px 0; font-size:14px; }
  .highlight.warn { background:#fff8e1; border-color:var(--orange); }
  .highlight.crit { background:#ffeaea; border-color:var(--red); }
  .note { color:var(--muted); font-size:13px; margin:6px 0; }
  ul { padding-left:20px; } li { margin:4px 0; font-size:14px; }
  .footer { text-align:center; color:var(--muted); font-size:12px; padding:18px 0; }
"""


def _grade_letter(g: str) -> str:
    return (g or "a").lower()


def _badge_html(st: str) -> str:
    return f'<span class="badge" style="background:{_COLOR.get(st, "#636e72")}">{_esc(_STATE_ZH.get(st, st))}</span>'


def _metric_table(metrics: list) -> str:
    if not metrics:
        return ""
    rows = "".join(
        f'<tr><td>{_esc(m.get("name", ""))}</td>'
        f'<td class="ta-c">{_esc(m.get("value", ""))}</td>'
        f'<td class="ta-c">{_esc(m.get("threshold", ""))}</td>'
        f'<td class="ta-c">{_esc(m.get("trend", ""))}</td></tr>'
        for m in metrics
    )
    return ("<table><tr><th>指标</th><th class='ta-c'>数值</th>"
            "<th class='ta-c'>阈值</th><th class='ta-c'>趋势</th></tr>"
            f"{rows}</table>")


def render_header(meta: dict, assessment: dict) -> str:
    grade = (assessment.get("grade") or "?").upper()
    icon = _GRADE_ICON.get(grade, "")
    delta = _delta_text(assessment)
    delta_html = f'<div class="meta"><span>{_esc(delta)}</span></div>' if delta else ""
    return f"""
<div class="header">
  <h1>{icon} 可观测报告 — {_esc(meta.get('app', 'application'))}</h1>
  <div class="score">{_esc(assessment.get('health_score', '?'))} <span style="font-size:18px">/ 100</span>
    &nbsp;<span class="rating rating-{_grade_letter(grade)}">{grade} · {_esc(assessment.get('grade_label', ''))}</span></div>
  {delta_html}
  <div class="meta">
    <span>{_esc(assessment.get('one_liner', ''))}</span>
  </div>
</div>
"""


def render_overview(layers: dict, assessment: dict) -> str:
    rows = []
    for name, layer in _ordered_layers(layers):
        st = layer.get("state", "unknown")
        rows.append(
            f'<tr><td>{_LAYER_LABEL.get(name, name)}</td>'
            f'<td class="ta-c">{_badge_html(st)}</td>'
            f'<td class="ta-c">{_esc(layer.get("score", "?"))}/{_esc(layer.get("max_score", "?"))}</td>'
            f'<td>{_esc(layer.get("evidence") or layer.get("reason") or "")}</td></tr>'
        )
    anomalies = ""
    for a in assessment.get("anomalies", []) or []:
        lvl = a.get("level", "warn")
        mark = "🔴" if lvl == "crit" else "🟠"
        anchor = a.get("anchor", "")
        link = f' &rarr; <a href="#{_esc(anchor)}">查看该层</a>' if anchor else ""
        anomalies += (f'<div class="highlight {lvl}">{mark} <b>{_esc(a.get("title", ""))}</b>: '
                      f'{_esc(a.get("message", ""))}{link}</div>')
    if not anomalies:
        anomalies = '<div class="highlight">✅ <b>无异常</b> — 各层均在健康阈值内。</div>'
    narrative = f'<p>{_esc(assessment.get("narrative", ""))}</p>' if assessment.get("narrative") else ""
    return f"""
<div class="card">
  <div class="section-title">📊 总览</div>
  {narrative}
  <table>
    <tr><th>维度</th><th class="ta-c">状态</th><th class="ta-c">得分</th><th>证据</th></tr>
    {''.join(rows)}
  </table>
  <p class="note">评级：🟢 A（&ge;90）· 🟡 B（&ge;75）· 🟠 C（&ge;60）· 🔴 D（&lt;60）。成本独立展示，不影响评分。</p>
  {anomalies}
</div>
"""


_LAYER_ICON = {"application": "🌐", "ecs": "🖥️", "rds": "🗄️", "availability": "✅"}


def render_layer_card(name: str, layer: dict) -> str:
    st = layer.get("state", "unknown")
    detail = f'<p>{_esc(layer.get("detail", ""))}</p>' if layer.get("detail") else ""
    return f"""
<div class="card" id="{name}">
  <div class="section-title">{_LAYER_ICON.get(name, '')} {_LAYER_LABEL.get(name, name)}
    &nbsp;{_badge_html(st)}
    &nbsp;<span class="note">{_esc(layer.get('score', '?'))}/{_esc(layer.get('max_score', '?'))}</span></div>
  <p>{_esc(layer.get('evidence') or layer.get('reason') or '')}</p>
  {_metric_table(layer.get('metrics') or [])}
  {detail}
</div>
"""


def render_cost_card(cost: dict) -> str:
    if cost.get("state") == "unknown":
        body = f'<p>{_badge_html("unknown")} {_esc(cost.get("reason", "当前账期暂无实际账单"))}</p>'
    else:
        cur = cost.get("currency", CURRENCY)
        items = "".join(
            f"<li>{_esc(r.get('product', '?'))}: {_esc(_money(r.get('amount'), cur))}</li>"
            for r in (cost.get("breakdown") or [])
        )
        body = (f"<p>账期 {_esc(cost.get('cycle', ''))}："
                f"<strong>{_esc(_money(cost.get('total'), cur))}</strong> {_esc(cur)}</p>"
                f"<ul>{items}</ul>")
    rows = ""
    if cost.get("evaluation"):
        rows += f"<tr><td style='width:140px'><b>评价</b></td><td>{_esc(cost['evaluation'])}</td></tr>"
    if cost.get("suggestion"):
        rows += f"<tr><td><b>建议</b></td><td>{_esc(cost['suggestion'])}</td></tr>"
    table = f"<table>{rows}</table>" if rows else ""
    return f"""
<div class="card" id="cost">
  <div class="section-title">💰 成本（实际账单）</div>
  {body}
  {table}
  <p class="note">仅实际账单金额，绝不预估。成本不影响健康分。</p>
</div>
"""


def render_reco_card(rec: dict) -> str:
    def _ul(items):
        if not items:
            return '<p class="note">无。</p>'
        return "<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>"
    return f"""
<div class="card">
  <div class="section-title">💡 建议</div>
  <h4>⚡ 立即</h4>{_ul(rec.get('immediate') or [])}
  <h4 style="margin-top:10px">📅 短期</h4>{_ul(rec.get('short_term') or [])}
  <h4 style="margin-top:10px">🔭 长期</h4>{_ul(rec.get('long_term') or [])}
</div>
"""


def render_footer(meta: dict, next_step: str, recent_action: dict | None = None) -> str:
    ns = f'<p>下一步：{_esc(next_step)}</p>' if next_step else ""
    ra = ""
    if isinstance(recent_action, dict) and recent_action.get("action"):
        v = f"（{recent_action['verification']}）" if recent_action.get("verification") else ""
        line = f"最近一次运维：{recent_action.get('time', '')} {recent_action['action']}{v}"
        ra = f"<p>{_esc(line)}</p>"
    return f"""
<div class="footer">
  {ns}
  {ra}
  <p>区域 {_esc(meta.get('region_label') or meta.get('region', 'N/A'))} · 窗口 {_esc(meta.get('window', 'N/A'))} · 数据源 {_esc(meta.get('data_source', 'N/A'))} · {_esc(meta.get('generated_at', ''))}</p>
</div>
"""


def render_html(data: dict) -> str:
    meta = data.get("meta", {}) or {}
    layers = data.get("layers", {}) or {}
    assessment = data.get("assessment", {}) or {}
    cost = data.get("cost")
    rec = data.get("recommendations", {}) or {}

    cards = [render_header(meta, assessment), '<div class="container">',
             render_overview(layers, assessment)]
    for name, layer in _ordered_layers(layers):
        cards.append(render_layer_card(name, layer))
    if isinstance(cost, dict):
        cards.append(render_cost_card(cost))
    if any(rec.get(k) for k in ("immediate", "short_term", "long_term")):
        cards.append(render_reco_card(rec))
    unknowns = data.get("unknowns") or []
    if unknowns:
        lis = "".join(f"<li>{_esc(u)}</li>" for u in unknowns)
        cards.append(f'<div class="card"><div class="section-title">❓ 未知 / 无法判断</div><ul>{lis}</ul></div>')
    cards.append(render_footer(meta, data.get("next_step", ""), data.get("recent_action")))
    cards.append("</div>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>可观测报告 — {_esc(meta.get('app', 'application'))}</title>
<style>{CSS}</style></head><body>
{''.join(cards)}
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="从 JSON 渲染可观测报告。")
    parser.add_argument("--input", "-i", help="JSON 输入路径；缺省从 stdin 读取。")
    parser.add_argument("--output", "-o", help="输出文件路径；除 --schema/--validate 外必填。")
    parser.add_argument("--format", "-f", choices=("md", "html"), default="md",
                        help="输出格式（默认 md）。")
    parser.add_argument("--schema", action="store_true", help="打印 JSON schema 后退出。")
    parser.add_argument("--validate", action="store_true",
                        help="仅校验输入 JSON，不渲染。")
    args = parser.parse_args()

    if args.schema:
        print(SCHEMA_DOC)
        return 0

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    if args.validate:
        errs = validate(data)
        if errs:
            print("✗ JSON 校验未通过：", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("✓ JSON 校验通过", file=sys.stderr)
        return 0

    if not args.output:
        parser.error("除 --schema 或 --validate 外，--output 为必填项")

    errs = validate(data)
    if errs:
        print("⚠ 渲染前校验发现问题（请按 SKILL 的报告章节修正）：", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)

    text = render_html(data) if args.format == "html" else render_md(data)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✓ 已写出 {args.format} 报告：{args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
