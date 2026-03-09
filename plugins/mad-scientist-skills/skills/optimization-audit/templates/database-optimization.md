# Database & Query Optimization Reference

Patterns and framework-specific examples for detecting N+1 queries, designing indexing strategies, analyzing query plans, configuring connection pools, and optimizing data access patterns.

## Purpose

Answer: "Are database queries efficient, properly indexed, and not generating unnecessary load?"

## Checklist

Before auditing, identify:

- [ ] Which ORM or query builder is used (Django ORM, SQLAlchemy, ActiveRecord, Hibernate/JPA, Prisma, Drizzle)
- [ ] Which database engine (PostgreSQL, MySQL, SQLite, MongoDB, SQL Server)
- [ ] Whether connection pooling is configured (and which pooler: built-in, pgBouncer, HikariCP)
- [ ] Whether query logging or slow query logs are enabled
- [ ] What pagination strategy is used (offset, cursor/keyset, none)
- [ ] Whether read replicas or sharding are in use
- [ ] What the expected data volume and growth rate are
- [ ] Whether any query performance monitoring is in place (pg_stat_statements, django-debug-toolbar, nplusone)

---

## N+1 Query Detection

The N+1 problem occurs when code executes 1 query to fetch a list of N items, then executes N additional queries to fetch related data for each item. This turns O(1) database round-trips into O(N).

### Django ORM

**BAD -- lazy loading triggers N+1:**
```python
# BAD -- 1 query for orders + N queries for customer (one per order)
orders = Order.objects.all()
for order in orders:
    print(order.customer.name)     # Each access triggers a separate query
    print(order.shipping_address)  # Another N queries if this is a FK
# Total: 1 + N + N queries
```

**GOOD -- select_related for ForeignKey / OneToOne (SQL JOIN):**
```python
# GOOD -- 1 query with JOIN
orders = Order.objects.select_related("customer", "shipping_address").all()
for order in orders:
    print(order.customer.name)     # No additional query -- already loaded
    print(order.shipping_address)  # No additional query
# Total: 1 query
```

**GOOD -- prefetch_related for ManyToMany / reverse ForeignKey (separate query):**
```python
# GOOD -- 2 queries: one for orders, one for all related items
orders = Order.objects.prefetch_related("items").all()
for order in orders:
    for item in order.items.all():  # No additional query -- prefetched
        print(item.name)
# Total: 2 queries regardless of N
```

**GOOD -- Prefetch() objects for filtered or annotated prefetches:**
```python
from django.db.models import Prefetch

# GOOD -- prefetch only active items with custom queryset
orders = Order.objects.prefetch_related(
    Prefetch(
        "items",
        queryset=Item.objects.filter(active=True).select_related("category"),
    )
).all()
# Total: 2 queries with filtering applied at the database level
```

### SQLAlchemy

**BAD -- default lazy loading in a loop:**
```python
# BAD -- 1 query for orders + N queries for customer
orders = session.query(Order).all()
for order in orders:
    print(order.customer.name)  # Lazy load triggers per iteration
```

**GOOD -- joinedload (SQL JOIN, single query):**
```python
from sqlalchemy.orm import joinedload

# GOOD -- single query with JOIN
orders = (
    session.query(Order)
    .options(joinedload(Order.customer))
    .all()
)
# Use for: ForeignKey / ManyToOne where related set is small
```

**GOOD -- selectinload (separate IN query, avoids cartesian explosion):**
```python
from sqlalchemy.orm import selectinload

# GOOD -- 2 queries: SELECT orders; SELECT items WHERE order_id IN (...)
orders = (
    session.query(Order)
    .options(selectinload(Order.items))
    .all()
)
# Use for: OneToMany / ManyToMany to avoid row multiplication
```

**GOOD -- subqueryload (separate subquery):**
```python
from sqlalchemy.orm import subqueryload

# GOOD -- 2 queries using a subquery for the related load
orders = (
    session.query(Order)
    .options(subqueryload(Order.items))
    .all()
)
# Use for: large result sets where IN clause would be too large
```

### ActiveRecord (Ruby on Rails)

**BAD -- N+1 via lazy association loading:**
```ruby
# BAD -- 1 query for orders + N queries for customer
orders = Order.all
orders.each do |order|
  puts order.customer.name  # Triggers a query per order
end
```

**GOOD -- includes (lets Rails choose JOIN or separate query):**
```ruby
# GOOD -- Rails decides: JOIN for small sets, separate query for large
orders = Order.includes(:customer, :items).all
orders.each do |order|
  puts order.customer.name  # Already loaded
  order.items.each { |item| puts item.name }
end
```

**GOOD -- preload (always separate queries) vs eager_load (always JOIN):**
```ruby
# Separate queries (avoids cartesian product for has_many):
orders = Order.preload(:items).all

# Single JOIN query (best for belongs_to / has_one):
orders = Order.eager_load(:customer).where(customers: { active: true })
```

### Hibernate / JPA (Java)

**BAD -- default lazy loading without batch fetching:**
```java
// BAD -- 1 query for orders + N queries for customer
List<Order> orders = entityManager
    .createQuery("SELECT o FROM Order o", Order.class)
    .getResultList();

for (Order order : orders) {
    System.out.println(order.getCustomer().getName()); // N+1
}
```

**GOOD -- JOIN FETCH in JPQL:**
```java
// GOOD -- single query with JOIN
List<Order> orders = entityManager
    .createQuery(
        "SELECT o FROM Order o JOIN FETCH o.customer",
        Order.class
    )
    .getResultList();
```

**GOOD -- @BatchSize for batched lazy loading:**
```java
@Entity
public class Order {
    @ManyToOne(fetch = FetchType.LAZY)
    @BatchSize(size = 25) // Load 25 customers at a time instead of 1
    private Customer customer;
}
```

**GOOD -- EntityGraph for dynamic fetch plans:**
```java
EntityGraph<Order> graph = entityManager.createEntityGraph(Order.class);
graph.addAttributeNodes("customer", "items");

List<Order> orders = entityManager
    .createQuery("SELECT o FROM Order o", Order.class)
    .setHint("jakarta.persistence.fetchgraph", graph)
    .getResultList();
```

### Prisma (TypeScript/JavaScript)

**BAD -- separate queries in a loop:**
```typescript
// BAD -- 1 query for orders + N queries for customer
const orders = await prisma.order.findMany();
for (const order of orders) {
    const customer = await prisma.customer.findUnique({
        where: { id: order.customerId },
    }); // N additional queries
}
```

**GOOD -- include for eager loading related records:**
```typescript
// GOOD -- single query with joins
const orders = await prisma.order.findMany({
    include: {
        customer: true,
        items: true,
    },
});
// orders[0].customer.name is available without additional queries
```

**GOOD -- select for fetching only needed fields:**
```typescript
// GOOD -- only fetch specific fields, reducing data transfer
const orders = await prisma.order.findMany({
    select: {
        id: true,
        total: true,
        customer: {
            select: { name: true, email: true },
        },
    },
});
```

---

## Indexing Strategy

### When to Create an Index

| Create an index when... | Do NOT index when... |
|------------------------|---------------------|
| Column appears in WHERE clauses frequently | Table has very few rows (<1,000) |
| Column appears in JOIN conditions | Column has very low cardinality (boolean, enum with 2-3 values) |
| Column is used in ORDER BY | Table is write-heavy with rare reads |
| Column is used in GROUP BY | Column is frequently updated (index maintenance cost) |
| Unique constraint is needed | You already have many indexes on the table (over-indexing) |
| Range queries on the column (>, <, BETWEEN) | Column stores large text (use full-text index instead) |

### Composite (Multi-Column) Indexes

**Key rule:** Column order matters. The index is usable for queries that filter on a left prefix of the columns.

```sql
-- Index on (status, created_at, customer_id)

-- GOOD -- uses index (left prefix match):
SELECT * FROM orders WHERE status = 'pending';
SELECT * FROM orders WHERE status = 'pending' AND created_at > '2025-01-01';
SELECT * FROM orders WHERE status = 'pending' AND created_at > '2025-01-01'
                      AND customer_id = 42;

-- BAD -- cannot use this index (skips leading column):
SELECT * FROM orders WHERE created_at > '2025-01-01';        -- status not specified
SELECT * FROM orders WHERE customer_id = 42;                 -- skips status, created_at
```

**Column order heuristic:** Place equality columns first, range columns last.

```sql
-- GOOD -- equality first, range last
CREATE INDEX idx_orders_status_created
    ON orders (status, created_at);

-- For query: WHERE status = 'pending' AND created_at > '2025-01-01'
-- Both columns are used efficiently
```

### Covering Indexes (Index-Only Scans)

A covering index includes all columns the query needs, so the database reads only the index -- never touching the table heap.

```sql
-- Query that benefits from a covering index:
SELECT customer_id, total FROM orders WHERE status = 'shipped';

-- Covering index -- includes all selected and filtered columns:
CREATE INDEX idx_orders_covering
    ON orders (status) INCLUDE (customer_id, total);
-- PostgreSQL uses INCLUDE for non-key columns
-- MySQL achieves this automatically if all columns are in the index key
```

### Partial Indexes (PostgreSQL)

Index only the rows that matter, reducing index size and write overhead.

```sql
-- Only 5% of orders are pending, but queries always filter for them
CREATE INDEX idx_orders_pending
    ON orders (created_at)
    WHERE status = 'pending';

-- Much smaller than indexing all orders by created_at
-- Only maintained when rows match the predicate
```

### Over-Indexing Risks

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow INSERT/UPDATE/DELETE | Too many indexes on the table | Drop unused indexes |
| Index bloat consuming storage | Indexes on high-churn columns | Evaluate necessity, REINDEX |
| Write amplification | Each write updates every index | Consolidate overlapping indexes |

**Find unused indexes (PostgreSQL):**
```sql
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## EXPLAIN Analysis Guide

### PostgreSQL

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;
```

| What to look for | Meaning | Action |
|-----------------|---------|--------|
| `Seq Scan` on a large table | Full table scan -- no index used | Add an index on the filter/join column |
| `Nested Loop` with high row count | O(N*M) join strategy | Check that inner side has an index; consider Hash Join |
| `Hash Join` | Builds hash table from one side, probes with other | Generally efficient; watch for large hash tables spilling to disk |
| `Sort` with `external merge` | Sort spilling to disk (work_mem too low) | Increase `work_mem` or add index for ORDER BY |
| `Bitmap Heap Scan` | Index scan followed by heap access with recheck | Normal for moderate selectivity; efficient |
| High `rows` vs `actual rows` | Planner estimate is wrong | Run `ANALYZE tablename;` to update statistics |
| `Buffers: shared read` (high) | Many pages read from disk (not cache) | Need more shared_buffers or query is scanning too much |

**Reading costs:**
```
Seq Scan on orders  (cost=0.00..1542.00 rows=50000 width=120)
                     ^^^^      ^^^^^^^
                     startup   total cost (in arbitrary units)
```

### MySQL

```sql
EXPLAIN SELECT ...;
-- Or for more detail:
EXPLAIN ANALYZE SELECT ...;  -- MySQL 8.0.18+
```

| Column | What to watch | Red flag |
|--------|--------------|----------|
| `type` | Access method | `ALL` = full table scan; want `ref`, `range`, or `const` |
| `possible_keys` | Indexes considered | `NULL` = no applicable index |
| `key` | Index actually used | `NULL` = no index chosen |
| `rows` | Estimated rows examined | Much larger than result set = inefficient |
| `Extra` | Additional info | `Using filesort` = sort without index; `Using temporary` = temp table created |

### SQLite

```sql
EXPLAIN QUERY PLAN SELECT ...;
```

| What to look for | Meaning | Action |
|-----------------|---------|--------|
| `SCAN TABLE` | Full table scan | Add index |
| `SEARCH TABLE ... USING INDEX` | Index used | Good |
| `USE TEMP B-TREE FOR ORDER BY` | Sorting without index | Add index matching ORDER BY |

### MongoDB

```javascript
db.collection.find({ status: "active" }).explain("executionStats");
```

| What to look for | Meaning | Action |
|-----------------|---------|--------|
| `COLLSCAN` | Collection scan (full scan) | Create index on query fields |
| `IXSCAN` | Index scan | Good |
| `totalDocsExamined` >> `nReturned` | Examining many docs, returning few | Index is not selective enough |
| `executionTimeMillis` | Wall clock time | Baseline for comparison |

---

## Connection Pooling

### Connection Pool Sizing Formula

For PostgreSQL, the recommended formula from the PostgreSQL wiki:

```
connections = ((core_count * 2) + effective_spindle_count)
```

Where:
- `core_count` = number of CPU cores on the database server
- `effective_spindle_count` = number of disks in the RAID array (use 1 for SSD)

**Example:** 4-core server with SSD = (4 * 2) + 1 = **9 connections**

This is the *total* across all application instances. If you have 3 app servers, each pool should be sized to `9 / 3 = 3` connections max.

**Key insight:** More connections is not better. Beyond the optimal count, connections compete for CPU and memory, increasing latency through context switching. A smaller pool with queuing often outperforms a large pool.

### Python -- SQLAlchemy

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://user:pass@host/db",
    pool_size=5,            # Maintained idle connections
    max_overflow=10,        # Extra connections allowed beyond pool_size
    pool_timeout=30,        # Seconds to wait for a connection before error
    pool_recycle=1800,      # Recycle connections after 30 min (avoids stale)
    pool_pre_ping=True,     # Test connection health before use
)
```

### Python -- psycopg (v3) Connection Pool

```python
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo="postgresql://user:pass@host/db",
    min_size=2,             # Minimum idle connections
    max_size=10,            # Maximum connections
    max_idle=300,           # Close idle connections after 5 minutes
    max_lifetime=3600,      # Recycle after 1 hour
    timeout=30,             # Wait timeout for a connection
)

# Usage
with pool.connection() as conn:
    conn.execute("SELECT ...")
```

### Python -- Django CONN_MAX_AGE

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mydb",
        "CONN_MAX_AGE": 600,    # Reuse connections for 10 minutes
        # Set to None for unlimited reuse (use with connection pooler like pgBouncer)
        # Set to 0 (default) to close after each request -- AVOID in production
    }
}

# For production with multiple workers, combine with pgBouncer:
# Django CONN_MAX_AGE=None -> pgBouncer (transaction pooling) -> PostgreSQL
```

### Node.js -- pg Pool

```javascript
const { Pool } = require("pg");

const pool = new Pool({
    host: "localhost",
    database: "mydb",
    user: "user",
    password: "pass",
    max: 10,                     // Maximum connections in pool
    idleTimeoutMillis: 30000,    // Close idle connections after 30s
    connectionTimeoutMillis: 5000, // Error if connection not acquired in 5s
    maxUses: 7500,               // Close connection after N uses (prevents leaks)
});

// Usage
const result = await pool.query("SELECT * FROM orders WHERE id = $1", [orderId]);
```

### Node.js -- Knex Pool

```javascript
const knex = require("knex")({
    client: "pg",
    connection: { host: "localhost", database: "mydb" },
    pool: {
        min: 2,                  // Minimum connections
        max: 10,                 // Maximum connections
        acquireTimeoutMillis: 30000,
        createTimeoutMillis: 5000,
        idleTimeoutMillis: 30000,
        reapIntervalMillis: 1000,
        createRetryIntervalMillis: 200,
    },
});
```

### Go -- database/sql

```go
import "database/sql"

db, err := sql.Open("postgres", "postgres://user:pass@host/db?sslmode=disable")
if err != nil {
    log.Fatal(err)
}

db.SetMaxOpenConns(10)          // Maximum total connections (open + idle)
db.SetMaxIdleConns(5)           // Maximum idle connections in pool
db.SetConnMaxLifetime(30 * time.Minute)  // Recycle after 30 min
db.SetConnMaxIdleTime(5 * time.Minute)   // Close idle connections after 5 min
```

### Java -- HikariCP

```java
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:postgresql://host/db");
config.setUsername("user");
config.setPassword("pass");

config.setMaximumPoolSize(10);       // Maximum connections
config.setMinimumIdle(2);            // Minimum idle connections
config.setIdleTimeout(600000);       // 10 min idle before close
config.setMaxLifetime(1800000);      // 30 min max lifetime
config.setConnectionTimeout(30000);  // 30s wait for connection
config.setLeakDetectionThreshold(60000); // Log warning if connection not returned in 60s

HikariDataSource ds = new HikariDataSource(config);
```

**Spring Boot application.properties:**
```properties
spring.datasource.hikari.maximum-pool-size=10
spring.datasource.hikari.minimum-idle=2
spring.datasource.hikari.idle-timeout=600000
spring.datasource.hikari.max-lifetime=1800000
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.leak-detection-threshold=60000
```

---

## Batch Operations

### INSERT Batching

**BAD -- row-by-row inserts in a loop:**
```python
# BAD -- N round-trips to database
for item in items:
    cursor.execute(
        "INSERT INTO items (name, price) VALUES (%s, %s)",
        (item.name, item.price),
    )
# 10,000 items = 10,000 round-trips
```

**GOOD -- batch insert with executemany or VALUES list:**
```python
# GOOD -- single round-trip with executemany (psycopg2)
from psycopg2.extras import execute_values

execute_values(
    cursor,
    "INSERT INTO items (name, price) VALUES %s",
    [(item.name, item.price) for item in items],
    page_size=1000,  # Batch size per statement
)
# 10,000 items = ~10 round-trips (batches of 1,000)
```

**GOOD -- Django bulk_create:**
```python
# GOOD -- single INSERT with multiple rows
Item.objects.bulk_create(
    [Item(name=item.name, price=item.price) for item in items],
    batch_size=1000,
)
```

**GOOD -- SQLAlchemy bulk insert:**
```python
# GOOD -- bulk insert
session.execute(
    insert(Item),
    [{"name": item.name, "price": item.price} for item in items],
)
session.commit()
```

**GOOD -- Prisma createMany:**
```typescript
// GOOD -- single bulk insert
await prisma.item.createMany({
    data: items.map((item) => ({
        name: item.name,
        price: item.price,
    })),
    skipDuplicates: true,
});
```

### Bulk UPDATE

**BAD -- individual updates in a loop:**
```python
# BAD -- N update queries
for item_id, new_price in updates:
    cursor.execute(
        "UPDATE items SET price = %s WHERE id = %s",
        (new_price, item_id),
    )
```

**GOOD -- bulk update with CASE or VALUES:**
```sql
-- GOOD -- single query updates multiple rows
UPDATE items
SET price = v.price
FROM (VALUES (1, 19.99), (2, 29.99), (3, 39.99)) AS v(id, price)
WHERE items.id = v.id;
```

**GOOD -- Django bulk_update:**
```python
# GOOD -- single UPDATE with CASE expression
items = Item.objects.filter(id__in=update_ids)
for item in items:
    item.price = new_prices[item.id]
Item.objects.bulk_update(items, ["price"], batch_size=1000)
```

### UPSERT Patterns

```sql
-- PostgreSQL (INSERT ... ON CONFLICT):
INSERT INTO items (sku, name, price)
VALUES ('SKU-001', 'Widget', 19.99)
ON CONFLICT (sku)
DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price;

-- MySQL (INSERT ... ON DUPLICATE KEY UPDATE):
INSERT INTO items (sku, name, price)
VALUES ('SKU-001', 'Widget', 19.99)
ON DUPLICATE KEY UPDATE name = VALUES(name), price = VALUES(price);
```

**Django -- update_or_create (single row) vs bulk approach:**
```python
# Single row upsert (still 1 query per row -- use sparingly):
Item.objects.update_or_create(
    sku="SKU-001",
    defaults={"name": "Widget", "price": 19.99},
)

# Bulk upsert (Django 4.1+):
Item.objects.bulk_create(
    [Item(sku="SKU-001", name="Widget", price=19.99)],
    update_conflicts=True,
    unique_fields=["sku"],
    update_fields=["name", "price"],
)
```

---

## Pagination Patterns

### Offset Pagination

**How it works:** `SELECT ... LIMIT 20 OFFSET 40` skips 40 rows, returns next 20.

**BAD -- offset pagination on large datasets:**
```sql
-- BAD -- database must read and discard 100,000 rows to get to page 5001
SELECT * FROM events ORDER BY created_at DESC LIMIT 20 OFFSET 100000;
-- Performance degrades linearly with page depth
```

```python
# BAD -- Django offset pagination on large table
from django.core.paginator import Paginator

paginator = Paginator(Event.objects.all(), 20)
page = paginator.page(5001)  # Internally: OFFSET 100000
```

| Page depth | Rows skipped | Typical latency |
|-----------|-------------|-----------------|
| Page 1 | 0 | ~1ms |
| Page 100 | 1,980 | ~5ms |
| Page 1,000 | 19,980 | ~50ms |
| Page 10,000 | 199,980 | ~500ms |
| Page 100,000 | 1,999,980 | ~5,000ms |

**When offset is acceptable:** Small datasets (<10,000 rows), admin/back-office UIs where deep pagination is rare, or when total count is needed.

### Cursor / Keyset Pagination

**How it works:** Use the last row's sort key as a starting point for the next page. The database can seek directly to the right position using an index.

**GOOD -- cursor pagination with consistent O(1) performance:**
```sql
-- GOOD -- uses index on (created_at, id) to seek directly
-- First page:
SELECT * FROM events
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Next page (pass last row's created_at and id as cursor):
SELECT * FROM events
WHERE (created_at, id) < ('2025-01-15T10:30:00', 12345)
ORDER BY created_at DESC, id DESC
LIMIT 20;
-- Performance is constant regardless of page depth
```

**GOOD -- Django cursor pagination with DRF:**
```python
# settings.py or view-level
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 20,
}

# views.py
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    pagination_class = CursorPagination
    ordering = "-created_at"
```

**GOOD -- Prisma cursor pagination:**
```typescript
// GOOD -- cursor-based pagination
const nextPage = await prisma.event.findMany({
    take: 20,
    skip: 1,            // Skip the cursor itself
    cursor: { id: lastEventId },
    orderBy: { createdAt: "desc" },
});
```

### Comparison

| Factor | Offset | Cursor/Keyset |
|--------|--------|---------------|
| Performance at depth | Degrades linearly | Constant O(1) |
| Jump to arbitrary page | Yes | No (forward/back only) |
| Total count available | Yes (extra query) | Not easily |
| Consistent with concurrent writes | No (rows can shift) | Yes (stable cursor) |
| Implementation complexity | Simple | Moderate |
| Best for | Small datasets, admin UIs | Feeds, timelines, APIs, large datasets |

---

## Query Optimization Patterns

### Covering Indexes for Read-Heavy Queries

Identify your most frequent read queries and ensure they can be served by index-only scans.

```sql
-- Frequent query:
SELECT status, COUNT(*) FROM orders
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY status;

-- Covering index:
CREATE INDEX idx_orders_created_status
    ON orders (created_at, status);
-- Index-only scan: no table heap access needed
```

### Materialized Views

Pre-compute expensive aggregations and refresh periodically.

```sql
-- Create materialized view for dashboard metrics
CREATE MATERIALIZED VIEW order_daily_stats AS
SELECT
    date_trunc('day', created_at) AS day,
    status,
    COUNT(*) AS order_count,
    SUM(total_cents) AS revenue_cents,
    AVG(total_cents) AS avg_order_cents
FROM orders
GROUP BY 1, 2;

-- Create index on the materialized view
CREATE UNIQUE INDEX idx_order_daily_stats
    ON order_daily_stats (day, status);

-- Refresh (can be scheduled via pg_cron or application):
REFRESH MATERIALIZED VIEW CONCURRENTLY order_daily_stats;
-- CONCURRENTLY allows reads during refresh (requires unique index)
```

**When to use materialized views:**
- Dashboard queries that aggregate large tables
- Reports that tolerate slightly stale data (minutes to hours)
- Queries that would otherwise require expensive JOINs or subqueries

**When NOT to use:**
- Data must be real-time (use application-level caching or live aggregation instead)
- Underlying data changes very frequently and freshness is critical

### Denormalization Trade-Offs

| Approach | Benefit | Cost | When to use |
|----------|---------|------|-------------|
| Counter cache column | Avoid COUNT(*) queries | Must update on every insert/delete | Frequently displayed counts (comment count, follower count) |
| Redundant column copy | Avoid JOIN for common lookups | Data inconsistency risk; must update in multiple places | Read-heavy display data (store customer_name on order) |
| JSON/JSONB column | Flexible schema, avoid joins for nested data | Harder to query, index, and enforce constraints | Configuration, metadata, audit trails |
| Precomputed aggregation table | Instant dashboard queries | Stale data; maintenance overhead | Analytics, reporting |

### Read Replicas

Route read queries to replicas to reduce load on the primary database.

**Django -- database router for read replicas:**
```python
class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return "replica"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
```

**Caution with read replicas:**
- Replication lag means replicas may return stale data
- Read-after-write consistency: after a write, immediately reading from a replica may return the old value
- Solution: read from primary for the current user's own data after a write; use replicas for other users' data

---

## Best Practices

- Profile before optimizing -- use EXPLAIN ANALYZE, query logs, and APM tools to find actual bottlenecks
- Add indexes based on real query patterns, not speculation
- Monitor query count per request to catch N+1 regressions (django-debug-toolbar, nplusone, bullet)
- Use batch operations for bulk data modifications -- never INSERT/UPDATE in a loop
- Choose cursor/keyset pagination for any API or feed with large datasets
- Size connection pools based on database capacity, not application demand
- Use connection pool health checks (pre-ping, test-on-borrow) to handle stale connections
- Run `ANALYZE` after bulk data loads to update query planner statistics
- Review slow query logs regularly and set appropriate thresholds (100ms is a common starting point)
- Consider pgBouncer or PgCat for PostgreSQL when application connection count exceeds database capacity

## Anti-Patterns

- Creating an index for every column "just in case" -- each index slows writes and consumes storage
- Using `SELECT *` when only specific columns are needed -- wastes I/O and network bandwidth
- Opening a new database connection per request without pooling -- connection setup costs 5-50ms each
- Using OFFSET pagination for public APIs or infinite scroll -- performance degrades with depth
- Holding transactions open during external API calls or user interactions -- causes lock contention
- Ignoring EXPLAIN output -- "it works" is not the same as "it is efficient"
- Using ORM lazy loading defaults without understanding the query pattern -- N+1 is the most common database performance problem
- Caching query results in the application without cache invalidation strategy -- serves stale data
- Running aggregate queries on the primary database during peak traffic -- use materialized views or read replicas
- Not monitoring connection pool utilization -- pool exhaustion causes request failures with no warning
