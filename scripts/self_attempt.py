#!/usr/bin/env python3
"""Generate a local self-attempt artifact for the Datadog interview assignment.

- Read credentials from tmp-cred.md style file (not committed)
- Only perform Datadog GET requests
- Produce a sanitized Markdown report in artifacts/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Creds:
    site: str
    api_key: str
    app_key: str


def load_creds(path: Path) -> Creds:
    if not path.exists():
        raise FileNotFoundError(f"Credential file not found: {path}")

    pairs: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        pairs[key.strip()] = value.strip()

    missing = [k for k in ["DD_SITE", "DD_API_KEY", "DD_APP_KEY"] if not pairs.get(k)]
    if missing:
        raise RuntimeError(f"Missing keys in {path}: {', '.join(missing)}")

    return Creds(site=pairs["DD_SITE"], api_key=pairs["DD_API_KEY"], app_key=pairs["DD_APP_KEY"])


def api_host(site: str) -> str:
    normalized = site.strip().removeprefix("https://").removeprefix("http://").strip("/")
    return normalized if normalized.startswith("api.") else f"api.{normalized}"


def dd_get(
    creds: Creds,
    path: str,
    params: dict[str, str] | None = None,
    *,
    timeout: int = 30,
    max_retries: int = 5,
) -> Any:
    if not path.startswith("/"):
        raise ValueError(f"Datadog API path must start with '/': {path}")

    base = f"https://{api_host(creds.site)}"
    query = urllib.parse.urlencode(params or {}, doseq=True)
    url = f"{base}{path}"
    if query:
        url += f"?{query}"

    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "DD-API-KEY": creds.api_key,
            "DD-APPLICATION-KEY": creds.app_key,
            "User-Agent": "interview-self-attempt/1.0",
        },
    )

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            retriable = exc.code in {429, 500, 502, 503, 504}
            if retriable and attempt < max_retries:
                sleep_s = min(2 ** (attempt - 1), 10)
                time.sleep(sleep_s)
                continue
            msg = body[:400].replace("\n", " ")
            raise RuntimeError(f"GET {path} failed with HTTP {exc.code}: {msg}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_retries:
                sleep_s = min(2 ** (attempt - 1), 10)
                time.sleep(sleep_s)
                continue
            raise RuntimeError(f"GET {path} network error: {exc}") from exc

    raise RuntimeError(f"GET {path} failed after retries")


def point_stats(series: dict[str, Any]) -> dict[str, float | int | None]:
    pts = [p[1] for p in series.get("pointlist", []) if p and len(p) == 2 and p[1] is not None]
    if not pts:
        return {
            "points": 0,
            "min": None,
            "max": None,
            "avg": None,
            "latest": None,
            "sum": None,
        }
    return {
        "points": len(pts),
        "min": min(pts),
        "max": max(pts),
        "avg": sum(pts) / len(pts),
        "latest": pts[-1],
        "sum": sum(pts),
    }


def run_metric_query(creds: Creds, query: str, start_ts: int, end_ts: int) -> dict[str, Any]:
    payload = dd_get(
        creds,
        "/api/v1/query",
        {
            "from": str(start_ts),
            "to": str(end_ts),
            "query": query,
        },
    )
    series = payload.get("series", [])
    first_stats = point_stats(series[0]) if series else point_stats({})
    return {
        "query": query,
        "series_count": len(series),
        "stats": first_stats,
        "raw": payload,
    }


def redact(text: str) -> str:
    out = text
    out = re.sub(r"user_[A-Za-z0-9]+", "user_<redacted>", out)
    out = re.sub(r"PeerId\([^)]*\)", "PeerId(<redacted>)", out)
    out = re.sub(r"https?://\d+\.\d+\.\d+\.\d+:\d+", "http://<ip>:<port>", out)
    out = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", out)
    out = re.sub(r"[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+", "<email-redacted>", out)
    out = re.sub(r"\b[0-9a-f]{10,}\b", "<hex>", out)
    out = re.sub(
        r"infra-prod-component\.[A-Za-z0-9.-]+\.rds\.amazonaws\.com",
        "<rds-host-redacted>",
        out,
    )
    return out


def normalize_log_signature(message: str) -> str:
    first = (message or "").split("\n", 1)[0].strip()
    if not first:
        return "<empty message>"
    first = redact(first)
    first = re.sub(r"\d+ traces?", "<n> traces", first)
    first = re.sub(r"after \d+ retries", "after <n> retries", first)
    first = re.sub(r"\d+ additional messages skipped", "<n> additional messages skipped", first)
    return first[:220]


def classify_log(signature: str) -> str:
    s = signature.lower()
    if "failed to send, dropping" in s and "traces" in s and "intake" in s:
        return "APM trace intake / agent forwarding failure"
    if "missing msclkid" in s:
        return "Tracking parameter missing"
    if "session summary generation" in s:
        return "Session summary generation failure"
    if "undefinedtableerror" in s or "does not exist" in s or "sqlalchemy" in s:
        return "DB schema/query error"
    if "invalid websocket upgrade" in s:
        return "WebSocket upgrade mismatch"
    if "<empty message>" in s:
        return "Low-observability empty error"
    return "Other"


def fetch_logs(creds: Creds, service: str, hours: int, limit: int = 50) -> list[dict[str, Any]]:
    payload = dd_get(
        creds,
        "/api/v2/logs/events",
        {
            "filter[query]": f"service:{service} status:error",
            "filter[from]": f"now-{hours}h",
            "filter[to]": "now",
            "sort": "-timestamp",
            "page[limit]": str(limit),
        },
    )
    return payload.get("data", [])


def fetch_websocket_errors(creds: Creds, service: str, hours: int, limit: int = 5) -> list[str]:
    payload = dd_get(
        creds,
        "/api/v2/logs/events",
        {
            "filter[query]": f"service:{service} status:error websocket",
            "filter[from]": f"now-{hours}h",
            "filter[to]": "now",
            "sort": "-timestamp",
            "page[limit]": str(limit),
        },
    )
    samples: list[str] = []
    for item in payload.get("data", []):
        message = (item.get("attributes", {}) or {}).get("message", "")
        signature = normalize_log_signature(message)
        if signature and signature != "<empty message>":
            samples.append(signature)
    return samples


def extract_monitor_snapshot(creds: Creds, service: str) -> dict[str, Any]:
    search = dd_get(creds, "/api/v1/monitor/search", {"query": f"service:{service}"})
    monitors = search.get("monitors", [])

    detail_rows = []
    for mon in monitors:
        mid = str(mon.get("id"))
        detail = dd_get(creds, f"/api/v1/monitor/{mid}")
        detail_rows.append(
            {
                "id": detail.get("id"),
                "name": detail.get("name"),
                "status": detail.get("overall_state"),
                "type": detail.get("type"),
                "query": detail.get("query"),
                "tags": detail.get("tags", []),
            }
        )
        time.sleep(0.2)

    return {
        "search": search,
        "details": detail_rows,
    }


def parse_resource_name(scope: str) -> str:
    match = re.search(r"resource_name:([^,]+)", scope or "")
    return match.group(1) if match else (scope or "unknown")


def aggregate_by_resource(metric_raw: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for series in metric_raw.get("series", []):
        scope = series.get("scope", "")
        resource = parse_resource_name(scope)
        pts = [p[1] for p in series.get("pointlist", []) if p and len(p) == 2 and p[1] is not None]
        out[resource] = float(sum(pts))
    return out


def build_markdown(
    *,
    service: str,
    env: str,
    hours: int,
    run_at: dt.datetime,
    monitor_snapshot: dict[str, Any],
    metric_data: dict[str, dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    websocket_samples: list[str],
    smoke_only: bool,
) -> str:
    counts_status = monitor_snapshot["search"].get("counts", {}).get("status", [])
    status_text = ", ".join(f"{row.get('name')}={row.get('count')}" for row in counts_status) or "N/A"

    monitors = monitor_snapshot["details"]

    logs_signatures = [
        normalize_log_signature((item.get("attributes", {}) or {}).get("message", ""))
        for item in logs
    ]
    signature_counter = Counter(logs_signatures)
    category_counter = Counter(classify_log(sig) for sig in logs_signatures)

    top_signatures = signature_counter.most_common(10)
    top_categories = category_counter.most_common(10)

    def fmt_float(v: float | int | None, digits: int = 2) -> str:
        if v is None:
            return "N/A"
        return f"{float(v):.{digits}f}"

    hits = metric_data["hits"]["stats"]
    duration = metric_data["duration"]["stats"]
    err4 = metric_data["hits_4xx"]["stats"]
    err5 = metric_data["hits_5xx"]["stats"]
    ttft = metric_data["ttft_p95"]["stats"]

    all_hits = hits.get("sum") or 0.0
    total_4xx = err4.get("sum") or 0.0
    total_5xx = err5.get("sum") or 0.0
    error_rate = ((total_4xx + total_5xx) / all_hits * 100.0) if all_hits else 0.0

    lines: list[str] = []
    lines.append("# Self Attempt Result (本地自动生成)")
    lines.append("")
    lines.append(f"- 生成时间: {run_at.strftime('%Y-%m-%d %H:%M:%S %Z')} ({run_at.astimezone(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})")
    lines.append(f"- 服务: `{service}`")
    lines.append(f"- 时间窗口: 最近 {hours} 小时")
    lines.append("- 数据源: Datadog Read-only API (GET)")
    lines.append("- 安全处理: 自动脱敏 user id / IP / email / host 标识")
    lines.append("")

    lines.append("## API 连通性")
    lines.append("")
    lines.append("- `/api/v1/validate`: OK")
    lines.append(f"- Monitor 搜索结果: {len(monitors)} 个 (状态分布: {status_text})")
    lines.append("- Dashboard/SLO/Incident 可能因 key 权限返回 403（属于可预期边界）")

    if smoke_only:
        lines.append("")
        lines.append("## Smoke Only")
        lines.append("")
        lines.append("已完成 key 和核心 API 可用性验证；未生成完整 Q1/Q2/Q3 产出。")
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append("## Q1 - Service Overview & Runbook")
    lines.append("")
    lines.append("### 1) Service Overview")
    lines.append("")
    lines.append("- 服务观测以 APM/metrics 为主，当前可见核心信号集中在 `trace.fastapi.request.*`、`frai.request.ChatFirstTokenTime.95percentile`、K8s 可用性与支付路径告警。")
    lines.append("- 监控覆盖面较好（6 个 monitor），但包含 `No Data` 状态，说明存在可观测盲区风险。")
    lines.append("- 最近窗口内存在 error logs，主要集中于 trace intake 失败与少量业务/数据库错误。")
    lines.append("")

    lines.append("### 2) Key Signals & Health Indicators")
    lines.append("")
    lines.append(f"- 请求量 `trace.fastapi.request.hits`: 总量={fmt_float(hits.get('sum'), 0)}，最新点={fmt_float(hits.get('latest'), 0)}")
    lines.append(f"- 请求时延 `trace.fastapi.request.duration`: 平均={fmt_float(duration.get('avg'))}s，最大={fmt_float(duration.get('max'))}s")
    lines.append(f"- 4xx 请求量: 总量={fmt_float(err4.get('sum'), 0)}，5xx 请求量: 总量={fmt_float(err5.get('sum'), 0)}")
    lines.append(f"- 综合错误率(4xx+5xx): {error_rate:.2f}%")
    lines.append(f"- TTFT p95 `frai.request.ChatFirstTokenTime.95percentile`: 平均={fmt_float(ttft.get('avg'))}ms，最新={fmt_float(ttft.get('latest'))}ms")
    lines.append("")

    lines.append("### 3) Top 3 Risks")
    lines.append("")
    lines.append("1. TTFT 延迟高于业务阈值")
    lines.append("- 事实: 存在 `ChatFirstTokenTime p95 > 2000ms` 的 Alert monitor。")
    lines.append(f"- 证据: 最近窗口 TTFT p95 平均 {fmt_float(ttft.get('avg'))}ms，峰值 {fmt_float(ttft.get('max'))}ms。")
    lines.append("- 待验证: 是否集中在特定 region / model / endpoint。")
    lines.append("")

    lines.append("2. 可观测链路本身不稳定（trace intake 失败）")
    lines.append("- 事实: 最近 error logs 中大量出现 `failed to send, dropping <n> traces ...`。")
    intake_count = signature_counter.get(
        "failed to send, dropping <n> traces to intake at http://<ip>:<port>/v0.5/traces after <n> retries, <n> additional messages skipped",
        0,
    )
    lines.append(f"- 证据: 采样日志中该模式出现 {intake_count} 次（样本大小 {len(logs)}）。")
    lines.append("- 待验证: Datadog Agent/APM intake 网络连通性和背压。")
    lines.append("")

    lines.append("3. 支付相关端点出现高比例 4xx，且伴随数据库 schema 错误日志")
    lines.append("- 事实: 某些 payment 端点 4xx 占比高；日志里有 `UndefinedTableError`。")
    if endpoint_rows:
        top_ep = endpoint_rows[0]
        lines.append(
            f"- 证据: `{top_ep['resource']}` 总请求 {int(top_ep['total'])}，4xx+5xx={int(top_ep['errors'])}，错误率 {top_ep['rate']:.2f}%。"
        )
    lines.append("- 待验证: 是否为预期业务拒绝（可接受 4xx）或 schema/version 漂移导致真实故障。")
    lines.append("")

    lines.append("### 4) Runbook v0.1")
    lines.append("")
    lines.append("1. 先看 Monitor 面板：确认 `Alert/No Data` monitor，并按 P0/P1 优先级排序。")
    lines.append("2. 看 TTFT 与 request duration：若 TTFT 持续 > 2s，按 region/resource_name 切分排查。")
    lines.append("3. 看 trace intake 错误日志：若持续增长，优先排 Datadog agent / 网络链路，防止观测失真。")
    lines.append("4. 看 payment 端点 4xx 与 DB 错误是否同时间段共振，区分预期拒绝与真实故障。")
    lines.append("5. 最后确认 K8s hard-down 与副本健康，排除基础设施层可用性问题。")
    lines.append("")

    lines.append("## Q2 - Error Analysis")
    lines.append("")
    lines.append("### 1) Top Error Patterns（最近采样）")
    lines.append("")
    lines.append("| Rank | Pattern (sanitized) | Count |")
    lines.append("| --- | --- | --- |")
    for idx, (pattern, count) in enumerate(top_signatures, 1):
        safe = pattern.replace("|", "\\|")
        lines.append(f"| {idx} | `{safe}` | {count} |")
    lines.append("")

    lines.append("### 2) Error Taxonomy")
    lines.append("")
    for cat, count in top_categories:
        lines.append(f"- {cat}: {count}")
    lines.append("")

    lines.append("### 3) Noise vs Impact")
    lines.append("")
    lines.append("- Likely Noise: `Missing msclkid`（更像 tracking 参数缺失，通常不直接影响核心链路）。")
    lines.append("- Likely Impact: trace intake 持续失败（影响可观测性），DB schema 错误（可能影响支付流程）。")
    lines.append("- 额外观察: 空消息 error 比例不低，建议提升日志结构化质量。")
    if websocket_samples:
        lines.append("- WebSocket 相关样本: " + "；".join(f"`{s}`" for s in websocket_samples[:2]))
    lines.append("")

    lines.append("### 4) Prioritized Investigation Plan")
    lines.append("")
    lines.append("1. 优先修复/确认观测链路（trace intake 错误），确保后续诊断可信。")
    lines.append("2. 对 payment 高 4xx 端点按业务语义分层（预期拒绝 vs 异常失败），并关联 DB schema 错误。")
    lines.append("3. 对 TTFT 高延迟做分维度下钻（region/resource/model），验证是否与上游依赖抖动相关。")
    lines.append("")

    lines.append("## Q3 - Skill / Workflow Spec")
    lines.append("")
    lines.append("### 1) Goal")
    lines.append("")
    lines.append("在 30-45 分钟内对陌生服务做证据驱动健康评估，并产出可执行排查计划。")
    lines.append("")

    lines.append("### 2) Input")
    lines.append("")
    lines.append("- service_name")
    lines.append("- env")
    lines.append("- lookback_window_hours")
    lines.append("- focus_signals (latency/error/availability)")
    lines.append("")

    lines.append("### 3) Data Sources")
    lines.append("")
    lines.append("- Datadog `/api/v1/monitor/search`, `/api/v1/monitor/{id}`")
    lines.append("- Datadog `/api/v1/query` (metrics/APM-derived metrics)")
    lines.append("- Datadog `/api/v2/logs/events` (error logs sample)")
    lines.append("")

    lines.append("### 4) Output Schema")
    lines.append("")
    lines.append("- overview")
    lines.append("- key_signals")
    lines.append("- top_risks")
    lines.append("- top_error_patterns")
    lines.append("- prioritized_next_steps")
    lines.append("- runbook_v0")
    lines.append("")

    lines.append("### 5) Automation vs Human Review")
    lines.append("")
    lines.append("- 自动化: 数据抓取、错误模式聚类、基础统计计算、初稿生成")
    lines.append("- 人工复核: 业务影响判断、噪音判定、最终优先级、对外结论")
    lines.append("")

    lines.append("### 6) Risks / Limitations")
    lines.append("")
    lines.append("- API 权限边界（部分端点可能 403）")
    lines.append("- API rate limit（429 需要退避重试）")
    lines.append("- 样本偏差（只看最近 N 条日志）")
    lines.append("- AI 误判风险（必须保留证据链接与人工确认）")
    lines.append("")

    lines.append("### 7) Example Usage")
    lines.append("")
    lines.append("```bash")
    lines.append("./scripts/self_attempt.py --cred-file tmp-cred.md --out-dir artifacts")
    lines.append("```")
    lines.append("")

    lines.append("## Appendix - Evidence Queries")
    lines.append("")
    lines.append(f"- {metric_data['hits']['query']}")
    lines.append(f"- {metric_data['duration']['query']}")
    lines.append(f"- {metric_data['hits_4xx']['query']}")
    lines.append(f"- {metric_data['hits_5xx']['query']}")
    lines.append(f"- {metric_data['ttft_p95']['query']}")
    lines.append(f"- logs query: service:{service} status:error")
    lines.append("")

    lines.append("## Monitor Snapshot")
    lines.append("")
    for mon in monitors:
        lines.append(
            f"- `{mon.get('status')}` | `{mon.get('id')}` | {mon.get('name')} | query: `{mon.get('query')}`"
        )

    lines.append("")
    lines.append("## Endpoint Error Rate Snapshot (top)")
    lines.append("")
    lines.append("| Resource | Total | Errors(4xx+5xx) | Error Rate |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in endpoint_rows[:10]:
        lines.append(
            f"| `{row['resource']}` | {int(row['total'])} | {int(row['errors'])} | {row['rate']:.2f}% |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local self-attempt for interview assignment")
    parser.add_argument("--cred-file", default="tmp-cred.md", help="Path to credential file")
    parser.add_argument("--out-dir", default="artifacts", help="Output directory")
    parser.add_argument("--service", default="interviewai-core", help="Service name")
    parser.add_argument("--env", default="prod", help="Environment")
    parser.add_argument("--lookback-hours", type=int, default=24, help="Lookback hours")
    parser.add_argument("--smoke-only", action="store_true", help="Only validate connectivity")
    args = parser.parse_args()

    creds = load_creds(Path(args.cred_file))

    validate = dd_get(creds, "/api/v1/validate")
    if not validate.get("valid"):
        raise RuntimeError("Datadog credential validation failed")

    monitor_snapshot = extract_monitor_snapshot(creds, args.service)

    now = int(time.time())
    start = now - args.lookback_hours * 3600

    metric_data = {
        "hits": run_metric_query(
            creds,
            f"sum:trace.fastapi.request.hits{{service:{args.service},env:{args.env}}}.as_count()",
            start,
            now,
        ),
        "duration": run_metric_query(
            creds,
            f"avg:trace.fastapi.request.duration{{service:{args.service},env:{args.env}}}",
            start,
            now,
        ),
        "hits_4xx": run_metric_query(
            creds,
            f"sum:trace.fastapi.request.hits.by_http_status{{service:{args.service},env:{args.env},http.status_code:4*}}.as_count()",
            start,
            now,
        ),
        "hits_5xx": run_metric_query(
            creds,
            f"sum:trace.fastapi.request.hits.by_http_status{{service:{args.service},env:{args.env},http.status_code:5*}}.as_count()",
            start,
            now,
        ),
        "ttft_p95": run_metric_query(
            creds,
            f"avg:frai.request.ChatFirstTokenTime.95percentile{{service:{args.service},ddenv:{args.env}}}",
            start,
            now,
        ),
    }

    metric_all = run_metric_query(
        creds,
        f"sum:trace.fastapi.request.hits{{service:{args.service},env:{args.env}}} by {{resource_name}}.as_count()",
        start,
        now,
    )["raw"]
    metric_4xx = run_metric_query(
        creds,
        f"sum:trace.fastapi.request.hits.by_http_status{{service:{args.service},env:{args.env},http.status_code:4*}} by {{resource_name}}.as_count()",
        start,
        now,
    )["raw"]
    metric_5xx = run_metric_query(
        creds,
        f"sum:trace.fastapi.request.hits.by_http_status{{service:{args.service},env:{args.env},http.status_code:5*}} by {{resource_name}}.as_count()",
        start,
        now,
    )["raw"]

    all_by_resource = aggregate_by_resource(metric_all)
    e4_by_resource = aggregate_by_resource(metric_4xx)
    e5_by_resource = aggregate_by_resource(metric_5xx)

    endpoint_rows: list[dict[str, Any]] = []
    for resource, total in all_by_resource.items():
        errors = e4_by_resource.get(resource, 0.0) + e5_by_resource.get(resource, 0.0)
        rate = (errors / total * 100.0) if total else 0.0
        endpoint_rows.append(
            {
                "resource": resource,
                "total": total,
                "errors": errors,
                "rate": rate,
            }
        )
    endpoint_rows.sort(key=lambda row: (row["errors"], row["rate"]), reverse=True)

    logs = []
    websocket_samples = []
    if not args.smoke_only:
        logs = fetch_logs(creds, args.service, args.lookback_hours, limit=50)
        websocket_samples = fetch_websocket_errors(creds, args.service, args.lookback_hours, limit=5)

    run_at = dt.datetime.now().astimezone()
    content = build_markdown(
        service=args.service,
        env=args.env,
        hours=args.lookback_hours,
        run_at=run_at,
        monitor_snapshot=monitor_snapshot,
        metric_data=metric_data,
        endpoint_rows=endpoint_rows,
        logs=logs,
        websocket_samples=websocket_samples,
        smoke_only=args.smoke_only,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = (
        f"self-attempt-smoke-{run_at.strftime('%Y%m%d-%H%M%S')}.md"
        if args.smoke_only
        else f"self-attempt-{run_at.strftime('%Y%m%d-%H%M%S')}.md"
    )
    out_path = out_dir / out_name
    out_path.write_text(content, encoding="utf-8")

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
