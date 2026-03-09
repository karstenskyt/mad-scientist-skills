# Structured Logging Reference

Patterns and framework-specific examples for structured, contextual logging that integrates with centralized log aggregation and distributed tracing.

## Purpose

Answer: "Are logs structured, contextual, and shipped to a central location?"

## Checklist

Before auditing, identify:

- [ ] Which logging framework is used (stdlib, structlog, pino, winston, zap, logback)
- [ ] Where logs are shipped (stdout, file, Elasticsearch, Loki, Datadog, CloudWatch)
- [ ] What format logs are emitted in (JSON, logfmt, plain text)
- [ ] Whether sensitive data (PII, secrets, tokens) could appear in log output
- [ ] Whether correlation IDs or trace context are injected into log entries
- [ ] What log retention and volume constraints exist

## JSON Logging Setup per Framework

### Python — `logging` + `python-json-logger`

**BAD — unstructured print/logging:**
```python
# BAD — unstructured, unparseable, no context
print(f"User {user_id} placed order {order_id}")

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.info("Order placed for user %s, order %s", user_id, order_id)
# Output: INFO:mymodule:Order placed for user 42, order abc-123
```

**GOOD — structured JSON with `python-json-logger`:**
```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"},
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info(
    "Order placed",
    extra={"user_id": user_id, "order_id": order_id, "total_cents": total},
)
# Output: {"timestamp": "2025-01-15T10:30:00", "name": "mymodule",
#          "level": "INFO", "message": "Order placed",
#          "user_id": 42, "order_id": "abc-123", "total_cents": 4999}
```

### Python — `structlog`

**GOOD — structlog with bound context:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

# Bind context once, carry it through the request lifecycle
log = log.bind(request_id=request_id, user_id=user_id)
log.info("order_placed", order_id=order_id, total_cents=total)
# Output: {"request_id": "req-abc", "user_id": 42, "event": "order_placed",
#          "order_id": "abc-123", "total_cents": 4999,
#          "timestamp": "2025-01-15T10:30:00Z", "level": "info"}
```

### Node.js — `pino`

**BAD — console.log with string interpolation:**
```javascript
// BAD — unstructured, no levels, no context
console.log(`User ${userId} placed order ${orderId}`);
```

**GOOD — pino with child loggers:**
```javascript
const pino = require("pino");

const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  timestamp: pino.stdTimeFunctions.isoTime,
  formatters: {
    level(label) {
      return { level: label };
    },
  },
});

// Create a child logger with bound context
const reqLogger = logger.child({ requestId, userId });
reqLogger.info({ orderId, totalCents: total }, "order placed");
// Output: {"level":"info","time":"2025-01-15T10:30:00.000Z",
//          "requestId":"req-abc","userId":42,
//          "orderId":"abc-123","totalCents":4999,"msg":"order placed"}
```

### Node.js — `winston`

**GOOD — winston with JSON format:**
```javascript
const winston = require("winston");

const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: "order-service" },
  transports: [new winston.transports.Console()],
});

logger.info("order placed", { userId, orderId, totalCents: total });
// Output: {"level":"info","message":"order placed","service":"order-service",
//          "timestamp":"2025-01-15T10:30:00.000Z",
//          "userId":42,"orderId":"abc-123","totalCents":4999}
```

### Go — `zap`

**BAD — fmt.Printf or log.Println:**
```go
// BAD — unstructured, no levels, unparseable
fmt.Printf("User %d placed order %s\n", userID, orderID)
log.Printf("Order placed: user=%d order=%s", userID, orderID)
```

**GOOD — zap with structured fields:**
```go
import "go.uber.org/zap"

logger, _ := zap.NewProduction()
defer logger.Sync()

logger.Info("order placed",
    zap.Int("user_id", userID),
    zap.String("order_id", orderID),
    zap.Int("total_cents", totalCents),
)
// Output: {"level":"info","ts":1705312200.000,"caller":"service/order.go:42",
//          "msg":"order placed","user_id":42,"order_id":"abc-123","total_cents":4999}
```

### Go — `zerolog`

**GOOD — zerolog with context:**
```go
import "github.com/rs/zerolog/log"

log.Info().
    Int("user_id", userID).
    Str("order_id", orderID).
    Int("total_cents", totalCents).
    Msg("order placed")
// Output: {"level":"info","time":"2025-01-15T10:30:00Z",
//          "user_id":42,"order_id":"abc-123","total_cents":4999,
//          "message":"order placed"}
```

### Java — `logback` + `logstash-encoder`

**BAD — string concatenation in log statements:**
```java
// BAD — string concatenation evaluated even if level is disabled, no structure
logger.info("User " + userId + " placed order " + orderId + " for $" + total);
```

**GOOD — SLF4J with MDC and logstash-encoder:**

`logback.xml`:
```xml
<configuration>
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>requestId</includeMdcKeyName>
      <includeMdcKeyName>userId</includeMdcKeyName>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="STDOUT" />
  </root>
</configuration>
```

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import static net.logstash.logback.argument.StructuredArguments.kv;

Logger logger = LoggerFactory.getLogger(OrderService.class);

MDC.put("requestId", requestId);
MDC.put("userId", String.valueOf(userId));

logger.info("order placed", kv("orderId", orderId), kv("totalCents", total));
// Output: {"@timestamp":"2025-01-15T10:30:00.000Z","level":"INFO",
//          "logger_name":"com.example.OrderService","message":"order placed",
//          "requestId":"req-abc","userId":"42",
//          "orderId":"abc-123","totalCents":4999}

MDC.clear(); // Always clear MDC after request completes
```

---

## Log Level Policy

| Level | What to log | Production guidance |
|-------|-------------|---------------------|
| **DEBUG** | Variable values, loop iterations, internal state transitions, SQL queries with parameters | Disabled in production by default. Enable per-module via config when investigating issues. |
| **INFO** | Request received/completed, business events (order placed, user signed up), startup/shutdown, config loaded | Always enabled. These are your primary audit trail. Keep volume manageable. |
| **WARNING** | Deprecated API usage, approaching rate limits, retry attempts, fallback to defaults, slow queries | Always enabled. Should trigger review but not pages. |
| **ERROR** | Failed operations that affect a single request (unhandled exceptions, external service failures, constraint violations) | Always enabled. Should feed into alerting. Include stack traces and context. |
| **CRITICAL/FATAL** | Application cannot continue (database unreachable, out of memory, corrupt state, certificate expired) | Always enabled. Should page on-call immediately. These indicate systemic failures. |

**Rules of thumb:**

- If you need to add a log line to debug a production issue, it should have been an INFO or WARNING all along
- Never log at ERROR for expected conditions (e.g., user input validation failures are INFO or WARNING)
- A healthy production system should produce zero ERROR lines under normal operation
- Log volume at each level should follow: DEBUG >> INFO > WARNING >> ERROR > CRITICAL

---

## Correlation ID Implementation

Correlation IDs tie logs from a single request or transaction together across services. When OpenTelemetry is in use, inject `trace_id` and `span_id` into every log entry.

### Python — OTel Log Bridge

```python
import structlog
from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter

def add_otel_context(logger, method_name, event_dict):
    """Inject OTel trace context into structlog entries."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
        event_dict["trace_flags"] = format(ctx.trace_flags, "02x")
    return event_dict

structlog.configure(
    processors=[
        add_otel_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

# Now every log line automatically includes trace_id and span_id
log = structlog.get_logger()
log.info("order_placed", order_id="abc-123")
# Output includes: "trace_id": "0af7651916cd43dd8448eb211c80319c", "span_id": "b7ad6b7169203331"
```

### Python — stdlib logging with OTel

```python
import logging
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Automatically injects otelTraceID, otelSpanID, otelServiceName into LogRecords
LoggingInstrumentor().instrument(set_logging_format=True)

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s"
)
```

### Node.js — pino with OTel

```javascript
const pino = require("pino");
const { context, trace } = require("@opentelemetry/api");

const logger = pino({
  mixin() {
    const span = trace.getSpan(context.active());
    if (span) {
      const ctx = span.spanContext();
      return {
        trace_id: ctx.traceId,
        span_id: ctx.spanId,
        trace_flags: `0${ctx.traceFlags.toString(16)}`,
      };
    }
    return {};
  },
});
```

### Go — zap with OTel

```go
import (
    "go.opentelemetry.io/otel/trace"
    "go.uber.org/zap"
)

func LoggerWithTrace(ctx context.Context, logger *zap.Logger) *zap.Logger {
    span := trace.SpanFromContext(ctx)
    if !span.SpanContext().IsValid() {
        return logger
    }
    return logger.With(
        zap.String("trace_id", span.SpanContext().TraceID().String()),
        zap.String("span_id", span.SpanContext().SpanID().String()),
    )
}

// Usage in a handler
func (s *Server) HandleOrder(ctx context.Context, req *OrderRequest) {
    log := LoggerWithTrace(ctx, s.logger)
    log.Info("order placed", zap.String("order_id", req.OrderID))
}
```

### Java — Logback with OTel

Add the `opentelemetry-logback-appender` dependency, then configure:

```xml
<configuration>
  <appender name="OTEL" class="io.opentelemetry.instrumentation.logback.appender.v1_0.OpenTelemetryAppender">
    <appender-ref ref="STDOUT" />
  </appender>

  <!-- MDC fields trace_id and span_id are auto-populated by the OTel Java agent -->
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>trace_id</includeMdcKeyName>
      <includeMdcKeyName>span_id</includeMdcKeyName>
    </encoder>
  </appender>
</configuration>
```

When using the OTel Java agent (`-javaagent:opentelemetry-javaagent.jar`), `trace_id` and `span_id` are automatically injected into MDC.

---

## PII Scrubbing Patterns

Logs must never contain unredacted personally identifiable information (PII). Accidentally logging PII creates compliance risk (GDPR, CCPA, HIPAA) and makes log storage a liability.

### Common PII Fields to Watch

| Field | Example | Risk |
|-------|---------|------|
| Email addresses | `user@example.com` | GDPR personal data |
| Social Security Numbers | `123-45-6789` | Identity theft |
| Phone numbers | `+1-555-123-4567` | GDPR personal data |
| IP addresses | `192.168.1.100` | Can be PII under GDPR |
| Credit card numbers | `4111-1111-1111-1111` | PCI-DSS violation |
| Passwords / tokens | `Bearer eyJhbGci...` | Direct security risk |
| Physical addresses | `123 Main St` | GDPR personal data |
| Date of birth | `1990-01-15` | Identity correlation |

### Approach: Allowlist vs Denylist

**Allowlist (recommended):** Only log fields you explicitly permit. Unknown fields are redacted or dropped.

```python
# GOOD — allowlist approach with structlog
ALLOWED_LOG_FIELDS = {"order_id", "status", "duration_ms", "error_code", "trace_id"}

def allowlist_filter(logger, method_name, event_dict):
    """Drop any key not in the allowlist (except standard fields)."""
    standard = {"event", "level", "timestamp"}
    return {k: v for k, v in event_dict.items() if k in ALLOWED_LOG_FIELDS | standard}
```

**Denylist (fragile):** Redact known sensitive fields. Risk: new sensitive fields slip through.

```python
# LESS SAFE — denylist approach (use only as defense in depth)
REDACT_FIELDS = {"password", "token", "ssn", "credit_card", "email", "phone", "authorization"}

def redact_sensitive(logger, method_name, event_dict):
    for key in event_dict:
        if key.lower() in REDACT_FIELDS:
            event_dict[key] = "***REDACTED***"
    return event_dict
```

### Field-Level Redaction Examples

```python
# Python — redact before logging
import re

def mask_email(email: str) -> str:
    """a]****@example.com"""
    local, domain = email.split("@")
    return f"{local[0]}****@{domain}"

def mask_card(number: str) -> str:
    """****-****-****-1111"""
    digits = re.sub(r"\D", "", number)
    return f"****-****-****-{digits[-4:]}"

def mask_ip(ip: str) -> str:
    """192.168.1.xxx"""
    parts = ip.split(".")
    parts[-1] = "xxx"
    return ".".join(parts)

# Use masked values when logging
logger.info("payment processed",
    extra={
        "email": mask_email(user.email),
        "card": mask_card(card_number),
        "client_ip": mask_ip(request.remote_addr),
    },
)
```

```javascript
// Node.js — pino redaction (built-in)
const logger = pino({
  redact: {
    paths: ["req.headers.authorization", "req.headers.cookie", "user.email", "user.ssn"],
    censor: "***REDACTED***",
  },
});
```

```go
// Go — zap with a custom field wrapper
func RedactedEmail(key string, email string) zap.Field {
    if at := strings.IndexByte(email, '@'); at > 0 {
        return zap.String(key, email[:1]+"****"+email[at:])
    }
    return zap.String(key, "***REDACTED***")
}

logger.Info("user signup", RedactedEmail("email", user.Email))
```

### Regex-Based Log Scrubber (Defense in Depth)

Apply as a final-stage processor before logs leave the application:

```python
import re

PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "***SSN***"),                     # SSN
    (re.compile(r"\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "***CC***"),# Visa
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "***EMAIL***"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.I), "Bearer ***REDACTED***"),
]

def scrub_pii(log_string: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        log_string = pattern.sub(replacement, log_string)
    return log_string
```

---

## Log Shipping Approaches

### Comparison Table

| Approach | How it works | Pros | Cons |
|----------|-------------|------|------|
| **stdout → container runtime → aggregator** | App writes to stdout; container runtime (Docker, containerd) captures to file; a DaemonSet (Fluentd, Fluent Bit, Vector) tails and ships | No app changes needed; 12-factor compliant; works with any language | Requires cluster-level DaemonSet; multi-line logs need special handling |
| **Sidecar** | A log collector container runs alongside the app in the same pod, reads from a shared volume or stdout | Per-pod config flexibility; tenant isolation; works in multi-tenant clusters | Higher resource overhead (one collector per pod); more YAML to manage |
| **Host agent** | A system-level agent (Datadog Agent, CloudWatch Agent, Filebeat) runs on each host and tails log files | Works outside Kubernetes; vendor-supported; handles rotation | Requires log files (not just stdout); host-level access needed |
| **Direct SDK** | Application sends logs directly to the backend via HTTP/gRPC (e.g., Datadog SDK, AWS SDK for CloudWatch) | No infrastructure needed; simple for small deployments | Tight vendor coupling; retry/buffering logic in app; network failures can lose logs |

### Recommended Patterns

**Kubernetes / containerized workloads:**
```
App (stdout/stderr)
  → Container runtime writes to /var/log/containers/*.log
  → DaemonSet (Fluent Bit / Vector) tails logs
  → Enriches with k8s metadata (pod, namespace, labels)
  → Ships to Elasticsearch / Loki / Datadog
```

**Traditional VMs:**
```
App → structured log file (JSON, rotated)
  → Filebeat / Fluentd / Vector tails the file
  → Ships to central aggregator
```

**Serverless (Lambda, Cloud Functions):**
```
App (stdout)
  → CloudWatch Logs / Cloud Logging (automatic)
  → Subscription filter → Elasticsearch / Datadog (optional)
```

---

## Log Format Comparison

### JSON

```json
{"timestamp":"2025-01-15T10:30:00Z","level":"info","msg":"order placed","order_id":"abc-123","user_id":42,"duration_ms":152}
```

**When to use:** Most production systems. Machine-parseable, self-describing, supported by every log aggregator.

**Pros:** Easy to parse, filter, and aggregate; supports nested fields; schema evolution is straightforward.

**Cons:** Verbose; harder to scan visually during local development; requires a JSON parser.

### logfmt

```
timestamp=2025-01-15T10:30:00Z level=info msg="order placed" order_id=abc-123 user_id=42 duration_ms=152
```

**When to use:** Systems where human readability in the terminal matters alongside machine parseability (common in Go ecosystems, Heroku).

**Pros:** More readable than JSON in a terminal; still machine-parseable; compact.

**Cons:** No standard spec (informal convention); no nested structures; quoting rules vary between implementations.

### Plain text

```
2025-01-15 10:30:00 INFO [order-service] Order placed for user 42, order abc-123 (152ms)
```

**When to use:** Local development only. Never in production.

**Pros:** Most human-readable format; no setup required.

**Cons:** Requires regex to parse; fragile extraction; poor support for filtering and aggregation at scale; context fields are baked into the message string.

### Format Decision Matrix

| Criterion | JSON | logfmt | Plain text |
|-----------|------|--------|------------|
| Machine parseability | Excellent | Good | Poor |
| Human readability (terminal) | Poor | Good | Excellent |
| Nested data support | Yes | No | No |
| Log aggregator support | Universal | Common | Requires custom parsing |
| Recommended for production | Yes | Yes (if no nesting needed) | No |

---

## Best Practices

- Use structured logging from day one — retrofitting unstructured logs is expensive and error-prone
- Keep log messages as static strings; put variable data in structured fields (`"order placed"` with `order_id` field, not `"order abc-123 placed"`)
- Include a `service` or `component` field in every log entry to identify the source in aggregated views
- Inject correlation IDs (trace_id, request_id) at the middleware/interceptor level so they propagate automatically
- Set log levels via configuration (environment variable or config file), not code changes
- Use child/bound loggers to accumulate context through the request lifecycle instead of repeating fields
- Sample verbose log paths (e.g., log 1 in 100 health check requests) to control volume
- Include timing information (`duration_ms`) in request completion logs for performance analysis
- Ensure stack traces are attached to the log entry as a field, not split across multiple lines
- Test that your log pipeline handles multi-line messages (stack traces, SQL) without splitting them

## Anti-Patterns

- Using `print()` / `console.log()` / `fmt.Println()` instead of a structured logger — loses levels, context, and parseability
- String-interpolating variables into log messages instead of using structured fields — defeats the purpose of structured logging
- Logging full request/response bodies — creates volume problems and PII risk
- Using ERROR level for expected conditions (invalid user input, 404s) — creates alert fatigue
- Logging sensitive data "temporarily for debugging" and forgetting to remove it
- Not setting up log rotation or retention policies — disk fills up, costs spiral
- Catching exceptions and logging them without re-raising or returning an error — swallows failures
- Logging inside tight loops without sampling — a single request can produce thousands of lines
- Using different log formats across services — makes aggregation and correlation painful
- Treating logs as a substitute for metrics — use counters/histograms for things you want to alert on or graph
