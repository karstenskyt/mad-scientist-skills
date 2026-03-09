# Metrics, SLIs, and SLOs Reference

Comprehensive guide to designing meaningful metrics, defining Service Level Indicators (SLIs) and Service Level Objectives (SLOs), and implementing error budget-driven alerting for production services.

## Purpose

Answer: "Are the right things measured? Are SLIs and SLOs defined for critical services?"

## Checklist

Before auditing, identify:

- [ ] What type of service is being measured (request-driven, pipeline, storage, infrastructure)
- [ ] What metrics already exist (application-level, infrastructure, business)
- [ ] Which monitoring backend is in use (Prometheus, Datadog, CloudWatch, Grafana Cloud, New Relic)
- [ ] Whether OpenTelemetry is adopted or planned
- [ ] What SLAs exist with customers (these constrain SLO targets)
- [ ] Who the SLO stakeholders are (engineering, product, leadership)

---

## RED Methodology

**When to use:** Request-driven services (APIs, web servers, microservices, gateways).

RED measures the three signals that matter most for services handling requests.

### Request Rate

What it tells you: traffic volume and demand patterns.

**What to measure:**
- Total requests per second, broken down by endpoint and method
- Request rate by response status class (2xx, 3xx, 4xx, 5xx)
- Rate by consumer/tenant (if multi-tenant)

**OTel metric examples:**

```python
# Python (OpenTelemetry)
from opentelemetry import metrics

meter = metrics.get_meter("myservice")
request_counter = meter.create_counter(
    name="http.server.request.count",
    description="Total HTTP requests received",
    unit="{request}",
)

request_counter.add(1, attributes={
    "http.request.method": "GET",
    "http.route": "/api/users",
    "http.response.status_code": 200,
})
```

```go
// Go (OpenTelemetry)
meter := otel.Meter("myservice")
requestCounter, _ := meter.Int64Counter(
    "http.server.request.count",
    metric.WithDescription("Total HTTP requests received"),
    metric.WithUnit("{request}"),
)

requestCounter.Add(ctx, 1, metric.WithAttributes(
    attribute.String("http.request.method", "GET"),
    attribute.String("http.route", "/api/users"),
    attribute.Int("http.response.status_code", 200),
))
```

```java
// Java (OpenTelemetry)
Meter meter = GlobalOpenTelemetry.getMeter("myservice");
LongCounter requestCounter = meter.counterBuilder("http.server.request.count")
    .setDescription("Total HTTP requests received")
    .setUnit("{request}")
    .build();

requestCounter.add(1, Attributes.of(
    AttributeKey.stringKey("http.request.method"), "GET",
    AttributeKey.stringKey("http.route"), "/api/users",
    AttributeKey.longKey("http.response.status_code"), 200L
));
```

### Error Rate

What it tells you: how often requests fail.

**What to measure:**
- Error ratio: errors / total requests
- Errors by type (5xx server errors vs. 4xx client errors)
- Errors by endpoint — find which routes are degraded
- Distinguish between retryable and non-retryable errors

**OTel metric examples:**

```python
# Python — track errors as attributes on the same counter
request_counter.add(1, attributes={
    "http.request.method": "POST",
    "http.route": "/api/orders",
    "http.response.status_code": 503,
    "error.type": "ServiceUnavailable",
})
```

```go
// Go — track errors via status code attribute
requestCounter.Add(ctx, 1, metric.WithAttributes(
    attribute.String("http.request.method", "POST"),
    attribute.String("http.route", "/api/orders"),
    attribute.Int("http.response.status_code", 503),
    attribute.String("error.type", "ServiceUnavailable"),
))
```

### Duration (Latency)

What it tells you: how long requests take.

**What to measure:**
- Request duration as a histogram (not average — averages hide tail latency)
- p50, p90, p95, p99 percentiles
- Duration by endpoint, method, and status code
- Upstream dependency latency (database queries, external API calls)

**OTel metric examples:**

```python
# Python — histogram for request duration
request_duration = meter.create_histogram(
    name="http.server.request.duration",
    description="Duration of HTTP server requests",
    unit="s",
)

request_duration.record(0.127, attributes={
    "http.request.method": "GET",
    "http.route": "/api/users/{id}",
    "http.response.status_code": 200,
})
```

```go
// Go — histogram for request duration
requestDuration, _ := meter.Float64Histogram(
    "http.server.request.duration",
    metric.WithDescription("Duration of HTTP server requests"),
    metric.WithUnit("s"),
)

requestDuration.Record(ctx, 0.127, metric.WithAttributes(
    attribute.String("http.request.method", "GET"),
    attribute.String("http.route", "/api/users/{id}"),
    attribute.Int("http.response.status_code", 200),
))
```

---

## USE Methodology

**When to use:** Resources and infrastructure (CPU, memory, disk, network, connection pools, thread pools, queues).

USE measures the three signals that matter most for resources.

### CPU

| Signal | What to measure | Example metric |
|--------|----------------|----------------|
| Utilization | % of CPU time consumed | `system_cpu_utilization` (0.0–1.0) |
| Saturation | Run queue length, context switches | `system_cpu_load_average_1m` |
| Errors | Machine check exceptions (rare) | Hardware-level counters |

### Memory

| Signal | What to measure | Example metric |
|--------|----------------|----------------|
| Utilization | % of memory in use | `system_memory_usage` / total |
| Saturation | Swap usage, OOM events, page faults | `system_paging_operations` |
| Errors | ECC errors (rare) | Hardware-level counters |

### Disk

| Signal | What to measure | Example metric |
|--------|----------------|----------------|
| Utilization | % of disk space used, I/O bandwidth used | `system_filesystem_utilization` |
| Saturation | I/O queue depth, await time | `system_disk_io_time` |
| Errors | Read/write errors, sector remaps | `system_disk_operations` with error attribute |

### Connection Pools

| Signal | What to measure | Example metric |
|--------|----------------|----------------|
| Utilization | Active connections / max pool size | `db_client_connections_usage` |
| Saturation | Pending connection requests, wait time | `db_client_connections_pending_requests` |
| Errors | Connection timeouts, refused connections | `db_client_connections_timeouts` |

### Queues (Message Brokers)

| Signal | What to measure | Example metric |
|--------|----------------|----------------|
| Utilization | Queue depth / max capacity | `messaging_queue_depth` |
| Saturation | Consumer lag, publish backpressure | `messaging_consumer_lag` |
| Errors | Dead-letter queue depth, delivery failures | `messaging_dlq_depth` |

---

## Metric Types Reference

| Type | When to use | Example metric | Example use case |
|------|-------------|----------------|------------------|
| **Counter** | Monotonically increasing value; only goes up (resets to 0 on restart) | `http_requests_total` | Count total HTTP requests; compute rate with `rate()` |
| **Gauge** | Value that goes up and down | `process_resident_memory_bytes` | Current memory usage, active connections, queue depth |
| **Histogram** | Distribution of values; need percentiles or bucket counts | `http_request_duration_seconds` | Request latency distributions; compute p50/p90/p99 |
| **Summary** | Pre-calculated percentiles on the client side (Prometheus-specific) | `rpc_duration_seconds{quantile="0.99"}` | When exact percentiles are needed and cannot be aggregated across instances |

**Counter vs. Gauge decision rule:** If it can only go up during normal operation, it is a counter. If it can go down, it is a gauge.

**Histogram vs. Summary decision rule:** Prefer histograms. Summaries cannot be aggregated across instances and the quantile values are fixed at instrumentation time. Histograms allow flexible percentile queries in PromQL and can be aggregated.

---

## SLI Design Patterns

### Availability SLI

Fraction of requests that succeed:

```
availability = (total_requests - error_requests) / total_requests
```

**Concrete example — HTTP API:**

```promql
# Availability over 30 days (proportion of non-5xx responses)
sum(rate(http_requests_total{status!~"5.."}[30d]))
/
sum(rate(http_requests_total[30d]))
```

**What counts as "successful":**
- 2xx and 3xx responses are successful
- 4xx responses are generally successful (the server did its job — the client sent a bad request)
- 5xx responses are errors
- Timeouts and connection resets are errors

### Latency SLI

Fraction of requests faster than a threshold:

```
latency_sli = requests_below_threshold / total_requests
```

**Concrete example — 99th percentile under 300ms:**

```promql
# Proportion of requests served within 300ms
sum(rate(http_request_duration_seconds_bucket{le="0.3"}[30d]))
/
sum(rate(http_request_duration_seconds_count[30d]))
```

**Threshold selection guidance:**
- Choose the threshold based on user experience, not server capability
- Typical thresholds: 100ms (interactive UI), 300ms (API calls), 1s (background operations), 5s (batch jobs)
- Use multiple SLIs for different latency tiers (e.g., p50 < 100ms AND p99 < 500ms)

### Throughput SLI

Fraction of time the system can handle the required load:

```
throughput_sli = minutes_above_min_throughput / total_minutes
```

**Concrete example — data pipeline processing at least 1000 events/sec:**

```promql
# Proportion of time processing rate exceeds 1000 events/sec
avg_over_time(
  (rate(pipeline_events_processed_total[5m]) > bool 1000)[30d:1m]
)
```

### Correctness SLI

Fraction of responses that return correct data:

```
correctness_sli = correct_responses / total_responses
```

Useful for data pipelines, ML inference services, and financial systems where returning a response is not enough — the response must be correct.

---

## SLO Target Selection

| SLO Target | Allowed downtime/year | Allowed downtime/month | Allowed downtime/week | Typical use case |
|------------|----------------------|------------------------|----------------------|------------------|
| 99% | 3d 15h 39m | 7h 18m | 1h 40m | Internal tools, batch jobs |
| 99.5% | 1d 19h 49m | 3h 39m | 50m 24s | Low-criticality services |
| 99.9% | 8h 45m | 43m 50s | 10m 4s | Most production APIs |
| 99.95% | 4h 22m | 21m 55s | 5m 2s | Customer-facing APIs |
| 99.99% | 52m 35s | 4m 23s | 1m 0s | Payment processing, auth |

**Target selection guidelines:**

- Start with 99.9% for most services — it is a practical default
- Never set an SLO higher than what you can actually achieve consistently
- Your SLO must be lower than your SLA (e.g., SLA of 99.9% needs an internal SLO of 99.95%)
- Higher SLOs cost exponentially more to maintain — each additional nine roughly 10x the engineering effort
- Different SLIs on the same service can have different targets (e.g., 99.9% availability but 99.5% latency)

---

## Error Budget and Burn Rate Alerting

### Error Budgets

An error budget is the inverse of your SLO: the amount of unreliability you are allowed.

```
error_budget = 1 - SLO_target
```

For a 99.9% SLO over 30 days:
- Error budget = 0.1% of requests = 43 minutes 50 seconds of downtime
- If you consume the entire budget, you must prioritize reliability over features

**Error budget policy decisions:**

| Budget remaining | Action |
|-----------------|--------|
| > 50% | Ship features freely |
| 25–50% | Increase caution, review risky deployments |
| 10–25% | Freeze non-critical changes, focus on reliability |
| < 10% | Incident mode — all efforts on reliability |
| Exhausted | Feature freeze until budget replenishes |

### Multi-Window Burn Rate Alerting

Burn rate measures how fast the error budget is being consumed relative to the SLO window.

```
burn_rate = actual_error_rate / (1 - SLO_target)
```

A burn rate of 1 means you will exactly exhaust the budget at the end of the window. A burn rate of 10 means you will exhaust the budget in 1/10 of the window.

**Multi-window alert thresholds (Google SRE recommendation for 30-day SLO):**

| Severity | Burn rate | Long window | Short window | Budget consumed if unresolved |
|----------|-----------|-------------|--------------|-------------------------------|
| Page (critical) | 14.4x | 1h | 5m | 2% in 1h |
| Page (high) | 6x | 6h | 30m | 5% in 6h |
| Ticket (medium) | 3x | 1d | 2h | 10% in 1d |
| Ticket (low) | 1x | 3d | 6h | 10% in 3d |

### Prometheus Recording and Alerting Rules

```yaml
# Recording rules — pre-compute SLI for efficiency
groups:
  - name: slo_recording_rules
    interval: 30s
    rules:
      # Error ratio over various windows
      - record: slo:http_error_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      - record: slo:http_error_ratio:rate30m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[30m]))
          /
          sum(rate(http_requests_total[30m]))

      - record: slo:http_error_ratio:rate1h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h]))
          /
          sum(rate(http_requests_total[1h]))

      - record: slo:http_error_ratio:rate6h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[6h]))
          /
          sum(rate(http_requests_total[6h]))

      - record: slo:http_error_ratio:rate1d
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1d]))
          /
          sum(rate(http_requests_total[1d]))

      - record: slo:http_error_ratio:rate3d
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[3d]))
          /
          sum(rate(http_requests_total[3d]))
```

```yaml
# Alerting rules — multi-window burn rate alerts
groups:
  - name: slo_burn_rate_alerts
    rules:
      # Critical: 14.4x burn rate over 1h, confirmed by 5m window
      - alert: SLOBurnRateCritical
        expr: |
          slo:http_error_ratio:rate1h > (14.4 * 0.001)
          and
          slo:http_error_ratio:rate5m > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error budget burn rate (critical)"
          description: >
            Error budget is being consumed at 14.4x the sustainable rate.
            At this rate, the entire 30-day budget will be exhausted in 2 hours.

      # High: 6x burn rate over 6h, confirmed by 30m window
      - alert: SLOBurnRateHigh
        expr: |
          slo:http_error_ratio:rate6h > (6 * 0.001)
          and
          slo:http_error_ratio:rate30m > (6 * 0.001)
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Elevated error budget burn rate"
          description: >
            Error budget is being consumed at 6x the sustainable rate.
            At this rate, the entire 30-day budget will be exhausted in 5 days.

      # Medium: 3x burn rate over 1d, confirmed by 2h window
      - alert: SLOBurnRateMedium
        expr: |
          slo:http_error_ratio:rate1d > (3 * 0.001)
          and
          slo:http_error_ratio:rate1h > (3 * 0.001)
        for: 15m
        labels:
          severity: info
          ticket: "true"
        annotations:
          summary: "Sustained error budget consumption"
          description: >
            Error budget is being consumed at 3x the sustainable rate.
            At this rate, the entire 30-day budget will be exhausted in 10 days.
```

### Grafana Dashboard Queries

```promql
# Current error budget remaining (percentage)
1 - (
  sum(increase(http_requests_total{status=~"5.."}[30d]))
  /
  (sum(increase(http_requests_total[30d])) * (1 - 0.999))
)

# Current burn rate
(
  slo:http_error_ratio:rate1h / 0.001
)

# Time until budget exhaustion at current burn rate (hours)
(
  (1 - (sum(increase(http_requests_total{status=~"5.."}[30d]))
        / (sum(increase(http_requests_total[30d])) * 0.001)))
  / (slo:http_error_ratio:rate1h / 0.001)
) * 720
```

---

## Metric Naming Conventions

### Prometheus Convention

Format: `<namespace>_<name>_<unit>`

| Rule | Good | Bad |
|------|------|-----|
| Use snake_case | `http_request_duration_seconds` | `httpRequestDurationSeconds` |
| Include unit as suffix | `http_request_duration_seconds` | `http_request_duration` |
| Use base units | `_seconds` (not `_milliseconds`) | `http_request_duration_ms` |
| Use `_total` suffix for counters | `http_requests_total` | `http_requests` |
| Use `_bytes` for sizes | `process_resident_memory_bytes` | `process_memory_mb` |
| Prefix with namespace | `myapp_cache_hits_total` | `cache_hits_total` |
| Avoid `_count` and `_sum` (reserved by histograms) | `http_requests_total` | `http_requests_count` |

**Common base units:**
- Time: `_seconds` (not milliseconds or microseconds)
- Size: `_bytes` (not kilobytes or megabytes)
- Temperature: `_celsius`
- Ratios: `_ratio` (0.0 to 1.0) or `_percent` (0 to 100)

### OpenTelemetry Semantic Conventions

OTel uses dot-separated names and follows the semantic conventions specification:

| OTel metric name | Prometheus equivalent |
|------------------|-----------------------|
| `http.server.request.duration` | `http_server_request_duration_seconds` |
| `http.server.active_requests` | `http_server_active_requests` |
| `db.client.connections.usage` | `db_client_connections_usage` |
| `process.runtime.jvm.memory.usage` | `process_runtime_jvm_memory_usage_bytes` |

When using the OTel Prometheus exporter, dots are automatically converted to underscores and units are appended as suffixes.

---

## High-Cardinality Prevention

### What Causes Cardinality Explosion

Cardinality = the number of unique time series. Each unique combination of metric name + label values creates a new time series.

```
total_series = metric_count * (label_1_values * label_2_values * ... * label_N_values)
```

A single metric with three labels of 10, 50, and 200 unique values creates 100,000 time series. This is a common source of monitoring system OOM, slow queries, and high storage costs.

### Label Value Guidelines

**Rule of thumb: each label should have fewer than 100 unique values.**

| Label cardinality | Risk level | Action |
|-------------------|-----------|--------|
| < 10 values | Safe | No concern |
| 10–100 values | Acceptable | Monitor growth |
| 100–1,000 values | Risky | Justify and bound |
| 1,000–10,000 values | Dangerous | Redesign — use logs or traces instead |
| > 10,000 values | Critical | Will crash most TSDB backends |

### Examples of Bad Labels

| Bad label | Why it is bad | Better alternative |
|-----------|---------------|-------------------|
| `user_id` | Millions of unique values | Use logs/traces for per-user data; aggregate by `user_tier` |
| `request_id` | Unique per request | Never put on metrics — use trace ID in traces |
| `full_url_path` (`/users/abc123/orders/456`) | Unique per entity | Use route template: `/users/{id}/orders/{id}` |
| `email` | PII and high cardinality | Remove entirely from metrics |
| `ip_address` | High cardinality and potentially PII | Aggregate by `region` or `subnet` |
| `error_message` (free text) | Unbounded unique values | Categorize into error codes: `TIMEOUT`, `CONNECTION_REFUSED` |
| `timestamp` | Infinite cardinality | Never use as a label — it is the inherent axis of time series |
| `query` (SQL or GraphQL) | Unbounded | Use `query_name` or `operation_type` |

### Detecting Cardinality Problems

```promql
# Top 10 metrics by number of time series
topk(10, count by (__name__)({__name__=~".+"}))

# Total number of active time series
count({__name__=~".+"})

# Check cardinality of a specific metric
count(http_request_duration_seconds_bucket) by (le)
```

```bash
# Prometheus TSDB status endpoint (shows high-cardinality metrics)
curl -s http://localhost:9090/api/v1/status/tsdb | jq '.data.seriesCountByMetricName[:10]'
```

---

## Best practices

- Instrument RED metrics for every request-driven service before it goes to production
- Use histograms for latency, not averages — averages hide tail latency that affects real users
- Define at least one availability SLI and one latency SLI for every user-facing service
- Set SLO targets based on user expectations, not on what the system currently achieves
- Implement multi-window burn rate alerting instead of static threshold alerts
- Use recording rules to pre-compute SLI ratios — raw queries over long windows are expensive
- Review SLOs quarterly with stakeholders — adjust targets based on actual reliability and business needs
- Keep metric cardinality under control by reviewing label values during instrumentation code review
- Follow naming conventions from the start — renaming metrics after dashboards and alerts exist is painful
- Track error budget consumption as a first-class engineering metric visible to the whole team
- Use OpenTelemetry semantic conventions for new instrumentation to ensure cross-tool compatibility
- Separate SLIs by meaningful dimensions (e.g., per-endpoint or per-customer-tier) to avoid masking problems

## Anti-patterns

- Measuring everything but alerting on nothing — metrics without SLOs are just storage costs
- Setting SLOs at 100% — nothing is 100% reliable; this eliminates error budget and blocks all change
- Alerting on raw error counts instead of error ratios — high-traffic services always have some errors
- Using averages as SLIs — a p50 of 50ms can hide a p99 of 30 seconds
- Putting user IDs, request IDs, or free-text fields as metric labels — cardinality explosion
- Creating one SLO for an entire platform instead of per-service — masks localized failures
- Setting SLO targets without looking at historical data — leads to immediately breached or meaninglessly loose SLOs
- Ignoring error budget depletion and continuing to ship features — defeats the purpose of SLOs
- Only measuring infrastructure metrics (CPU, memory) without application-level RED metrics — infrastructure can be healthy while the application is broken
- Using `Summary` metric type when you need to aggregate across instances — summaries cannot be aggregated
