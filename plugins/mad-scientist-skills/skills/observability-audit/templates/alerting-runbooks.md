# Alerting & Runbooks Reference

Comprehensive guide to alert design, SLO-based burn rate alerting, runbook authoring, escalation paths, and on-call operational hygiene.

## Purpose

Answer: "When something breaks, do the right people know, and do they know what to do?"

## Checklist

Before auditing, identify:

- [ ] Which alerting platform is in use (Prometheus/Alertmanager, Datadog, PagerDuty, Opsgenie, Grafana Alerting)
- [ ] Whether an on-call rotation exists and is staffed
- [ ] Whether runbooks exist for current alerts and where they are stored
- [ ] Whether an escalation path is defined and documented
- [ ] Whether alert history and acknowledgment data is available for review

---

## Alert Design Principles

### Alert on symptoms, not causes

Alerts should reflect user-visible impact, not internal system mechanics.

| Symptom-based (good) | Cause-based (bad) | Why |
|----------------------|-------------------|-----|
| `latency_p99 > SLO_target` | `cpu_usage > 80%` | High CPU might not affect users; high latency always does |
| `error_rate > 1%` | `pod_restart_count > 3` | Restarts are a cause — error rate is what users feel |
| `success_rate < 99.9%` | `disk_usage > 90%` | Disk might be fine for hours; success rate drop is immediate pain |
| `checkout_failures > 0.5%` | `database_connections > 100` | Business metric directly maps to revenue impact |

### Every alert must be actionable

If there is nothing a human can do when the alert fires, it should not be an alert. It belongs in a dashboard or a log.

**The 3am test:** Would you wake someone up for this? If not, it is a ticket or a log — not a page.

| Actionable | Not actionable | What to do instead |
|-----------|----------------|-------------------|
| "API error rate exceeded SLO" | "CPU is at 78%" | Dashboard metric |
| "Payment processing down" | "Deployment completed" | Notification / log |
| "Certificate expires in 7 days" | "Disk usage at 60%" | Capacity planning review |
| "No data from heartbeat in 5 min" | "Pod restarted once" | Kubernetes event log |

### Multi-window burn rate for SLOs

Simple threshold alerts produce too many false positives. Multi-window burn rate alerts detect real SLO violations by requiring that a high burn rate is sustained across both a long window and a short window.

- **Long window** catches sustained burns (e.g., 1 hour)
- **Short window** confirms the problem is happening right now (e.g., 5 minutes)
- Both must exceed the burn rate threshold before the alert fires

### Severity levels with clear routing

| Severity | Routing | Response time | Example |
|----------|---------|---------------|---------|
| **Page** (SEV1/SEV2) | Wake someone up — PagerDuty, phone call | Immediate (< 15 min ack) | Payment processing down, data loss risk |
| **Ticket** (SEV3) | Create a ticket — next business day | < 8 hours | Elevated error rate on non-critical endpoint |
| **Log** (SEV4/info) | Log for review — dashboard, Slack channel | Best effort | Elevated latency within SLO budget |

---

## Alert Quality Metrics

| Metric | What it measures | Healthy target | How to compute |
|--------|-----------------|----------------|----------------|
| Signal-to-noise ratio | Proportion of actionable alerts to total alerts | > 80% actionable | `actionable_alerts / total_alerts` over 30 days |
| MTTA (mean time to acknowledge) | How fast on-call responds | < 5 min for pages | Average time from alert fire to ack |
| MTTR (mean time to resolve) | How fast incidents are resolved | < 1 hour for SEV1 | Average time from alert fire to resolution |
| Alert fatigue indicators | Alerts ignored, snoozed, or auto-resolved | < 10% ignored | `(snoozed + ignored) / total_alerts` |
| False positive rate | Alerts that fired but required no action | < 20% | `false_positives / total_alerts` over 30 days |
| Pages per on-call shift | Volume burden on the on-call engineer | <= 2 per shift | Count of page-severity alerts per rotation |

---

## SLO Burn Rate Alerting

### Concept

A burn rate of 1x means you will exactly exhaust your error budget over the SLO window (typically 30 days). A burn rate of 14.4x means you will exhaust your 30-day error budget in roughly 2 days if the rate continues.

Multi-window alerts combine:
- A **long window** (e.g., 1 hour) to detect sustained problems
- A **short window** (e.g., 5 minutes) to confirm the problem is current

The alert fires only when **both** windows exceed the burn rate threshold, eliminating most false positives.

### Burn rate reference

| Burn rate | Budget consumption | Time to exhaust 30-day budget | Severity |
|-----------|-------------------|-------------------------------|----------|
| 14.4x | 2% in 1 hour | ~2 days | Page |
| 6x | 5% in 6 hours | ~5 days | Page |
| 3x | 10% in 1 day | ~10 days | Ticket |
| 1x | 100% in 30 days | 30 days | Log / review |

### Prometheus recording rules

```yaml
# Recording rule: error ratio over different windows
groups:
  - name: slo-burn-rate
    interval: 30s
    rules:
      # 5-minute error ratio
      - record: slo:error_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      # 1-hour error ratio
      - record: slo:error_ratio:rate1h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h]))
          /
          sum(rate(http_requests_total[1h]))
```

### Prometheus alert rule — 2-window burn rate

```yaml
groups:
  - name: slo-burn-rate-alerts
    rules:
      # Page: 14.4x burn rate over 1h AND 5m windows
      # SLO target: 99.9% (error budget = 0.1%)
      - alert: HighErrorBurnRate
        expr: |
          slo:error_ratio:rate1h > (14.4 * 0.001)
            and
          slo:error_ratio:rate5m > (14.4 * 0.001)
        for: 2m
        labels:
          severity: page
          slo: availability
        annotations:
          summary: "High error burn rate — SLO at risk"
          description: >
            Error burn rate is {{ $value | humanizePercentage }} over 1h
            (14.4x budget consumption). The 30-day error budget will be
            exhausted in ~2 days at this rate.
          runbook_url: "https://runbooks.example.com/high-error-burn-rate"

      # Ticket: 3x burn rate over 3d AND 6h windows
      - alert: ElevatedErrorBurnRate
        expr: |
          slo:error_ratio:rate3d > (3 * 0.001)
            and
          slo:error_ratio:rate6h > (3 * 0.001)
        for: 5m
        labels:
          severity: ticket
          slo: availability
        annotations:
          summary: "Elevated error burn rate — SLO budget eroding"
          description: >
            Error burn rate is 3x normal over 3 days.
            Budget will be exhausted in ~10 days at this rate.
          runbook_url: "https://runbooks.example.com/elevated-error-burn-rate"
```

### Grafana alert rule example

```yaml
# Grafana unified alerting rule (provisioned via YAML)
apiVersion: 1
groups:
  - orgId: 1
    name: slo-burn-rate
    folder: SLO Alerts
    interval: 1m
    rules:
      - uid: high-error-burn-rate
        title: "High Error Burn Rate (14.4x)"
        condition: burn_rate_breached
        data:
          - refId: error_rate_1h
            relativeTimeRange:
              from: 3600
              to: 0
            datasourceUid: prometheus
            model:
              expr: |
                sum(rate(http_requests_total{status=~"5.."}[1h]))
                / sum(rate(http_requests_total[1h]))
          - refId: error_rate_5m
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              expr: |
                sum(rate(http_requests_total{status=~"5.."}[5m]))
                / sum(rate(http_requests_total[5m]))
          - refId: burn_rate_breached
            datasourceUid: "__expr__"
            model:
              type: classic_conditions
              conditions:
                - evaluator:
                    type: gt
                    params: [0.0144]  # 14.4 * 0.001
                  query:
                    params: [error_rate_1h]
                - evaluator:
                    type: gt
                    params: [0.0144]
                  query:
                    params: [error_rate_5m]
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "SLO burn rate critical — page on-call"
          runbook_url: "https://runbooks.example.com/high-error-burn-rate"
```

---

## Runbook Template

Every alert that can page someone must have a runbook. The runbook is the single source of truth for what to do when an alert fires.

````markdown
# Alert: [Alert Name]

## Severity: [page/ticket/log]

## Impact: [What users experience]

Describe the user-visible symptoms. Example: "Users see 500 errors on the checkout
page. Approximately 5% of checkout attempts are failing."

## Diagnosis Steps

1. Check [dashboard link] for the affected service
2. Query: `[specific PromQL/Datadog/SQL query to scope the problem]`
3. Look for [specific pattern — e.g., spike in error logs, upstream timeout, deployment correlation]
4. Check recent deployments: `kubectl rollout history deployment/<service>`
5. Verify upstream dependencies: `curl -s https://status.dependency.com/api/status`

## Remediation

- If **recent deployment caused it**: Roll back with `kubectl rollout undo deployment/<service>`
- If **upstream dependency is down**: Enable circuit breaker / failover — see [failover runbook link]
- If **resource exhaustion** (OOM, disk, connections): Scale horizontally with `kubectl scale deployment/<service> --replicas=<N>`
- If **data issue**: Pause processing, notify data team, do NOT retry until root cause identified

## Escalation

- **L1**: On-call engineer — 15 min to acknowledge, 30 min to begin remediation
- **L2**: Team lead — escalate if no progress after 30 min or if scope expands
- **L3**: Engineering manager — escalate if customer-facing impact exceeds 1 hour or if cross-team coordination needed

## Post-Incident

- [ ] Update this runbook if diagnosis or remediation steps changed
- [ ] File postmortem if SEV1 or SEV2
- [ ] Add automated fix or detection if manual remediation was repetitive
- [ ] Review alert thresholds — did the alert fire at the right time?
````

---

## Escalation Path Design

### L1 → L2 → L3 structure

| Level | Who | Time threshold | Contact method | Decision criteria |
|-------|-----|---------------|----------------|-------------------|
| **L1** | On-call engineer | 0–15 min to ack, 30 min to begin remediation | PagerDuty / Opsgenie auto-page | All alerts route here first |
| **L2** | Team lead / senior engineer | Escalate after 30 min without progress | PagerDuty escalation + Slack | Problem requires deeper expertise or broader context |
| **L3** | Engineering manager / VP | Escalate after 1 hour of customer impact | Phone call + Slack + email | Cross-team coordination, executive communication, customer notification |

### Escalation triggers

Escalate immediately (skip time thresholds) if:

- Data loss is occurring or suspected
- Security breach is detected
- Blast radius is expanding (more services going down)
- On-call engineer is not confident in the remediation path
- Customer SLA is at risk of formal breach

### Escalation anti-patterns

- **Hero culture**: One person handles everything, never escalates — leads to burnout and longer incidents
- **Escalation anxiety**: Fear of "bothering" senior people — that is literally what escalation paths are for
- **Missing contact info**: Escalation policy says "contact team lead" but no phone number or PagerDuty schedule
- **No fallback**: Primary on-call is unreachable and there is no secondary

---

## Alert Grouping and Inhibition

### Alertmanager grouping

Group related alerts to avoid a flood of notifications during a cascading failure.

```yaml
# alertmanager.yml
route:
  receiver: default
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s        # wait before sending first notification for a group
  group_interval: 5m     # wait before sending updates for an existing group
  repeat_interval: 4h    # re-notify after this long if alert still firing

  routes:
    - match:
        severity: page
      receiver: pagerduty-critical
      group_by: ['alertname', 'cluster']
      group_wait: 10s
      continue: false

    - match:
        severity: ticket
      receiver: slack-tickets
      group_by: ['alertname', 'service']
      group_wait: 1m
```

### Alertmanager inhibition rules

Suppress downstream alerts when a root-cause alert is already firing.

```yaml
# alertmanager.yml
inhibit_rules:
  # If the entire cluster is down, suppress all service-level alerts for that cluster
  - source_match:
      alertname: ClusterDown
    target_match_re:
      alertname: '.+'
    equal: ['cluster']

  # If a node is down, suppress pod-level alerts on that node
  - source_match:
      alertname: NodeNotReady
    target_match_re:
      alertname: '(PodCrashLooping|PodNotReady|ContainerOOMKilled)'
    equal: ['node']

  # If a database is down, suppress query latency alerts
  - source_match:
      alertname: DatabaseDown
    target_match:
      alertname: QueryLatencyHigh
    equal: ['database_cluster']
```

### Datadog composite monitors

Datadog uses composite monitors to combine multiple conditions into a single alert, similar to Alertmanager grouping and inhibition.

```
# Composite monitor: only alert if BOTH conditions are true
# Trigger: API error rate is high AND it's not a planned maintenance window

Monitor A: avg(last_5m):sum:http.requests.errors{service:api} / sum:http.requests.total{service:api} > 0.01
Monitor B: NOT scheduled_maintenance_window

Composite: A && !B
```

Use composite monitors to:
- Avoid alerting during maintenance windows
- Require multiple signals before paging (similar to multi-window burn rate)
- Suppress alerts when a known upstream dependency is down

---

## Dead-Man's-Switch / Heartbeat Monitoring

A dead-man's-switch alert fires when an expected signal **stops arriving**. This catches silent failures — the most dangerous kind, because nothing looks wrong until you check.

### Alertmanager Watchdog alert

Alertmanager ships a built-in `Watchdog` alert that always fires. If it stops firing, your monitoring pipeline itself is broken.

```yaml
# Prometheus alert rule
groups:
  - name: meta-monitoring
    rules:
      - alert: Watchdog
        expr: vector(1)
        labels:
          severity: none
        annotations:
          summary: "Watchdog alert — proves alerting pipeline is functional"

      # Alert if Watchdog stops
      - alert: AlertmanagerDown
        expr: absent(up{job="alertmanager"} == 1)
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "Alertmanager is not responding — alerting pipeline may be down"
```

Configure a **dead-man's-switch receiver** (e.g., PagerDuty, Healthchecks.io, Cronitor) that expects a regular heartbeat from the Watchdog. If the heartbeat stops, the external service pages you.

### Datadog "no data" alerts

```
# Datadog monitor: alert when metric stops reporting
Monitor type: Metric
Query: avg(last_5m):avg:app.heartbeat{service:payment-processor}
Alert condition: "Notify if data is missing for more than 5 minutes"
```

### Custom heartbeat patterns

```yaml
# Application emits a heartbeat metric every 60 seconds
# Prometheus alert when heartbeat is missing
groups:
  - name: heartbeat-monitoring
    rules:
      - alert: ServiceHeartbeatMissing
        expr: |
          time() - max by (service) (app_heartbeat_timestamp_seconds) > 300
        for: 1m
        labels:
          severity: page
        annotations:
          summary: "No heartbeat from {{ $labels.service }} in 5 minutes"
          description: >
            The service {{ $labels.service }} has not emitted a heartbeat
            in over 5 minutes. The service may be down, frozen, or unable
            to reach the metrics endpoint.
          runbook_url: "https://runbooks.example.com/heartbeat-missing"
```

**What to heartbeat-monitor:**
- Batch jobs / cron jobs (did the nightly job actually run?)
- Queue consumers (is the consumer alive and processing?)
- External data feeds (is the vendor still sending data?)
- The monitoring system itself (meta-monitoring)

---

## Chaos Engineering for Alert Testing

Alerts that have never fired might not work when you need them. Periodically validate that alerts fire correctly and route to the right people.

### Simple validation approaches

| Test | How | What it validates |
|------|-----|-------------------|
| Kill a pod | `kubectl delete pod <pod> --grace-period=0` | Pod crash alerts, auto-scaling, runbook accuracy |
| Inject latency | Envoy fault injection or `tc qdisc add` | Latency SLO alerts, timeout handling |
| Stop a heartbeat | Pause the heartbeat emitter process | Dead-man's-switch alerts |
| Fill disk | `dd if=/dev/zero of=/tmp/fill bs=1M count=1024` | Disk pressure alerts, eviction behavior |
| Block network | `iptables -A OUTPUT -d <dependency> -j DROP` | Upstream dependency alerts, circuit breakers |
| Return errors | Feature flag to return 500s on a test endpoint | Error rate alerts, burn rate alerts |

### Tools

| Tool | Scope | Best for |
|------|-------|----------|
| **Gremlin** | Full platform — network, CPU, disk, process | Enterprise, broad fault injection |
| **Chaos Monkey** (Netflix) | Random instance termination | Resilience to instance failure |
| **Litmus** (CNCF) | Kubernetes-native chaos experiments | Cloud-native, CRD-based experiments |
| **Chaos Mesh** (CNCF) | Kubernetes-native, rich fault types | Kubernetes, fine-grained experiments |
| **Manual** | Ad-hoc testing in staging | Quick validation, no tooling overhead |

### Alert testing schedule

| Frequency | What to test |
|-----------|-------------|
| Weekly | Dead-man's-switch / Watchdog — confirm monitoring pipeline works |
| Monthly | One critical alert — kill a staging pod, verify page arrives |
| Quarterly | Full escalation path — simulate SEV1 and walk through the entire escalation |
| After every change | Any modified alert rule — verify it fires and routes correctly |

---

## On-Call Hygiene

### Rotation best practices

| Practice | Why |
|----------|-----|
| Minimum 2 people in rotation | Prevents single points of failure and burnout |
| Rotation length: 1 week | Long enough for context, short enough to be sustainable |
| Follow-the-sun for global teams | No one should be on-call during sleep hours if avoidable |
| Primary + secondary on-call | Secondary provides backup if primary is unreachable |
| Exclude holidays and PTO | On-call overrides must be scheduled in advance |

### Handoff checklist

At the start of each on-call shift:

- [ ] Review open incidents and their current status
- [ ] Check alert history from the previous shift — any recurring issues?
- [ ] Verify PagerDuty/Opsgenie schedule shows you as on-call
- [ ] Confirm notification channels work (test page to your phone)
- [ ] Read handoff notes from previous on-call engineer
- [ ] Check for any scheduled deployments, maintenance windows, or migrations
- [ ] Know who your secondary on-call and escalation contacts are

### Sustainable on-call targets

| Metric | Target | Action if exceeded |
|--------|--------|--------------------|
| Pages per shift | <= 2 | Fix noisy alerts, improve automation |
| Sleep interruptions per shift | 0 (ideal), <= 1 (acceptable) | Re-evaluate alert thresholds and severity |
| Percentage of time spent on incidents | < 25% of shift | Invest in reliability, automate remediations |
| On-call compensation | Defined and fair | Formal policy, comp time or pay differential |

### Post-on-call review

At the end of each on-call shift:

- [ ] Document all incidents and how they were resolved
- [ ] File tickets for toil reduction (noisy alerts, missing runbooks, manual steps that should be automated)
- [ ] Update runbooks that were inaccurate or incomplete during incidents
- [ ] Flag any alerts that fired but were not actionable (candidates for removal or downgrade)
- [ ] Hand off open issues to the next on-call with written context

---

## Best practices

- Every page-severity alert must have a runbook linked in the alert annotation
- Use multi-window burn rate alerting for SLOs — never simple static thresholds for availability
- Review alert quality metrics monthly — track false positive rate, MTTA, and pages per shift
- Test alerts regularly — an alert that has never fired is an alert you cannot trust
- Keep runbooks next to the code or in a well-known wiki — they must be findable in 30 seconds under stress
- Define and publish the escalation path — every engineer should know how to escalate without searching
- Treat on-call as a first-class engineering responsibility — budget time for toil reduction, not just firefighting
- Use alert grouping and inhibition to prevent notification storms during cascading failures
- Implement heartbeat monitoring for critical batch jobs, queue consumers, and the monitoring system itself
- Run a quarterly "alert fire drill" — simulate a SEV1 and walk through the entire response process

## Anti-patterns

- Alerting on causes instead of symptoms (CPU, disk, memory thresholds with no user impact correlation)
- Alerts without runbooks — the on-call engineer is left guessing at 3am
- No severity levels — every alert pages, leading to alert fatigue and ignored pages
- "Christmas tree" dashboards — everything is red but nothing is actionable
- Alert fatigue accepted as normal — "we just ignore most of them" is a system design failure
- Missing dead-man's-switch — silent failures go undetected for hours or days
- Never testing alerts — finding out the alert is misconfigured during a real incident
- Hero culture on-call — one person handles everything, never escalates, eventually burns out
- Runbooks that say "contact $PERSON" instead of documenting the actual steps — knowledge is locked in one head
- Copy-pasting alert rules without tuning thresholds to the specific service's baseline
