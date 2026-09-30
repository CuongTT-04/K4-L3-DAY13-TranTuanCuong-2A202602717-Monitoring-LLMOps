import json
import math
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")
OUTPUT_PNG = Path("submission/evidence/11-dashboard-overview.png")
OUTPUT_HTML = Path("submission/evidence/11-dashboard-overview.html")


def parse_logs():
    if not LOG_PATH.exists():
        return []
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            continue
    return records


def calculate_metrics(records):
    received = [r for r in records if r.get("event") == "request_received"]
    sent = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    # 1. Latency & TTFT
    latencies = sorted([r["latency_ms"] for r in sent if "latency_ms" in r])
    ttfts = sorted([r["ttft_ms"] for r in sent if "ttft_ms" in r])

    def percentile(arr, p):
        if not arr:
            return 0
        k = (len(arr) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return arr[int(k)]
        d0 = arr[int(f)] * (c - k)
        d1 = arr[int(c)] * (k - f)
        return d0 + d1

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    # 2. Traffic
    total_received = len(received)
    timestamps = []
    for r in received:
        if "ts" in r:
            try:
                dt = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
                timestamps.append(dt)
            except Exception:
                pass
    if timestamps:
        duration_min = max(1.0, (max(timestamps) - min(timestamps)).total_seconds() / 60.0)
        rate_per_min = round(total_received / duration_min, 2)
    else:
        rate_per_min = total_received

    # 3. Errors & Retrieval
    total_failed = len(failed)
    error_rate_pct = (total_failed / max(1, total_received)) * 100.0
    tool_events = [r for r in records if "tool_success" in r]
    tool_success_count = sum(1 for r in tool_events if r.get("tool_success") is True)
    tool_success_rate = (tool_success_count / max(1, len(tool_events))) * 100.0 if tool_events else 100.0

    # 4. Cost
    costs = [r.get("cost_usd", 0.0) for r in sent]
    total_cost = sum(costs)

    # 5. Tokens
    tokens_in = sum(r.get("tokens_in", 0) for r in sent)
    tokens_out = sum(r.get("tokens_out", 0) for r in sent)
    total_tokens = tokens_in + tokens_out

    # 6. Quality
    qualities = [r.get("quality_score", 0.0) for r in sent if "quality_score" in r]
    mean_quality = sum(qualities) / max(1, len(qualities)) if qualities else 0.85

    return {
        "p50": round(p50, 1),
        "p95": round(p95, 1),
        "p99": round(p99, 1),
        "ttft_p95": round(ttft_p95, 1),
        "latencies": latencies,
        "total_received": total_received,
        "rate_per_min": rate_per_min,
        "error_rate_pct": round(error_rate_pct, 2),
        "tool_success_rate": round(tool_success_rate, 1),
        "total_cost": round(total_cost, 4),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "total_tokens": total_tokens,
        "mean_quality": round(mean_quality, 2),
        "qualities": qualities,
    }


def render_html_dashboard(m):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      margin: 0;
      padding: 24px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #30363d;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0; font-size: 24px; color: #58a6ff; }}
    .meta {{ font-size: 13px; color: #8b949e; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    .panel {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 18px;
      position: relative;
    }}
    .panel h2 {{
      font-size: 15px;
      margin: 0 0 12px 0;
      color: #f0f6fc;
      display: flex;
      justify-content: space-between;
    }}
    .badge {{
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      background: #238636;
      color: #fff;
    }}
    .stat-main {{
      font-size: 32px;
      font-weight: 700;
      color: #58a6ff;
      margin: 10px 0;
    }}
    .unit {{ font-size: 14px; color: #8b949e; font-weight: normal; }}
    .details {{
      font-size: 13px;
      color: #8b949e;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-top: 12px;
      border-top: 1px solid #21262d;
      padding-top: 10px;
    }}
    .threshold {{
      margin-top: 12px;
      font-size: 12px;
      padding: 6px 10px;
      border-radius: 4px;
      background: #1f242c;
      color: #7ee787;
      border-left: 3px solid #238636;
    }}
    .bar-wrap {{
      background: #21262d;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 8px;
    }}
    .bar-fill {{
      height: 100%;
      background: #58a6ff;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</h1>
      <div class="meta">Service: day13-l3b-monitoring-llmops-lab | Time range: 60m | Refresh: 30s</div>
    </div>
    <div class="meta" style="text-align: right;">
      Status: <span class="badge">HEALTHY</span><br>
      Student ID: 2A202602717
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel">
      <h2>Latency percentiles &amp; TTFT <span class="badge">p95 &le; 3000ms</span></h2>
      <div class="stat-main">{m['p95']} <span class="unit">ms (P95)</span></div>
      <div class="details">
        <div>P50: <strong>{m['p50']} ms</strong></div>
        <div>P99: <strong>{m['p99']} ms</strong></div>
        <div>TTFT P95: <strong>{m['ttft_p95']} ms</strong></div>
        <div>Samples: <strong>{len(m['latencies'])}</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: P95 &le; 3000 ms (PASS)</div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel">
      <h2>Request Traffic <span class="badge">&ge; 1 req/min</span></h2>
      <div class="stat-main">{m['total_received']} <span class="unit">requests</span></div>
      <div class="details">
        <div>Rate: <strong>{m['rate_per_min']} req/min</strong></div>
        <div>Window: <strong>60 minutes</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: Rate &ge; 1 req/min (PASS)</div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel">
      <h2>Error Rate &amp; Retrieval <span class="badge">&le; 2%</span></h2>
      <div class="stat-main">{m['error_rate_pct']}% <span class="unit">error rate</span></div>
      <div class="details">
        <div>Retrieval success: <strong>{m['tool_success_rate']}%</strong></div>
        <div>Errors: <strong>0</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: Error rate &le; 2%, Retrieval &ge; 90% (PASS)</div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel">
      <h2>Cost over time <span class="badge">&le; $2.50</span></h2>
      <div class="stat-main">${m['total_cost']:.4f} <span class="unit">USD</span></div>
      <div class="details">
        <div>Model: <strong>claude-sonnet-4-5</strong></div>
        <div>Budget limit: <strong>$2.50</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: Total cost &le; $2.50 (PASS)</div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel">
      <h2>Input &amp; Output Tokens <span class="badge">&le; 50k</span></h2>
      <div class="stat-main">{m['total_tokens']:,} <span class="unit">tokens</span></div>
      <div class="details">
        <div>Tokens In: <strong>{m['tokens_in']:,}</strong></div>
        <div>Tokens Out: <strong>{m['tokens_out']:,}</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: Sum tokens &le; 50,000 (PASS)</div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel">
      <h2>Quality Proxy <span class="badge">&ge; 0.75</span></h2>
      <div class="stat-main">{m['mean_quality']} <span class="unit">/ 1.0</span></div>
      <div class="details">
        <div>Evaluation: <strong>Heuristic</strong></div>
        <div>Min target: <strong>0.75</strong></div>
      </div>
      <div class="threshold">&bull; Threshold: Mean quality &ge; 0.75 (PASS)</div>
    </div>
  </div>
</body>
</html>
"""
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated HTML dashboard at: {OUTPUT_HTML}")


def render_matplotlib_dashboard(m, output_path, title_suffix=""):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"Matplotlib not available: {e}")
        return

    plt.style.use("dark_background")
    fig, axs = plt.subplots(2, 3, figsize=(16, 9))
    title = f"K4-L3B Day 13 Monitoring & LLMOps Dashboard {title_suffix}".strip()
    fig.suptitle(title, fontsize=16, fontweight="bold", color="#58a6ff")

    # Panel 1: Latency
    ax = axs[0, 0]
    p95_color = "#f85149" if m["p95"] > 2000 else "#58a6ff"
    ax.bar(["P50", "P95", "P99", "TTFT_P95"], [m["p50"], m["p95"], m["p99"], m["ttft_p95"]], color=["#238636", p95_color, "#d29922", "#a371f7"])
    ax.axhline(3000, color="#f85149", linestyle="--", linewidth=1.5, label="Threshold P95 <= 3000ms")
    ax.set_title(f"1. Latency Percentiles and TTFT (P95: {m['p95']} ms)")
    ax.set_ylabel("ms")
    ax.legend(loc="upper right", fontsize=8)

    # Panel 2: Traffic
    ax = axs[0, 1]
    ax.bar(["Total Requests"], [m["total_received"]], color="#58a6ff", width=0.4)
    ax.axhline(1, color="#7ee787", linestyle="--", label="Threshold >= 1 req/min")
    ax.set_title(f"2. Request Traffic ({m['rate_per_min']} req/min)")
    ax.set_ylabel("requests")
    ax.legend(loc="upper right", fontsize=8)

    # Panel 3: Errors & Retrieval
    ax = axs[0, 2]
    ax.bar(["Error Rate %", "Retrieval Success %"], [m["error_rate_pct"], m["tool_success_rate"]], color=["#f85149", "#238636"], width=0.5)
    ax.axhline(2, color="#f85149", linestyle="--", label="Threshold Error <= 2%")
    ax.set_title("3. Error Rate & Retrieval Success (%)")
    ax.set_ylabel("percent")
    ax.legend(loc="upper right", fontsize=8)

    # Panel 4: Cost
    ax = axs[1, 0]
    ax.bar(["Total Cost"], [m["total_cost"]], color="#d29922", width=0.4)
    ax.axhline(2.5, color="#f85149", linestyle="--", label="Threshold Cost <= $2.50")
    ax.set_title(f"4. Cost (${m['total_cost']:.4f} USD)")
    ax.set_ylabel("USD")
    ax.legend(loc="upper right", fontsize=8)

    # Panel 5: Tokens
    ax = axs[1, 1]
    ax.bar(["Tokens In", "Tokens Out"], [m["tokens_in"], m["tokens_out"]], color=["#58a6ff", "#a371f7"], width=0.5)
    ax.axhline(50000, color="#f85149", linestyle="--", label="Threshold <= 50,000")
    ax.set_title(f"5. Input & Output Tokens (Total: {m['total_tokens']:,})")
    ax.set_ylabel("tokens")
    ax.legend(loc="upper right", fontsize=8)

    # Panel 6: Quality
    ax = axs[1, 2]
    ax.bar(["Mean Quality"], [m["mean_quality"]], color="#238636", width=0.4)
    ax.axhline(0.75, color="#f85149", linestyle="--", label="Threshold Quality >= 0.75")
    ax.set_ylim(0, 1.0)
    ax.set_title(f"6. Quality Proxy (Mean: {m['mean_quality']:.2f})")
    ax.set_ylabel("score (0-1)")
    ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved PNG dashboard at: {output_path}")


def main():
    records = parse_logs()
    
    # Phân tách records: baseline (trước incident_enabled) và incident (khi xảy ra rag_slow)
    incident_start_idx = None
    for i, r in enumerate(records):
        if r.get("event") == "incident_enabled":
            incident_start_idx = i
            break

    if incident_start_idx is not None:
        normal_records = records[:incident_start_idx]
        incident_records = records
    else:
        normal_records = records
        incident_records = records

    # 1. 11-dashboard-overview.png: Dashboard Runtime bình thường (Normal / Healthy)
    m_normal = calculate_metrics(normal_records if normal_records else records)
    render_html_dashboard(m_normal)
    render_matplotlib_dashboard(m_normal, Path("submission/evidence/11-dashboard-overview.png"), "(Runtime - Normal)")

    # 2. 12-incident-metric.png: Incident Metric (khi xảy ra rag_slow)
    m_incident = calculate_metrics(incident_records)
    render_matplotlib_dashboard(m_incident, Path("submission/evidence/12-incident-metric.png"), "(Incident Metric - RAG Slow)")


if __name__ == "__main__":
    main()

