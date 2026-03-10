---
name: optimization-audit
description: Comprehensive optimization audit with two modes and a single tier. Planning mode designs performance strategy, capacity planning, and scaling architecture. Audit mode scans code and infrastructure for performance anti-patterns, inefficient algorithms, N+1 queries, missing caching, concurrency issues, and resource waste. Single tier — optimization tools are overwhelmingly free/open-source. Use when asked to "optimization audit", "performance review", "find bottlenecks", "optimize this", "check efficiency", or "resource audit".
---

# Optimization Audit

A comprehensive optimization skill with two modes and a single tier:

**Modes:**
- **Planning** (before code exists) — performance strategy, capacity planning, scaling architecture, data access design
- **Audit** (on existing code) — scanning for performance anti-patterns, inefficient algorithms, N+1 queries, missing caching, concurrency issues, and resource waste

**Single tier:** Unlike the security and observability audits, optimization tools are overwhelmingly free/open-source (profilers, EXPLAIN, load testers, linters). Enterprise APM platforms are already covered by the observability-audit skill, so a Standard/Enterprise split would duplicate coverage.

**Core question:** "Is this system using resources efficiently?"

## When to use this skill

- When the user says "optimization audit", "performance review", "find bottlenecks", "optimize this", "check efficiency", or "resource audit"
- Before designing a new system (planning mode) — to define performance strategy, capacity planning, and scaling architecture early
- On an existing codebase (audit mode) — to find and fix performance anti-patterns and resource waste
- Before a production deployment — to validate performance posture
- After adding new services, data pipelines, or performance-sensitive features
- When investigating production performance incidents or cost overruns

## Mode detection

Determine which mode to operate in based on the project state:

| Signal | Mode | Rationale |
|--------|------|-----------|
| User says "design for performance", "plan scaling", "capacity planning" | **Planning** | Architecture-level performance strategy |
| User says "audit", "optimize", "find bottlenecks", "performance review" | **Audit** | Code and infrastructure scanning |
| No source code exists yet (only docs, diagrams, RFCs) | **Planning** | Nothing to profile — design the strategy |
| Source code and/or infrastructure files exist | **Audit** | Concrete artifacts to analyze |
| Both code and a request to "plan performance" | **Both** | Run planning phases on architecture, audit phases on code |

When in doubt, ask the user. If both modes apply, run all 14 phases.

## Severity classification

Every finding must be assigned a severity:

| Severity | Criteria | Action | SLA |
|----------|----------|--------|-----|
| **Critical** | Causes outages, OOM crashes, connection exhaustion, quadratic algorithms on user-facing paths, unbounded memory growth | Fix immediately before any deployment | Block release |
| **High** | Measurable performance degradation >2x expected; N+1 queries, missing indexes on production queries, no connection pooling, missing compression | Fix before next release | 1 sprint |
| **Medium** | Suboptimal but functional; oversized resources, missing caching, debug logging in production, suboptimal serialization | Schedule fix | 2 sprints |
| **Low** | Best practice deviation; naming conventions, minor allocation patterns, potential micro-optimizations | Track in backlog | Best effort |

## Audit process

Execute all applicable phases in order. Skip phases marked for a mode you are not running. Skip conditional phases (8, 9, 10, 11) when their preconditions are not met. Do NOT skip applicable phases. Do NOT claim completion without evidence.

**Phase order:** 0 → 0.5 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13

---

### Phase 0: Anti-Pattern Scan (Audit mode)

Fast grep-based scan for performance anti-patterns across all categories. Runs first to catch obvious issues before deeper analysis. This is the workhorse phase — most optimization audit value comes from grep-able anti-patterns.

Scan all source files for these patterns. Each match requires manual review — some may be intentional. Organize findings by category.

#### Algorithm anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python | `for .* in .*:\s*for .* in .*:` (nested loops over same/related collections) | Potential O(n^2) | High |
| Python | `if .* in list_var` inside a loop | O(n) lookup per iteration; use set | High |
| Python | `re\.compile\(` inside function body (not module level) | Regex recompilation per call | Medium |
| Python | `re\.(match\|search\|findall\|sub)\(` inside a `for\|while` loop without pre-compiled pattern | Regex recompilation per iteration | High |
| Python | `str += ` or `string = string + ` in a loop | O(n^2) string building | Medium |
| JS/TS | `array\.indexOf\(` or `array\.includes\(` inside a loop | O(n) lookup per iteration; use Set | High |
| JS/TS | `string += ` in a loop | String concatenation overhead | Medium |
| JS/TS | `new RegExp\(` inside a loop | Regex recompilation per iteration | High |
| Java | `new String\(\)` or `"" \+` in a loop | StringBuilder not used | Medium |
| Go | `strings\.Contains\(` or linear search inside a loop | Use map for O(1) lookup | High |
| Go | `append\(` without pre-allocating slice capacity | Repeated reallocation | Medium |
| Any | `.sort()` when only min/max/top-K needed | Use heap / partial sort | Medium |
| Any | `(a+)+\|(a\|a)+\|(a\|b)*a(a\|b)*` regex patterns | Catastrophic backtracking (ReDoS) risk | Critical |

#### Memory anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python | `@lru_cache` without `maxsize` (or `maxsize=None`) | Unbounded cache | Critical |
| Python | `global ` + mutable data structures | Global state that grows unboundedly | High |
| Python | `df = pd\.read_csv\(` on large files without `chunksize` | Entire file loaded into memory | High |
| JS/TS | `addEventListener\(` without corresponding `removeEventListener` | Event listener leak | High |
| JS/TS | `setInterval\(` without `clearInterval` | Timer leak | High |
| JS/TS | `new Map\(\)` or `new Set\(\)` used as cache without eviction | Unbounded growth | High |
| Go | `go func\(\)` without context cancellation or done channel | Goroutine leak | Critical |
| Go | `make\(` with `0` capacity for slices that grow large | Repeated reallocation | Medium |
| Java | `static.*Map\|static.*List\|static.*Set` without size limit | Static collection leak | High |
| Java | `ThreadLocal` without `remove()` in finally block | Thread-local memory leak | High |
| Rust | `Box::leak\|mem::forget` | Intentional leak — verify intentional | Medium |
| Any | `.*cache.*=.*\{\}` or `.*cache.*= new Map` without TTL/max entries | Unbounded cache | Critical |

#### Concurrency anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python | `time\.sleep\(` inside `async def` | Blocking the event loop | Critical |
| Python | `requests\.\(get\|post\)` inside `async def` | Sync HTTP in async context | Critical |
| Python | `open\(` (file I/O) inside `async def` without `aiofiles` | Sync file I/O in async context | High |
| JS/TS | `await` inside `for` loop (sequential awaits) | Should use `Promise.all()` for parallel | High |
| JS/TS | `new Promise` with blocking operations | Blocking the event loop | Critical |
| Go | `sync\.Mutex` with large critical sections | Lock contention | High |
| Go | `go func\(\)` in a loop without `semaphore` or `errgroup` | Unbounded goroutine fan-out | High |
| Java | `synchronized` on broad scope | Coarse-grained locking | High |
| Java | `Executors\.newFixedThreadPool\(1\)` | Artificially serialized execution | Medium |
| Any | `Lock\(\)` or `mutex` acquired in nested fashion | Deadlock risk | Critical |

#### Database anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python (Django) | `.objects.all()` in template or loop without `.select_related()` / `.prefetch_related()` | N+1 query | Critical |
| Python (Django) | `for obj in queryset:.*obj\.related_field` | N+1 query via lazy loading | Critical |
| Python (SQLAlchemy) | `session\.query\(` inside a `for` loop | N+1 query | Critical |
| Ruby (ActiveRecord) | `.each do.*\.association_name` without `.includes()` | N+1 query | Critical |
| Java (Hibernate/JPA) | `@ManyToOne` or `@OneToMany` with default `FetchType.EAGER` or lazy without batch | N+1 / over-fetching | High |
| Any ORM | `SELECT \*` or `model.objects.all()` when specific columns suffice | Over-fetching | Medium |
| Any | `INSERT INTO` inside a `for\|while\|each` loop | Row-by-row insert instead of batch | High |
| Any | `execute\(` or `query\(` inside a loop body | Potential N+1 | High |
| SQL | `LIKE '%term%'` | Leading wildcard prevents index use | High |
| SQL | `ORDER BY.*OFFSET \d+` with large offset | Inefficient pagination; use cursor/keyset | High |
| Python | `psycopg2\.connect\(` or `create_engine\(` inside request handler | New connection per request | Critical |
| Node.js | `new Pool\(\)` or `createConnection\(` inside request handler | Pool per request | Critical |
| Go | `sql\.Open\(` inside handler instead of at startup | New pool per request | Critical |
| Java | `DriverManager\.getConnection\(` without connection pool | No pooling | Critical |

#### HTTP N+1 anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python | `requests\.(get\|post\|put\|delete)\(` inside a `for\|while` loop | N+1 HTTP API calls — sequential per-item requests instead of batch | High |
| Python | `fetch_url\(` or custom HTTP wrapper inside a `for\|while` loop | N+1 via abstracted HTTP calls | High |
| Python | `httpx\.(get\|post)\(` inside a `for\|while` loop (not async) | N+1 via httpx sync client | High |
| Python | `session\.(get\|post)\(` inside a `for\|while` loop without concurrency | Sequential HTTP session calls | High |
| JS/TS | `axios\.(get\|post)\(` or `fetch\(` inside a `for\|forEach\|map` loop | N+1 API calls; should batch or parallelize | High |
| Go | `http\.Get\(` or `client\.Do\(` inside a `for` loop | Sequential HTTP requests | High |
| Any | Per-item API calls where batch endpoint exists | N+1 over network instead of database | High |

This is the network equivalent of N+1 database queries. Common in data ingestion pipelines that fetch per-record or per-match data from REST APIs. The fix is typically batch endpoints, concurrent requests (`asyncio`/`httpx.AsyncClient`/goroutine fan-out), or Scatter-Gather patterns.

#### Logging overhead anti-patterns

| Language | Pattern | Issue | Severity |
|----------|---------|-------|----------|
| Python | `logging\.debug\(f"` or `logging\.debug\(".*"\.format\(` | Eager string evaluation in debug | Medium |
| Python | `logger\.\w+\(.*json\.dumps\(` | Expensive serialization even when log level disabled | Medium |
| Java | `logger\.debug\("" \+` | String concatenation even if debug is off; use `{}` placeholders | Medium |
| Any | `log\.\w+\(` inside `for\|while\|each` (high-iteration loop body) | Per-iteration logging overhead | High |
| Config | `level.*DEBUG\|level.*TRACE\|LOG_LEVEL.*debug` in production config | Debug logging in production | High |
| Python | `traceback\.print_exc\(\)\|traceback\.format_exc\(\)` for handled exceptions | Unnecessary stack trace | Medium |

For each finding: record file path, line number, pattern matched, category, severity, and whether it is a true positive or intentional usage.

**Output:** Anti-pattern findings table organized by category with file paths, severity, and true/false positive classification.

---

### Phase 0.5: Documentation & Tech Debt Scan (Audit mode)

Scan project documentation for **already-known** performance concerns. Code-level grep patterns (Phase 0) catch what's visible in source files, but many performance risks are documented in planning files rather than flagged by anti-pattern grep — especially scaling risks, N+1 patterns over HTTP (not ORM), deferred compute, and architectural bottlenecks.

#### Files to scan

Search for these files (case-insensitive) in the project root and `docs/` directory:

| File | Purpose |
|------|---------|
| `TODO.md`, `TODO.txt`, `TODO` | Active task and tech debt tracking |
| `ROADMAP.md` | Future development plans, often including performance strategies |
| `PLAN.md` | Implementation plans with performance decisions |
| `TECH_DEBT.md`, `DEBT.md` | Explicit tech debt tracking |
| `CHANGELOG.md` | Recent performance-related changes |
| `docs/plans/*.md` | Phase-specific implementation plans |
| `CLAUDE.md`, `AGENTS.md` | May contain performance standards and budgets |

#### Keywords to grep

Search each file for these keywords (case-insensitive):

`performance`, `optimize`, `optimization`, `bottleneck`, `slow`, `latency`, `throughput`, `OOM`, `out of memory`, `memory`, `N+1`, `scale`, `scaling`, `cache`, `caching`, `index`, `indexing`, `timeout`, `budget`, `cost`, `expensive`, `heavy`, `vectorize`, `parallelize`, `batch`, `sequential`, `iterrows`, `toPandas`, `collect()`, `TODO`, `FIXME`, `HACK`, `tech debt`

#### What to extract

For each match, record:

| Field | Description |
|-------|-------------|
| Source file | Which documentation file |
| Item ID | TODO #, issue number, or section heading |
| Description | The documented performance concern |
| Current status | Active, deferred, resolved, or planned |
| Related code | File paths or module names mentioned |

#### Why this phase exists

- **N+1 over HTTP** may not match ORM-focused grep patterns but is documented in TODO files
- **OOM risks at scale** are invisible in code that works fine at current volume but documented as known debt
- **Deferred compute** (e.g., provisioned columns not yet populated) is intentional but worth surfacing
- **Planned optimizations** (caching layers, horizontal scaling) provide context for audit findings

#### Integration with later phases

Findings from this phase should be **cross-referenced** in the final report (Phase 13). For each code-level finding, note whether it was already tracked in documentation. For documented concerns not caught by code scanning, add them to the findings with source attribution.

**Output:** Table of documented performance concerns with status, related code paths, and cross-reference notes for later phases.

---

### Phase 1: Discovery (Both modes)

Explore the project to understand its performance surface:

- Read `CLAUDE.md`, `README.md`, `AGENTS.md`, and any architecture docs
- Read `TODO.md`, `ROADMAP.md`, `PLAN.md`, and `TECH_DEBT.md` if they exist — note any documented performance concerns (these feed into Phase 0.5 cross-referencing)
- Identify the tech stack, frameworks, and language versions
- Map the **performance surface**:
  - Services and entry points: APIs, workers, cron jobs, event consumers
  - Data stores: databases, caches, queues, object storage
  - External integrations: third-party APIs, SaaS services, cloud provider services
  - Deployment model: containers, serverless, VMs, managed services
  - Workload profile: request-driven, batch, streaming, event-driven, mixed
  - Traffic patterns: steady-state, bursty, diurnal, seasonal
  - Existing performance baselines: SLAs, SLOs, latency targets, throughput targets
  - Performance-sensitive paths: checkout, search, real-time feeds, data ingestion
  - Data pipeline components: ETL/ELT jobs, dbt models, Airflow DAGs, Spark jobs
  - Frontend assets: JS bundles, CSS, images, CDN configuration
  - Infrastructure-as-code: Terraform, CloudFormation, Pulumi, Kubernetes manifests
  - Profiling and benchmarking tooling: existing load tests, profilers, performance budgets

**Output:** A performance surface summary listing all services, data stores, deployment model, workload profile, and performance-sensitive paths.

---

### Phase 2: Algorithm & Data Structure Efficiency (Audit mode)

Evaluate algorithm complexity and data structure selection on hot paths.

Load `templates/algorithm-complexity.md` for the full Big-O reference with per-language profiling tools and data structure selection guide.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Unnecessary nested loops | O(n^2) or worse where O(n) or O(n log n) is achievable | High |
| Linear search on large collections | Sequential scan where hash map / set / binary search applies | High |
| Repeated computation | Same expensive calculation performed multiple times without caching | Medium |
| Inefficient sorting | Sorting entire collection when only top-K needed (use heap) | Medium |
| String concatenation in loops | Building strings with `+=` instead of `StringBuilder` / `join()` / `strings.Builder` | Medium |
| Unbounded collection growth | Lists, maps, or caches that grow without eviction or size limits | High |
| Inappropriate data structure | Using list where set provides O(1) lookup; using map where array suffices | Medium |
| Redundant traversals | Multiple passes over same collection that could merge into one | Low |
| Missing early termination | Loops that continue after the answer is found | Low |
| Quadratic string operations | Regex compilation inside loops, repeated `in` checks on lists | Medium |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python | `for .* in .*:\s*for .* in .*:` | Potential O(n^2) |
| Python | `if .* in list_var` inside a loop | O(n) lookup per iteration |
| Python | `re\.compile\(` inside function body | Regex recompilation per call |
| Python | `str += ` in a loop | O(n^2) string building |
| JS/TS | `array\.indexOf\(` or `array\.includes\(` inside a loop | O(n) lookup per iteration |
| Go | `strings\.Contains\(` inside a loop | Linear search per iteration |
| Go | `append\(` without pre-allocating capacity | Repeated reallocation |
| Any | `.sort()` when only min/max/top-K needed | Use heap / partial sort |

**Output:** Algorithm and data structure findings with Big-O assessment and recommended alternatives.

---

### Phase 3: Memory Management (Audit mode)

Evaluate memory allocation patterns, leak potential, cache sizing, and GC pressure.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Memory leaks | Objects retained beyond useful lifetime (event listeners, closures, global caches) | Critical |
| Excessive allocation | Allocating large objects in hot paths; objects that could be pooled or reused | High |
| Buffer sizing | Buffers too small (frequent resizing) or too large (wasted memory) | Medium |
| Large object retention | Holding references to large objects (DataFrames, images, response bodies) longer than needed | High |
| Unbounded caches | In-memory caches without TTL or max-size eviction | Critical |
| Goroutine / thread leaks | Goroutines, threads, or async tasks spawned but never joined or canceled | Critical |
| Closure captures | Closures inadvertently capturing large objects or entire scopes | Medium |
| Copy vs reference | Unnecessary deep copies of large data structures | Medium |
| Object pooling absence | Frequently created/destroyed expensive objects (DB connections, HTTP clients, buffers) | High |
| GC pressure | High allocation rate causing frequent garbage collection pauses | Medium |
| Scale-aware memory risk | `.toPandas()`, `.collect()`, or full-table loads that work at current volume but will OOM at 2-5x data growth | High |
| Missing memory budget documentation | No documented limits for in-memory operations (e.g., max rows for `.toPandas()`, max payload size) | Medium |

**Scale-aware assessment:** For each `.toPandas()`, `.collect()`, `pd.read_csv()`, or similar full-load operation, estimate whether the current data volume is close to a memory cliff. Check project documentation (TODO, ROADMAP) for known OOM risks. A function that works at 3M rows but will OOM at 6M is a High finding even if it works today.

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python | `@lru_cache` without `maxsize` (or `maxsize=None`) | Unbounded cache |
| Python | `global ` + mutable data structures | Global state that grows unboundedly |
| Python | `df = pd\.read_csv\(` without `chunksize` | Entire file in memory |
| JS/TS | `addEventListener\(` without `removeEventListener` | Event listener leak |
| JS/TS | `setInterval\(` without `clearInterval` | Timer leak |
| JS/TS | `new Map\(\)` or `new Set\(\)` as cache without eviction | Unbounded growth |
| Go | `go func\(\)` without context cancellation | Goroutine leak |
| Go | `make\(` with `0` capacity for slices that grow large | Repeated reallocation |
| Java | `static.*Map\|static.*List\|static.*Set` without size limit | Static collection leak |
| Java | `ThreadLocal` without `remove()` in finally | Thread-local memory leak |
| Any | `.*cache.*=.*\{\}` without TTL/max entries | Unbounded cache |

**Output:** Memory management findings with leak risk assessment and remediation recommendations.

---

### Phase 4: Concurrency & Parallelism (Audit mode)

Evaluate thread/goroutine pools, async correctness, lock contention, and backpressure mechanisms.

Load `templates/concurrency-patterns.md` for the full concurrency reference with thread pool sizing formulas and Enterprise Integration Patterns.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Thread pool sizing | Thread pool size appropriate for workload (CPU-bound: ~core count; I/O-bound: higher) | High |
| Async/await correctness | Blocking calls inside async functions; missing `await`; sync I/O in async context | Critical |
| Lock contention | Coarse-grained locks that serialize concurrent operations | High |
| Deadlock potential | Lock ordering violations, nested lock acquisition | Critical |
| Race conditions | Shared mutable state accessed without synchronization | Critical |
| Connection pool exhaustion | All connections in use, new requests blocked or rejected | Critical |
| Worker pool saturation | All workers busy, incoming work queued unboundedly | High |
| Unnecessary serialization | Sequential processing where parallel would be safe and faster | Medium |
| Fan-out without backpressure | Spawning unbounded concurrent operations (e.g., 10K goroutines hitting same API) | High |
| Context / cancellation propagation | Long-running operations not respecting cancellation signals | Medium |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python | `time\.sleep\(` inside `async def` | Blocking the event loop |
| Python | `requests\.\(get\|post\)` inside `async def` | Sync HTTP in async context |
| Python | `open\(` inside `async def` without `aiofiles` | Sync file I/O in async context |
| Python | `ThreadPoolExecutor\(max_workers=` | Verify sizing is reasonable |
| JS/TS | `await` inside `for` loop | Sequential awaits; use `Promise.all()` |
| Go | `sync\.Mutex` with large critical sections | Lock contention |
| Go | `go func\(\)` in a loop without semaphore/errgroup | Unbounded fan-out |
| Java | `synchronized` on broad scope | Coarse-grained locking |
| Java | `Executors\.newFixedThreadPool\(1\)` | Artificially serialized |
| Any | `Lock\(\)` or `mutex` acquired in nested fashion | Deadlock risk |
| Any | `global\|static\|shared` mutable state without lock | Race condition risk |

**Output:** Concurrency findings with contention analysis and recommended patterns.

---

### Phase 5: Database & Query Optimization (Both modes)

Evaluate query efficiency, indexing strategy, connection pooling, and ORM patterns.

Load `templates/database-optimization.md` for the full database optimization reference with N+1 detection per ORM, EXPLAIN analysis, and connection pooling guidance.

**Planning mode:** Design the data access strategy:
- Which queries will be on the critical path? (latency-sensitive vs background)
- What indexing strategy is appropriate for the access patterns?
- How will connection pooling be configured? (pool size, idle management)
- What ORM patterns will prevent N+1 queries? (eager loading, batch fetching)
- What pagination strategy? (cursor/keyset for large datasets, offset for small)
- Where are read replicas appropriate?

**Audit mode:**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| N+1 queries | Loop that executes a query per iteration instead of batch/join | Critical |
| Missing indexes | Queries filtering or joining on non-indexed columns; full table scans | Critical |
| SELECT * usage | Fetching all columns when only a few are needed | Medium |
| Unbounded queries | Queries without LIMIT or pagination on potentially large result sets | High |
| Missing EXPLAIN analysis | Complex queries not analyzed with EXPLAIN/EXPLAIN ANALYZE | High |
| Inefficient JOINs | Cartesian products, joining on non-indexed columns, unnecessary JOINs | High |
| Query in loop | Individual INSERTs/UPDATEs instead of batch operations | High |
| Unused indexes | Indexes that exist but are never used by any query | Medium |
| Over-indexing | Too many indexes on write-heavy tables, slowing inserts/updates | Medium |
| Missing connection pooling | New connection per request instead of reusing pooled connections | Critical |
| Full table scans on large tables | Sequential scans where index scan is possible | High |
| Lock contention from long transactions | Transactions held open longer than necessary | High |
| Missing read replicas | All queries hitting the primary; reads not offloaded | Medium |
| Offset-based pagination on large datasets | Using OFFSET for deep pagination (degrades linearly) | High |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python (Django) | `.objects.all()` without `.select_related()` / `.prefetch_related()` | N+1 query |
| Python (Django) | `for obj in queryset:.*obj\.related_field` | N+1 via lazy loading |
| Python (SQLAlchemy) | `session\.query\(` inside a `for` loop | N+1 query |
| Python (SQLAlchemy) | `relationship\(` without `lazy='joined'` or `lazy='subquery'` when always accessed | Lazy loading N+1 |
| Ruby (ActiveRecord) | `.each do.*\.association_name` without `.includes()` | N+1 query |
| Java (Hibernate/JPA) | `@ManyToOne` or `@OneToMany` with default fetch or lazy without batch | N+1 / over-fetching |
| Any ORM | `SELECT \*` when specific columns suffice | Over-fetching |
| Any | `INSERT INTO` inside a `for\|while\|each` loop | Row-by-row insert |
| Any | `execute\(` or `query\(` inside a loop body | Potential N+1 |
| SQL | `LIKE '%term%'` | Leading wildcard prevents index use |
| SQL | `ORDER BY.*OFFSET \d+` with large offset | Inefficient pagination |
| SQL | `SELECT.*FROM.*WHERE.*NOT IN \(SELECT` | Subquery vs JOIN performance |
| Python | `psycopg2\.connect\(` or `create_engine\(` inside request handler | New connection per request |
| Python | `requests\.Session\(\)` created per request | Session per request |
| Node.js | `new Pool\(\)` or `createConnection\(` inside request handler | Pool per request |
| Go | `sql\.Open\(` inside handler | New pool per request |
| Java | `DriverManager\.getConnection\(` without pool | No connection pooling |
| Any | `max_connections=1` or very low pool sizes | Artificial bottleneck |

Note: For N+1 patterns over HTTP (REST API calls in loops instead of ORM queries in loops), see **Phase 0 → HTTP N+1 anti-patterns**. The same principle applies — batch or parallelize instead of sequential per-item requests.

**Output:** Database optimization findings with query analysis, indexing gaps, and connection pooling assessment.

---

### Phase 6: Caching Strategy (Both modes)

Evaluate cache layers, invalidation correctness, hit ratios, memoization, and HTTP caching.

Load `templates/caching-strategies.md` for the full caching reference with 5-layer cache architecture, invalidation patterns, and stampede protection.

**Planning mode:** Design the caching strategy:
- Which operations are cacheable? (read-heavy, stable data, expensive computations)
- What cache layers are needed? (L1 in-process, L2 distributed, CDN, HTTP, browser)
- What invalidation strategy? (TTL, event-driven, write-through, write-behind)
- How will cache stampede be prevented? (singleflight, probabilistic early expiry, locking)
- What are the consistency requirements? (eventual consistency acceptable? TTL tolerance?)

**Audit mode:**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Missing cache for repeated expensive operations | Same DB query, API call, or computation repeated with same inputs | High |
| Cache invalidation correctness | Stale data served after source of truth changes | Critical |
| Cache sizing | Cache too small (constant eviction) or too large (memory waste) | Medium |
| TTL appropriateness | TTL too short (frequent misses) or too long (stale data) | Medium |
| Cache stampede protection | Thundering herd when cache expires (all requests hit backend) | High |
| Memoization opportunities | Pure functions called repeatedly with same arguments without memoization | Medium |
| HTTP cache headers | Missing `Cache-Control`, `ETag`, `Last-Modified` on cacheable responses | Medium |
| CDN configuration | Static assets and cacheable API responses not served from CDN | Medium |
| Multi-layer caching | Missing L1 (in-process) + L2 (distributed) for high-traffic paths | Low |
| Cache warming | Cold start after deployment with no pre-warming strategy | Low |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python | Expensive function without `@lru_cache` / `@cache` decorator | Missing memoization |
| Python | `redis\.get\(` with `redis\.set\(.*ex=None` | Cache without expiry |
| JS/TS | No `Cache-Control` header in API response middleware | Missing HTTP cache headers |
| HTTP | `Cache-Control: no-cache, no-store` on all responses including static assets | Over-restrictive caching |
| HTTP | No `ETag` or `Last-Modified` on GET responses | Missing conditional request support |
| Any | `cache\.delete\(` or `cache\.invalidate\(` absent after write operations | Missing cache invalidation |
| Any | Identical query or API call appearing in multiple code paths | Cacheable operation not cached |

**Output:** Caching strategy findings with hit ratio analysis, invalidation gaps, and recommended cache layers.

---

### Phase 7: Serialization & Network (Audit mode)

Evaluate data serialization format, compression, protocol optimization, and payload sizing.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Serialization format choice | JSON vs Protobuf vs MessagePack vs Avro for the use case | Medium |
| Over-serialization | Serializing and deserializing data that will just be passed through | High |
| Large payload transfer | Transferring entire objects when only a subset of fields is needed | High |
| Response compression | gzip/brotli/zstd not enabled for API responses | High |
| Repeated serialization | Same object serialized multiple times in a request lifecycle | Medium |
| HTTP/2 or HTTP/3 | Modern HTTP protocol not enabled for multiplexing and header compression | Medium |
| Keep-alive connections | TCP/HTTP keep-alive disabled, creating connections per request | High |
| Request batching | Multiple small API calls that could be batched into one | Medium |
| Chatty APIs | Too many round trips for a single user action | High |
| Base64 bloat | Binary data Base64-encoded in JSON (33% overhead) where binary transport available | Medium |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Python | `json\.dumps\(.*json\.loads\(` in sequence | Unnecessary serialization round-trip |
| Python | `pickle\.dumps\|pickle\.loads` for data transfer | Slow, insecure serialization |
| JS/TS | `JSON\.parse\(JSON\.stringify\(` | Deep clone via JSON — expensive |
| JS (frontend) | `fetch\(\)` in a `for\|forEach\|map` loop | Sequential API calls; should batch |
| JS (frontend) | `setInterval\(.*fetch\|poll` with short interval | Consider WebSocket/SSE |
| Server config | `gzip off\|compress: false\|compression: false` | Compression disabled |
| Server config | `keepalive_timeout 0\|Connection: close` | Keep-alive disabled |
| Nginx | `http2 off` or missing `http2` directive | HTTP/2 not enabled |
| Any | `base64` encoding of large binary payloads in JSON responses | 33% overhead; use binary format |
| Any | `for .* in .*: .*\.to_json\(\)\|\.to_dict\(\)` | Per-item serialization in loop |
| Any | Response without `Content-Encoding: gzip\|br\|zstd` header | Missing compression |

**Output:** Serialization and network findings with payload analysis and compression recommendations.

---

### Phase 8: Frontend & API Optimization (Audit mode) — CONDITIONAL

**Only execute this phase if frontend code exists** (HTML, CSS, JS/TS, React, Vue, Angular, Svelte, or if the project serves API responses that shape client rendering).

Load `templates/frontend-performance.md` for the full frontend performance reference with Core Web Vitals, bundle optimization, and rendering patterns.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Bundle size | JavaScript bundle too large, not code-split | High |
| Code splitting | Monolithic bundle instead of route-based splitting | High |
| Tree-shaking | Dead code not eliminated from production bundles | Medium |
| Image optimization | Unoptimized images (no WebP/AVIF, no responsive sizes, no lazy loading) | High |
| Render-blocking resources | CSS/JS blocking initial render without `async` / `defer` | High |
| Font loading | Custom fonts blocking text rendering (no `font-display: swap`) | Medium |
| Third-party scripts | Heavy third-party scripts loaded synchronously | High |
| Unnecessary re-renders | React/Vue components re-rendering when props haven't changed | Medium |
| Missing virtual scrolling | Rendering thousands of list items instead of virtualizing | High |
| Core Web Vitals | LCP, INP, CLS not meeting thresholds | High |
| Pagination (API) | Large collections returned without pagination | Critical |
| Cursor-based pagination | Large datasets using offset instead of cursor/keyset pagination | High |
| Sparse fieldsets | API returns all fields when clients only need a subset | Medium |
| GraphQL query complexity | No depth/cost limiting on GraphQL queries | High |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| HTML | `<script src=` without `async\|defer\|type="module"` | Render-blocking script |
| HTML | `<img ` without `loading="lazy"` (below fold) | Eager image loading |
| HTML | `<img ` without `srcset` or `<picture>` | No responsive images |
| CSS | `@import url\(` in CSS (not preprocessor) | Render-blocking cascade |
| CSS | `* \{` universal selector | Performance-impacting CSS |
| React | Component without `React.memo\|useMemo\|useCallback` on expensive renders | Unnecessary re-renders |
| React | `useEffect\(\(\) =>.*fetch` without cleanup/caching | Missing data caching |
| JS | `document\.querySelectorAll\(` inside `requestAnimationFrame\|scroll\|resize` handler | Layout thrashing |
| JS | `import ` (static import) of large libraries not needed on initial load | Should be dynamic `import()` |
| Webpack/Vite | No `splitChunks\|manualChunks` configuration | Missing code splitting |
| Django | `serializer_class =` without `fields = ` specification | Serializing all fields |
| FastAPI | `response_model=` returning full model when subset would do | Over-fetching |
| Express | `res\.json\(results\)` without pagination metadata | Missing pagination |
| GraphQL | No `depthLimit\|costAnalysis\|queryComplexity` middleware | Unbounded query depth |
| Any API | `return .*\.all\(\)\|return .*find\(\{\}\)` without limit/pagination | Unbounded response |

**Output:** Frontend and API optimization findings with bundle analysis, Core Web Vitals assessment, and API response shaping recommendations.

---

### Phase 9: Data Pipeline Efficiency (Both modes) — CONDITIONAL

**Only execute this phase if data pipeline tools are detected** (dbt, Spark, Airflow, Dagster, Prefect, Pandas for ETL, or similar pipeline frameworks).

Load `templates/pipeline-efficiency.md` for the full pipeline efficiency reference with batch/stream trade-offs, incremental processing patterns, and storage format selection.

**Planning mode:** Design the pipeline efficiency strategy:
- What are the latency requirements? (batch overnight, micro-batch hourly, near-real-time)
- Which pipelines should be incremental vs full rebuild?
- What storage format is appropriate? (Parquet for analytics, Delta/Iceberg for updates)
- How will data skew be detected and mitigated?
- What dead letter handling is needed for failed records?

**Audit mode:**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Batch vs streaming mismatch | Using batch for near-real-time, or streaming for overnight analytics | High |
| Full recomputation vs incremental | Reprocessing entire dataset when only new/changed records need processing | High |
| Data skew | Uneven partition sizes causing some tasks to take much longer | High |
| Shuffle operations | Unnecessary shuffles in distributed computation (Spark: repartition, groupByKey) | High |
| Storage format | Row-format (CSV, JSON) for analytical queries instead of columnar (Parquet, ORC) | High |
| Compression | Uncompressed data in storage or transit | Medium |
| Predicate pushdown | Filtering after read instead of pushing predicates to storage layer | High |
| Column pruning | Reading all columns from wide tables when only a few are needed | Medium |
| Materialization strategy | Recomputing expensive intermediate results instead of materializing them | Medium |
| Idempotency | Pipeline not safe to re-run (produces duplicates or corrupts state) | High |
| Dead letter handling | Failed records silently dropped instead of quarantined | High |
| Row-by-row processing | Python loops over DataFrames instead of vectorized operations | High |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Spark/PySpark | `groupByKey\(\)` instead of `reduceByKey\(\)` or `aggregateByKey\(\)` | Unnecessary shuffle, high memory |
| Spark/PySpark | `collect\(\)` on large datasets | Bringing all data to driver |
| Spark/PySpark | `repartition\(\d+\)` without clear justification | Unnecessary shuffle |
| Spark/PySpark | `\.toPandas\(\)` on large DataFrames | Converting distributed to local memory |
| dbt | `materialized='table'` on models that could be `incremental` | Full rebuild each run |
| dbt | No `is_incremental()` guard in incremental models | Not truly incremental |
| Pandas | `pd\.read_csv\(` for large files without `chunksize` or `usecols` | All data in memory |
| Pandas | `df\.apply\(` on row axis for vectorizable operations | Python-speed instead of C-speed |
| SQL | `INSERT INTO.*SELECT \*` without column specification | Over-fetching in ETL |
| Any | `to_csv\(\)` for data used analytically downstream | Should use Parquet |
| Any | `for row in` iteration over large dataset instead of vectorized ops | Row-by-row processing |

#### Exhaustive `.iterrows()` / `.apply(axis=1)` enumeration

In addition to the grep patterns above, **enumerate ALL instances** of `.iterrows()`, `.itertuples()`, `df.apply(axis=1)`, and `for row in df` across the entire codebase. For each instance, classify it:

| Classification | Criteria | Severity |
|----------------|----------|----------|
| **Vectorizable — data transformation** | Loop body performs aggregation, filtering, dict building, or accumulation that can be replaced with `groupby()`, `melt()`, `merge()`, `set_index().to_dict()`, or vectorized numpy operations | High (>10K rows), Medium (<10K rows), Low (<100 rows) |
| **Vectorizable — lookup optimization** | Loop body contains a DataFrame filter like `df[df["key"] == val]` that can be replaced with pre-built `groupby().get_group()` | Medium (regardless of outer loop size) |
| **Domain-required — per-item function call** | Loop body calls a function with inherently per-item logic (physics model, geometry test, ML inference with no batch API) | Acceptable — but check if inner data fetching/lookup is optimizable |
| **Orchestration loop** | Loop iterates over a small control set (competition-seasons, match IDs) to drive batch processing | Acceptable |
| **UI / display code** | Loop builds visualization data for <100 items | Low |

**Important severity calibration:** When a loop is classified as "domain-required" but contains an inner vectorizable lookup (e.g., a DataFrame filter inside the loop), rate the **lookup optimization** separately from the loop itself. The loop is Acceptable; the inner lookup is Medium. Do not rate the entire loop as High just because it uses `.iterrows()`.

**Output:** Data pipeline efficiency findings with processing pattern analysis and storage format recommendations.

---

### Phase 10: Container & Startup Optimization (Audit mode) — CONDITIONAL

**Only execute this phase if Dockerfiles, docker-compose files, or Kubernetes manifests exist.**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Multi-stage builds | Application image contains build tools, compilers, dev dependencies | High |
| Base image selection | Using full OS image (ubuntu, debian) instead of slim/distroless/alpine | High |
| Layer ordering | Frequently changing layers (code) not last in Dockerfile | Medium |
| Dependency caching | Package install layer not cached (dependencies reinstalled on every code change) | High |
| `.dockerignore` | `node_modules`, `.git`, `__pycache__`, test files included in build context | Medium |
| Image size | Image > 500MB for a typical application | Medium |
| Pinned versions | Base image using `latest` instead of pinned digest or version | Medium |
| Build cache utilization | CI/CD not caching Docker layers between builds | Medium |
| Non-root user | Container running as root | Medium |
| Resource limits | No CPU/memory limits in orchestrator config | High |
| Cold start time | Application takes > 30s to become ready | High |
| Eager initialization | Loading all resources at startup instead of lazy-initializing | Medium |
| Startup probe alignment | Application marked ready before it can handle requests | High |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Dockerfile | `FROM (ubuntu\|debian\|centos\|node):latest` | Unpinned, oversized base image |
| Dockerfile | `COPY \. \.` before `RUN .*install` | Invalidates dependency cache on any code change |
| Dockerfile | `RUN apt-get install` without `--no-install-recommends` | Extra packages installed |
| Dockerfile | `RUN pip install` without `--no-cache-dir` | pip cache stored in image |
| Dockerfile | No `USER` instruction | Running as root |
| Dockerfile | No `.dockerignore` file alongside Dockerfile | Build context bloat |
| Dockerfile | `RUN npm install` instead of `RUN npm ci` | Non-deterministic installs |
| docker-compose | No `deploy.resources.limits` | Missing resource limits |
| Kubernetes | No `resources.limits` in pod spec | Missing resource limits |
| Kubernetes | No `HorizontalPodAutoscaler` for variable workloads | Missing auto-scaling |
| Python (Lambda) | `import (tensorflow\|torch\|pandas\|sklearn)` at module top level | Heavy imports on cold start |
| Node.js (Lambda) | `require\('aws-sdk'\)` importing entire SDK | Should import only needed client |
| Any | `time\.sleep\|Thread\.sleep` in startup sequence | Artificial startup delay |

**Output:** Container and startup optimization findings with image analysis and cold start assessment.

---

### Phase 11: Cloud Cost & Right-Sizing (Both modes) — CONDITIONAL

**Only execute this phase if IaC (Terraform, CloudFormation, Pulumi), Kubernetes manifests, or cloud deployment configuration exists.**

Load `templates/cloud-cost-optimization.md` for the full cloud cost reference with right-sizing methodology, auto-scaling patterns, and cost estimation tools.

**Planning mode:** Design the cost optimization strategy:
- What is the workload profile? (steady-state, bursty, diurnal, batch)
- Where can spot/preemptible instances be used? (fault-tolerant workloads, batch jobs)
- What auto-scaling strategy? (reactive, predictive, queue-based)
- What storage tiering policy? (hot/warm/cold based on access frequency)
- Can any workloads scale to zero? (serverless, KEDA, scale-to-zero on idle)

**Audit mode:**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Over-provisioned compute | CPU utilization consistently < 20%, memory < 30% | High |
| Under-provisioned compute | CPU > 80% sustained, OOM kills, throttling | Critical |
| Auto-scaling configuration | No auto-scaling, or scaling thresholds too conservative/aggressive | High |
| Spot/preemptible usage | Fault-tolerant workloads not using spot instances (60-90% savings) | High |
| Reserved capacity | Steady-state workloads on on-demand pricing without reservations | High |
| Storage tiering | Infrequently accessed data on expensive hot storage tier | High |
| Idle resources | Running resources during off-hours (dev/staging environments) | High |
| Orphaned resources | Detached volumes, unused IPs, stale snapshots, empty load balancers | Medium |
| Serverless vs always-on | Always-on instances for bursty/infrequent workloads | Medium |
| Oversized databases | RDS instance with < 10% CPU utilization | High |
| Horizontal scaling capability | Application stateful, preventing horizontal scale-out | High |
| Scale-down policy | No scale-down cooldown causing thrashing | Medium |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Terraform | `instance_type = ".*xlarge\|.*2xlarge\|.*4xlarge"` (verify against utilization) | Potentially oversized |
| Terraform | No `autoscaling_group` or `auto_scaling_configuration` | Missing auto-scaling |
| Terraform | `storage_type = "gp2"` | Should be `gp3` (cheaper, better performance) |
| Terraform | `engine = "oracle-\|sqlserver-"` | Commercial DB license costs |
| Terraform | `transition.*days = ` not configured in S3 lifecycle | No storage tiering |
| Kubernetes | `resources.requests.cpu` >> actual usage | Over-provisioned pods |
| Kubernetes | No `HorizontalPodAutoscaler` for variable workloads | Missing auto-scaling |
| Terraform/K8s | `min_size = .*max_size` (same value) | Auto-scaling effectively disabled |
| Terraform | `cooldown = 0\|cooldown_period = 0` | No scale-down cooldown; thrashing |
| Code | `session\[` or `flask\.session\[` with default in-memory store | Stateful; can't scale horizontally |
| Code | File writes to local filesystem in request handler | Local state prevents scaling |
| docker-compose | No `deploy.resources.limits` | Unbounded resource usage |

**Output:** Cloud cost and right-sizing findings with resource utilization analysis and cost optimization recommendations.

---

### Phase 12: Profiling & Benchmarking Posture (Both modes)

Evaluate the maturity of performance testing, regression detection, and profiling practices.

Load `templates/profiling-benchmarking.md` for the full profiling and benchmarking reference with per-language profiling tools, load testing methodology, and performance budget patterns.

**Planning mode:** Design the performance testing strategy:
- What performance baselines need to be established? (latency targets, throughput targets)
- Where should load tests run? (CI/CD, staging, production canary)
- What performance budgets should be enforced? (response time, bundle size, resource usage)
- How will performance regressions be detected? (CI gates, trend monitoring)

**Audit mode:**

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Performance test suite | Automated performance tests exist and run in CI/CD | High |
| Baseline metrics established | p50/p95/p99 latency baselines documented for key operations | High |
| Performance regression detection | CI/CD fails or alerts on performance degradation | High |
| Load testing | Load test scenarios cover realistic traffic patterns | Medium |
| Stress testing | System tested beyond expected peak to find breaking points | Medium |
| Profiling artifacts | CPU/memory profiles captured and analyzed for hot paths | Medium |
| Performance budget | Maximum response time, bundle size, or resource usage defined and enforced | Medium |
| Realistic test data | Load tests use representative data volumes and distributions | Medium |
| Soak testing | Extended-duration tests to detect memory leaks and resource exhaustion | Low |
| Comparative benchmarks | Performance tracked across versions / commits | Medium |

#### Grep patterns

| Language | Pattern | Issue |
|----------|---------|-------|
| Test config | No `performance\|benchmark\|load-test\|perf` directory or config | Missing performance tests |
| CI config | No performance test step in CI/CD pipeline | No regression detection |
| Any | `# TODO.*performance\|# TODO.*benchmark\|# FIXME.*slow` | Acknowledged performance debt |
| Test files | `time\.sleep\|Thread\.sleep` in performance tests | Artificial delays invalidate results |

**Output:** Profiling and benchmarking posture assessment with gaps and recommended tooling.

---

### Phase 13: Findings Report (Both modes)

Generate the final report. The format depends on the mode.

#### Planning mode report

Present the performance strategy and design recommendations:

```markdown
## Performance Strategy — [System Name]

### Performance Surface Summary
- Services: [list]
- Data stores: [list]
- Workload profile: [request-driven / batch / streaming / mixed]
- Traffic pattern: [steady / bursty / diurnal / seasonal]
- Performance-sensitive paths: [list]

### Data Access Strategy
| Path | Access Pattern | Caching | Pagination | Indexing |
|------|---------------|---------|------------|---------|
| Product search | Read-heavy, filtered | L1 + L2, 5min TTL | Cursor-based | Composite on (category, price) |

### Capacity Planning
| Component | Expected Load | Sizing | Scaling Strategy |
|-----------|--------------|--------|-----------------|
| API servers | 1K req/sec peak | 4x c5.xlarge | HPA on request rate |
| PostgreSQL | 500 queries/sec | r5.2xlarge | Read replicas for read load |

### Caching Strategy
| Layer | Technology | Scope | TTL | Invalidation |
|-------|-----------|-------|-----|-------------|
| L1 (in-process) | lru_cache | Per-instance | 60s | TTL expiry |
| L2 (distributed) | Redis | Shared | 5min | Event-driven on write |
| CDN | CloudFront | Global | 24hr | Cache-busting on deploy |

### Design Recommendations
| # | Area | Recommendation | Priority | ROI |
|---|------|----------------|----------|-----|
| 1 | Database | Implement connection pooling with pgBouncer | Critical | High effort / High gain |
| 2 | Caching | Add Redis L2 cache for product catalog | High | Medium effort / High gain |

### Performance Design Checklist
- [ ] Data access patterns identified for all critical paths
- [ ] Indexing strategy designed for query patterns
- [ ] Connection pooling configured for all data stores
- [ ] Caching layers defined with invalidation strategy
- [ ] Auto-scaling policy designed for workload profile
- [ ] Performance baselines and budgets defined
- [ ] Load testing plan created
- [ ] Storage format selected for analytical workloads (if applicable)
- [ ] Pagination strategy selected for all list endpoints
```

#### Audit mode report

Present concrete findings with fix status and ROI estimates:

```markdown
## Optimization Audit Report — [System Name]

### Executive Summary
- Total findings: X
- Critical: X | High: X | Medium: X | Low: X
- Fixed during audit: X
- Remaining: X
- Estimated performance improvement: [summary of key gains]

### Findings
| # | Severity | Phase | File:Line | Description | ROI (Effort/Gain) | Status |
|---|----------|-------|-----------|-------------|-------------------|--------|
| 1 | Critical | Phase 0 | src/api.py:42 | N+1 query in product listing (adds ~200ms/page) | Low effort / High gain | Fixed |
| 2 | High | Phase 5 | src/db.py:18 | Missing index on orders.user_id (full table scan) | Low effort / High gain | Fixed |
| 3 | Medium | Phase 6 | src/views.py:55 | Repeated API call without caching | Medium effort / Medium gain | Recommended |

### Quick Wins (fix in < 30 minutes, significant gain)
| # | Finding | Estimated Impact | Fix |
|---|---------|-----------------|-----|
| 1 | Add missing index on orders.user_id | ~10x query speedup | `CREATE INDEX idx_orders_user_id ON orders(user_id);` |
| 2 | Enable gzip compression on API responses | ~70% bandwidth reduction | Add compression middleware |

### Phase Coverage Matrix
| Phase | Checks Run | Findings | Key Result |
|-------|-----------|----------|------------|
| Phase 0: Anti-Patterns | [X patterns scanned] | [Y findings] | [summary] |
| Phase 0.5: Documentation Scan | [X files scanned] | [Y documented concerns] | [summary] |
| Phase 1: Discovery | [X surfaces mapped] | [Y findings] | [summary] |
| Phase 2: Algorithms | [X checks] | [Y findings] | [summary] |
| Phase 3: Memory | [X checks] | [Y findings] | [summary] |
| Phase 4: Concurrency | [X checks] | [Y findings] | [summary] |
| Phase 5: Database | [X checks] | [Y findings] | [summary] |
| Phase 6: Caching | [X checks] | [Y findings] | [summary] |
| Phase 7: Serialization | [X checks] | [Y findings] | [summary] |
| Phase 8: Frontend (if applicable) | [X checks] | [Y findings] | [summary] |
| Phase 9: Pipelines (if applicable) | [X checks] | [Y findings] | [summary] |
| Phase 10: Containers (if applicable) | [X checks] | [Y findings] | [summary] |
| Phase 11: Cloud Cost (if applicable) | [X checks] | [Y findings] | [summary] |
| Phase 12: Profiling Posture | [X checks] | [Y findings] | [summary] |

### Optimization Maturity Rating
- **Checks passed**: X/Y (Z% coverage)
- **Overall**: [Optimized / Mostly Optimized / Needs Optimization / Significant Waste]

### Phase 0.5 Cross-Reference
| Documented Concern | Source | Related Finding | Status |
|--------------------|--------|-----------------|--------|
| "N+1 sequential API calls" | TODO #3 | Finding #X (or: New — not caught by code scan) | Tracked |
| "OOM risk at 2x volume" | TODO #4 | Finding #Y (P1/P2 column projection) | Partially addressed |

### Documented Optimization Strategies (Not Yet Implemented)
If the project's ROADMAP or planning docs describe optimization strategies not yet in code, list them here for context. These are not findings — they are planned work that provides context for the audit results.

| Strategy | Source | Relevance to Audit |
|----------|--------|-------------------|
| Example: 5-layer caching architecture | ROADMAP.md | Explains why L2/L3 caching is absent (planned, not overlooked) |

### Ready for production: Yes / No (with blockers)
```

---

## Important rules

- **Fix as you go.** When audit mode finds a Critical or High issue that you can fix, fix it immediately. Don't just report — remediate. Add missing indexes, enable compression, fix N+1 queries.
- **Evidence-based claims.** Every finding must include file path, line number, or specific evidence. Never say "probably slow."
- **Quantify impact.** Optimization is relative, not binary. Every finding should estimate the impact: "N+1 adds ~200ms/page" not just "N+1 found." Use Big-O analysis, EXPLAIN output, or measurement to back up claims.
- **ROI-oriented.** Findings must estimate effort vs impact. Quick wins (5 min fix, 10x gain) are prioritized over structural changes (multi-sprint, 2x gain).
- **Fix obvious wins, benchmark structural changes.** Add a missing index? Yes, fix it. Rewrite the concurrency model? Recommend benchmarking first, then fix.
- **No assumptions.** Read the actual code, configs, and infrastructure files. Don't assume performance is good because a framework is used.
- **Verify fixes.** After fixing a performance issue, re-run the check that found it to confirm the fix works.
- **Respect existing patterns.** If the project has established performance patterns, extend them rather than introducing new ones.
- **Conditional phases.** Phase 8 (Frontend) only if frontend code exists. Phase 9 (Pipeline) only if pipeline tools detected. Phase 10 (Container) only if Dockerfiles/K8s exist. Phase 11 (Cloud Cost) only if IaC/cloud config exists. Skip irrelevant phases to keep signal-to-noise high.
- **Scope awareness.** Don't flag managed-service built-in optimization as a finding (e.g., auto-scaling managed by a PaaS).
- **Single tier.** There is no Standard/Enterprise split. All checks are actionable with free/open-source tools.
- **Prioritize.** Fix Critical and High findings. Track Medium and Low in the backlog. Don't let perfect be the enemy of fast.
