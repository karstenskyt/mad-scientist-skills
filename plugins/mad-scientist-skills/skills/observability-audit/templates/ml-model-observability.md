# ML & Model Observability Reference

Monitoring patterns for machine learning models in production. Covers drift detection, performance estimation without ground truth, model registry practices, and integration with OpenTelemetry and Prometheus.

## Purpose

Answer: "Can we detect when models degrade, drift, or produce invalid outputs before they impact users?"

## Checklist

Before auditing, identify:

- [ ] Which models are deployed in production (type, framework, serving infrastructure)
- [ ] Whether ground truth labels are available, delayed, or unavailable
- [ ] Whether a model registry exists (MLflow, Weights & Biases, SageMaker Model Registry)
- [ ] What monitoring backend is in use (Prometheus, Datadog, Grafana, CloudWatch)
- [ ] Whether training-time reference distributions are stored and versioned

## Model Lifecycle Monitoring

Each stage of the model lifecycle requires different observability signals:

| Stage | What to Monitor | Key Metrics |
|-------|----------------|-------------|
| **Training** | Loss convergence, gradient norms, data quality | Training loss, validation loss, learning rate, data row counts |
| **Validation** | Holdout performance, fairness metrics, calibration | AUC, precision/recall, calibration error, subgroup performance |
| **Deployment** | Artifact integrity, dependency versions, rollout health | Schema match, library versions, canary error rates |
| **Production** | Input drift, output drift, latency, error rates | PSI, KS statistic, p50/p99 latency, 5xx rate, prediction distribution |
| **Retraining** | Trigger conditions, data freshness, performance recovery | Drift score trends, label lag, post-retrain metric delta |

---

## Drift Detection Methods

### Population Stability Index (PSI)

Compares the distribution of a feature or prediction between a reference (training) period and the current (production) period using binned histogram comparison.

**Thresholds:**

| PSI Value | Interpretation |
|-----------|---------------|
| < 0.1 | No significant change |
| 0.1 - 0.2 | Minor shift — investigate |
| > 0.2 | Significant drift — action required |

**Python implementation (numpy only):**

```python
import numpy as np

def compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Compute Population Stability Index between two distributions."""
    # Use reference distribution to define bin edges
    edges = np.histogram_bin_edges(reference, bins=bins)

    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)

    # Convert to proportions, clip to avoid log(0)
    ref_pct = np.clip(ref_counts / ref_counts.sum(), 1e-6, None)
    cur_pct = np.clip(cur_counts / cur_counts.sum(), 1e-6, None)

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)

# Usage
reference_scores = np.load("reference_predictions.npy")
current_scores = np.array(todays_predictions)
psi = compute_psi(reference_scores, current_scores)
print(f"PSI = {psi:.4f}")  # > 0.2 means significant drift
```

---

### CUSUM (Cumulative Sum)

Sequential change-detection algorithm that accumulates deviations from a target mean. Runs in O(n) time and uses no external dependencies.

**Why it's valuable:** Single-point threshold checks (e.g., "alert if error > X") miss sustained small shifts. CUSUM accumulates evidence over time, so a series of slightly-above-average errors will eventually trigger an alert even if no single observation crosses a threshold.

```python
def cusum(values: list[float], target: float, threshold: float) -> list[int]:
    """Detect sustained upward shifts using CUSUM.
    Returns list of indices where cumulative deviation exceeds threshold."""
    s_high = 0.0
    change_points = []
    for i, x in enumerate(values):
        s_high = max(0.0, s_high + (x - target))
        if s_high > threshold:
            change_points.append(i)
            s_high = 0.0  # reset after detection
    return change_points

# Usage: detect when daily error rate drifts above the training-time mean
mean_error = 0.05  # training-time baseline
threshold = 3 * std_error  # 3-sigma rule
shifts = cusum(daily_error_rates, target=mean_error, threshold=threshold)
```

---

### KS Test (Kolmogorov-Smirnov)

Non-parametric test that compares the empirical CDFs of two samples. Returns a test statistic and p-value.

```python
from scipy.stats import ks_2samp

statistic, p_value = ks_2samp(reference_distribution, current_distribution)
# p_value < 0.05 → reject null hypothesis → distributions differ significantly
```

**Interpreting the p-value:** A small p-value (< 0.05) means the two distributions are statistically unlikely to have come from the same underlying distribution. The KS statistic itself (0 to 1) measures the maximum distance between the two CDFs — larger values indicate greater divergence.

**Caution:** With very large sample sizes, even trivially small differences become statistically significant. Pair the p-value with effect-size measures like PSI or Wasserstein distance.

---

### Wasserstein Distance (Earth Mover's Distance)

Quantifies the "work" required to transform one distribution into another. Unlike the KS test, it captures the magnitude of the shift, not just whether a shift exists.

```python
from scipy.stats import wasserstein_distance

distance = wasserstein_distance(reference_distribution, current_distribution)
# Threshold is domain-specific — compare against historical baselines
```

**When to prefer Wasserstein:** When you need to know *how much* distributions have diverged, not just *whether* they have. Useful for setting graduated alert thresholds.

---

### Hard Constraints (Domain-Specific Invariants)

Some outputs have physical or logical bounds that must always hold, regardless of drift statistics. Violations are immediate bugs, not gradual degradation.

**Examples:**

```python
# Probability outputs must be in [0, 1]
assert 0.0 <= prediction <= 1.0, f"Probability out of bounds: {prediction}"

# Multi-class probabilities must sum to ~1.0
assert abs(sum(class_probs) - 1.0) < 1e-5, f"Probabilities sum to {sum(class_probs)}"

# Physical constraints (e.g., pedestrian speed model)
assert 0.0 <= predicted_speed < 15.0, f"Speed {predicted_speed} m/s exceeds physical bound"

# Type and range checks
assert isinstance(prediction, float), f"Expected float, got {type(prediction)}"
assert predicted_count >= 0, "Count predictions must be non-negative"
```

**Best practice:** Implement hard constraints as the first layer of monitoring. They are cheap to evaluate, never produce false positives when calibrated correctly, and catch catastrophic failures instantly.

---

## Reference Baselines

Drift detection requires a reference distribution to compare against. How you store and version that reference matters.

**Storage approaches:**

| Approach | Pros | Cons |
|----------|------|------|
| Config files (JSON/YAML with histogram bin edges and counts) | Simple, version-controlled, human-readable | Manual updates, limited to summary stats |
| Seed data files (parquet/npy snapshots of training features) | Full distribution available for any test | Storage cost grows with data volume |
| Model registry artifacts (MLflow logged artifacts) | Co-versioned with model, single source of truth | Requires registry infrastructure |
| Delta / Iceberg tables | Scalable, time-travel queries, schema evolution | Heavier infrastructure, overkill for small teams |

**Comparison approach:**

1. At training time, compute and store reference distributions (histograms, quantiles, summary stats) alongside the model artifact
2. At serving time, buffer predictions into time windows (e.g., 1 hour, 1 day)
3. Compare each window against the stored reference using PSI, KS, or Wasserstein
4. Version references with the model — when you retrain, generate new baselines

```python
# Example: storing reference stats with MLflow
import mlflow
import json

ref_stats = {
    "feature_histograms": {name: np.histogram(col, bins=10) for name, col in features.items()},
    "prediction_quantiles": np.quantile(predictions, [0.1, 0.25, 0.5, 0.75, 0.9]).tolist(),
    "prediction_mean": float(predictions.mean()),
    "prediction_std": float(predictions.std()),
}
with open("reference_stats.json", "w") as f:
    json.dump(ref_stats, f)

mlflow.log_artifact("reference_stats.json")
```

---

## Performance Estimation Without Ground Truth

Many production models operate in settings where "correct answers" are ambiguous, expensive to obtain, or delayed by weeks or months (e.g., loan default models, long-horizon forecasts, content recommendation).

### Confidence-Based Performance Estimation (CBPE)

**Concept (from NannyML):** If a model is well-calibrated, its predicted probabilities approximate the true probability of each class. CBPE uses these calibrated probabilities to estimate confusion matrix entries and derive performance metrics (accuracy, F1, ROC AUC) without ground truth.

**When to use:**
- Classification models where labels arrive with significant delay
- Scenarios where labeling is expensive or subjective
- As a leading indicator before ground truth labels become available

**Requirements:**
- The model must output calibrated probabilities (use Platt scaling or isotonic regression if not)
- A reference period with known ground truth to validate the estimator

```python
import nannyml as nml

# Set up CBPE estimator
estimator = nml.CBPE(
    y_pred_proba="predicted_probability",
    y_pred="predicted_class",
    y_true="actual_class",        # only needed for the reference period
    problem_type="classification_binary",
    metrics=["roc_auc", "f1"],
    chunk_size=500,
)

# Fit on reference period (where ground truth is available)
estimator.fit(reference_df)

# Estimate on production data (no ground truth needed)
results = estimator.estimate(production_df)
results.plot().show()
```

---

## Open-Source Monitoring Tools

| Tool | Focus | Key Features | License |
|------|-------|-------------|---------|
| **Evidently AI** | Drift detection, data quality | 100+ pre-built drift metrics, HTML dashboard reports, test suites for CI/CD | Apache 2.0 |
| **NannyML** | Performance estimation | CBPE for ground-truth-free monitoring, drift detection, realized performance tracking | Apache 2.0 |
| **WhyLogs** | Lightweight profiling | Statistical profiles (~1 KB per feature), mergeable across distributed systems, zero-config | Apache 2.0 |

### Integration Paths

**Evidently AI to Prometheus/Grafana:**
```python
from evidently.metrics import DataDriftTable
from evidently.report import Report

report = Report(metrics=[DataDriftTable()])
report.run(reference_data=ref_df, current_data=cur_df)

# Export metrics to Prometheus via custom collector or push gateway
drift_results = report.as_dict()
# Parse drift_results["metrics"] and expose via prometheus_client gauges
```

**WhyLogs to OpenTelemetry:**
```python
import whylogs as why
from opentelemetry import metrics

profile = why.log(df).profile()
view = profile.view()

# Extract stats and push as OTel metrics
meter = metrics.get_meter("ml.monitoring")
for col_name, col_profile in view.get_columns().items():
    gauge = meter.create_gauge(f"feature.{col_name}.mean")
    gauge.set(col_profile.get_metric("distribution").mean.value)
```

**NannyML results to alerts:**
```python
results = estimator.estimate(production_df)
for metric in results.data.columns:
    if "alert" in metric and results.data[metric].any():
        # Send to PagerDuty, Slack, OpsGenie, etc.
        send_alert(f"Estimated performance degradation detected: {metric}")
```

---

## Model Registry Patterns

### Version Tracking

Every deployed model should have a unique, immutable version identifier tied to its training data, code, and hyperparameters.

```python
import mlflow

with mlflow.start_run():
    mlflow.log_params(hyperparams)
    mlflow.log_metrics(eval_metrics)
    mlflow.sklearn.log_model(model, "model", registered_model_name="fraud-detector")
```

### Champion/Challenger Aliases

Use aliases (not version numbers) to manage promotion:

```python
from mlflow import MlflowClient

client = MlflowClient()

# Promote a new model version to Champion
client.set_registered_model_alias("fraud-detector", "champion", version=5)

# Set up a challenger for A/B testing
client.set_registered_model_alias("fraud-detector", "challenger", version=6)

# Load by alias in serving code
champion = mlflow.pyfunc.load_model("models:/fraud-detector@champion")
challenger = mlflow.pyfunc.load_model("models:/fraud-detector@challenger")
```

### A/B Deployment

Route a percentage of traffic to the challenger model and compare live metrics:

```python
import random

def predict(input_data):
    if random.random() < 0.1:  # 10% traffic to challenger
        model = load_model("challenger")
        model_tag = "challenger"
    else:
        model = load_model("champion")
        model_tag = "champion"

    result = model.predict(input_data)
    emit_metric("prediction", value=result, tags={"model": model_tag})
    return result
```

### Rollback

If the champion degrades, roll back by re-pointing the alias:

```python
# Rollback: point champion alias back to previous version
client.set_registered_model_alias("fraud-detector", "champion", version=4)
```

---

## Custom OTel Attributes for ML

No official OpenTelemetry semantic conventions exist for ML workloads. The following custom attribute namespace is recommended for consistency:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `model.name` | string | Registered model name | `"fraud-detector"` |
| `model.version` | string | Model version or alias | `"v5"`, `"champion"` |
| `model.input_count` | int | Number of input features | `42` |
| `model.output_mean` | float | Mean of prediction batch | `0.73` |
| `model.output_p90` | float | 90th percentile of prediction batch | `0.95` |
| `model.drift_psi` | float | Current PSI score vs. reference | `0.18` |
| `pipeline.source` | string | Upstream data pipeline or table | `"feature-store/user-features/v3"` |

**Usage with OpenTelemetry Python SDK:**

```python
from opentelemetry import trace

tracer = trace.get_tracer("ml.inference")

with tracer.start_as_current_span("model.predict") as span:
    span.set_attribute("model.name", "fraud-detector")
    span.set_attribute("model.version", "v5")
    span.set_attribute("model.input_count", len(features))

    predictions = model.predict(features)

    span.set_attribute("model.output_mean", float(predictions.mean()))
    span.set_attribute("model.output_p90", float(np.percentile(predictions, 90)))
    span.set_attribute("model.drift_psi", compute_psi(reference, predictions))
```

---

## Alert Thresholds for Drift

| Method | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| **PSI** | > 0.2 | Warning | Investigate feature distributions, check upstream data pipelines |
| **PSI** | > 0.5 | Critical | Likely data pipeline break — halt predictions or fall back to rules |
| **CUSUM** | Exceeds 3 sigma | Warning | Sustained small shift detected — schedule retraining |
| **KS test** | p-value < 0.05 | Warning | Statistically significant distribution change — review with effect size |
| **KS test** | p-value < 0.001 | Critical | Strong evidence of distribution shift — validate model outputs |
| **Wasserstein** | > domain-specific baseline | Warning | Magnitude of shift exceeds historical norms — compare with PSI |
| **Hard constraint** | Any violation | Critical | Immediate bug — model producing impossible outputs, investigate now |

**Escalation pattern:** Warning triggers investigation and Slack notification. Critical triggers PagerDuty alert and automatic fallback to the previous champion model or rule-based system.

---

## Best Practices

- Monitor inputs *and* outputs — input drift causes output drift, but output drift can also occur from model internals (e.g., stale embeddings)
- Store reference baselines as model artifacts, versioned alongside the model itself
- Use multiple drift methods together — PSI for magnitude, KS for statistical significance, hard constraints for invariants
- Buffer predictions into time windows (1 hour, 1 day) before computing drift — single-request comparisons are too noisy
- Set up CBPE or equivalent estimation when ground truth is delayed by more than a few hours
- Treat drift alerts like test failures — investigate every one, even if the model "seems fine"
- Start with hard constraints and PSI before adding more sophisticated methods — simple monitors catch most production failures
- Tag every prediction with model name and version for retroactive analysis

## Anti-patterns

- "We'll monitor after launch" — drift detection should be part of the deployment checklist, not an afterthought
- Monitoring only accuracy when ground truth is available — accuracy is a lagging indicator; drift metrics are leading indicators
- Using a single drift method and treating it as definitive — each method has blind spots
- Setting alert thresholds without reference to historical baselines — arbitrary thresholds cause alert fatigue or missed detections
- Retraining on a schedule instead of in response to detected drift — wastes compute when the model is fine, misses urgent drift between scheduled runs
- Ignoring hard constraints because "the model is well-trained" — all models can produce invalid outputs under distribution shift
- Logging predictions without storing the input features — makes root-cause analysis impossible when drift is detected
- Treating all features equally in drift monitoring — focus on the features that matter most to model performance (use feature importance as a guide)
