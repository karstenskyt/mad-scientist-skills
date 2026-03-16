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

### Ingestion Skip Guards (No-Op Efficiency)

Ingestion pipelines are often written for correctness (idempotent `replaceWhere`) but miss the efficiency half: checking whether data already exists before doing expensive fetch/parse/write work. On scheduled runs, this turns every no-op into a full re-ingest.

**The problem:** An ingestion pipeline with 5 data sources × 60 partitions each might execute ~300 HTTP requests, ~300 `df.count()` calls, and ~300 Delta writes on every scheduled run — even when nothing has changed. At 1-3 seconds per Delta write on serverless, that's 5-15 minutes of pure overhead.

**BAD** — unconditional fetch and write on every run:

```python
# Downloads and overwrites every partition, every run, regardless of what exists
for match_id in all_match_ids:
    data = fetch_match_data(match_id)  # HTTP request every time
    df = spark.createDataFrame(data)
    row_count = validate_dataframe(df, required_cols, "source")  # df.count() every time
    write_delta_table(df, catalog, schema, table_name,
                      replace_where=f"match_id = '{match_id}'",
                      row_count=row_count)  # Delta write every time
```

**GOOD** — skip guard checks existing partitions first:

```python
# Check what already exists — one Spark job, regardless of source count
full_table = f"{catalog}.{schema}.{table_name}"
existing: set[str] = set()
if spark.catalog.tableExists(full_table):
    existing = {
        str(row["match_id"])
        for row in spark.table(full_table)
        .select("match_id").distinct().collect()
    }
new_ids = [mid for mid in all_match_ids if str(mid) not in existing]
if not new_ids:
    logger.info("All %d partitions already ingested — skipping", len(existing))
    return

# Only fetch and write new data
for match_id in new_ids:
    data = fetch_match_data(match_id)
    df = spark.createDataFrame(data)
    row_count = validate_dataframe(df, required_cols, "source")
    write_delta_table(df, catalog, schema, table_name,
                      replace_where=f"match_id = '{match_id}'",
                      row_count=row_count)
```

**Key implementation notes:**

- Use `str()` normalization when comparing keys — Spark may return `int` while Delta stores `string`
- The existence check is one Spark job with minimal overhead (~2-5 seconds) vs. minutes of wasted work
- The skip guard is compatible with `replaceWhere` idempotency — new data is still overwritten correctly
- For metadata tables (competitions, teams) that are small and change rarely, a hash comparison or row count check can skip the overwrite

**Common variations:**

| Source Type | Skip Guard Strategy |
|-------------|-------------------|
| Per-match data (events, tracking) | Check `match_id` against existing partition keys |
| Per-competition data (season tables) | Check `competition_id` or `(competition_id, season_id)` |
| Immutable reference data (players, teams) | Row count comparison or content hash |
| External file downloads (GitHub, S3) | Cache to local/cloud storage on first download; check file existence before re-downloading |

**Audit checklist for each ingestion module:**

- [ ] Does `main()` query the target table before entering the fetch loop?
- [ ] Does it short-circuit (return early) when all partitions exist?
- [ ] Are metadata table writes (competitions, matches lists) also guarded?
- [ ] Are HTTP downloads cached for immutable sources?
- [ ] How many operations execute on a no-op run? (Target: <5 seconds)

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

## Distributed Execution: `applyInPandas` / `mapInPandas`

When Python libraries (NumPy, scikit-learn, XGBoost, custom analytics) must be used for computation, the critical question is **where** that computation runs — on the driver node or distributed across executors.

### The Driver-Bound Anti-Pattern

The most common anti-pattern in PySpark analytics pipelines: pulling distributed data to the driver via `.toPandas()`, processing it with Python/Pandas, then pushing results back via `spark.createDataFrame()`. This means executors sit idle while the driver does all the work, and the entire dataset must fit in driver memory.

**BAD** — sequential chunk-and-release on the driver:

```python
import gc

# All computation on the 16 GB driver — executors idle
matches = spark.sql("SELECT DISTINCT match_id FROM tracking").toPandas()
results = []
for _, row in matches.iterrows():
    match_id = row["match_id"]
    match_df = spark.sql(f"SELECT * FROM tracking WHERE match_id = '{match_id}'").toPandas()
    result = compute_analytics(match_df)  # CPU-bound on driver
    results.append(result)
    del match_df; gc.collect()  # Release memory for next chunk

output_df = spark.createDataFrame(pd.concat(results))
output_df.write.format("delta").mode("overwrite").save(output_path)
```

**GOOD** — distributed via `applyInPandas`:

```python
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

result_schema = StructType([
    StructField("match_id", StringType()),
    StructField("player_id", StringType()),
    StructField("metric_value", DoubleType()),
])

def compute_analytics_udf(match_df: pd.DataFrame) -> pd.DataFrame:
    """Runs on executor — never touches driver memory."""
    return compute_analytics(match_df)

# Spark distributes groups across executors automatically
result = (
    spark.table("tracking")
    .groupBy("match_id")
    .applyInPandas(compute_analytics_udf, schema=result_schema)
)
result.write.format("delta").mode("overwrite").save(output_path)
```

### When to Use Each Pattern

| Pattern | When to Use | Key Constraint |
|---------|-------------|----------------|
| `applyInPandas` | Group-by computation where each group is independent | Each materialized group must fit in executor memory |
| `mapInPandas` | Row-level or partition-level transforms (no grouping needed) | Iterator-based, lower memory footprint |
| `.toPandas()` on driver | Small result sets (<5M rows), global operations that cannot be partitioned | Driver memory ceiling |

### Group Key Selection

The group key determines parallelism AND memory usage. Finer keys = more parallelism + smaller groups, but check correctness.

| Scenario | Naive Key | Better Key | Why |
|----------|-----------|------------|-----|
| Per-match computation, decomposable across sub-groups | `match_id` | `(match_id, period)` or `(match_id, frame_batch)` | More parallel groups, smaller memory per group |
| Per-match computation, requires full match context | `match_id` | `match_id` | Cannot decompose — correctness requires all frames |
| Per-competition aggregation | `competition_id` | `competition_id` | Large groups but unavoidable for cross-match computation |

**Formal decomposability test — all three criteria must hold:**

1. **Independent**: The loop body for each group/iteration is independent — no cross-group state, no ordering dependency, no shared mutable accumulator
2. **Aggregation result**: The final result is an aggregation (sum, count, mean, max) over per-group outputs
3. **Associative + commutative**: Partial results can be combined in any order — `sum(batch_1) + sum(batch_2) == sum(all)`

If all three hold, the computation can be split into finer groups (e.g., `(match_id, period)` or `(match_id, frame_batch_id)`) with `applyInPandas`, and the final aggregation done via Spark-native `groupBy().agg()`.

```python
# DECOMPOSABLE: per-player xT is sum of per-frame xT — split into frame batches
# 1. Fine-grained applyInPandas by (match_id, frame_batch_id)
# 2. Spark groupBy("player_id").agg(sum("off_ball_xt")) across all batches

# NOT DECOMPOSABLE: entity resolution requires global TF-IDF matrix
# Must stay on driver or use a single large executor
```

### Synthetic Partition Keys

When natural sub-groups don't exist or are too coarse, create synthetic partition keys for uniform distribution:

```python
from pyspark.sql import functions as F

# Time-based batching: split long time series into fixed-size batches
batch_size = 270  # ~270 sampled frames per batch (5 min of play at 1fps)
tracking_sdf = tracking_sdf.withColumn(
    "frame_batch_id",
    (F.col("frame") / (frame_rate * batch_size)).cast("int")
)
# Group by (match_id, frame_batch_id) — creates ~20 groups per match

# Row-based batching: split a flat collection into uniform chunks
num_batches = 90  # target ~100 items per batch
player_sdf = player_sdf.withColumn(
    "batch_id", (F.monotonically_increasing_id() % num_batches).cast("int")
)
# Group by batch_id — creates ~90 uniform groups
```

**Sizing formula:** Each materialized group must fit in executor memory. Estimate:

```
group_bytes = (n_rows_per_group × n_cols × 8 bytes_per_float64)
```

Target: `group_bytes < 800 MB` (leaving headroom below the 1 GB UDF limit on serverless).

| Group too large? | Fix |
|-----------------|-----|
| Yes (>800 MB) | Create finer synthetic key (`frame_batch_id`, `row_batch_id`) |
| No (<10 MB) | Consider coarser key to reduce group count and overhead |

### Non-Distributable Computation

Not everything can or should be migrated to `applyInPandas`. Document these explicitly to avoid wasted refactoring effort:

| Criteria | Example | Why it can't distribute |
|----------|---------|------------------------|
| **Global cross-group state** | TF-IDF vectorization, global normalization, cross-source entity resolution | Requires the full dataset to compute global statistics (IDF weights, z-scores) |
| **Full-corpus training** | ML model training that needs representative samples from all groups | Partitioned training produces biased models; each group has too few samples |
| **Ordering-sensitive across groups** | Time-series analysis requiring cross-match temporal ordering | Results depend on relative position across the full dataset |
| **Small bounded operations** | Metadata queries, config loading, 100-row seed tables | Overhead of distribution exceeds the computation cost |

When you identify a non-distributable pipeline, document **why** it stays on the driver. This prevents future audits from re-flagging it.

### Multi-Pass Distributed Architecture

When a pipeline has stages with different grouping requirements, chain multiple `applyInPandas` calls with progressively coarser grouping:

**BAD** — single-pass forces the coarsest group key for all stages:

```python
# Everything grouped by match_id, even though credit assignment is per-period
results = (
    joined_sdf
    .groupBy("match_id")
    .applyInPandas(do_everything, schema=output_schema)
)
```

**GOOD** — two-pass with appropriate granularity per stage:

```python
# Pass 1: Credit assignment — independent per period (finer grouping = more parallelism)
credits_sdf = (
    joined_sdf
    .groupBy("match_id", "period")
    .applyInPandas(assign_credits_period, schema=credits_schema)
)

# Pass 2: Value estimation — needs all credits from match (coarser grouping)
valued_sdf = (
    credits_sdf
    .groupBy("match_id")
    .applyInPandas(estimate_values_match, schema=valued_schema)
)
```

**When to use multi-pass:** When an earlier stage is embarrassingly parallel at fine granularity (per-event, per-frame, per-period) but a later stage requires coarser context (per-match, per-competition). The fine-grained pass does the expensive work; the coarse pass does cheap aggregation or model scoring.

### Model Loading on Executors

When UDFs need ML models or large lookup tables, load once per executor process, not once per group.

**BAD** — loads model every time the UDF is called:

```python
def predict_udf(group_df: pd.DataFrame) -> pd.DataFrame:
    model = load_model("/path/to/model")  # Loaded for every group!
    return group_df.assign(prediction=model.predict(group_df))
```

**GOOD** — module-level cache reused across groups on the same executor:

```python
_model_cache: dict[str, object] = {}

def predict_udf(group_df: pd.DataFrame) -> pd.DataFrame:
    if "model" not in _model_cache:
        _model_cache["model"] = load_model("/dbfs/path/to/model")
    model = _model_cache["model"]
    return group_df.assign(prediction=model.predict(group_df))
```

**Why this works:** Spark reuses Python worker processes across groups on the same executor. The module-level dict persists for the lifetime of the worker process, so the model is loaded once per executor, not once per group. On serverless environments without broadcast variables, this is the standard pattern for sharing large objects across UDF invocations.

**What to cache:** ML models (XGBoost, Doc2Vec, scikit-learn), lookup tables, pre-computed indices. Load from shared storage (UC Volumes, S3, GCS) inside the UDF body — not from driver memory, which is inaccessible on executors.

**What NOT to cache:** Per-group data (defeats the purpose of groupBy), mutable state that should reset per group, connections to external services (not available on serverless executors).

### Serverless Compute Constraints

When targeting Databricks Serverless (or similar managed Spark environments), be aware of hard limits:

| Constraint | Limit | Impact |
|------------|-------|--------|
| Driver memory | 16 GB (fixed) | Caps `.toPandas()` data volume |
| Per-UDF executor memory | 1 GB | Each `applyInPandas` group must stay under ~800 MB |
| `df.cache()` / `df.persist()` | Not supported | Cannot cache intermediate results |
| Broadcast variables | Not supported | Close over small objects or load from storage |
| Internet access in UDFs | Not available | Models must be pre-staged to cloud storage / UC Volume |
| Spark config | Only 6 `spark.sql.*` params | Cannot tune executor count, memory, or instance type |

### Estimating Group Sizes

Before migrating to `applyInPandas`, estimate the in-memory size of the largest group:

```python
# Quick estimate: sample one group, measure pandas memory
sample_group = spark.sql("""
    SELECT * FROM tracking WHERE match_id = (
        SELECT match_id FROM tracking GROUP BY match_id ORDER BY COUNT(*) DESC LIMIT 1
    )
""").toPandas()
print(f"Largest group: {sample_group.memory_usage(deep=True).sum() / 1e6:.0f} MB")
# If > 800 MB: split into sub-groups or use mapInPandas with iterator
```

---

## Redundant Computation in Loop Bodies

When a function is called N times in a loop, look for setup work repeated identically across calls. This is distinct from algorithmic complexity — the function itself may be O(n), but calling it N times with redundant setup is O(N × setup_cost + N × n).

### Pattern: Shared Setup Across Function Calls

**BAD** — function called per-player repeats team split for every player:

```python
# compute_metric() splits DataFrame into home/away on every call
for i in range(len(players_df)):
    x, y = players_df.iloc[i]["x"], players_df.iloc[i]["y"]
    metric = compute_metric(players_df, x, y)  # Re-splits home/away inside!
    results.append(metric)
```

**GOOD** — hoist shared setup, pass batch of inputs:

```python
# Split once, pass all points at once
home_mask = players_df["team"] == "home"
home_df = players_df[home_mask]
away_df = players_df[~home_mask]

# Batch version accepts (n, 2) array of points
all_points = np.column_stack([players_df["x"].values, players_df["y"].values])
metrics = compute_metric_batch(home_df, away_df, all_points)
```

### Pattern: Cache-Eligible Repeated Computation

When iterations share identical input data for an expensive sub-computation, cache by input hash.

**BAD** — Ward clustering recomputed per pass, identical for passes in same frame:

```python
for _, pass_row in passes_df.iterrows():
    frame_defenders = get_defenders_at_frame(pass_row["frame"])
    clusters = ward_clustering(frame_defenders)  # Identical for same frame!
    is_line_breaking = check_line_breaking(pass_row, clusters)
```

**GOOD** — cache by frame:

```python
cluster_cache: dict[int, np.ndarray] = {}
for _, pass_row in passes_df.iterrows():
    frame = pass_row["frame"]
    if frame not in cluster_cache:
        frame_defenders = get_defenders_at_frame(frame)
        cluster_cache[frame] = ward_clustering(frame_defenders)
    is_line_breaking = check_line_breaking(pass_row, cluster_cache[frame])
```

### Identification Checklist

When reviewing a loop that calls a function N times:

1. **Does the function accept the same DataFrame/collection on every call?** → The function likely re-derives subsets (home/away split, team filter, position extraction) on every invocation. Hoist the derivation.
2. **Does the function accept scalar arguments (x, y, timestamp) drawn from a DataFrame?** → The function may have a batch-compatible inner implementation. Pass all scalars at once as an array.
3. **Does the function perform expensive sub-computation (clustering, matrix factorization, model loading) that depends on a subset of its inputs?** → Cache by the subset that determines the expensive result.
4. **Is the final result an aggregation over per-iteration outputs?** → The loop may be map-reduce decomposable — parallelize with `applyInPandas` + Spark aggregation.
5. **Does the inner function's core computation already support batch inputs that the wrapper doesn't expose?** → Look past the function's public signature at its internal math. If the core uses matrix operations, NumPy broadcasting, or numerical integration that naturally handles arrays, the batch version may only need to hoist setup and pass stacked inputs (e.g., `(n, 2)` array instead of scalar `(x, y)` pair). This is the highest-ROI optimization when found — often 10-20x with minimal code change.

---

## Anti-Patterns

| Anti-Pattern | Impact | Fix |
|--------------|--------|-----|
| Full rebuild when incremental is possible | Wasted compute | `incremental` materialization with guards |
| CSV/JSON for analytical workloads | Slow reads, no pushdown | Migrate to Parquet or Delta Lake |
| `groupByKey()` in Spark | Excessive shuffle, OOM | `reduceByKey()` or DataFrame aggregations |
| `collect()` / `toPandas()` on large data | Driver OOM | Distributed ops or aggregate first |
| Driver-bound analytics loop | Executors idle, sequential | `applyInPandas` / `mapInPandas` with natural group key |
| `df.apply(func, axis=1)` | 100x slower than vectorized | `np.select`, vectorized Pandas methods |
| Over-partitioned data (tiny files) | Slow listing, high overhead | Compact files, reduce granularity |
| No dead letter handling | Silent data loss | Quarantine failed records with metadata |
| Skewed joins without mitigation | Straggler tasks dominate | Salt keys or broadcast joins |
| Redundant setup in per-item function call | N × setup_cost wasted | Hoist shared setup, batch inputs, or cache |
| Ingestion no-op waste | Minutes to hours of wasted compute, network, and Delta I/O on every scheduled run | Add skip guard: query target table for existing partitions, short-circuit when nothing is new |
| Unconditional source download | Network I/O for data already in Delta | Check target partition exists before downloading source |
| Multi-pass file parsing | 2x I/O for same file | Merge extraction into single pass |
| Missing download cache for static sources | Repeated downloads of immutable data from GitHub/S3/CDN | Cache to UC Volume or local storage on first download |
| **DataFrame filter inside pipeline loop** | `for event in events: df[df["key"] == event["key"]]` — full O(n) scan per event, O(n×m) total | Pre-build `groupby()` dict or `set_index()` before loop; merge/join instead of loop. On tracking-scale data (>100K rows), always Critical. See algorithm-complexity.md §5 for full pattern. |

## Best Practices

- Measure before optimizing — use `run_results.json`, Spark UI, or execution logs to find bottlenecks
- Start with storage format and partitioning — largest gains with least code change
- Make incremental the default for large tables — full rebuilds need explicit justification
- Set file size targets at 128MB-1GB for Parquet — compact small files regularly
- Use broadcast joins when one side is small (<500MB) — eliminates shuffle entirely
- Enable AQE in Spark 3.x — free runtime optimization
- Track dead letter rates as a pipeline health signal — alert when rate exceeds 5%
- Vectorize all DataFrame operations — avoid `apply(axis=1)`, `iterrows()`, Python loops
- Move Python analytics to executors via `applyInPandas` — the driver should orchestrate, not compute
- Choose the finest correct group key — decomposable computations should use sub-match grouping for maximum parallelism
- Cache model loading on executors — module-level `_model_cache` dict, not per-group load
- Estimate group sizes before migrating to `applyInPandas` — groups must fit in executor memory (1 GB on serverless)
- Hoist shared setup out of per-item loops — repeated team splits, index builds, and model loads are free speedups
- Estimate pipeline cost per run — make cost visible to drive optimization decisions
- Use model selection (`dbt run --select`) for iteration — avoid running the full DAG
- Add skip guards to every ingestion pipeline — check existing partitions before fetching/parsing/writing; no-op runs should complete in seconds, not minutes
- Cache immutable source downloads — GitHub releases, Figshare ZIPs, and static API endpoints don't change between runs; download once, read from cache thereafter
- Audit ingestion no-op cost explicitly — count HTTP requests, file parses, `df.count()` calls, and Delta writes that execute when nothing is new; this is the single highest-ROI optimization for scheduled pipelines
