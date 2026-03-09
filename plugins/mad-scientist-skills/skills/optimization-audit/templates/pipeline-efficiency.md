# Data Pipeline Efficiency Reference

Optimization patterns for data pipelines covering batch/streaming trade-offs, incremental processing, storage format selection, partitioning, data skew mitigation, Spark/dbt tuning, vectorized operations, dead letter handling, and cost estimation.

## Purpose

Answer: "Are data pipelines processing data efficiently with appropriate batch/stream trade-offs, incremental strategies, and storage formats?"

## Checklist

Before auditing, identify:

- [ ] Pipeline orchestrator (Airflow, Dagster, Prefect, dbt Cloud, custom)
- [ ] Processing engine (Spark, Flink, dbt, Pandas, Polars, custom SQL)
- [ ] Storage layer (data warehouse, data lake, object storage, Delta Lake, Iceberg)
- [ ] Data volume and velocity (GB/day, events/sec, batch cadence)
- [ ] Latency requirements (real-time, near-real-time, daily, weekly)
- [ ] Current materialization strategy (full rebuild, incremental, append-only)
- [ ] Existing partitioning scheme (time, hash, range, none)
- [ ] Storage formats in use (CSV, JSON, Parquet, ORC, Delta, Iceberg)

---

## Batch vs Streaming Decision Matrix

| Criterion | Batch | Micro-Batch | Streaming |
|-----------|-------|-------------|-----------|
| **Latency tolerance** | Hours to daily | Minutes | Seconds to milliseconds |
| **Data volume** | Large (GB-TB per run) | Moderate (MB-GB per interval) | Continuous (events/sec) |
| **Processing complexity** | Complex multi-table joins, aggregations | Moderate transformations | Simple transforms, enrichment |
| **Error handling** | Replay entire batch | Replay interval | Per-record retry, DLQ |
| **Cost profile** | Predictable, scheduled | Moderate, interval-based | Always-on infrastructure |
| **State management** | Stateless or checkpoint-based | Windowed state | Continuous state (Flink, Kafka Streams) |
| **Infrastructure** | Spark, dbt, Airflow | Spark Structured Streaming, dbt | Flink, Kafka Streams, Kinesis |
| **When to use** | Nightly analytics, ML training, reporting | Dashboard refresh every 5-15 min | Fraud detection, alerting, live feeds |

### Decision Flowchart

```
1. Sub-minute latency required?  YES → Streaming (Flink, Kafka Streams)
2. Sub-hour latency required?    YES → Micro-batch (Spark Structured Streaming)
3. Data volume > 100GB per run?  YES → Batch with distributed engine (Spark)
4. Otherwise                          → Batch with single-node (dbt, Pandas, SQL)
```

**BAD** — streaming infrastructure for a daily dashboard:

```python
# Over-engineered: Kafka + Flink for data consumed once per day
env = StreamExecutionEnvironment.get_execution_environment()
kafka_source = KafkaSource.builder().set_topics("orders").build()
# 24/7 infrastructure for daily consumption — wasteful
```

**GOOD** — scheduled batch for daily analytics:

```python
# Right-sized: daily dbt run triggered by Airflow at 06:00 UTC
# Cost: a few minutes of compute per day instead of 24/7 streaming
```

---

## Incremental Processing

### dbt Incremental Models

**BAD** — full table rebuild every run:

```sql
{{ config(materialized='table') }}
SELECT order_id, customer_id, amount, created_at
FROM {{ ref('stg_orders') }}
```

**GOOD** — incremental with `is_incremental()` guard:

```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

SELECT order_id, customer_id, amount, created_at
FROM {{ ref('stg_orders') }}
{% if is_incremental() %}
WHERE created_at > (SELECT MAX(created_at) FROM {{ this }})
{% endif %}
```

### Delta Lake MERGE (Upsert)

**BAD** — overwrite entire table for upserts:

```python
new_data.write.format("delta").mode("overwrite").save("/data/orders")
```

**GOOD** — MERGE for efficient upsert:

```python
from delta.tables import DeltaTable

target = DeltaTable.forPath(spark, "/data/orders")
target.alias("t").merge(
    new_data.alias("s"), "t.order_id = s.order_id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

### Append-Only with Watermarks

```sql
-- Track last processed timestamp to avoid scanning historical data
INSERT INTO events_processed
SELECT * FROM raw_events
WHERE event_time > (
    SELECT COALESCE(MAX(event_time), '1970-01-01') FROM events_processed
)
```

### When Full Rebuild Is Correct

| Scenario | Rationale |
|----------|-----------|
| Schema migration | Column types changed, new columns backfilled |
| Business logic change | Historical records need recomputation |
| Data correction | Source data was retroactively fixed |
| Small tables (<1GB) | Incremental overhead exceeds rebuild cost |

Use `dbt run --full-refresh -s model_name` for targeted rebuilds.

---

## Storage Format Selection

| Format | Type | Compression | Predicate Pushdown | Column Pruning | ACID | Best For |
|--------|------|-------------|--------------------|--------------------|------|----------|
| CSV | Row | None (unless gzipped) | No | No | No | Human-readable exchange, small datasets |
| JSON/NDJSON | Row | Moderate (gzip) | No | No | No | Semi-structured data, API payloads |
| Parquet | Columnar | Excellent (Snappy, ZSTD) | Yes | Yes | No | Analytical queries, data lakes |
| ORC | Columnar | Excellent (ZLIB, Snappy) | Yes | Yes | No | Hive ecosystem |
| Delta Lake | Columnar (Parquet) | Excellent | Yes | Yes | Yes | ACID on lakes, time travel, CDC |
| Iceberg | Columnar (Parquet/ORC) | Excellent | Yes | Yes | Yes | Multi-engine lakes, hidden partitioning |

### Migration: CSV to Parquet

**BAD** — CSV for analytics:

```python
df = pd.read_csv("data/orders.csv")
# or: spark.read.csv("s3://bucket/orders/*.csv", header=True, inferSchema=True)
```

**GOOD** — Parquet for analytics:

```python
df = pd.read_parquet("data/orders.parquet", columns=["order_id", "amount"])
# or: spark.read.parquet("s3://bucket/orders/")
```

**Migration script:**

```python
# One-time: convert CSV to Parquet
df = pd.read_csv("data/orders.csv")
df.to_parquet("data/orders.parquet", engine="pyarrow", compression="snappy")

# For large files: chunked conversion
for chunk in pd.read_csv("data/large.csv", chunksize=500_000):
    chunk.to_parquet(f"data/orders/part-{chunk.index[0]}.parquet", compression="snappy")
```

---

## Partitioning Strategy

| Type | Use Case | Example | Advantages |
|------|----------|---------|------------|
| Time-based | Event data, logs, transactions | `year=2025/month=01/day=15/` | Natural pruning for time-range queries |
| Hash-based | Evenly distributed access | `hash(user_id) % 256` | Even distribution, good for joins |
| Range-based | Ordered data with range queries | `amount_bucket=0-100/100-1000/` | Range scan efficiency |
| Composite | Multi-dimensional queries | `region=us/year=2025/month=01/` | Multiple pruning dimensions |

### Partition Pruning

**BAD** — query scans all partitions:

```sql
SELECT SUM(amount) FROM orders WHERE status = 'completed'
```

**GOOD** — partition filter enables pruning:

```sql
SELECT SUM(amount) FROM orders
WHERE order_date BETWEEN '2025-01-01' AND '2025-01-31'
  AND status = 'completed'
```

### Optimal File Sizes

| File Size | Assessment |
|-----------|------------|
| < 10 MB | Too small — excessive metadata overhead, slow listing |
| 10-128 MB | Acceptable for moderate workloads |
| **128 MB - 1 GB** | **Optimal for Parquet** |
| > 1 GB | Too large — limits parallelism, OOM risk |

### Over-Partitioning vs Under-Partitioning

```
# BAD: over-partitioned (thousands of tiny files)
s3://bucket/events/year=2025/month=01/day=15/hour=00/minute=00/  (<1MB)

# BAD: under-partitioned (single massive file)
s3://bucket/events/part-00000.parquet  (50GB)

# GOOD: right-sized (daily partitions, 128MB-1GB files)
s3://bucket/events/date=2025-01-15/part-00000.parquet  (256MB)
```

### File Compaction

```python
# Delta Lake: OPTIMIZE compacts small files
spark.sql("OPTIMIZE delta.`s3://bucket/events/`")
# With Z-ORDER for multi-column query patterns
spark.sql("OPTIMIZE delta.`s3://bucket/events/` ZORDER BY (customer_id)")
```

---

## Data Skew Detection and Mitigation

### Detection

```python
from pyspark.sql import functions as F

partition_sizes = df.groupBy("partition_key").agg(F.count("*").alias("row_count"))
stats = partition_sizes.agg(
    F.max("row_count").alias("max_count"),
    F.expr("percentile_approx(row_count, 0.5)").alias("median_count"),
).collect()[0]
skew_ratio = stats["max_count"] / stats["median_count"]
print(f"Skew ratio: {skew_ratio:.1f}x (target: <3x)")
```

### Mitigation: Salting

**BAD** — join on skewed key directly:

```python
# customer_id="BIGCORP" has 10M rows, others have <1K — one task dominates
result = orders.join(customers, "customer_id")
```

**GOOD** — salt the skewed key:

```python
NUM_SALT_BUCKETS = 10
orders_salted = orders.withColumn("salt", (F.rand() * NUM_SALT_BUCKETS).cast("int"))
customers_exploded = customers.withColumn(
    "salt", F.explode(F.array([F.lit(i) for i in range(NUM_SALT_BUCKETS)]))
)
result = orders_salted.join(
    customers_exploded,
    (orders_salted.customer_id == customers_exploded.customer_id)
    & (orders_salted.salt == customers_exploded.salt),
)
```

### Mitigation: Broadcast Join for Small Tables

**BAD** — shuffle join when one side is small:

```python
result = orders.join(products, "product_id")  # default: sort-merge join with shuffle
```

**GOOD** — broadcast the small table:

```python
from pyspark.sql.functions import broadcast
result = orders.join(broadcast(products), "product_id")  # no shuffle
```

```python
# Increase broadcast threshold (default 10MB) for tables up to ~500MB
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100m")
```

### Adaptive Query Execution (AQE)

```python
# Enable AQE (default in Spark 3.2+) — free runtime optimization
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionFactor", "5")
spark.conf.set("spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes", "256m")
```

---

## Spark/PySpark Optimization

### reduceByKey vs groupByKey

**BAD** — `groupByKey` shuffles all values to the reducer:

```python
totals = rdd.groupByKey().mapValues(sum)  # all values shipped across network
```

**GOOD** — `reduceByKey` combines locally before shuffling:

```python
totals = rdd.reduceByKey(lambda a, b: a + b)  # local combine, then shuffle
```

### Avoid collect() and toPandas() on Large Datasets

**BAD** — pulling distributed data to driver:

```python
all_rows = df.collect()         # OOM: entire DataFrame to driver
pdf = spark_df.toPandas()       # OOM: entire DataFrame to driver as Pandas
```

**GOOD** — process distributed or convert only aggregated results:

```python
df.foreachPartition(process_partition)                  # distributed processing
sample = df.limit(100).collect()                        # bounded sample
result = spark_df.groupBy("cat").agg(F.sum("amt")).toPandas()  # small result only
```

### Partition Tuning

```python
# Rule of thumb: 128MB per partition, 2-4 partitions per core
# Repartition (triggers shuffle — use when increasing partitions)
df = df.repartition(400, "date")
# Coalesce (no shuffle — use when decreasing partitions)
df = df.coalesce(100)
```

### Persist/Cache Strategy

```python
from pyspark import StorageLevel

df_filtered = df.filter(F.col("status") == "active")
df_filtered.persist(StorageLevel.MEMORY_AND_DISK)  # cache for reuse

count = df_filtered.count()
summary = df_filtered.groupBy("category").count()

df_filtered.unpersist()  # free resources when done
```

| Storage Level | When to Use |
|---------------|-------------|
| `MEMORY_ONLY` | Data fits in memory, recompute is expensive |
| `MEMORY_AND_DISK` | Default — spills to disk if memory insufficient |
| `DISK_ONLY` | Large datasets, recomputation is very expensive |
| `MEMORY_ONLY_SER` | Memory-constrained, trades CPU for space |

---

## dbt Optimization

### Materialization Strategy

| Materialization | Build Time | Query Time | Storage | When to Use |
|-----------------|-----------|------------|---------|-------------|
| `view` | Instant | Slow (recomputes) | None | Light transforms, queried by downstream models |
| `ephemeral` | None (CTE) | N/A | None | Reusable logic, never queried directly |
| `table` | Slow (full rebuild) | Fast | Full copy | Small tables, infrequent changes |
| `incremental` | Fast (delta only) | Fast | Full copy | Large tables, append/update pattern |

```
Decision: Is the model queried by BI tools?
  NO  → view or ephemeral
  YES → Is source data > 1M rows?
    NO  → table
    YES → Can you identify new/changed rows? YES → incremental, NO → table
```

### run_results.json Parsing for Execution Time Analysis

```python
import json
from pathlib import Path

def analyze_dbt_performance(path="target/run_results.json"):
    """Parse dbt run results to find slow models and optimization targets."""
    data = json.loads(Path(path).read_text())
    models = []
    for r in data["results"]:
        node = r["unique_id"]
        if not node.startswith("model."):
            continue
        elapsed = r.get("execution_time", 0)
        rows = r.get("adapter_response", {}).get("rows_affected", "unknown")
        mat = "unknown"
        if "node" in r and "config" in r["node"]:
            mat = r["node"]["config"].get("materialized", "unknown")
        models.append({"model": node.split(".")[-1], "seconds": round(elapsed, 2),
                        "rows": rows, "materialization": mat, "status": r["status"]})

    models.sort(key=lambda x: x["seconds"], reverse=True)
    total_time = sum(m["seconds"] for m in models)
    print(f"Total build time: {total_time:.0f}s ({total_time / 60:.1f} min)")
    for m in models[:10]:
        pct = (m["seconds"] / total_time * 100) if total_time > 0 else 0
        print(f"  {m['model']}: {m['seconds']}s ({pct:.1f}%) [{m['materialization']}]")

    # Flag table models > 60s as incremental candidates
    for m in models:
        if m["materialization"] == "table" and m["seconds"] > 60:
            print(f"  Candidate for incremental: {m['model']} ({m['seconds']}s)")
    return models
```

### Model Selection for Partial Runs

```bash
dbt run --select state:modified+    # modified models + downstream
dbt run --select +fct_orders        # model + upstream dependencies
dbt run --select tag:critical       # tagged subset
dbt run --exclude tag:slow          # skip expensive models for iteration
```

---

## Vectorized Operations

### Pandas: apply() vs Vectorized

**BAD** — row-by-row processing:

```python
def categorize(row):
    if row["amount"] > 1000: return "high"
    elif row["amount"] > 100: return "medium"
    else: return "low"

df["category"] = df.apply(categorize, axis=1)  # ~100x slower than vectorized
```

**GOOD** — vectorized with `np.select`:

```python
import numpy as np
conditions = [df["amount"] > 1000, df["amount"] > 100]
choices = ["high", "medium"]
df["category"] = np.select(conditions, choices, default="low")
```

### Pandas: iterrows() vs groupby

**BAD** — Python-level iteration:

```python
totals = {}
for _, row in df.iterrows():
    totals[row["customer_id"]] = totals.get(row["customer_id"], 0) + row["amount"]
```

**GOOD** — vectorized aggregation:

```python
totals = df.groupby("customer_id")["amount"].sum()
```

### NumPy Broadcasting vs Python Loops

**BAD** — nested Python loops:

```python
distances = [[math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
              for p2 in points] for p1 in points]
```

**GOOD** — NumPy broadcasting:

```python
pts = np.array(points)
diff = pts[:, np.newaxis, :] - pts[np.newaxis, :, :]
distances = np.sqrt(np.sum(diff ** 2, axis=2))
```

### String Operations

**BAD** — `apply` for string manipulation:

```python
df["clean"] = df["name"].apply(lambda x: x.strip().lower().replace(" ", "_"))
```

**GOOD** — vectorized string methods:

```python
df["clean"] = df["name"].str.strip().str.lower().str.replace(" ", "_", regex=False)
```

---

## Dead Letter Patterns

Quarantine failed records instead of silently dropping them or halting the pipeline.

### Dead Letter Table Schema

```sql
CREATE TABLE pipeline_dead_letters (
    dl_id           BIGINT GENERATED ALWAYS AS IDENTITY,
    pipeline_name   TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    source_record_id TEXT,
    error_category  TEXT NOT NULL,  -- 'validation', 'transformation', 'load'
    error_reason    TEXT NOT NULL,
    failed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_payload     JSONB,
    retry_count     INT DEFAULT 0,
    reprocessed     BOOLEAN DEFAULT FALSE
);
```

### Retry with Exponential Backoff

```python
import time, random

def process_with_retry(record, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries + 1):
        try:
            return transform(record)
        except TransientError as e:
            if attempt == max_retries:
                send_to_dead_letter(record, error=str(e), retry_count=attempt)
                return None
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 1))
        except ValidationError as e:
            send_to_dead_letter(record, error=str(e), retry_count=0)
            return None
```

### DLQ Monitoring

```sql
-- Alert if dead letter rate > 5% over last hour
SELECT pipeline_name, COUNT(*) AS dl_count,
    COUNT(*)::FLOAT / NULLIF(
        (SELECT COUNT(*) FROM pipeline_run_stats
         WHERE run_start > NOW() - INTERVAL '1 hour'
         AND pipeline_name = dl.pipeline_name), 0) AS dl_rate
FROM pipeline_dead_letters dl
WHERE failed_at > NOW() - INTERVAL '1 hour'
GROUP BY pipeline_name
ORDER BY dl_rate DESC;
```

### Reprocessing Strategy

| Strategy | When to Use | Implementation |
|----------|-------------|----------------|
| Automated retry | Transient errors (timeouts, rate limits) | Scheduled job retries where `retry_count < max` |
| Manual review | Validation errors, data quality issues | Dashboard for reviewing failed records |
| Bulk replay | Source correction, schema fix | Re-extract from source, mark originals superseded |
| Discard with audit | Known bad data (test records, spam) | Mark `reprocessed = TRUE` with reason |

---

## Pipeline Cost Estimation

### Per-Run Cost Calculation

```python
def estimate_pipeline_cost(run_metadata: dict) -> dict:
    """Estimate cost of a single pipeline run."""
    compute_hours = run_metadata["duration_seconds"] / 3600
    compute_cost = (compute_hours * run_metadata.get("instance_cost_per_hour", 0.50)
                    * run_metadata.get("num_instances", 1))

    gb_read = run_metadata.get("bytes_read", 0) / (1024 ** 3)
    gb_written = run_metadata.get("bytes_written", 0) / (1024 ** 3)
    storage_cost = gb_read * 0.01 + gb_written * 0.05  # approximate S3 GET/PUT

    wh_seconds = run_metadata.get("warehouse_seconds", 0)
    wh_cost = (wh_seconds / 3600) * run_metadata.get("warehouse_cost_per_hour", 2.00)

    total = compute_cost + storage_cost + wh_cost
    return {"compute": round(compute_cost, 4), "storage": round(storage_cost, 4),
            "warehouse": round(wh_cost, 4), "total": round(total, 4),
            "cost_per_gb": round(total / max(gb_read, 0.001), 4)}
```

### Resource Utilization Metrics

| Metric | Source | Action Threshold |
|--------|--------|------------------|
| CPU utilization | Spark UI, CloudWatch | <20% over-provisioned, >80% under-provisioned |
| Memory utilization | Spark UI, executor logs | >85% OOM risk |
| Shuffle bytes | Spark UI | Growing faster than data volume |
| Spill to disk | Spark UI | Any spill — increase memory or partitions |
| Duration trend | run_results.json, orchestrator | >2x median of last 14 runs |
| Cost per run | Cost allocation tags | >20% increase without volume growth |

### Cost Optimization Quick Wins

| Action | Typical Savings | Effort |
|--------|----------------|--------|
| Switch CSV to Parquet | 50-90% storage, 5-20x faster reads | Low |
| Add partition pruning | 50-99% less data scanned | Low |
| Convert table to incremental | 80-99% less compute per run | Medium |
| Right-size Spark executors | 20-50% compute cost | Low |
| Use spot instances for batch | 60-90% compute cost | Medium |
| Enable compression (Snappy/ZSTD) | 50-80% storage cost | Low |
| Compact small files | 2-5x faster reads | Low |

---

## Anti-Patterns

| Anti-Pattern | Impact | Fix |
|--------------|--------|-----|
| Full rebuild when incremental is possible | Wasted compute | `incremental` materialization with guards |
| CSV/JSON for analytical workloads | Slow reads, no pushdown | Migrate to Parquet or Delta Lake |
| `groupByKey()` in Spark | Excessive shuffle, OOM | `reduceByKey()` or DataFrame aggregations |
| `collect()` / `toPandas()` on large data | Driver OOM | Distributed ops or aggregate first |
| `df.apply(func, axis=1)` | 100x slower than vectorized | `np.select`, vectorized Pandas methods |
| Over-partitioned data (tiny files) | Slow listing, high overhead | Compact files, reduce granularity |
| No dead letter handling | Silent data loss | Quarantine failed records with metadata |
| Skewed joins without mitigation | Straggler tasks dominate | Salt keys or broadcast joins |

## Best Practices

- Measure before optimizing — use `run_results.json`, Spark UI, or execution logs to find bottlenecks
- Start with storage format and partitioning — largest gains with least code change
- Make incremental the default for large tables — full rebuilds need explicit justification
- Set file size targets at 128MB-1GB for Parquet — compact small files regularly
- Use broadcast joins when one side is small (<500MB) — eliminates shuffle entirely
- Enable AQE in Spark 3.x — free runtime optimization
- Track dead letter rates as a pipeline health signal — alert when rate exceeds 5%
- Vectorize all DataFrame operations — avoid `apply(axis=1)`, `iterrows()`, Python loops
- Estimate pipeline cost per run — make cost visible to drive optimization decisions
- Use model selection (`dbt run --select`) for iteration — avoid running the full DAG
