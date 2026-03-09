# Distributed Tracing Reference

End-to-end request tracing across distributed services. Covers context propagation standards, span naming and attributes, sampling strategies, and correlation with logs.

## Purpose

Answer: "Can we trace a request end-to-end across all services and see where time is spent?"

## Checklist

Before auditing, identify:

- [ ] How many services participate in a typical request path
- [ ] Communication patterns in use (synchronous HTTP/gRPC, asynchronous messaging, batch jobs)
- [ ] Whether any tracing instrumentation exists today (OpenTelemetry, Jaeger client, Zipkin, AWS X-Ray)
- [ ] Which trace backend is used or planned (Jaeger, Tempo, Zipkin, Datadog, Honeycomb, AWS X-Ray)
- [ ] Which languages and frameworks are in the service fleet

---

## Context Propagation Standards

Context propagation is how trace identity travels across service boundaries. Every outgoing request must carry trace context; every incoming request must extract it.

### W3C TraceContext (recommended)

The W3C standard uses the `traceparent` header. This is the default in OpenTelemetry and should be the first choice for new systems.

**Header format:**

```
traceparent: {version}-{trace_id}-{parent_id}-{trace_flags}
```

| Field | Length | Description |
|-------|--------|-------------|
| `version` | 2 hex chars | Always `00` for the current spec |
| `trace_id` | 32 hex chars | Globally unique identifier for the entire trace |
| `parent_id` | 16 hex chars | Identifier of the calling span |
| `trace_flags` | 2 hex chars | `01` = sampled, `00` = not sampled |

**Example:**
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

**Configuration (OpenTelemetry SDK):**

Python:
```python
from opentelemetry.propagators.composite import CompositeTextMapPropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

set_global_textmap(CompositeTextMapPropagator([
    TraceContextTextMapPropagator(),
    W3CBaggagePropagator(),
]))
```

Node.js:
```javascript
const { W3CTraceContextPropagator } = require('@opentelemetry/core');
const { W3CBaggagePropagator } = require('@opentelemetry/core');
const { CompositePropagator } = require('@opentelemetry/core');

const propagator = new CompositePropagator({
  propagators: [
    new W3CTraceContextPropagator(),
    new W3CBaggagePropagator(),
  ],
});
```

### B3 Propagation (Zipkin ecosystem)

Used by Zipkin and systems that pre-date W3C TraceContext. Use B3 when integrating with legacy Zipkin-instrumented services.

**Headers:**

| Header | Description |
|--------|-------------|
| `X-B3-TraceId` | 16 or 32 hex chars — trace identifier |
| `X-B3-SpanId` | 16 hex chars — current span identifier |
| `X-B3-ParentSpanId` | 16 hex chars — parent span identifier (optional) |
| `X-B3-Sampled` | `1` = sampled, `0` = not sampled |

B3 also supports a single-header format: `b3: {trace_id}-{span_id}-{sampling}-{parent_span_id}`

**When to use each:**

| Standard | Use when |
|----------|----------|
| W3C TraceContext | Greenfield systems, OpenTelemetry-native stacks, cross-vendor interop |
| B3 | Existing Zipkin ecosystem, or services that only support B3 |
| Both (composite) | Migration period — propagate both, accept either |

---

## Span Naming Conventions

Consistent span names make traces searchable and dashboards meaningful. Follow OpenTelemetry semantic conventions.

| Signal Type | Pattern | Example |
|-------------|---------|---------|
| HTTP server | `HTTP {METHOD} {route}` | `HTTP GET /api/users` |
| HTTP client | `HTTP {METHOD} {host}{route}` | `HTTP POST payments-service/charge` |
| Database | `{operation} {table}` | `SELECT users` |
| RPC (gRPC) | `{package.Service}/{Method}` | `grpc.UserService/GetUser` |
| Messaging (produce) | `{destination} send` | `order.events send` |
| Messaging (consume) | `{destination} receive` | `order.events receive` |
| Messaging (process) | `{destination} process` | `order.events process` |
| Internal operation | `{component}.{operation}` | `cache.lookup` |

**Rules:**
- Use low-cardinality names — parameterize IDs out (`GET /users/{id}`, not `GET /users/12345`)
- Keep names short but descriptive
- Use the route template, not the resolved path

---

## Span Attribute Semantic Conventions

OpenTelemetry defines semantic conventions for span attributes. Using standard attribute names enables cross-service querying and vendor-neutral dashboards.

### HTTP Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `http.method` | string | Required | HTTP method (`GET`, `POST`, etc.) |
| `http.status_code` | int | Required | HTTP response status code |
| `http.url` | string | Recommended | Full URL (for client spans) |
| `http.route` | string | Recommended | Route template (`/users/{id}`) |
| `http.target` | string | Recommended | Path and query string |
| `http.scheme` | string | Recommended | `http` or `https` |
| `net.host.name` | string | Recommended | Server hostname |

### Database Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `db.system` | string | Required | Database type (`postgresql`, `mysql`, `redis`, `mongodb`) |
| `db.name` | string | Recommended | Database name |
| `db.statement` | string | Recommended | Database statement (**sanitized** — no parameter values!) |
| `db.operation` | string | Recommended | Operation name (`SELECT`, `INSERT`, `findOne`) |

> **Security:** Always sanitize `db.statement` to strip query parameter values. Never record raw user input or PII in span attributes. Use parameterized queries and record only the template: `SELECT * FROM users WHERE id = ?`

### RPC Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `rpc.system` | string | Required | RPC system (`grpc`, `jsonrpc`, `connect`) |
| `rpc.service` | string | Recommended | Full service name |
| `rpc.method` | string | Recommended | Method name |
| `rpc.grpc.status_code` | int | Required (gRPC) | gRPC status code |

### Messaging Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `messaging.system` | string | Required | Messaging system (`kafka`, `rabbitmq`, `sqs`) |
| `messaging.destination` | string | Required | Topic or queue name |
| `messaging.operation` | string | Required | `send`, `receive`, or `process` |
| `messaging.message_id` | string | Recommended | Message identifier |

---

## Span Status and Error Recording

### When to Set Error Status

Set `SpanStatusCode.ERROR` when the operation has **failed from the caller's perspective**:

| Scenario | Set ERROR? |
|----------|-----------|
| HTTP 5xx response (server span) | Yes |
| HTTP 4xx response (server span) | No (client error, not server failure) |
| HTTP 4xx response (client span) | Depends — `404` on expected lookup is not an error |
| Unhandled exception | Yes |
| Business rule violation (e.g., insufficient funds) | No (expected outcome) |
| Timeout or connection failure | Yes |

### GOOD Error Recording

**Python:**
```python
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    try:
        result = process(order)
        span.set_attribute("order.id", order.id)
    except Exception as exc:
        span.set_status(StatusCode.ERROR, str(exc))
        span.record_exception(exc)
        raise
```

**Node.js:**
```javascript
const { SpanStatusCode } = require('@opentelemetry/api');

const span = tracer.startSpan('process_order');
try {
  const result = await process(order);
  span.setAttribute('order.id', order.id);
} catch (err) {
  span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
  span.recordException(err);
  throw err;
} finally {
  span.end();
}
```

### BAD Error Recording

**Python:**
```python
# BAD — swallows the error context, doesn't record exception details
with tracer.start_as_current_span("process_order") as span:
    try:
        result = process(order)
    except Exception:
        span.set_status(StatusCode.ERROR)  # no message — useless when debugging
        # missing span.record_exception() — stack trace is lost
        # missing raise — silently swallows the error
        return None
```

**Node.js:**
```javascript
// BAD — ends span before recording error, loses exception details
const span = tracer.startSpan('process_order');
try {
  const result = await process(order);
} catch (err) {
  span.end(); // ending before recording — error info is lost
  span.setStatus({ code: SpanStatusCode.ERROR }); // ignored after end()
  throw err;
}
```

---

## Sampling Strategies

Sampling controls which traces are recorded. The right strategy balances visibility with cost.

### Head-based Sampling

Sampling decision is made at trace creation (root span) and propagated to all downstream services.

| Strategy | Description | Use when |
|----------|-------------|----------|
| `AlwaysOn` | Record every trace | Development, low-traffic services |
| `AlwaysOff` | Record nothing | Disabling tracing without removing instrumentation |
| `TraceIdRatioBased` | Sample a fixed percentage based on trace ID | Steady-state production with predictable cost |
| `ParentBased` | Respect the parent span's sampling decision | All child services (ensures complete traces) |

**Configuration (OpenTelemetry SDK):**

Python:
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBasedTraceIdRatio

# Sample 10% of traces — child services inherit the decision
sampler = ParentBasedTraceIdRatio(0.1)
```

Node.js:
```javascript
const { ParentBasedSampler, TraceIdRatioBasedSampler } = require('@opentelemetry/sdk-trace-base');

const sampler = new ParentBasedSampler({
  root: new TraceIdRatioBasedSampler(0.1), // 10% of root spans
});
```

### Tail-based Sampling

Sampling decision is made **after** the trace is complete, in the OpenTelemetry Collector. This captures all interesting traces regardless of head-based ratio.

**Error-focused (keep all error traces):**
```yaml
# otel-collector-config.yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

**Latency-focused (keep slow traces):**
```yaml
processors:
  tail_sampling:
    decision_wait: 30s
    num_traces: 100000
    policies:
      - name: slow-requests
        type: latency
        latency:
          threshold_ms: 2000
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 1
```

**Choosing a strategy:**

| Concern | Recommendation |
|---------|---------------|
| Low traffic (< 1K req/s) | `AlwaysOn` head-based — keep everything |
| Moderate traffic (1K–10K req/s) | `ParentBased` + `TraceIdRatioBased` at 10–50% |
| High traffic (> 10K req/s) | Head-based at 1–5% + tail-based for errors and latency outliers |
| Debugging a specific issue | Temporarily raise sampling or add attribute-based sampling |

**Cost impact:** Trace storage is typically the largest observability cost. Tail-based sampling in the Collector is the most cost-effective approach for high-traffic systems because it keeps only the traces that matter.

---

## Trace-to-Log Correlation

Inject `trace_id` and `span_id` into every log record so you can jump from a log line to its trace and vice versa.

### Python (stdlib logging + OpenTelemetry)

```python
import logging
from opentelemetry import trace

class TraceContextFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        record.trace_id = format(ctx.trace_id, '032x') if ctx.trace_id else '0' * 32
        record.span_id = format(ctx.span_id, '016x') if ctx.span_id else '0' * 16
        return True

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s [trace_id=%(trace_id)s span_id=%(span_id)s] %(message)s'
))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.addFilter(TraceContextFilter())
```

### Node.js (pino + OpenTelemetry)

```javascript
const { trace } = require('@opentelemetry/api');
const pino = require('pino');

const logger = pino({
  mixin() {
    const span = trace.getActiveSpan();
    if (span) {
      const ctx = span.spanContext();
      return {
        trace_id: ctx.traceId,
        span_id: ctx.spanId,
      };
    }
    return {};
  },
});
```

**Tip:** Many backends (Grafana, Datadog, Honeycomb) can auto-link logs to traces if the `trace_id` field is present. Check your backend's documentation for the expected field name.

---

## Span Events vs Child Spans

Span events and child spans both add detail to a trace, but they serve different purposes.

| Use span events when... | Use child spans when... |
|------------------------|----------------------|
| Recording a point-in-time occurrence (no duration) | The operation has meaningful duration you want to measure |
| Adding lightweight annotations (cache hit/miss, retry attempt) | The operation crosses a service or component boundary |
| The occurrence doesn't represent a separate unit of work | You need separate attributes or status for the operation |
| You want minimal overhead | The operation might fail independently |

**Span event example (Python):**
```python
with tracer.start_as_current_span("handle_request") as span:
    # Lightweight annotation — no separate duration
    span.add_event("cache.lookup", {"cache.hit": True, "cache.key": "user:123"})

    # Another event — retry happened
    span.add_event("http.retry", {"retry.attempt": 2, "retry.reason": "timeout"})
```

**Child span example (Python):**
```python
with tracer.start_as_current_span("handle_request"):
    # Separate operation with its own duration and potential failure
    with tracer.start_as_current_span("db.query_user") as db_span:
        db_span.set_attribute("db.system", "postgresql")
        db_span.set_attribute("db.statement", "SELECT * FROM users WHERE id = ?")
        user = db.query(user_id)
```

---

## Baggage Propagation

W3C Baggage allows you to propagate cross-cutting key-value pairs across service boundaries. Useful for tenant IDs, feature flags, or routing hints.

**Header format:**
```
baggage: tenant_id=acme-corp,feature_flag=new-checkout,request_priority=high
```

**Python:**
```python
from opentelemetry import baggage, context

# Set baggage (returns a new context token)
ctx = baggage.set_baggage("tenant_id", "acme-corp")
token = context.attach(ctx)

# Read baggage in a downstream service
tenant = baggage.get_baggage("tenant_id")
```

**Node.js:**
```javascript
const { propagation, context, baggage } = require('@opentelemetry/api');

// Set baggage
const bag = propagation.createBaggage({
  'tenant_id': { value: 'acme-corp' },
});
const ctx = propagation.setBaggage(context.active(), bag);

// Read baggage in a downstream service
const currentBaggage = propagation.getBaggage(context.active());
const tenantId = currentBaggage?.getEntry('tenant_id')?.value;
```

**Security considerations:**
- Baggage is transmitted in HTTP headers in **plaintext** — never put sensitive data (tokens, passwords, PII) in baggage
- Baggage values are visible to every service in the call chain, including third-party services
- Validate and sanitize baggage values on ingestion — a malicious upstream could inject arbitrary keys
- Set size limits — the `baggage` header has no built-in size cap, and oversized headers can cause request failures
- Consider stripping baggage at trust boundaries (e.g., at the API gateway before calling external services)

---

## Best Practices

- Instrument at the framework level first (HTTP server/client, database drivers, gRPC interceptors) before adding custom spans
- Use `ParentBased` sampling so child services always respect the root span's sampling decision — never re-sample downstream
- Keep span names low-cardinality — parameterize dynamic segments (`/users/{id}` not `/users/42`)
- Add business-relevant attributes (`order.id`, `customer.tier`) to make traces useful beyond debugging
- Export traces via OTLP to the OpenTelemetry Collector rather than directly to a backend — the Collector provides buffering, retry, and tail sampling
- Set service name and version as resource attributes on every service so traces are properly attributed
- Test context propagation across every service boundary — a single service that drops headers breaks the entire trace
- Use trace-based testing in CI to verify critical paths produce complete traces

## Anti-Patterns

- "Trace everything, sample nothing" — sending 100% of traces in production leads to massive storage costs and noisy data
- Creating a span for every function call — traces become unusable walls of spans. Instrument boundaries and meaningful operations only
- Using high-cardinality span names (`GET /users/12345`) — blows up backend indexing and makes aggregation impossible
- Recording raw SQL with parameter values in `db.statement` — leaks PII and credentials into your trace backend
- Ignoring `ParentBased` sampling — if child services make independent sampling decisions, you get broken partial traces
- Relying only on head-based sampling — you miss errors and latency outliers. Use tail-based sampling for those
- Putting sensitive data in baggage — it travels in plaintext headers through every service in the chain
- Not correlating traces with logs — you lose the ability to jump between signals when debugging
- Setting span status to ERROR for client errors (HTTP 4xx) — inflates error rates and buries real failures
