# Profiling & Benchmarking Reference

Comprehensive guide to performance testing methodology, load testing tools, micro-benchmarking, regression detection in CI, profiling techniques, performance budgets, and results interpretation.

## Purpose

Answer: "Is there a systematic approach to measuring, tracking, and preventing performance regressions?"

## Checklist

Before auditing, identify:

- [ ] Whether any performance tests exist (load tests, benchmarks, profiling scripts)
- [ ] Whether a performance baseline is documented (p50/p95/p99 latency, throughput)
- [ ] Whether CI/CD includes a performance regression gate
- [ ] Whether profiling has been run and results analyzed
- [ ] Whether performance budgets are defined and enforced

---

## Performance Testing Methodology

Each type of performance test answers a different question. Use the matrix below to select the appropriate type for the situation.

| Type | Question it answers | Duration | Traffic pattern | When to use |
|------|-------------------|----------|-----------------|-------------|
| **Load testing** | Can the system handle expected traffic? | 5-30 min | Steady at expected peak | Before every major release; validates capacity meets SLAs |
| **Stress testing** | Where does the system break? | 10-30 min | Ramp up beyond expected peak | Quarterly; after infrastructure changes; capacity planning |
| **Soak testing** | Are there memory leaks or resource exhaustion over time? | 2-24 hours | Steady at moderate load | After dependency upgrades; when memory growth is suspected |
| **Spike testing** | Can the system handle sudden traffic bursts? | 5-15 min | Sharp increase then drop | Before marketing campaigns; flash sale preparation |
| **Capacity testing** | What is the maximum throughput before degradation? | 15-45 min | Incremental ramp until failure | Infrastructure planning; scaling architecture decisions |

### Testing order for a new system

1. **Load test** first to validate expected traffic works
2. **Stress test** to find the breaking point
3. **Spike test** to verify recovery from bursts
4. **Soak test** to catch slow leaks
5. **Capacity test** to document maximum throughput

---

## Load Testing Tools

### Tool comparison

| Tool | Language | Protocol | Distributed | Scripting | Best for |
|------|----------|----------|-------------|-----------|----------|
| **k6** | JavaScript | HTTP, gRPC, WebSocket | Yes (k6 Cloud) | JS ES6 modules | Developer-friendly scripting, CI integration |
| **locust** | Python | HTTP, custom | Yes (built-in) | Python classes | Python teams, complex user flows |
| **wrk/wrk2** | C | HTTP | No | Lua (optional) | Maximum raw HTTP throughput measurement |
| **hey** | Go | HTTP | No | CLI flags only | Quick one-liner HTTP benchmarks |
| **artillery** | YAML/JS | HTTP, WebSocket, Socket.io | Yes (Artillery Cloud) | YAML scenarios | Scenario-based, config-driven testing |
| **gatling** | Scala | HTTP, WebSocket, JMS | Yes | Scala DSL | JVM teams, detailed HTML reports |

### k6

Modern, developer-friendly load testing with JavaScript scripting.

```bash
# Install
brew install k6          # macOS
choco install k6         # Windows
snap install k6          # Linux
```

```javascript
// load-test.js — k6 load test script
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiDuration = new Trend('api_duration', true);

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 50 },   // ramp up to 50 users
    { duration: '5m', target: 50 },   // hold at 50 users
    { duration: '2m', target: 200 },  // ramp up to 200 users
    { duration: '5m', target: 200 },  // hold at 200 users
    { duration: '1m', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<300', 'p(99)<500'],  // 95% < 300ms, 99% < 500ms
    errors: ['rate<0.01'],                           // error rate < 1%
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // GET request
  const listRes = http.get('http://localhost:8080/api/items', {
    headers: { 'Authorization': 'Bearer test-token' },
  });
  check(listRes, {
    'list status is 200': (r) => r.status === 200,
    'list response time < 200ms': (r) => r.timings.duration < 200,
  });
  errorRate.add(listRes.status !== 200);
  apiDuration.add(listRes.timings.duration);

  // POST request
  const payload = JSON.stringify({ name: 'test-item', value: Math.random() });
  const createRes = http.post('http://localhost:8080/api/items', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(createRes, {
    'create status is 201': (r) => r.status === 201,
  });

  sleep(1); // think time between iterations
}
```

```bash
# Run
k6 run load-test.js
k6 run --vus 100 --duration 5m load-test.js    # override from CLI
k6 run --out json=results.json load-test.js     # export results
```

### locust

Python-based distributed load testing with a web UI.

```bash
# Install
pip install locust
```

```python
# locustfile.py — locust load test
from locust import HttpUser, task, between, tag
import json
import random

class APIUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 second think time
    host = "http://localhost:8080"

    def on_start(self):
        """Run once per user on startup — login, setup."""
        response = self.client.post("/api/auth/login", json={
            "username": "loadtest",
            "password": "test-password",  # pragma: allowlist secret
        })
        self.token = response.json().get("token", "")

    @task(3)  # weight=3 — runs 3x more often than weight=1 tasks
    @tag("read")
    def list_items(self):
        self.client.get("/api/items", headers={
            "Authorization": f"Bearer {self.token}",
        })

    @task(1)
    @tag("write")
    def create_item(self):
        self.client.post("/api/items",
            json={"name": f"item-{random.randint(1, 10000)}"},
            headers={"Authorization": f"Bearer {self.token}"},
        )

    @task(2)
    @tag("read")
    def get_item(self):
        item_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/items/{item_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()  # 404 is expected for missing items
```

```bash
# Run
locust -f locustfile.py                             # web UI at http://localhost:8089
locust -f locustfile.py --headless -u 100 -r 10     # headless: 100 users, 10/sec ramp
locust -f locustfile.py --tags read                  # run only read tasks
```

### wrk / wrk2

High-performance HTTP benchmarking tools written in C. wrk2 adds constant-throughput mode for accurate latency measurement.

```bash
# wrk — maximum throughput measurement
wrk -t12 -c400 -d30s http://localhost:8080/api/items

# wrk2 — constant throughput (accurate latency at target RPS)
wrk2 -t4 -c100 -d60s -R2000 http://localhost:8080/api/items
#   -R2000 = target 2000 requests/sec (constant throughput)
```

### hey

Simple HTTP load generator — ideal for quick one-off benchmarks.

```bash
# Install
go install github.com/rakyll/hey@latest

# 200 requests, 50 concurrent
hey -n 200 -c 50 http://localhost:8080/api/items

# 30 seconds duration, 10 concurrent, with headers
hey -z 30s -c 10 \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/items

# POST with body
hey -n 1000 -c 20 -m POST \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}' \
  http://localhost:8080/api/items
```

### artillery

YAML-based scenario definition for structured load tests.

```yaml
# artillery-config.yml
config:
  target: "http://localhost:8080"
  phases:
    - duration: 60
      arrivalRate: 5
      name: "Warm up"
    - duration: 300
      arrivalRate: 50
      name: "Sustained load"
    - duration: 60
      arrivalRate: 100
      name: "Peak"
  defaults:
    headers:
      Authorization: "Bearer test-token"

scenarios:
  - name: "Browse and purchase"
    flow:
      - get:
          url: "/api/items"
          capture:
            json: "$.items[0].id"
            as: "itemId"
      - think: 2
      - get:
          url: "/api/items/{{ itemId }}"
      - think: 1
      - post:
          url: "/api/cart"
          json:
            itemId: "{{ itemId }}"
            quantity: 1
```

```bash
artillery run artillery-config.yml
artillery run --output report.json artillery-config.yml
artillery report report.json    # generate HTML report
```

### gatling

JVM-based load testing with Scala DSL and detailed HTML reports.

```scala
// BasicSimulation.scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class BasicSimulation extends Simulation {
  val httpProtocol = http
    .baseUrl("http://localhost:8080")
    .acceptHeader("application/json")
    .header("Authorization", "Bearer test-token")

  val scn = scenario("API Load Test")
    .exec(http("List Items").get("/api/items").check(status.is(200)))
    .pause(1.second, 3.seconds)
    .exec(http("Get Item").get("/api/items/1").check(status.is(200)))

  setUp(
    scn.inject(
      rampUsersPerSec(1).to(50).during(1.minute),
      constantUsersPerSec(50).during(5.minutes),
    )
  ).protocols(httpProtocol)
   .assertions(
     global.responseTime.percentile3.lt(300),  // p95 < 300ms
     global.successfulRequests.percent.gt(99),
   )
}
```

---

## Micro-Benchmarking

Micro-benchmarks measure the performance of isolated code units. They complement load tests by pinpointing exactly which function or algorithm is slow.

### Python: pytest-benchmark

```bash
pip install pytest-benchmark
```

```python
# test_performance.py
import pytest
from myapp.processing import transform_data, parse_records

def test_transform_small_dataset(benchmark):
    data = [{"id": i, "value": f"item-{i}"} for i in range(100)]
    result = benchmark(transform_data, data)
    assert len(result) == 100

def test_transform_large_dataset(benchmark):
    data = [{"id": i, "value": f"item-{i}"} for i in range(10_000)]
    result = benchmark(transform_data, data)
    assert len(result) == 10_000

def test_parse_records(benchmark):
    raw = "id,name,value\n" + "\n".join(
        f"{i},item-{i},{i*10}" for i in range(1000)
    )
    benchmark.pedantic(parse_records, args=(raw,), rounds=50, warmup_rounds=5)
```

```bash
pytest test_performance.py --benchmark-only
pytest test_performance.py --benchmark-json=benchmark.json       # export for CI
pytest test_performance.py --benchmark-compare=0001              # compare to baseline
pytest test_performance.py --benchmark-autosave                  # auto-save baseline
```

### Python: timeit

```python
import timeit

# Quick one-liner from CLI
# python -m timeit -s "data = list(range(1000))" "set(data)"

# In code
setup = "data = list(range(10000))"
list_lookup = timeit.timeit("999 in data", setup=setup, number=10000)
set_lookup = timeit.timeit("999 in s", setup=setup + "; s = set(data)", number=10000)
print(f"List lookup: {list_lookup:.4f}s, Set lookup: {set_lookup:.4f}s")
```

### JavaScript: Benchmark.js

```bash
npm install benchmark
```

```javascript
// bench.js
const Benchmark = require('benchmark');
const suite = new Benchmark.Suite();

const data = Array.from({ length: 10000 }, (_, i) => i);
const dataSet = new Set(data);

suite
  .add('Array.includes', () => { data.includes(9999); })
  .add('Set.has', () => { dataSet.has(9999); })
  .add('Array.indexOf', () => { data.indexOf(9999); })
  .on('cycle', (event) => { console.log(String(event.target)); })
  .on('complete', function () {
    console.log('Fastest is ' + this.filter('fastest').map('name'));
  })
  .run({ async: true });
```

### Go: testing.B with benchstat

```go
// processing_test.go
package processing

import (
    "testing"
)

func BenchmarkTransformSmall(b *testing.B) {
    data := generateData(100)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Transform(data)
    }
}

func BenchmarkTransformLarge(b *testing.B) {
    data := generateData(10000)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Transform(data)
    }
}

func BenchmarkLookupMap(b *testing.B) {
    m := make(map[string]int, 10000)
    for i := 0; i < 10000; i++ {
        m[fmt.Sprintf("key-%d", i)] = i
    }
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _ = m["key-9999"]
    }
}

// Report allocations
func BenchmarkAllocations(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        result := make([]byte, 0)
        for j := 0; j < 100; j++ {
            result = append(result, byte(j))
        }
    }
}
```

```bash
# Run benchmarks
go test -bench=. -benchmem ./...

# Save baseline and compare with benchstat
go test -bench=. -count=10 ./... > old.txt
# ... make changes ...
go test -bench=. -count=10 ./... > new.txt
benchstat old.txt new.txt
```

### Java: JMH (Java Microbenchmark Harness)

```java
// TransformBenchmark.java
import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@State(Scope.Benchmark)
@Warmup(iterations = 3, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(2)
public class TransformBenchmark {

    private List<Item> smallData;
    private List<Item> largeData;

    @Setup
    public void setup() {
        smallData = generateItems(100);
        largeData = generateItems(10_000);
    }

    @Benchmark
    public List<Item> transformSmall() {
        return Transformer.transform(smallData);
    }

    @Benchmark
    public List<Item> transformLarge() {
        return Transformer.transform(largeData);
    }
}
```

```bash
# Run JMH
mvn clean install
java -jar target/benchmarks.jar
java -jar target/benchmarks.jar -rf json -rff results.json   # export JSON
```

### Rust: criterion

```toml
# Cargo.toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[[bench]]
name = "transform_bench"
harness = false
```

```rust
// benches/transform_bench.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};

fn bench_transform(c: &mut Criterion) {
    let mut group = c.benchmark_group("transform");
    for size in [100, 1_000, 10_000].iter() {
        let data = generate_data(*size);
        group.bench_with_input(BenchmarkId::from_parameter(size), &data, |b, data| {
            b.iter(|| transform(black_box(data)));
        });
    }
    group.finish();
}

criterion_group!(benches, bench_transform);
criterion_main!(benches);
```

```bash
cargo bench
cargo bench -- transform    # run only benchmarks matching "transform"
```

### .NET: BenchmarkDotNet

```csharp
// TransformBenchmark.cs
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;

[MemoryDiagnoser]
[RankColumn]
public class TransformBenchmark
{
    private List<Item> _smallData;
    private List<Item> _largeData;

    [GlobalSetup]
    public void Setup()
    {
        _smallData = GenerateItems(100);
        _largeData = GenerateItems(10_000);
    }

    [Benchmark(Baseline = true)]
    public List<Item> TransformSmall() => Transformer.Transform(_smallData);

    [Benchmark]
    public List<Item> TransformLarge() => Transformer.Transform(_largeData);
}

// Program.cs
BenchmarkRunner.Run<TransformBenchmark>();
```

```bash
dotnet run -c Release
```

---

## Performance Regression Detection in CI

Detecting performance regressions automatically prevents slow code from reaching production.

### Strategy overview

| Approach | Pros | Cons | Best for |
|----------|------|------|----------|
| Compare against fixed baseline | Simple, deterministic | Baseline goes stale | Stable APIs, mature codebases |
| Compare against previous run | Always current | Noisy on shared CI runners | Active development |
| Statistical comparison (benchstat) | Accounts for variance | Requires multiple runs | Micro-benchmarks |
| Performance budget threshold | Absolute limits | Must be tuned per endpoint | Response time SLAs |

### GitHub Actions — Continuous Benchmark

```yaml
# .github/workflows/benchmark.yml
name: Performance Regression Check

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run benchmarks
        run: |
          # Python example — adapt for your language
          pip install pytest pytest-benchmark
          pytest tests/benchmarks/ \
            --benchmark-only \
            --benchmark-json=output.json

      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: output.json
          # Comment on PR if performance regresses by more than 10%
          alert-threshold: '110%'
          comment-on-alert: true
          fail-on-alert: true
          # Store results in gh-pages branch for tracking
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          benchmark-data-dir-path: dev/bench
```

### GitHub Actions — Go benchmarks with benchstat

```yaml
# .github/workflows/go-benchmark.yml
name: Go Benchmark Regression

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Install benchstat
        run: go install golang.org/x/perf/cmd/benchstat@latest

      - name: Benchmark baseline (main branch)
        run: |
          git stash
          git checkout main
          go test -bench=. -count=6 -benchmem ./... > /tmp/old.txt
          git checkout -

      - name: Benchmark PR branch
        run: |
          git stash pop || true
          go test -bench=. -count=6 -benchmem ./... > /tmp/new.txt

      - name: Compare results
        run: |
          echo "## Benchmark Comparison" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          benchstat /tmp/old.txt /tmp/new.txt >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          # Fail if any benchmark regressed significantly
          benchstat /tmp/old.txt /tmp/new.txt | grep -q '+' && \
            echo "WARNING: Possible regression detected" || true
```

### Storing baselines

| Method | How | When to update |
|--------|-----|----------------|
| Git branch (`gh-pages`) | Benchmark action pushes results to a tracking branch | Every merge to main |
| CI artifact storage | Upload benchmark JSON as build artifact | Every build |
| Dedicated metrics store | Push results to InfluxDB, Prometheus, or Datadog | Every build |
| Committed baseline file | Check in `benchmark-baseline.json` | Manual update after intentional changes |

### Alerting on degradation

| Threshold | Action | Rationale |
|-----------|--------|-----------|
| > 5% regression | Warning comment on PR | Minor regression, may be noise |
| > 10% regression | Fail the CI check | Significant regression, must be justified |
| > 25% regression | Block merge + notify team | Major regression, likely a bug |

---

## Profiling Methodology

Profiling identifies where time and resources are spent. Use profiling to diagnose bottlenecks found through load testing or benchmarking.

### CPU Profiling

**Sampling vs instrumentation:**

| Approach | How it works | Overhead | Best for |
|----------|-------------|----------|----------|
| **Sampling** | Periodically records the call stack (e.g., every 1ms) | Low (1-5%) | Production-safe profiling, finding hot functions |
| **Instrumentation** | Wraps every function call with timing code | High (10-100x) | Exact call counts, detailed call graphs |

**Recommended: Use sampling profilers for initial investigation, instrumentation only for targeted deep dives.**

Tools by language:

| Language | Sampling profiler | Instrumentation profiler |
|----------|------------------|------------------------|
| Python | `py-spy`, `scalene` | `cProfile`, `line_profiler` |
| Go | `pprof` (CPU) | `go tool trace` |
| Java | `async-profiler`, JFR | VisualVM |
| Node.js | `clinic.js`, `0x` | `--prof` flag |
| Rust | `cargo flamegraph`, `perf` | `tracing` crate |
| .NET | `dotnet-trace` | Visual Studio Profiler |

### Memory Profiling

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Heap snapshots** | All live objects, their types, and sizes at a point in time | Suspected memory leak; high RSS |
| **Allocation tracking** | Where objects are allocated and how frequently | High GC pressure; excessive allocation rate |
| **Growth over time** | Compare snapshots taken at intervals | Confirming a leak; finding the leaking type |

Tools by language:

| Language | Tool | Command |
|----------|------|---------|
| Python | `tracemalloc` | `tracemalloc.start(); snapshot = tracemalloc.take_snapshot()` |
| Python | `memray` | `memray run script.py && memray flamegraph output.bin` |
| Go | `pprof` (heap) | `go tool pprof http://localhost:6060/debug/pprof/heap` |
| Node.js | Chrome DevTools | `node --inspect app.js` then take heap snapshot |
| Java | JFR + JDK Mission Control | `java -XX:StartFlightRecording=duration=60s,filename=rec.jfr` |

### I/O Profiling

| Type | What to measure | Tools |
|------|----------------|-------|
| **Disk I/O** | Read/write throughput, IOPS, latency | `iostat`, `iotop`, `blktrace` |
| **Network I/O** | Bandwidth, connection count, DNS latency | `ss`, `nethogs`, `tcpdump`, Wireshark |
| **Database I/O** | Query execution time, lock wait time, connection count | `pg_stat_statements`, slow query log, APM |
| **File descriptor usage** | Open file/socket count | `lsof`, `/proc/<pid>/fd` |

### Flame Graph Interpretation

Flame graphs visualize where CPU time (or allocations) are spent. Each bar represents a function; width represents time (or count).

**How to read a flame graph:**

1. **X-axis = time proportion** (not chronological order). Wider bars consume more time.
2. **Y-axis = call stack depth.** Bottom is the entry point; top is the leaf function.
3. **Color is typically arbitrary** (or based on module/package). Do not read meaning into color unless the tool documents it.

**What to look for:**

| Pattern | What it means | Action |
|---------|--------------|--------|
| **Wide plateau at the top** | A single leaf function consuming significant time | Optimize or replace that function |
| **Wide bar in the middle** | A framework or library function dominating | Check if it is called too often or with too much data |
| **Many narrow towers** | Many small functions, no single bottleneck | Likely I/O-bound, not CPU-bound; profile I/O instead |
| **Recursive deep stacks** | Deep recursion | Check for excessive recursion depth or convert to iteration |
| **GC / runtime bars** | Garbage collection or runtime overhead | Reduce allocation rate; tune GC parameters |

**Generating flame graphs:**

```bash
# Python (py-spy)
py-spy record -o flamegraph.svg -- python app.py

# Go (pprof)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30

# Java (async-profiler)
asprof -d 30 -f flamegraph.html <pid>

# Node.js (0x)
npx 0x app.js

# Rust
cargo flamegraph --bin myapp

# Linux (perf)
perf record -g -p <pid> -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg
```

---

## Performance Budgets

Performance budgets define maximum acceptable values for key metrics. They convert aspirational goals into enforceable limits.

### Response Time Budgets

| Percentile | Target | Rationale |
|------------|--------|-----------|
| **p50** | < 100ms | Median user experience should feel instant |
| **p95** | < 300ms | Most users should have a good experience |
| **p99** | < 1000ms | Even tail users should not wait excessively |
| **p99.9** | < 3000ms | Extreme tail should not time out |

Define budgets per endpoint type:

| Endpoint type | p50 | p95 | p99 |
|---------------|-----|-----|-----|
| Health check | < 5ms | < 10ms | < 50ms |
| Read (single record) | < 50ms | < 150ms | < 500ms |
| Read (list/search) | < 100ms | < 300ms | < 1000ms |
| Write (create/update) | < 100ms | < 500ms | < 1500ms |
| Batch operation | < 500ms | < 2000ms | < 5000ms |
| Report generation | < 2000ms | < 5000ms | < 10000ms |

### Bundle Size Budgets (Frontend)

| Budget | Target | Enforcement |
|--------|--------|-------------|
| Initial JS bundle (gzipped) | < 200KB | `bundlesize` or `size-limit` in CI |
| Initial CSS (gzipped) | < 50KB | `bundlesize` in CI |
| Total page weight (initial load) | < 1MB | Lighthouse CI budget |
| Individual route chunk | < 50KB gzipped | Webpack/Vite bundle analysis |
| Third-party JS | < 100KB gzipped | `bundlephobia` check before adding deps |

### Memory Budgets

| Resource | Budget | Enforcement |
|----------|--------|-------------|
| Container memory limit | 2x average working set | Kubernetes `resources.limits.memory` |
| Heap size limit | 70% of container limit | JVM `-Xmx`, Node.js `--max-old-space-size` |
| RSS growth per hour | < 5% of baseline | Soak test + monitoring alert |
| Goroutine / thread count | < 10,000 | Runtime monitoring + alert |

### Enforcing Budgets in CI

```yaml
# .github/workflows/performance-budget.yml
name: Performance Budget

on:
  pull_request:
    branches: [main]

jobs:
  bundle-size:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run build

      # size-limit check
      - uses: andresz1/size-limit-action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}

  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci && npm run build && npm start &
      - name: Lighthouse CI
        uses: treosh/lighthouse-ci-action@v11
        with:
          urls: |
            http://localhost:3000/
            http://localhost:3000/dashboard
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true

  response-time:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start application
        run: docker compose up -d && sleep 10
      - name: Run k6 budget check
        run: |
          k6 run --quiet load-test.js 2>&1 | tee results.txt
          # k6 exits non-zero if thresholds are violated
```

**Lighthouse budget file:**

```json
[
  {
    "path": "/*",
    "resourceSizes": [
      { "resourceType": "script", "budget": 200 },
      { "resourceType": "stylesheet", "budget": 50 },
      { "resourceType": "image", "budget": 300 },
      { "resourceType": "total", "budget": 1000 }
    ],
    "timings": [
      { "metric": "largest-contentful-paint", "budget": 2500 },
      { "metric": "interactive", "budget": 3500 },
      { "metric": "cumulative-layout-shift", "budget": 0.1 }
    ]
  }
]
```

---

## Realistic Test Data

Load tests with unrealistic data produce misleading results. Test data must approximate production characteristics.

### Data requirements

| Dimension | What to match | Why it matters |
|-----------|--------------|---------------|
| **Volume** | Production-scale row counts and request rates | Small datasets fit in cache; production may not |
| **Distribution** | Skewed access patterns (e.g., 80% of reads hit 20% of records) | Uniform access masks hot-key and cache problems |
| **Cardinality** | Realistic number of distinct values per field | Low cardinality hides index selectivity issues |
| **Size** | Realistic payload sizes, text lengths, blob sizes | Small payloads hide serialization and network costs |
| **Edge cases** | Maximum-length fields, unicode, empty collections, nulls | Edge cases trigger different code paths |

### Data generation tools

| Tool | Language | Best for |
|------|----------|----------|
| **Faker** | Python, JS, Ruby, Java, Go, PHP | Realistic names, addresses, emails, dates |
| **factory_boy** | Python | Django/SQLAlchemy model factories |
| **Fishery** | TypeScript | TypeScript/JS model factories |
| **FactoryBot** | Ruby | Rails model factories |
| **Instancio** | Java | Java object generation |
| **testcontainers** | Multi-language | Spin up real databases with seed data |
| **Snaplet** | PostgreSQL | Generate production-like data from schema |

### Anonymized production data

When possible, use anonymized snapshots of production data. This provides the most realistic distribution and edge cases.

Requirements for safe use:

- PII removed or hashed (names, emails, addresses, phone numbers)
- Secrets scrubbed (API keys, tokens, passwords)
- Referential integrity preserved
- Data volume representative (full copy or statistically sampled subset)

---

## Results Interpretation

### Percentiles

| Percentile | Meaning | Use for |
|------------|---------|---------|
| **p50 (median)** | Half of requests are faster, half are slower | Typical user experience |
| **p95** | 95% of requests are faster than this value | Performance SLA target |
| **p99** | 99% of requests are faster than this value | Tail latency; worst case for most users |
| **p99.9** | 1 in 1000 requests is slower | Extreme tail; timeout and retry thresholds |
| **Average (mean)** | Arithmetic mean of all values | Avoid — distorted by outliers; use percentiles instead |

**Rule of thumb:** Set SLOs on p95 or p99, not on averages. A system with a 50ms average can have a 5-second p99.

### Throughput Curves

As concurrency increases, throughput follows a characteristic pattern:

```
Throughput
    ^
    |         ___________
    |        /           \
    |       /             \
    |      /               \
    |     /                 \
    |    /                   \
    |   /                     \
    +--/-------------------------> Concurrency
       A       B         C

A = Linear scaling (system not saturated)
B = Saturation point (inflection — throughput plateaus)
C = Degradation (contention, queuing, timeouts cause throughput drop)
```

**Finding the inflection point:**

1. Run a capacity test with increasing concurrency (e.g., 10, 50, 100, 200, 500)
2. Plot throughput (req/sec) vs concurrency
3. The inflection point is where throughput stops increasing linearly
4. This is the system's effective capacity under current architecture

### Identifying Bottleneck Type

| Bottleneck | Symptoms | How to confirm | Fix direction |
|------------|----------|----------------|---------------|
| **CPU-bound** | CPU at 100%, latency increases linearly with load | CPU flame graph shows hot functions | Optimize algorithm, add CPU, horizontal scale |
| **Memory-bound** | High memory usage, GC pauses, OOM kills | Memory profiler shows large allocations or leaks | Reduce allocation, add memory, fix leaks |
| **I/O-bound** | CPU idle, high disk/network wait | `iostat` shows high await; `strace` shows blocking reads | Async I/O, caching, faster storage, connection pooling |
| **Network-bound** | Low CPU, low disk, high latency on remote calls | Tracing shows time spent in HTTP/RPC calls | Batching, compression, caching, co-location |
| **Lock-bound** | Low CPU utilization despite many threads | Thread dump shows threads waiting on locks | Reduce lock scope, use read-write locks, lock-free structures |
| **Connection-bound** | "Connection refused" or pool exhausted errors | Connection pool metrics show 100% utilization | Increase pool size, add read replicas, reduce connection hold time |

### Amdahl's Law

Amdahl's Law defines the theoretical maximum speedup from parallelism:

```
Speedup = 1 / (S + P/N)

S = fraction of work that is serial (cannot be parallelized)
P = fraction of work that is parallel (P = 1 - S)
N = number of parallel processors/threads
```

| Serial fraction (S) | Max speedup (infinite cores) | Speedup with 8 cores | Speedup with 64 cores |
|---------------------|-----------------------------|-----------------------|----------------------|
| 50% | 2x | 1.78x | 1.97x |
| 25% | 4x | 3.03x | 3.76x |
| 10% | 10x | 4.71x | 8.83x |
| 5% | 20x | 5.93x | 14.74x |
| 1% | 100x | 7.48x | 39.25x |

**Key insight:** If 25% of the work is serial, no amount of parallelism can achieve more than a 4x speedup. Before adding more threads or cores, reduce the serial portion.

**When parallelism helps:**

- Work is CPU-bound with a small serial fraction
- Individual tasks are independent and do not share mutable state
- The overhead of coordination (thread creation, synchronization) is small relative to the work

**When parallelism does NOT help:**

- Work is I/O-bound (adding threads adds contention, not throughput)
- High serial fraction (lock contention, shared state, sequential dependencies)
- Task granularity is too small (coordination overhead exceeds the work)
- Single-threaded bottleneck exists (database, external API rate limit)

---

## Best Practices

- Run load tests in an environment that matches production (same instance types, network topology, database size)
- Use constant-throughput tools (wrk2, k6 with constant arrival rate) for accurate latency measurement — open-loop, not closed-loop
- Always warm up the system before measuring (JIT compilation, cache population, connection pool initialization)
- Run micro-benchmarks multiple times and use statistical comparison (benchstat, pytest-benchmark compare) — single runs are meaningless
- Profile before optimizing — never guess where the bottleneck is
- Track performance metrics over time, not just pass/fail — gradual degradation is invisible without trending
- Define performance budgets early in the project — retrofitting budgets is painful
- Use realistic test data that matches production volume, distribution, and cardinality
- Automate performance regression detection in CI — manual testing does not scale
- Separate performance tests from functional tests — they have different infrastructure and time requirements

## Anti-Patterns

- Running benchmarks on shared CI runners without accounting for noisy-neighbor variance
- Using averages instead of percentiles for latency measurements
- Load testing with trivially small datasets that fit entirely in cache
- Testing only the happy path — errors and edge cases often have different performance characteristics
- Profiling in debug mode — debug builds disable optimizations and inflate measurements
- Benchmarking without warmup — cold JVM, empty caches, and uninitialized pools produce misleading results
- Setting performance budgets based on aspirations rather than measurements
- Running soak tests for only a few minutes — leaks may take hours to manifest
- Ignoring tail latency (p99, p99.9) — the users who experience the worst latency are often the most valuable (large carts, complex queries)
- Optimizing before profiling — "premature optimization is the root of all evil" applies when you have not measured
