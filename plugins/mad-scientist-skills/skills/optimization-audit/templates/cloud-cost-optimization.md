# Cloud Cost Optimization Reference

Actionable reference for cloud cost analysis, right-sizing, auto-scaling, storage tiering, and FinOps practices. Use during Phase 11 (Cloud Cost & Right-Sizing) of the optimization audit.

## Purpose

Answer: "Are cloud resources appropriately sized, scaled, and priced for the actual workload?"

## Checklist

Before auditing, identify:

- [ ] Which cloud provider(s) are in use (AWS, Azure, GCP, multi-cloud)
- [ ] What IaC tool manages infrastructure (Terraform, CloudFormation, Pulumi, CDK)
- [ ] Whether Kubernetes is used (EKS, AKS, GKE, self-managed)
- [ ] What workload profiles exist (steady-state, bursty, diurnal, batch)
- [ ] Whether cost monitoring is already in place (Cost Explorer, Kubecost, etc.)
- [ ] What tagging strategy exists for cost allocation
- [ ] Whether commitment-based discounts are active (Reserved Instances, Savings Plans)

---

## Right-Sizing Methodology

Right-sizing matches resource allocation to actual utilization. It is the single highest-ROI cloud optimization — typically 20-40% savings with no architectural changes.

### Utilization Thresholds

| Classification | CPU Utilization | Memory Utilization | Action |
|---------------|----------------|-------------------|--------|
| Under-provisioned | > 80% sustained | > 90% or OOM kills | Scale up — performance and reliability at risk |
| Right-sized | 40-70% | 50-80% | No action — headroom is appropriate |
| Over-provisioned | < 20% | < 30% | Scale down — paying for unused capacity |
| Idle | < 5% | < 10% | Evaluate for termination or scale-to-zero |

### Step-by-Step Methodology

1. **Collect utilization data** over a minimum of 14 days (captures weekly patterns). 30 days is better.
2. **Identify peak utilization** — right-size to the p95 peak, not the average. Average 15% may have peaks of 70%.
3. **Separate workload types:**
   - **Steady-state services:** target 40-70% CPU at p95 peak
   - **Batch jobs:** target 70-90% CPU during execution
   - **Dev/staging:** target lowest cost; scale-to-zero when idle
4. **Check memory independently** — CPU and memory do not always correlate. A service may be CPU-right-sized but memory-over-provisioned (common with JVM defaults).
5. **Recommend specific instance changes** with projected savings:

```
# BAD — over-provisioned
Current:  m5.2xlarge (8 vCPU, 32 GB) at $0.384/hr — CPU avg 12%, Memory avg 25%

# GOOD — right-sized
Proposed: m5.large (2 vCPU, 8 GB) at $0.096/hr
Savings:  $184/month (65% reduction)
```

6. **Validate before applying** — never downsize without checking p95/p99 peaks.

### Cloud Provider Right-Sizing Tools

| Tool | Provider | What it does |
|------|----------|-------------|
| AWS Compute Optimizer | AWS | Analyzes CloudWatch metrics, recommends instance types for EC2, EBS, Lambda |
| Azure Advisor | Azure | Cost and performance recommendations for VMs, SQL, storage |
| GCP Recommender | GCP | VM right-sizing, committed use discount, idle resource detection |
| `kubectl top pods` | Kubernetes | Real-time CPU/memory usage per pod |
| Kubecost | Kubernetes | Per-pod, per-namespace cost allocation and right-sizing |

### Kubernetes Resource Right-Sizing

```yaml
# BAD — over-provisioned pod (common default-copy-paste pattern)
resources:
  requests:
    cpu: "2000m"
    memory: "4Gi"
  limits:
    cpu: "4000m"
    memory: "8Gi"
# Actual usage: 200m CPU, 512Mi memory — paying for 10x what is needed

# GOOD — right-sized based on observed usage
resources:
  requests:
    cpu: "300m"      # ~1.5x observed p95 usage
    memory: "768Mi"  # ~1.5x observed p95 usage
  limits:
    cpu: "600m"      # 2x request for burst headroom
    memory: "1Gi"    # Hard cap to prevent OOM affecting other pods
```

**Rule of thumb:** Set requests to 1.2-1.5x observed p95 usage. Set limits to 1.5-2x requests.

---

## Auto-Scaling Patterns

Auto-scaling matches capacity to demand. Without it, you either over-provision (waste money) or under-provision (degrade performance).

### Kubernetes HPA

```yaml
# CPU-based HPA with scale-down protection
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-server
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 2
  maxReplicas: 20
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown prevents thrashing
      policies:
        - type: Percent
          value: 25                    # Scale down at most 25% at a time
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0    # Scale up immediately
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    # Custom metrics (better for most APIs — directly reflects demand)
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"          # Target 100 RPS per pod
```

### KEDA (Event-Driven Autoscaler)

KEDA extends HPA with event-driven scaling, including scale-to-zero.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-processor
spec:
  scaleTargetRef:
    name: order-processor
  minReplicaCount: 0               # Scale to zero when queue is empty
  maxReplicaCount: 50
  cooldownPeriod: 300              # 5 min before scaling to zero
  triggers:
    - type: rabbitmq
      metadata:
        queueName: orders
        queueLength: "5"           # 1 pod per 5 messages
```

### AWS Auto Scaling

**Target tracking** (recommended default): Set a target metric value and AWS adjusts capacity to maintain it. **Predictive scaling**: Uses ML to anticipate demand — good for diurnal patterns. **Step scaling**: Define explicit scaling steps for fine-grained control.

```hcl
# Terraform — target tracking scaling policy
resource "aws_autoscaling_policy" "target_tracking" {
  name                   = "cpu-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 60.0
  }
}
```

### Scaling Metrics Selection

| Metric | Best for | Why |
|--------|---------|-----|
| CPU utilization | General compute | Simple, universally available |
| Request rate (RPS) | API servers, web apps | Directly reflects demand; more responsive than CPU |
| Queue depth | Worker/consumer services | Scales to match work backlog |
| Custom business metric | Specialized workloads | Concurrent users, active jobs, pending uploads |
| Response latency | Latency-sensitive services | Scale before users experience degradation |

**Anti-pattern:** Scaling only on CPU when the real bottleneck is I/O, memory, or external dependencies.

### Cooldown and Thrashing Prevention

- **Scale-up cooldown:** Keep short (0-60s). Fast reaction to demand is critical.
- **Scale-down cooldown:** Set to 5-10 minutes minimum. Premature scale-down causes oscillation.
- **Scale-down rate:** Limit to 10-25% of capacity per period. Gradual prevents capacity cliffs.

### Min/Max Configuration

| Setting | Guidance |
|---------|----------|
| **Minimum replicas** | Handle baseline traffic without scaling events. At least 2 for HA. |
| **Maximum replicas** | Set based on budget cap, not infinite. Include cost alert at 80% of max. |
| **Min = Max** | Effectively disables auto-scaling. Only for steady-state, latency-critical services. |

---

## Spot/Preemptible Instances

Spot instances (AWS), preemptible VMs (GCP), and Spot VMs (Azure) offer 60-90% savings. The tradeoff: the provider can reclaim them with 2 minutes notice (AWS) or 30 seconds (GCP).

### When to Use

| Workload type | Spot-safe? | Why |
|---------------|-----------|-----|
| Stateless API servers (behind LB) | Yes | Traffic reroutes to remaining instances |
| Batch/ETL jobs (with checkpointing) | Yes | Jobs resume from checkpoint |
| CI/CD build agents | Yes | Builds retry on failure |
| Dev/staging environments | Yes | Interruption is acceptable |
| ML training (with checkpointing) | Yes | Resume from last checkpoint |
| Single-instance databases | No | Data loss risk on interruption |
| Stateful services without replication | No | State loss on reclamation |

### Mixed Instance Strategy

Use an on-demand base for reliability + spot instances for scaling. Diversify across instance families (m5, m5a, m6i) and AZs to reduce interruption risk. Set `on_demand_base_capacity` to your minimum reliable count and `spot_allocation_strategy` to `capacity-optimized`.

### Interruption Handling

- **Graceful shutdown:** Handle SIGTERM. Drain connections, finish in-flight requests, save state.
- **Metadata polling:** Check the interruption notice endpoint every 5 seconds.
- **Checkpointing:** For long-running jobs, save progress periodically so work is not lost.

---

## Reserved Instances and Savings Plans

Commitment-based discounts trade flexibility for cost reduction. They make sense for predictable, steady-state workloads.

### When Reserved Makes Sense

| Criteria | Reserved/Savings Plan | On-Demand | Spot |
|----------|----------------------|-----------|------|
| Runs 24/7 for 12+ months | Yes | No | No |
| Predictable, steady resource needs | Yes | No | Partial |
| Variable, bursty workloads | No | Yes | Yes |
| Short-lived projects (< 6 months) | No | Yes | Yes |

### Break-Even Calculation

```
Break-even months = (Upfront cost) / (On-demand monthly - Reserved monthly)

Example (m5.large, us-east-1):
  On-demand:       $70.08/month
  1-year reserved: $43.80/month (no upfront) — 37.5% savings
  3-year reserved: $27.01/month (all upfront) — 61.5% savings
```

### Utilization Tracking

- **Target:** > 80% utilization of all reserved capacity
- **If < 60%:** Investigate. Consider selling on AWS Reserved Instance Marketplace.
- **Tools:** AWS Cost Explorer RI Utilization report, Azure Reservation utilization, GCP CUD reports

---

## Storage Tiering

Storage costs accumulate silently. Moving data to the right tier based on access frequency is low-effort, high-impact.

### S3 Storage Classes

| Tier | Cost (per GB/month) | Access frequency | Use case |
|------|-------------------|-----------------|----------|
| Standard | ~$0.023 | Frequent (daily) | Active application data |
| Intelligent-Tiering | ~$0.023 + monitoring | Unknown/variable | Unpredictable access patterns |
| Standard-IA | ~$0.0125 | Infrequent (monthly) | Backups, older logs |
| One Zone-IA | ~$0.010 | Infrequent, non-critical | Reproducible data |
| Glacier Instant | ~$0.004 | Rare (quarterly) | Archive with ms access |
| Glacier Flexible | ~$0.0036 | Rare (1-2x/year) | Compliance archives |
| Deep Archive | ~$0.00099 | Almost never | Regulatory retention |

### EBS Volume Types

| Type | IOPS | Cost | When to use |
|------|------|------|-------------|
| gp3 | 3,000 baseline (up to 16,000) | $0.08/GB | **Default choice** — cheaper AND faster than gp2 |
| gp2 | 3 IOPS/GB (burst to 3,000) | $0.10/GB | **Legacy** — migrate to gp3 for 20% savings |
| io2 | Up to 64,000 | $0.125/GB + IOPS | High-performance databases |
| st1 | 500 baseline | $0.045/GB | Sequential workloads (Hadoop, Kafka) |

**Key insight:** gp3 is 20% cheaper than gp2 AND provides better baseline performance. There is no reason to use gp2 for new volumes.

### Lifecycle Policies

```hcl
# Terraform — S3 lifecycle rules for automatic tiering
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
    expiration {
      days = 2555  # 7 years for compliance
    }
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
```

---

## Scale-to-Zero

Scale-to-zero eliminates cost for idle workloads. Particularly valuable for dev/staging environments, bursty event-driven services, and internal tools with low usage.

### Candidates for Scale-to-Zero

| Workload | Scale-to-zero? | Implementation |
|----------|---------------|----------------|
| Dev/staging environments | Yes — idle nights/weekends | Scheduled scaling (cron) |
| Event-driven workers | Yes — no events, no pods | KEDA with queue-based trigger |
| Internal admin tools | Yes — used a few times/day | Serverless (Lambda/Cloud Functions) |
| Webhook receivers | Yes — bursty, unpredictable | Serverless or KEDA |
| Batch/ETL jobs | Yes — run on schedule | Kubernetes Jobs or Step Functions |
| Production API servers | No — cold start unacceptable | Keep minimum replicas |
| Databases | No — startup too long | Use serverless variants (Aurora Serverless) |

### Implementation Patterns

**Serverless (Lambda, Cloud Functions):** Inherently scales to zero. Use for event handlers (S3 triggers, SQS consumers), low-traffic APIs (< 1M requests/month), and scheduled tasks (cron replacements).

**KEDA Scale-to-Zero for Kubernetes:** Set `minReplicaCount: 0` on a ScaledObject with queue-based or cron triggers. Set `cooldownPeriod` to 300 seconds to avoid premature scale-down.

**Scheduled Scaling for Dev/Staging:** Use `aws_autoscaling_schedule` to set `desired_capacity = 0` at 6 PM weekdays and `desired_capacity = 1` at 8 AM. Saves approximately 70% on non-production costs.

```hcl
# Terraform — dev environment business hours only
resource "aws_autoscaling_schedule" "scale_down_evening" {
  scheduled_action_name  = "scale-down-evening"
  autoscaling_group_name = aws_autoscaling_group.dev.name
  min_size               = 0
  max_size               = 0
  desired_capacity       = 0
  recurrence             = "0 18 * * MON-FRI"
}
```

---

## Cost Estimation Tools

Shift cost awareness left — catch expensive infrastructure changes before they are deployed.

### Infracost (Terraform Cost Estimation)

```bash
# Generate cost estimate for a Terraform plan
infracost breakdown --path .

# Compare cost of a change (in CI/CD pull requests)
infracost diff --path . --compare-to infracost-base.json
```

Use `infracost/actions/setup@v3` and `infracost/actions/comment@v3` GitHub Actions to post cost diffs as PR comments automatically.

### Cost Monitoring Tools Comparison

| Tool | Scope | Best for | Cost |
|------|-------|---------|------|
| Infracost | Terraform IaC | Pre-deployment cost estimation | Free (open-source) + paid cloud |
| Kubecost | Kubernetes | Per-pod/namespace cost allocation | Free (open-source) + paid |
| OpenCost | Kubernetes | CNCF K8s cost monitoring | Free (open-source) |
| AWS Cost Explorer | AWS | Historical cost analysis, forecasting | Free (included) |
| Azure Cost Management | Azure | Budget alerts, cost analysis | Free (included) |
| GCP Billing Reports | GCP | Cost breakdown, budget alerts | Free (included) |
| CloudHealth / Apptio | Multi-cloud | Enterprise cost governance | Paid |

---

## Orphaned Resource Detection

Orphaned resources are cloud resources no longer attached to anything useful but still incurring charges. They accumulate after deployments, failed teardowns, and manual experiments.

### Detection Checklist

| Resource | How to detect | Typical waste |
|----------|--------------|--------------|
| Detached EBS volumes | `Available` state, no attachment | $0.10/GB/month |
| Unused Elastic IPs | Allocated but not associated | $3.60/month each |
| Stale EBS snapshots | No associated AMI, older than 90 days | Varies by size |
| Empty load balancers | No registered targets | $16-22/month each |
| Unused NAT gateways | No route table references | $32/month + data |
| Idle RDS instances | < 1% CPU for 14+ days | Instance-type dependent |
| Unused security groups | No attached ENIs | Free, but audit noise |
| Old Lambda versions | Not referenced by aliases | Minor storage cost |

### AWS CLI Detection Commands

```bash
# Detached EBS volumes
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query 'Volumes[*].{ID:VolumeId,Size:Size}' --output table

# Unused Elastic IPs
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null].{IP:PublicIp}' --output table

# Unattached network interfaces
aws ec2 describe-network-interfaces --filters Name=status,Values=available \
  --query 'NetworkInterfaces[*].{ID:NetworkInterfaceId}' --output table
```

---

## Egress Optimization

Data transfer costs are often the surprise line item on cloud bills. Cross-region and internet egress fees compound at scale.

### Cost Structure (AWS Typical)

| Transfer type | Cost |
|--------------|------|
| Intra-AZ (same AZ) | Free |
| Inter-AZ (same region) | $0.01/GB each direction |
| Inter-region | $0.02/GB |
| Internet egress | $0.09/GB (first 10 TB) |
| S3 to CloudFront (same region) | Free |
| VPC endpoint to S3/DynamoDB | Free (data transfer) |

### Optimization Patterns

**1. VPC Endpoints for AWS Services** — Replace internet-routed traffic with private endpoints. Gateway endpoints (S3, DynamoDB) are free. Interface endpoints have a small hourly cost but save NAT Gateway processing charges ($0.045/GB).

**2. CDN Offloading** — Serve static assets and cacheable API responses from edge. S3-to-CloudFront transfer in the same region is free.

**3. Data Locality** — Keep compute and storage in the same region/AZ. Use regional read replicas instead of cross-region reads. Compress data before cross-region transfer.

**4. Cross-Region Reduction** — Consolidate to fewer regions when multi-region is not required. Batch synchronization over real-time replication when eventual consistency is acceptable.

---

## Driver-vs-Executor Cost Analysis

On managed Spark platforms (Databricks, EMR, Dataproc), executor nodes are already provisioned and billed as part of the cluster. When analytics pipelines pull data to the driver via `.toPandas()` and process it sequentially, the executors sit idle — you are paying for distributed compute but only using the driver.

### Detection

Look for these signals:

| Signal | Indicates |
|--------|-----------|
| Driver CPU at 80-100%, executor CPU near 0% | Driver-bound sequential processing |
| Pipeline duration dominated by Python loops, not Spark stages | Work happening on driver, not executors |
| `for match_id in ...: spark.sql(...).toPandas()` pattern | Per-item driver round-trip |
| Total wall-clock >> (total_data / cluster_throughput) | Cluster underutilized |

### Cost Impact

Migrating driver-bound computation to executors via `applyInPandas`:

- **Reduces wall-clock time** proportionally to the number of executor cores utilized
- **Does NOT increase cost** — the same cluster resources are used, just more efficiently
- **May reduce cost** — shorter wall-clock means the cluster (especially serverless) is released sooner

```
# Example cost calculation
# Current: 20 matches × 10 min each = 200 min wall-clock on driver
#          Executors: idle for 200 min, still billed
# After:   20 matches × 10 min each / 8 executor slots = 25 min wall-clock
#          Same DBU cost, 8x faster completion, cluster released 175 min earlier
```

### When to Flag

Flag as **High severity** when:
1. Executors are provisioned (not serverless scale-to-zero) AND idle during driver processing
2. Pipeline wall-clock exceeds 30 minutes with sequential `.toPandas()` loops
3. The computation is decomposable (see pipeline-efficiency.md decomposability test)

Do NOT flag when:
1. The operation is genuinely non-distributable (global TF-IDF, full-corpus training)
2. Data volume is small enough that distribution overhead exceeds the benefit
3. The cluster is serverless with instant scale-to-zero (idle executors cost nothing)

---

## FinOps Practices

FinOps makes cloud cost a first-class engineering concern, not an afterthought discovered during quarterly budget reviews.

### Mandatory Tagging Strategy

| Tag | Purpose | Example values |
|-----|---------|---------------|
| `team` | Cost ownership | `platform`, `data-eng`, `ml` |
| `environment` | Separate prod from non-prod | `production`, `staging`, `development` |
| `service` | Per-service cost tracking | `api-gateway`, `order-service` |
| `cost-center` | Financial allocation | `CC-1234`, `engineering` |
| `managed-by` | IaC or manual | `terraform`, `cloudformation`, `manual` |

```hcl
# Terraform — enforce tagging with default_tags
provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      environment = var.environment
      team        = var.team
      service     = var.service
      cost-center = var.cost_center
      managed-by  = "terraform"
    }
  }
}
```

### Budget Alerts

Set alerts at 50%, 80%, and 100% of expected spend. Escalate recipients as thresholds increase (engineering at 50%, finance at 80%, leadership at 100%). Use `aws_budgets_budget` (Terraform) or `AWS::Budgets::Budget` (CloudFormation) with `notification` blocks per threshold.

### Cost Review Cadence

| Frequency | Who | What |
|-----------|-----|------|
| Daily | Automated alerts | Budget thresholds, anomaly detection |
| Weekly | Engineering team | Per-service cost trends, new resource review |
| Monthly | Engineering + Finance | Cost vs budget, right-sizing, commitment utilization |
| Quarterly | Leadership | RI/Savings Plan renewals, architecture cost review |

### Cost Allocation Best Practices

- **Tag compliance:** Enforce 100% tagging. Untagged resources get flagged for cleanup.
- **Showback before chargeback:** Start with visibility before allocating costs to teams.
- **Unit economics:** Track cost per request, per user, per pipeline run — not just total spend.
- **Anomaly detection:** Enable AWS Cost Anomaly Detection or equivalent. A 3x spike often indicates a bug.

---

## Best Practices

- Right-size first, then optimize pricing (spot, reserved). Right-sizing is reversible; commitments lock you in.
- Use gp3 for all new EBS volumes — cheaper and faster than gp2 with no downside.
- Implement S3 lifecycle policies on every bucket. Access frequency always decreases over time.
- Scale dev/staging to zero outside business hours — saves approximately 70% on non-production costs.
- Run infracost in CI/CD on every Terraform PR. Engineers should see cost impact before merging.
- Tag everything. Untagged resources are unmanaged resources.
- Set budget alerts at 50%, 80%, and 100% of expected spend.
- Use VPC endpoints for high-traffic AWS service calls to save NAT Gateway charges.
- Diversify spot instance types across multiple families and AZs to reduce interruption risk.
- Track reserved instance utilization monthly. Unused reservations are pure waste.

## Anti-Patterns

- Running dev/staging environments 24/7 when they are only used during business hours
- Using gp2 EBS volumes for new deployments (gp3 is cheaper and faster)
- Setting HPA min = max, effectively disabling auto-scaling
- Scaling only on CPU when the real bottleneck is queue depth or request rate
- No scale-down cooldown, causing scaling thrashing (rapid up/down oscillation)
- Over-provisioning "just to be safe" without data — 2x headroom is reasonable, 10x is waste
- Ignoring egress costs until the bill arrives — data transfer is often the surprise cost driver
- No tagging strategy — makes cost allocation and orphan detection impossible
- Buying reserved instances before right-sizing — locking in the wrong instance type for 1-3 years
- Treating all workloads the same — batch jobs, APIs, and event processors have different cost profiles
