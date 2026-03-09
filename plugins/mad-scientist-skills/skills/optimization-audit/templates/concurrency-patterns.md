# Concurrency Patterns Reference

Patterns, formulas, and per-language guidance for safe and efficient concurrent code. Covers thread pool sizing, async/await correctness, lock contention, backpressure, enterprise integration patterns, connection pools, race condition detection, and concurrency testing.

## Purpose

Answer: "Are concurrent operations safe, efficient, and non-blocking?"

## Checklist

Before auditing, identify:

- [ ] Primary concurrency model (threads, goroutines, async/await, actors, processes)
- [ ] Languages and runtimes in use (GIL constraints, virtual threads, event loop)
- [ ] Workload profile — CPU-bound, I/O-bound, or mixed
- [ ] Number of available CPU cores in production
- [ ] Existing thread/connection pool configurations
- [ ] External dependencies with latency (databases, APIs, message brokers)
- [ ] Deployment model (single instance, horizontally scaled, serverless)

---

## Thread Pool Sizing

Incorrect thread pool sizes are one of the most common concurrency issues. Too few threads under-utilizes hardware; too many causes excessive context switching and memory overhead.

### Sizing Formulas

| Workload Type | Formula | Rationale |
|---------------|---------|-----------|
| CPU-bound | `threads = core_count` (or `core_count + 1`) | One thread per core saturates CPU. The +1 accounts for occasional page faults or brief I/O. |
| I/O-bound | `threads = core_count * (1 + wait_time / compute_time)` | Threads spend most time waiting; more threads keep CPU busy during waits. |
| Mixed | Profile to determine the wait/compute ratio, then apply the I/O-bound formula | Avoid guessing — measure actual wait and compute durations. |

**Example:** 8-core machine, average request waits 100ms on database and computes for 10ms:
`threads = 8 * (1 + 100/10) = 88 threads`

### Per-Language Configuration

**Python — ThreadPoolExecutor:**
```python
# BAD — arbitrary thread count with no reasoning
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=200)  # why 200?
```

```python
# GOOD — sized based on workload characteristics
import os
from concurrent.futures import ThreadPoolExecutor

core_count = os.cpu_count() or 4

# CPU-bound work
cpu_executor = ThreadPoolExecutor(max_workers=core_count + 1)

# I/O-bound work (e.g., HTTP calls averaging 200ms wait, 5ms compute)
io_executor = ThreadPoolExecutor(max_workers=core_count * (1 + 200 // 5))
```

**Java — ForkJoinPool and Virtual Threads:**
```java
// BAD — single-threaded pool for I/O-bound work
ExecutorService executor = Executors.newFixedThreadPool(1);

// BAD — unbounded thread creation
ExecutorService executor = Executors.newCachedThreadPool();
```

```java
// GOOD — sized pool for I/O-bound work
int coreCount = Runtime.getRuntime().availableProcessors();
int waitMs = 100, computeMs = 10;
int poolSize = coreCount * (1 + waitMs / computeMs);
ExecutorService executor = Executors.newFixedThreadPool(poolSize);

// GOOD — JDK 21+ virtual threads for I/O-bound work (auto-scaling)
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
```

**Go — GOMAXPROCS:**
```go
// Go sets GOMAXPROCS to core count by default since Go 1.5.
// Override only when running in a container with CPU limits.

import "go.uber.org/automaxprocs/maxprocs"

func main() {
    // Automatically set GOMAXPROCS to match container CPU quota
    _, _ = maxprocs.Set()
}
```

**Node.js — worker_threads:**
```javascript
// BAD — spawning more workers than cores for CPU-bound tasks
const { Worker } = require('worker_threads');
for (let i = 0; i < 100; i++) {
  new Worker('./cpu-task.js'); // 100 workers on an 8-core machine
}
```

```javascript
// GOOD — worker pool sized to core count
const os = require('os');
const { Worker } = require('worker_threads');
const Piscina = require('piscina');

const pool = new Piscina({
  filename: './cpu-task.js',
  maxThreads: os.cpus().length,
});
```

---

## Async/Await Correctness

Async/await simplifies concurrent code, but misuse silently destroys performance. The most common mistake is blocking an async context with synchronous operations.

### Python — asyncio

```python
# BAD — blocking the event loop with synchronous sleep
import time, asyncio

async def handle_request():
    time.sleep(5)  # blocks the entire event loop for 5 seconds
    return "done"
```

```python
# GOOD — non-blocking sleep
import asyncio

async def handle_request():
    await asyncio.sleep(5)  # yields control back to event loop
    return "done"
```

```python
# BAD — synchronous HTTP library in async function
import requests

async def fetch_data(url):
    response = requests.get(url)  # blocks the event loop
    return response.json()
```

```python
# GOOD — async HTTP library
import aiohttp

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

```python
# BAD — synchronous file I/O in async function
async def read_config():
    with open("config.json") as f:  # blocks the event loop
        return json.load(f)
```

```python
# GOOD — async file I/O with aiofiles
import aiofiles, json

async def read_config():
    async with aiofiles.open("config.json") as f:
        content = await f.read()
        return json.loads(content)
```

```python
# GOOD — wrapping unavoidable sync code with asyncio.to_thread()
import asyncio

async def compute_heavy():
    # Runs in a thread pool, does not block the event loop
    result = await asyncio.to_thread(cpu_intensive_function, arg1, arg2)
    return result
```

**Detection:** Enable asyncio debug mode to catch blocking calls:
```python
import asyncio
asyncio.get_event_loop().set_debug(True)
# Logs warnings when a coroutine takes >100ms without yielding
```

### JavaScript/TypeScript

```javascript
// BAD — sequential awaits in a loop
async function fetchAll(urls) {
  const results = [];
  for (const url of urls) {
    const res = await fetch(url); // each request waits for the previous one
    results.push(await res.json());
  }
  return results;
}
```

```javascript
// GOOD — parallel execution with Promise.all()
async function fetchAll(urls) {
  const promises = urls.map(url => fetch(url).then(res => res.json()));
  return Promise.all(promises);
}
```

```javascript
// GOOD — controlled concurrency with Promise.allSettled() for partial failure
async function fetchAll(urls) {
  const promises = urls.map(url => fetch(url).then(res => res.json()));
  const results = await Promise.allSettled(promises);
  return results
    .filter(r => r.status === 'fulfilled')
    .map(r => r.value);
}
```

```javascript
// GOOD — streaming with for await...of
async function processStream(readable) {
  for await (const chunk of readable) {
    await processChunk(chunk); // processes one at a time, backpressure-friendly
  }
}
```

```javascript
// BAD — blocking the event loop with synchronous computation
app.get('/hash', (req, res) => {
  const hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512');
  res.send(hash); // blocks all other requests during computation
});
```

```javascript
// GOOD — offload CPU-bound work to worker thread
const { Worker, parentPort } = require('worker_threads');

app.get('/hash', async (req, res) => {
  const hash = await runInWorker('./hash-worker.js', { password, salt });
  res.send(hash);
});
```

### Go — Goroutines and errgroup

```go
// BAD — unbounded goroutine fan-out
func processAll(items []Item) error {
    for _, item := range items {
        go process(item) // 10K items = 10K goroutines hammering downstream
    }
    // No way to know when they finish or if they failed
    return nil
}
```

```go
// GOOD — bounded concurrency with errgroup
import "golang.org/x/sync/errgroup"

func processAll(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(10) // max 10 concurrent goroutines

    for _, item := range items {
        item := item // capture loop variable
        g.Go(func() error {
            return process(ctx, item)
        })
    }
    return g.Wait() // blocks until all complete, returns first error
}
```

```go
// GOOD — context cancellation propagation
func fetchWithTimeout(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return nil, err
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, err // includes context.DeadlineExceeded
    }
    defer resp.Body.Close()
    return io.ReadAll(resp.Body)
}
```

```go
// GOOD — sync.WaitGroup for fire-and-forget with known completion
func processAll(items []Item) {
    var wg sync.WaitGroup
    sem := make(chan struct{}, 10) // semaphore for bounded concurrency

    for _, item := range items {
        wg.Add(1)
        sem <- struct{}{} // acquire
        go func(it Item) {
            defer wg.Done()
            defer func() { <-sem }() // release
            process(it)
        }(item)
    }
    wg.Wait()
}
```

### Java — CompletableFuture and Virtual Threads

```java
// BAD — sequential blocking calls
List<String> results = new ArrayList<>();
for (String url : urls) {
    results.add(httpClient.send(request(url), ofString()).body()); // sequential
}
```

```java
// GOOD — parallel with CompletableFuture
List<CompletableFuture<String>> futures = urls.stream()
    .map(url -> CompletableFuture.supplyAsync(
        () -> httpClient.send(request(url), ofString()).body(),
        executor))
    .toList();

List<String> results = futures.stream()
    .map(CompletableFuture::join)
    .toList();
```

```java
// GOOD — JDK 21+ virtual threads with structured concurrency
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    List<Subtask<String>> subtasks = urls.stream()
        .map(url -> scope.fork(() -> httpClient.send(request(url), ofString()).body()))
        .toList();

    scope.join().throwIfFailed();
    List<String> results = subtasks.stream()
        .map(Subtask::get)
        .toList();
}
```

### Rust — Tokio

```rust
// BAD — blocking the Tokio runtime with synchronous I/O
async fn read_file() -> String {
    std::fs::read_to_string("data.txt").unwrap() // blocks the async worker thread
}
```

```rust
// GOOD — use tokio::fs for async file I/O
async fn read_file() -> String {
    tokio::fs::read_to_string("data.txt").await.unwrap()
}
```

```rust
// GOOD — spawn_blocking for unavoidable sync work
async fn compute() -> u64 {
    tokio::task::spawn_blocking(|| {
        cpu_intensive_work() // runs on a dedicated blocking thread pool
    }).await.unwrap()
}
```

```rust
// BAD — sequential awaits
async fn fetch_all(urls: Vec<String>) -> Vec<String> {
    let mut results = vec![];
    for url in urls {
        results.push(fetch(&url).await); // sequential
    }
    results
}
```

```rust
// GOOD — concurrent with tokio::join! (fixed set) or JoinSet (dynamic)
use tokio::task::JoinSet;

async fn fetch_all(urls: Vec<String>) -> Vec<String> {
    let mut set = JoinSet::new();
    for url in urls {
        set.spawn(async move { fetch(&url).await });
    }

    let mut results = vec![];
    while let Some(res) = set.join_next().await {
        results.push(res.unwrap());
    }
    results
}
```

---

## Lock Contention Reduction

Locks are necessary for shared mutable state, but coarse-grained locking serializes work and destroys throughput.

### Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| Read-write locks | Allow concurrent reads, exclusive writes | Read-heavy workloads (>90% reads) |
| Lock striping | Partition data, each partition has its own lock | Hash maps, partitioned data structures |
| Lock-free (CAS) | Compare-and-swap atomic operations | Counters, flags, simple state machines |
| Copy-on-write | Readers see immutable snapshot, writers create new version | Configuration, infrequently-updated lookup tables |
| Channel-based | Communicate via message passing instead of shared state | Go, Rust, Erlang — preferred idiom |

### Read-Write Lock Examples

```go
// BAD — mutex for read-heavy cache
type Cache struct {
    mu    sync.Mutex
    items map[string]string
}

func (c *Cache) Get(key string) string {
    c.mu.Lock()         // blocks all other readers too
    defer c.mu.Unlock()
    return c.items[key]
}
```

```go
// GOOD — RWMutex allows concurrent reads
type Cache struct {
    mu    sync.RWMutex
    items map[string]string
}

func (c *Cache) Get(key string) string {
    c.mu.RLock()         // multiple goroutines can read simultaneously
    defer c.mu.RUnlock()
    return c.items[key]
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = value
}
```

```java
// GOOD — ReadWriteLock in Java
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

public class Cache<K, V> {
    private final ReadWriteLock lock = new ReentrantReadWriteLock();
    private final Map<K, V> map = new HashMap<>();

    public V get(K key) {
        lock.readLock().lock();
        try { return map.get(key); }
        finally { lock.readLock().unlock(); }
    }

    public void put(K key, V value) {
        lock.writeLock().lock();
        try { map.put(key, value); }
        finally { lock.writeLock().unlock(); }
    }
}
```

### Lock-Free / CAS Operations

```go
// GOOD — atomic counter instead of mutex-protected int
import "sync/atomic"

var requestCount atomic.Int64

func handleRequest() {
    requestCount.Add(1) // lock-free, no contention
}
```

```java
// GOOD — AtomicReference for lock-free state update
import java.util.concurrent.atomic.AtomicReference;

AtomicReference<Config> config = new AtomicReference<>(initialConfig);

// Update atomically — retry if another thread updated first
config.updateAndGet(current -> current.withNewValue(newVal));
```

```python
# Python — GIL makes simple assignments atomic, but compound operations are not.
# Use threading.Lock for compound operations, or queue.Queue for producer-consumer.
import queue

work_queue = queue.Queue(maxsize=100)  # thread-safe, bounded
```

---

## Backpressure Patterns

Without backpressure, fast producers overwhelm slow consumers, leading to memory exhaustion, cascading failures, or dropped work.

### Bounded Queues

```python
# BAD — unbounded queue grows forever if consumer is slower than producer
import asyncio

queue = asyncio.Queue()  # unbounded — no limit on pending items
```

```python
# GOOD — bounded queue applies backpressure to producers
import asyncio

queue = asyncio.Queue(maxsize=100)

async def producer():
    await queue.put(item)  # blocks when queue is full — natural backpressure

async def consumer():
    item = await queue.get()
    await process(item)
```

### Semaphore-Based Concurrency Limiting

```python
# GOOD — semaphore limits concurrent operations
import asyncio

sem = asyncio.Semaphore(10)  # max 10 concurrent operations

async def fetch_with_limit(url):
    async with sem:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()

async def fetch_all(urls):
    return await asyncio.gather(*(fetch_with_limit(u) for u in urls))
```

```javascript
// GOOD — p-limit for controlled concurrency in Node.js
import pLimit from 'p-limit';

const limit = pLimit(10); // max 10 concurrent

const results = await Promise.all(
  urls.map(url => limit(() => fetch(url).then(r => r.json())))
);
```

### Rate Limiting — Token Bucket

```go
// GOOD — rate limiter for outbound API calls
import "golang.org/x/time/rate"

// 10 requests per second, burst of 20
limiter := rate.NewLimiter(rate.Limit(10), 20)

func callAPI(ctx context.Context) error {
    if err := limiter.Wait(ctx); err != nil {
        return err // context cancelled or deadline exceeded
    }
    return doAPICall()
}
```

```python
# GOOD — token bucket rate limiter
import asyncio, time

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()

    async def acquire(self):
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            await asyncio.sleep(1 / self.rate)
```

### Fan-Out Control

```go
// BAD — unbounded fan-out overwhelms downstream service
for _, item := range items { // 50K items
    go func(it Item) {
        callExternalAPI(it) // 50K concurrent HTTP requests
    }(item)
}
```

```go
// GOOD — bounded fan-out with worker pool
func processItems(ctx context.Context, items []Item) error {
    jobs := make(chan Item, 100)    // buffered channel
    g, ctx := errgroup.WithContext(ctx)

    // Fixed number of workers
    for i := 0; i < 20; i++ {
        g.Go(func() error {
            for item := range jobs {
                if err := callExternalAPI(ctx, item); err != nil {
                    return err
                }
            }
            return nil
        })
    }

    // Feed jobs
    for _, item := range items {
        select {
        case jobs <- item:
        case <-ctx.Done():
            break
        }
    }
    close(jobs)
    return g.Wait()
}
```

---

## Enterprise Integration Patterns for Throughput

These patterns, drawn from enterprise integration architecture, apply to any system that needs to parallelize work, distribute load, or move large data efficiently.

### Splitter

Break a large unit of work into smaller, independently processable chunks. Enables parallel execution and reduces per-unit failure blast radius.

```python
# GOOD — split large batch into chunks for parallel processing
import asyncio
from itertools import islice

def chunk(iterable, size):
    iterator = iter(iterable)
    while batch := list(islice(iterator, size)):
        yield batch

async def process_large_batch(records: list[dict]):
    chunks = list(chunk(records, 100))  # split 10K records into 100-record chunks

    tasks = [process_chunk(c) for c in chunks]
    results = await asyncio.gather(*tasks)
    return [item for sublist in results for item in sublist]

async def process_chunk(records: list[dict]) -> list[dict]:
    # Each chunk is processed independently
    return [transform(r) for r in records]
```

```go
// GOOD — splitter in Go with bounded workers
func splitAndProcess(ctx context.Context, items []Item, chunkSize int) ([]Result, error) {
    var chunks [][]Item
    for i := 0; i < len(items); i += chunkSize {
        end := min(i+chunkSize, len(items))
        chunks = append(chunks, items[i:end])
    }

    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(10)
    results := make([][]Result, len(chunks))

    for i, chunk := range chunks {
        i, chunk := i, chunk
        g.Go(func() error {
            r, err := processChunk(ctx, chunk)
            results[i] = r
            return err
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return flatten(results), nil
}
```

### Scatter-Gather

Fan out work to multiple workers or services, then collect and merge results. Useful for parallel search, aggregation, or calling multiple independent data sources.

```python
# GOOD — scatter-gather: query multiple data sources in parallel
import asyncio

async def scatter_gather(query: str) -> dict:
    results = await asyncio.gather(
        search_database(query),
        search_cache(query),
        search_external_api(query),
        return_exceptions=True,  # don't fail if one source errors
    )

    merged = {}
    for result in results:
        if isinstance(result, Exception):
            log.warning(f"Source failed: {result}")
            continue
        merged.update(result)
    return merged
```

```java
// GOOD — scatter-gather with CompletableFuture
public Map<String, Object> scatterGather(String query) {
    var dbFuture = CompletableFuture.supplyAsync(() -> searchDatabase(query), executor);
    var cacheFuture = CompletableFuture.supplyAsync(() -> searchCache(query), executor);
    var apiFuture = CompletableFuture.supplyAsync(() -> searchApi(query), executor);

    CompletableFuture.allOf(dbFuture, cacheFuture, apiFuture).join();

    Map<String, Object> merged = new HashMap<>();
    merged.putAll(getOrDefault(dbFuture));
    merged.putAll(getOrDefault(cacheFuture));
    merged.putAll(getOrDefault(apiFuture));
    return merged;
}

private Map<String, Object> getOrDefault(CompletableFuture<Map<String, Object>> f) {
    try { return f.get(); }
    catch (Exception e) { return Map.of(); }
}
```

### Content-Based Router

Route work items to specialized processors based on their type or characteristics. Different item types may have different performance profiles or processing requirements.

| Routing Criteria | Example | Benefit |
|------------------|---------|---------|
| Data type | Images to GPU workers, text to CPU workers | Optimal resource utilization |
| Size | Small payloads inline, large payloads via storage reference | Avoid memory pressure |
| Priority | High-priority to fast-path queue, low-priority to batch queue | SLA compliance |
| Region | Route to nearest data center | Latency reduction |

```python
# GOOD — content-based routing
async def route_and_process(items: list[WorkItem]):
    cpu_items = []
    gpu_items = []
    io_items = []

    for item in items:
        match item.type:
            case "image_resize" | "video_transcode":
                gpu_items.append(item)
            case "api_call" | "db_query":
                io_items.append(item)
            case _:
                cpu_items.append(item)

    results = await asyncio.gather(
        process_on_gpu_pool(gpu_items),
        process_on_io_pool(io_items),
        process_on_cpu_pool(cpu_items),
    )
    return merge_results(results)
```

### Claim Check

When passing messages through a queue or broker, store the large payload in external storage (S3, blob store, database) and pass only a reference (the "claim check") through the message channel. Reduces message broker memory pressure and network bandwidth.

| Without Claim Check | With Claim Check |
|---------------------|-----------------|
| 10MB payload in message queue | 200-byte reference in message queue |
| Broker memory pressure at scale | Broker stays lightweight |
| Network bandwidth per message is high | Payload fetched only when needed |
| Message size limits may be hit | No size constraints |

```python
# BAD — large payload through message queue
await queue.put({"type": "process", "data": large_dataframe.to_json()})  # 50MB message
```

```python
# GOOD — claim check pattern
import uuid

async def send_with_claim_check(queue, payload: bytes):
    ref = f"work/{uuid.uuid4()}"
    await storage.put(ref, payload)           # store payload in S3/blob storage
    await queue.put({"type": "process", "ref": ref})  # send lightweight reference

async def receive_with_claim_check(queue):
    msg = await queue.get()
    payload = await storage.get(msg["ref"])   # fetch payload when ready to process
    result = process(payload)
    await storage.delete(msg["ref"])          # clean up after processing
    return result
```

---

## Connection Pool Patterns

Connection creation is expensive (TCP handshake, TLS negotiation, authentication). Pools amortize this cost across many operations.

### Sizing Guidelines

| Factor | Guidance |
|--------|----------|
| Minimum idle | Enough to handle baseline traffic without cold-start latency |
| Maximum size | Do not exceed database `max_connections / number_of_app_instances` |
| Idle timeout | Close connections idle longer than 5-10 minutes to free server resources |
| Max lifetime | Rotate connections every 30-60 minutes to pick up DNS changes and rebalance |
| Validation | Validate connections before use (test-on-borrow) or periodically |

**PostgreSQL rule of thumb:** `connections = (core_count * 2) + effective_spindle_count`
For SSDs, effective_spindle_count is typically 1, so: `connections = (cores * 2) + 1`

### Per-Language Configuration

**Python — SQLAlchemy:**
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@host/db",  # pragma: allowlist secret
    pool_size=10,           # maintained idle connections
    max_overflow=20,        # additional connections under load (total max = 30)
    pool_timeout=30,        # seconds to wait for a connection before error
    pool_recycle=1800,      # recycle connections after 30 minutes
    pool_pre_ping=True,     # validate connections before use
)
```

**Node.js — pg Pool:**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  max: 20,                          // maximum connections
  idleTimeoutMillis: 300000,        // close idle connections after 5 minutes
  connectionTimeoutMillis: 5000,    // fail fast if no connection available
});
```

**Go — database/sql:**
```go
import "database/sql"

db, _ := sql.Open("postgres", dsn)
db.SetMaxOpenConns(25)              // max total connections
db.SetMaxIdleConns(10)              // max idle connections
db.SetConnMaxLifetime(30 * time.Minute)  // rotate connections
db.SetConnMaxIdleTime(5 * time.Minute)   // close idle connections
```

**Java — HikariCP:**
```java
HikariConfig config = new HikariConfig();
config.setMaximumPoolSize(20);
config.setMinimumIdle(5);
config.setIdleTimeout(300000);       // 5 minutes
config.setMaxLifetime(1800000);      // 30 minutes
config.setConnectionTimeout(5000);   // 5 seconds
config.setLeakDetectionThreshold(60000); // warn if connection held >60s
```

### HTTP Client Connection Reuse

```python
# BAD — creating a new session per request
async def fetch(url):
    async with aiohttp.ClientSession() as session:  # new session = new connections
        async with session.get(url) as resp:
            return await resp.json()
```

```python
# GOOD — reuse a single session across requests
class HttpClient:
    def __init__(self):
        connector = aiohttp.TCPConnector(
            limit=100,           # max total connections
            limit_per_host=10,   # max connections per host
            ttl_dns_cache=300,   # cache DNS lookups for 5 minutes
        )
        self.session = aiohttp.ClientSession(connector=connector)

    async def fetch(self, url):
        async with self.session.get(url) as resp:
            return await resp.json()
```

### gRPC Channel Reuse

```go
// BAD — new connection per RPC call
func callService(ctx context.Context) (*pb.Response, error) {
    conn, _ := grpc.Dial("service:50051", grpc.WithInsecure())
    defer conn.Close()
    client := pb.NewMyServiceClient(conn)
    return client.DoWork(ctx, &pb.Request{})
}
```

```go
// GOOD — shared, long-lived gRPC channel
var (
    conn   *grpc.ClientConn
    client pb.MyServiceClient
    once   sync.Once
)

func getClient() pb.MyServiceClient {
    once.Do(func() {
        var err error
        conn, err = grpc.Dial("service:50051",
            grpc.WithTransportCredentials(insecure.NewCredentials()),
            grpc.WithDefaultServiceConfig(`{"loadBalancingConfig": [{"round_robin":{}}]}`),
        )
        if err != nil {
            log.Fatal(err)
        }
        client = pb.NewMyServiceClient(conn)
    })
    return client
}
```

---

## Race Condition Detection

Race conditions are among the hardest concurrency bugs to diagnose because they are non-deterministic — they may only manifest under specific timing and load conditions.

### Per-Language Detection Tools

| Language | Tool | How to Use |
|----------|------|------------|
| Go | Race detector | `go test -race ./...` or `go run -race main.go` |
| C/C++/Rust | ThreadSanitizer (TSan) | Compile with `-fsanitize=thread` (clang/gcc) |
| Java | `-XX:+UseThreadSanitizer` (experimental) | JVM flag; or use `jcstress` for stress-testing concurrent code |
| Python | GIL (partial protection) | GIL prevents data races on CPython objects but **not** logical races |
| JS/Node.js | Single-threaded | No data races in main thread, but `SharedArrayBuffer` with `Worker` requires `Atomics` |
| Rust | Compiler | Borrow checker prevents data races at compile time in safe code |

### Go Race Detector

```bash
# Run tests with race detection (add to CI pipeline)
go test -race -count=1 ./...

# Run application with race detection (development/staging only — 5-10x slowdown)
go run -race main.go
```

The race detector instruments memory accesses at compile time and reports unsynchronized access to shared variables at runtime. It has no false positives — every report is a real bug.

### Python GIL Considerations

The GIL (Global Interpreter Lock) prevents concurrent execution of Python bytecode, which means:

| Protected by GIL | NOT protected by GIL |
|-------------------|---------------------|
| Single bytecode operations (`x = 1`) | Multi-step operations (`x += 1` across threads) |
| `dict` and `list` individual operations | Check-then-act patterns (`if key not in d: d[key] = val`) |
| Reference counting | File I/O ordering |
| N/A | `multiprocessing` shared state |
| N/A | C extensions that release the GIL |

```python
# BAD — logical race condition despite GIL
import threading

counter = 0

def increment():
    global counter
    for _ in range(100000):
        counter += 1  # read-modify-write is NOT atomic

threads = [threading.Thread(target=increment) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
# counter will be LESS than 1000000 due to race condition
```

```python
# GOOD — use threading.Lock for compound operations
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(100000):
        with lock:
            counter += 1
```

### JavaScript SharedArrayBuffer Caveats

```javascript
// BAD — unsynchronized access to SharedArrayBuffer from Workers
const shared = new SharedArrayBuffer(4);
const view = new Int32Array(shared);
// Worker 1: view[0] += 1
// Worker 2: view[0] += 1
// Result is unpredictable without Atomics
```

```javascript
// GOOD — use Atomics for SharedArrayBuffer
const shared = new SharedArrayBuffer(4);
const view = new Int32Array(shared);
Atomics.add(view, 0, 1); // atomic increment
Atomics.load(view, 0);   // atomic read
```

---

## Concurrency Testing

Concurrency bugs often hide during normal testing because tests run with low parallelism and deterministic timing. Dedicated concurrency testing is required to surface these issues.

### Testing Strategies

| Strategy | What It Reveals | Tools |
|----------|----------------|-------|
| Load testing | Thread pool exhaustion, connection pool limits, queue overflow | k6, locust, wrk2, hey |
| Stress testing | Behavior under extreme concurrency (2-10x normal load) | k6, locust, gatling |
| Soak testing | Slow resource leaks (goroutine leaks, connection leaks, memory growth) | k6 (extended duration), custom scripts |
| Race detection | Data races, unsynchronized shared state | Go `-race`, TSan, jcstress |
| Chaos testing | Behavior when concurrent operations fail mid-flight | toxiproxy, chaos-monkey, litmus |

### Load Testing Examples

**k6 — concurrent virtual users:**
```javascript
// k6-concurrent-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // ramp up to 50 concurrent users
    { duration: '5m', target: 50 },   // hold at 50 for 5 minutes
    { duration: '2m', target: 200 },  // spike to 200 concurrent users
    { duration: '5m', target: 200 },  // hold at 200
    { duration: '1m', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95th percentile under 500ms
    http_req_failed: ['rate<0.01'],    // less than 1% failure rate
  },
};

export default function () {
  const res = http.get('http://localhost:8080/api/data');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(Math.random() * 2); // randomized think time
}
```

**locust — Python-based load testing:**
```python
# locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(3)
    def read_data(self):
        self.client.get("/api/data")

    @task(1)
    def write_data(self):
        self.client.post("/api/data", json={"key": "value"})
```

### Stress Testing Concurrent Paths

Focus testing on the specific code paths where concurrency bugs are most likely:

```python
# Stress test for race conditions — hammer a shared resource from many threads
import concurrent.futures
import threading

def test_concurrent_counter():
    counter = SharedCounter()  # your implementation under test
    errors = []

    def increment_many():
        try:
            for _ in range(10000):
                counter.increment()
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(increment_many) for _ in range(50)]
        concurrent.futures.wait(futures)

    assert not errors, f"Errors during concurrent access: {errors}"
    assert counter.value == 500000, f"Race condition: expected 500000, got {counter.value}"
```

```go
// Go — stress test with -race flag
func TestConcurrentMapAccess(t *testing.T) {
    m := NewSafeMap() // your implementation under test
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(2)
        go func(id int) {
            defer wg.Done()
            for j := 0; j < 1000; j++ {
                m.Set(fmt.Sprintf("key-%d-%d", id, j), j)
            }
        }(i)
        go func(id int) {
            defer wg.Done()
            for j := 0; j < 1000; j++ {
                _ = m.Get(fmt.Sprintf("key-%d-%d", id, j))
            }
        }(i)
    }
    wg.Wait()
}
// Run: go test -race -run TestConcurrentMapAccess -count=10
```

### Chaos Approaches for Concurrency Bugs

| Approach | Implementation | What It Catches |
|----------|---------------|-----------------|
| Inject random delays | `toxiproxy` between services, `tc` for network delays | Timing-dependent bugs, timeout handling |
| Kill connections mid-request | `toxiproxy` with `reset_peer` | Connection pool recovery, retry logic |
| Saturate thread pools | Send burst traffic exceeding pool capacity | Queue overflow, rejection handling, backpressure |
| Slow downstream | Add latency to database or external API responses | Connection pool exhaustion, cascade failures |
| CPU starvation | `stress-ng --cpu` to consume CPU during test | Thread starvation, priority inversion |

**toxiproxy example — add latency to database:**
```bash
# Add 500ms latency to all database connections
toxiproxy-cli toxic add -t latency -a latency=500 -a jitter=200 postgres_downstream

# Verify your application handles it (connection pool exhaustion, timeouts)
k6 run load-test.js

# Remove the toxic
toxiproxy-cli toxic remove -n latency_downstream postgres_downstream
```

---

## Anti-Patterns

| Anti-Pattern | Impact | Fix |
|-------------|--------|-----|
| Blocking calls in async context | Event loop stalls, all requests delayed | Use async libraries or `to_thread()` / `spawn_blocking` |
| Sequential awaits in a loop | N operations take N * latency instead of max(latency) | `Promise.all()`, `asyncio.gather()`, `errgroup` |
| Unbounded fan-out | Downstream overwhelm, OOM, connection exhaustion | Semaphore, worker pool, bounded channel |
| Thread pool sized by guesswork | Under/over-utilization, context switch overhead | Apply sizing formula based on measured wait/compute ratio |
| Coarse-grained locks | Serialized throughput, high contention | RWMutex, lock striping, lock-free structures |
| Missing backpressure | Memory growth, cascade failures | Bounded queues, rate limiters, semaphores |
| Large payloads through message queues | Broker memory pressure, network bottleneck | Claim check pattern |
| No race condition testing | Latent data corruption bugs | Go `-race`, TSan, stress tests in CI |
| Connection per request | TCP/TLS handshake overhead on every call | Connection pools with proper sizing |
| Ignoring cancellation | Wasted work, goroutine/thread leaks | Propagate `context.Context`, `CancellationToken`, `AbortController` |
