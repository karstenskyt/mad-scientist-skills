# OpenTelemetry Instrumentation Reference

Comprehensive reference for instrumenting applications with OpenTelemetry. Covers SDK setup, auto-instrumentation, exporter configuration, Collector deployment, and conventions for custom telemetry across all three pillars: logs, metrics, and traces.

## Purpose

Answer: "Does this application have proper OpenTelemetry instrumentation? Are the three pillars (logs, metrics, traces) covered?"

## Checklist

Before auditing, identify:

- [ ] Which language and runtime the application uses (Python, Node.js, Go, Java, .NET)
- [ ] Which web framework is used (Django, Flask, FastAPI, Express, Next.js, Spring Boot, ASP.NET)
- [ ] What deployment model is in place (Kubernetes, ECS, bare VM, serverless)
- [ ] Whether any telemetry already exists (StatsD, Prometheus client, structured logging, Jaeger SDK)
- [ ] Which observability backend is targeted (Grafana stack, Datadog, Splunk, AWS CloudWatch, self-hosted)

---

## OTel SDK Setup Per Language

### Python

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "my-service",
    "service.version": "1.0.0",
    "deployment.environment": "production",
})

provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
```

### Node.js

```bash
npm install @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/exporter-trace-otlp-grpc
```

```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-grpc";
import { Resource } from "@opentelemetry/resources";
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
} from "@opentelemetry/semantic-conventions";

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: "my-service",
    [ATTR_SERVICE_VERSION]: "1.0.0",
  }),
  traceExporter: new OTLPTraceExporter(),
});

sdk.start();
```

### Go

```bash
go get go.opentelemetry.io/otel \
       go.opentelemetry.io/otel/sdk \
       go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
```

```go
package main

import (
    "context"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func initTracer(ctx context.Context) (*sdktrace.TracerProvider, error) {
    exporter, err := otlptracegrpc.New(ctx)
    if err != nil {
        return nil, err
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceName("my-service"),
            semconv.ServiceVersion("1.0.0"),
        )),
    )
    otel.SetTracerProvider(tp)
    return tp, nil
}
```

### Java

```xml
<!-- Maven -->
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-api</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-sdk</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```

```java
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.semconv.ResourceAttributes;

Resource resource = Resource.getDefault()
    .merge(Resource.create(Attributes.of(
        ResourceAttributes.SERVICE_NAME, "my-service",
        ResourceAttributes.SERVICE_VERSION, "1.0.0"
    )));

SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
    .addSpanProcessor(BatchSpanProcessor.builder(
        OtlpGrpcSpanExporter.builder().build()
    ).build())
    .setResource(resource)
    .build();

OpenTelemetry openTelemetry = OpenTelemetrySdk.builder()
    .setTracerProvider(tracerProvider)
    .buildAndRegisterGlobal();
```

---

## Auto-Instrumentation Packages

### Python

| Package | Instruments |
|---------|-------------|
| `opentelemetry-instrumentation-requests` | `requests` HTTP client |
| `opentelemetry-instrumentation-urllib3` | `urllib3` HTTP client |
| `opentelemetry-instrumentation-httpx` | `httpx` async HTTP client |
| `opentelemetry-instrumentation-django` | Django request/response lifecycle |
| `opentelemetry-instrumentation-flask` | Flask request/response lifecycle |
| `opentelemetry-instrumentation-fastapi` | FastAPI request/response lifecycle |
| `opentelemetry-instrumentation-sqlalchemy` | SQLAlchemy database queries |
| `opentelemetry-instrumentation-psycopg2` | PostgreSQL via psycopg2 |
| `opentelemetry-instrumentation-redis` | Redis commands |
| `opentelemetry-instrumentation-celery` | Celery task execution |
| `opentelemetry-instrumentation-grpc` | gRPC client and server |
| `opentelemetry-instrumentation-kafka-python` | Kafka producer/consumer |
| `opentelemetry-instrumentation-boto3sqs` | AWS SQS via boto3 |
| `opentelemetry-instrumentation-logging` | stdlib `logging` correlation |

**Bulk install:**
```bash
opentelemetry-bootstrap -a install
```

### Node.js

| Package | Instruments |
|---------|-------------|
| `@opentelemetry/instrumentation-http` | Node.js `http`/`https` modules |
| `@opentelemetry/instrumentation-express` | Express middleware and routes |
| `@opentelemetry/instrumentation-fastify` | Fastify request lifecycle |
| `@opentelemetry/instrumentation-nestjs-core` | NestJS controllers and providers |
| `@opentelemetry/instrumentation-pg` | PostgreSQL via `pg` |
| `@opentelemetry/instrumentation-mysql2` | MySQL via `mysql2` |
| `@opentelemetry/instrumentation-mongodb` | MongoDB operations |
| `@opentelemetry/instrumentation-redis-4` | Redis v4 commands |
| `@opentelemetry/instrumentation-grpc` | gRPC client and server |
| `@opentelemetry/instrumentation-kafkajs` | KafkaJS producer/consumer |
| `@opentelemetry/instrumentation-aws-sdk` | AWS SDK v3 calls |

### Go

| Package | Instruments |
|---------|-------------|
| `go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp` | `net/http` client and server |
| `go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc` | gRPC client and server |
| `go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin` | Gin router |
| `go.opentelemetry.io/contrib/instrumentation/github.com/gorilla/mux/otelmux` | Gorilla Mux router |
| `go.opentelemetry.io/contrib/instrumentation/github.com/labstack/echo/otelecho` | Echo router |
| `github.com/XSAM/otelsql` | `database/sql` queries |
| `go.opentelemetry.io/contrib/instrumentation/github.com/Shopify/sarama/otelsarama` | Kafka via Sarama |
| `go.opentelemetry.io/contrib/instrumentation/go.mongodb.org/mongo-driver/mongo/otelmongo` | MongoDB operations |

### Java

| Package | Instruments |
|---------|-------------|
| Java Agent (`-javaagent:opentelemetry-javaagent.jar`) | **Everything** — JDBC, HTTP clients, Servlet, Spring, gRPC, Kafka, and 100+ libraries automatically |

The Java agent is the recommended approach. It requires zero code changes.

```bash
java -javaagent:opentelemetry-javaagent.jar \
     -Dotel.service.name=my-service \
     -jar myapp.jar
```

---

## Exporter Configuration

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | `http://localhost:4317` (gRPC), `http://localhost:4318` (HTTP) |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Transport protocol | `grpc`, `http/protobuf`, `http/json` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Authentication headers | `Authorization=Bearer token123` |
| `OTEL_EXPORTER_OTLP_CERTIFICATE` | TLS CA certificate path | `/etc/ssl/certs/ca.pem` |
| `OTEL_SERVICE_NAME` | Service name resource attribute | `order-service` |
| `OTEL_RESOURCE_ATTRIBUTES` | Additional resource attributes | `deployment.environment=prod,service.version=2.1.0` |
| `OTEL_TRACES_SAMPLER` | Sampling strategy | `parentbased_traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG` | Sampler argument | `0.1` (10% sampling) |
| `OTEL_LOGS_EXPORTER` | Log exporter type | `otlp`, `console`, `none` |
| `OTEL_METRICS_EXPORTER` | Metrics exporter type | `otlp`, `prometheus`, `none` |
| `OTEL_TRACES_EXPORTER` | Traces exporter type | `otlp`, `console`, `none` |
| `OTEL_PROPAGATORS` | Context propagation format | `tracecontext,baggage` (W3C default) |
| `OTEL_EXPORTER_OTLP_COMPRESSION` | Payload compression | `gzip` |

### Exporter Types

**OTLP (gRPC)** — preferred for production:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

**OTLP (HTTP/protobuf)** — for environments where gRPC is not available:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

**Prometheus** — metrics only, pull-based:
```bash
OTEL_METRICS_EXPORTER=prometheus
# Exposes /metrics endpoint on port 9464 by default
```

**Console** — development and debugging:
```bash
OTEL_TRACES_EXPORTER=console
OTEL_METRICS_EXPORTER=console
OTEL_LOGS_EXPORTER=console
```

**File** — useful for batch processing or local development:
```bash
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# Pair with a Collector that exports to file (see Collector section)
```

---

## OTel Collector Configuration

The Collector is a vendor-agnostic proxy that receives, processes, and exports telemetry data. Deploy it as a sidecar, DaemonSet, or standalone service.

### Minimal Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    send_batch_size: 1024
    timeout: 5s

  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  resource:
    attributes:
      - key: deployment.environment
        value: production
        action: upsert

exporters:
  otlphttp:
    endpoint: https://otlp-backend.example.com:4318
    headers:
      Authorization: "Bearer ${env:OTLP_AUTH_TOKEN}"

  debug:
    verbosity: basic

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlphttp]

  telemetry:
    logs:
      level: info
    metrics:
      address: 0.0.0.0:8888
```

### Key Components

**Receivers** — how data enters the Collector:
- `otlp` — OTLP over gRPC and HTTP (the standard)
- `prometheus` — scrape Prometheus endpoints
- `filelog` — tail log files
- `hostmetrics` — CPU, memory, disk, network metrics from the host

**Processors** — transform data in the pipeline:
- `batch` — group spans/metrics/logs for efficient export
- `memory_limiter` — prevent OOM by dropping data under memory pressure
- `resource` — add/modify resource attributes
- `filter` — drop unwanted telemetry (e.g., health check spans)
- `attributes` — add/modify/delete span or log attributes
- `tail_sampling` — sample decisions based on complete traces

**Exporters** — where data goes:
- `otlp` / `otlphttp` — forward to another Collector or backend
- `prometheus` — expose a Prometheus scrape endpoint
- `file` — write to local JSON files
- `debug` — print to Collector stdout (development only)

---

## Resource Attribute Conventions

Resource attributes identify the entity producing telemetry. Use [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/resource/) for standard attributes.

| Attribute | Required | Example | Purpose |
|-----------|----------|---------|---------|
| `service.name` | Yes | `order-service` | Unique name of the service |
| `service.version` | Yes | `2.4.1` | Deployed version (use semver or git SHA) |
| `deployment.environment` | Yes | `production` | Deployment target (`production`, `staging`, `development`) |
| `service.namespace` | Recommended | `ecommerce` | Logical grouping of related services |
| `host.name` | Recommended | `ip-10-0-1-42` | Hostname of the machine |
| `service.instance.id` | Recommended | `pod-abc123` | Unique instance identifier (pod name, container ID) |
| `cloud.provider` | If applicable | `aws` | Cloud provider (`aws`, `gcp`, `azure`) |
| `cloud.region` | If applicable | `us-east-1` | Cloud region |
| `k8s.namespace.name` | If on K8s | `default` | Kubernetes namespace |
| `k8s.pod.name` | If on K8s | `order-svc-5f8d7` | Kubernetes pod name |

**Set via environment variable:**
```bash
OTEL_RESOURCE_ATTRIBUTES="service.name=order-service,service.version=2.4.1,deployment.environment=production,service.namespace=ecommerce"
```

---

## Custom Attribute Namespaces

When no semantic convention exists for your domain, define custom attributes using a `<domain>.*` namespace. This avoids collisions with future OTel conventions and keeps attributes discoverable.

**Rules:**
- Use lowercase dot-separated namespaces
- Prefix with your domain or business area
- Document custom attributes in a shared schema registry or team wiki
- Never use top-level names that could collide with OTel conventions

**Examples:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `analytics.model.name` | string | Name of the ML model used for inference |
| `analytics.model.version` | string | Version of the ML model |
| `analytics.prediction.confidence` | float | Confidence score of a prediction |
| `pipeline.source` | string | Data pipeline source system |
| `pipeline.stage` | string | Current pipeline stage (`ingest`, `transform`, `load`) |
| `pipeline.run_id` | string | Unique identifier for a pipeline execution |
| `batch.row_count` | int | Number of rows processed in a batch operation |
| `batch.byte_size` | int | Byte size of the batch payload |
| `tenant.id` | string | Multi-tenant customer identifier |
| `tenant.plan` | string | Customer subscription tier |
| `feature_flag.name` | string | Feature flag evaluated during the request |
| `feature_flag.variant` | string | Variant returned by the feature flag system |

**Usage in code (Python):**
```python
with tracer.start_as_current_span("run-inference") as span:
    span.set_attribute("analytics.model.name", "fraud-detector")
    span.set_attribute("analytics.model.version", "3.2.1")
    span.set_attribute("analytics.prediction.confidence", 0.97)
    span.set_attribute("batch.row_count", len(batch))
```

---

## Dual-Export Pattern

Use the `OTEL_MODE` environment variable to switch between telemetry tiers depending on the deployment context. This lets individual developers run lightweight local telemetry while production uses a full enterprise backend.

### Tier Definitions

| `OTEL_MODE` | Target | Use Case |
|--------------|--------|----------|
| `personal` | Local file / S3 bucket | Solo developer, local debugging, cost-free |
| `team` | Shared Grafana / Jaeger | Team-level visibility, shared staging environments |
| `enterprise` | Grafana Cloud / Datadog / Splunk | Production, SLA monitoring, cross-team correlation |

### Layered Collector Configuration

The Collector config switches exporters based on the mode. Use a config file per tier or a single config with conditional logic via environment variable substitution.

**Personal tier** — export to local files or S3:
```yaml
exporters:
  file/traces:
    path: /var/otel/traces.jsonl
    rotation:
      max_megabytes: 100
      max_backups: 3
  awss3:
    s3uploader:
      region: us-east-1
      s3_bucket: my-dev-telemetry
      s3_prefix: traces

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [file/traces]
```

**Enterprise tier** — export to managed backends:
```yaml
exporters:
  otlphttp/grafana:
    endpoint: https://otlp-gateway-prod-us-east-0.grafana.net/otlp
    headers:
      Authorization: "Basic ${env:GRAFANA_OTLP_TOKEN}"

  datadog:
    api:
      key: ${env:DD_API_KEY}
      site: datadoghq.com

  splunk_hec:
    endpoint: https://splunk-hec.example.com:8088/services/collector
    token: ${env:SPLUNK_HEC_TOKEN}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [otlphttp/grafana]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/grafana]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlphttp/grafana]
```

### Application-Side Switching

```bash
# .env.local (developer machine)
OTEL_MODE=personal
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# .env.production
OTEL_MODE=enterprise
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.monitoring.svc:4317
```

The application code does not change between tiers. Only the Collector configuration and endpoint differ.

---

## Framework-Specific Setup

| Framework | Language | Setup Approach |
|-----------|----------|---------------|
| **Django** | Python | Add `opentelemetry-instrumentation-django`. Set `DJANGO_SETTINGS_MODULE` before `DjangoInstrumentor().instrument()`. Use middleware order: OTel middleware should wrap all others. |
| **Flask** | Python | `FlaskInstrumentor().instrument_app(app)` after app creation. For factory pattern, instrument inside `create_app()`. |
| **FastAPI** | Python | `FastAPIInstrumentor.instrument_app(app)`. Works with Uvicorn. Add `opentelemetry-instrumentation-starlette` for full ASGI coverage. |
| **Express** | Node.js | Register instrumentations in a `tracing.js` file. Load it before app code: `node -r ./tracing.js app.js`. |
| **Next.js** | Node.js | Create `instrumentation.ts` in project root with `register()` export (App Router). Use `@vercel/otel` for Vercel deployments or manual SDK setup otherwise. |
| **Spring Boot** | Java | Use the Java agent (`-javaagent:opentelemetry-javaagent.jar`) or Spring Boot Starter: `io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter`. |
| **ASP.NET** | .NET | `AddOpenTelemetry()` in `Program.cs`. Use `AspNetCoreInstrumentation`, `HttpClientInstrumentation`, and `SqlClientInstrumentation`. |

### Key Pattern: Initialize Telemetry Before Application Code

Every framework follows the same rule — the OTel SDK must be initialized before any application code runs. This ensures all auto-instrumentation hooks are registered before libraries are imported or instantiated.

**Python:**
```bash
# Use opentelemetry-instrument CLI wrapper
opentelemetry-instrument --service_name my-service python app.py

# Or programmatic setup in a sitecustomize.py / conftest.py / app entrypoint
```

**Node.js:**
```bash
# Use --require to load tracing before app
node --require ./tracing.js app.js

# Or with the auto-instrumentation agent
npx @opentelemetry/auto-instrumentations-node app.js
```

**Java:**
```bash
# Agent attaches before main() runs
java -javaagent:opentelemetry-javaagent.jar -jar myapp.jar
```

**Go:**
```go
// Initialize in main() before starting the HTTP server
func main() {
    tp, _ := initTracer(context.Background())
    defer tp.Shutdown(context.Background())

    // Now start the server
    http.ListenAndServe(":8080", handler)
}
```

---

## Best Practices

- Always set `service.name`, `service.version`, and `deployment.environment` as resource attributes — these are the minimum for useful telemetry
- Use the OTel Collector instead of exporting directly from applications — it decouples your app from the backend and enables buffering, retrying, and enrichment
- Enable `batch` and `memory_limiter` processors in the Collector — batch for efficiency, memory limiter to prevent OOM
- Use `parentbased_traceidratio` sampler instead of `traceidratio` — it respects upstream sampling decisions, keeping traces complete
- Correlate logs with traces by injecting `trace_id` and `span_id` into log records — this enables jumping from a log line to its trace
- Set `OTEL_EXPORTER_OTLP_COMPRESSION=gzip` in production — reduces network bandwidth significantly
- Pin auto-instrumentation package versions to avoid breaking changes on upgrade
- Test instrumentation in CI — assert that spans are created for critical paths (use in-memory exporters in tests)
- Use semantic conventions for attributes wherever they exist before inventing custom ones
- Shut down the tracer provider gracefully on application exit to flush pending spans

## Anti-Patterns

- Exporting directly to a backend from the application without a Collector — couples the app to the vendor and loses buffering/retry capability
- Using `AlwaysOn` sampler in production for high-throughput services — generates excessive data and cost, use head or tail sampling instead
- Adding high-cardinality attributes to metrics (e.g., `user.id`, `request.id`) — causes metric cardinality explosion and storage blowup
- Creating a new span for every function call — produces excessively deep traces with noise, instrument meaningful operations only
- Ignoring `span.record_exception()` and `span.set_status(ERROR)` — errors become invisible in trace backends
- Hardcoding exporter endpoints in application code instead of using environment variables — makes configuration inflexible across environments
- Forgetting to propagate context in async code or across thread boundaries — breaks trace continuity and produces orphaned spans
- Using `console` exporter in production — floods stdout and degrades performance
- Not setting a `memory_limiter` on the Collector — a traffic spike can OOM the Collector and lose all buffered telemetry
- Mixing OpenTelemetry with legacy tracing SDKs (Jaeger client, Zipkin client) without migration — causes duplicate spans and context propagation conflicts
