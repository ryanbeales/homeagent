#!/usr/bin/env python3
"""
Prometheus anomaly detector
Runs every hour, fetches the last 60 min of data, flags >20 % spikes,
and reports which pod/service is responsible.
"""
import os
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# ------------------ Configuration ------------------
PROMETHEUS_URL = "https://prometheus.crobasaurusrex.ryanbeales.com"

# Example queries – adjust to your metric names
METRICS = {
  "cpu_usage": 'sum(rate(container_cpu_usage_seconds_total{job="kubelet"}[5m])) by (pod_name)',
  "mem_usage": 'sum(container_memory_usage_bytes{job="kubelet"}) by (pod_name)',
  "slab_memory": 'sum(node_memory_Slab_bytes) by (node)',
}

THRESHOLD_PCT = 20.0          # spike threshold (percent)
DATA_DIR = Path("/app/data/shared")   # use persistent dir so container doesn't lose it
DATA_DIR.mkdir(parents=True, exist_ok=True)
PREV_FILE = DATA_DIR / "prometheus_anomaly_cache.json"

# ---------------------------------------------------
def query_prometheus(query: str, start: float, end: float, step: str = "1m"):
  """Run a query_range request and return raw JSON."""
  url = f"{PROMETHEUS_URL}/api/v1/query_range"
  params = {
      "query": query,
      "start": start,
      "end": end,
      "step": step,
  }
  
  query_string = urllib.parse.urlencode(params)
  full_url = f"{url}?{query_string}"
  req = urllib.request.Request(full_url)
  with urllib.request.urlopen(req, timeout=30) as response:
      return json.loads(response.read().decode('utf-8'))

def compute_average(values):
  """Average over a list of float values."""
  return sum(values) / len(values) if values else 0.0

def get_latest_avg(metric_name: str, start_ts: float, end_ts: float):
  """Return the average value of a metric over the given window."""
  resp = query_prometheus(METRICS[metric_name], start_ts, end_ts)
  if resp["status"] != "success":
      raise RuntimeError(f"Prometheus query failed: {resp}")

  # Prometheus returns data points; we average them
  samples = resp["data"]["result"]
  if not samples:
      return 0.0, []

  # We expect one series per pod/node; average over all
  totals = []
  for series in samples:
      values = [float(v[1]) for v in series["values"]]
      totals.append(compute_average(values))

  overall_avg = compute_average(totals)
  return overall_avg, samples

def load_prev():
  if PREV_FILE.exists():
      with PREV_FILE.open() as f:
          return json.load(f)
  return {}

def save_prev(data):
  with PREV_FILE.open("w") as f:
      json.dump(data, f, indent=2)

def detect_spikes(prev, current, metric_name):
  """Return list of (pod, percent_change) where spike > THRESHOLD."""
  spikes = []
  # Current should be a list of series (one per pod/node)
  # Prev is a dict keyed by series name (e.g., pod_name)
  for series in current:
      name = series["metric"].get("pod_name") or series["metric"].get("node")
      if not name:
          continue

      curr_vals = [float(v[1]) for v in series["values"]]
      curr_avg = compute_average(curr_vals)
      prev_avg = prev.get(name, 0.0)

      if prev_avg == 0:
          continue

      pct_change = ((curr_avg - prev_avg) / prev_avg) * 100
      if pct_change >= THRESHOLD_PCT:
          spikes.append((name, pct_change, curr_avg, prev_avg))
  return spikes

def main():
  now = datetime.utcnow()
  end_ts = now.timestamp()
  start_ts = (now - timedelta(hours=1)).timestamp()
  prev_metrics = load_prev()
  summaries = []

  for metric, query in METRICS.items():
      try:
          curr_avg, series = get_latest_avg(metric, start_ts, end_ts)

          # Prepare a simple dict of pod->avg for persistence
          curr_dict = {
              s["metric"].get("pod_name") or s["metric"].get("node"): compute_average(
                  [float(v[1]) for v in s["values"]]
              )
              for s in series
          }

          # Detect spikes
          spikes = detect_spikes(prev_metrics.get(metric, {}), series, metric)
          if spikes:
              for pod, pct, cur, prev in spikes:
                  summaries.append(
                      f"[{metric}] {pod} spiked {pct:.1f}% "
                      f"(prev={prev:.1f}, curr={cur:.1f})"
                  )

          # Store for next run
          prev_metrics[metric] = curr_dict

      except Exception as e:
          summaries.append(f"[{metric}] error: {e}")

  # Persist
  save_prev(prev_metrics)

  # Output
  if summaries:
      msg = "\n".join(summaries)
  else:
      msg = "✅ No significant anomalies detected in the last hour."

  print(msg)

if __name__ == "__main__":
  main()
