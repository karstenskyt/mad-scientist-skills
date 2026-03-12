# Cognitive Load Assessment

## Purpose

Answer: "Is the interface consuming more working memory than the task inherently requires?"

## Sweller's Cognitive Load Theory (CLT)

John Sweller's cognitive load theory (1988) distinguishes three types of load. The audit's primary target is **extraneous load** — cognitive overhead caused by poor design rather than inherent task complexity.

### Load Taxonomy

| Load Type | Source | Controllable? | Design Goal |
|-----------|--------|---------------|-------------|
| **Intrinsic** | Inherent task complexity. Determined by the domain and the learner's expertise | Not directly — but can be managed through scaffolding | Scaffold with progressive disclosure. Break complex tasks into learnable chunks |
| **Extraneous** | Poor design. Interface decisions that consume working memory without advancing the task | **Yes — this is the audit's primary target** | **Eliminate.** Every instance is a design deficiency |
| **Germane** | Productive learning. Cognitive effort spent building accurate mental models and schemas | Yes — design can encourage or discourage it | **Maximize.** Consistent patterns, meaningful grouping, clear feedback all promote schema building |

### Examples by Load Type

| Scenario | Load Type | Why |
|----------|-----------|-----|
| Comparing two complex statistical distributions | Intrinsic | The comparison is inherently complex regardless of interface |
| Having to remember a value from Page A while on Page B | Extraneous | Interface design forces unnecessary recall |
| Learning that blue = home team, red = away team consistently | Germane | User builds a reusable schema |
| Scrolling back and forth to cross-reference two tables | Extraneous | Interface could place them side-by-side |
| Figuring out which of 12 similar buttons is the right one | Extraneous | Interface could group/label better |
| Understanding that "xT" means expected threat after seeing it with a tooltip | Germane | User learns domain vocabulary in context |

## NASA-TLX Scoring Guide

The NASA Task Load Index (Hart & Staveland, 1988) is a 6-dimension subjective workload assessment. While originally designed for human subjects testing, its dimensions provide a structured framework for expert evaluation of interface cognitive demands.

### Dimensions

| Dimension | Scale | What to evaluate | High score means |
|-----------|-------|-----------------|-----------------|
| **Mental Demand** | 1 (Low) — 20 (High) | How much thinking, deciding, calculating, remembering, searching is required to complete the task? | Interface demands excessive cognitive processing |
| **Physical Demand** | 1 (Low) — 20 (High) | How much clicking, scrolling, typing, mouse movement is required? | Interface demands excessive physical interaction |
| **Temporal Demand** | 1 (Low) — 20 (High) | How much time pressure does the user feel? Is the pace imposed by the system (timeouts, auto-refresh, loading delays)? | System creates urgency or forces waiting |
| **Effort** | 1 (Low) — 20 (High) | How hard does the user have to work to accomplish their level of performance? | Disproportionate effort for the task |
| **Performance** | 1 (Good) — 20 (Poor) | How successful is the user in accomplishing the task? (Note: scale is inverted) | Users feel they failed or got an incomplete result |
| **Frustration** | 1 (Low) — 20 (High) | How insecure, discouraged, irritated, stressed is the experience? | Interface creates negative emotional response |

### Scoring Procedure (Expert Evaluation)

1. Select the 3-5 most critical user tasks (from Phase 2)
2. Walk through each task step-by-step in the actual interface
3. Score each dimension 1-20 based on your expert assessment
4. Calculate the unweighted average across dimensions
5. Flag any single dimension scoring >15 (regardless of average)

### Interpretation

| Average Score | Rating | Action |
|--------------|--------|--------|
| 1-5 | **Low load** | Interface handles cognitive demands well |
| 6-10 | **Moderate load** | Acceptable for expert users; may overwhelm novices |
| 11-15 | **High load** | Redesign needed — significant extraneous load present |
| 16-20 | **Critical load** | Task is likely failing for most users |

## Information Density Heuristics

Quantitative thresholds for detecting cognitive overload. These are guidelines, not hard rules — context matters (a stock trading terminal has different norms than a consumer app).

### Per-Screen Thresholds

| Metric | Threshold | Severity | Rationale |
|--------|-----------|----------|-----------|
| Interactive elements per viewport | >15 | High | Exceeds comfortable scanning capacity |
| Distinct data points visible simultaneously | >30 | Medium | Information overload without grouping |
| Decision points per task step | >3 | High | Choice overload at individual steps |
| Sequential decisions per complete task | >7 | High | Exceeds working memory span for decision chain |
| Visual hierarchy levels on one screen | >4 | Medium | Too many levels — unclear what's most important |
| Text paragraphs before first interactive element | >2 | Medium | Wall of text before action — users skip to action |
| Data table columns visible without scrolling | >10 | Medium | Too many columns to scan effectively |
| Navigation items at one level | >7 | Medium | Miller's Law — more than 7 items need grouping |
| Filters visible simultaneously | >8 | Medium | Filter overload — need grouping or progressive disclosure |
| Form fields visible without scrolling | >10 | Medium | Long forms intimidate — group into sections |

### Cross-Screen Thresholds

| Metric | Threshold | Severity | Rationale |
|--------|-----------|----------|-----------|
| Information user must remember from a previous screen | Any | High | Extraneous load — interface should carry context forward |
| Steps to undo an action | >2 | High | Recovery should be immediate (Ctrl+Z or one click) |
| Pages visited to complete one logical task | >3 | Medium | Task should be co-located unless inherently multi-phase |
| Times user must re-enter the same information | Any | High | Interface should remember and pre-fill |

## Progressive Disclosure Patterns

Progressive disclosure is the primary tool for managing intrinsic load without adding extraneous load.

### Disclosure Levels

| Level | What to show | When to show | Mechanism |
|-------|-------------|-------------|-----------|
| **Level 0** | Core task elements only | Always visible | Main page content |
| **Level 1** | Common options and secondary actions | On request (one click) | Expandable sections, dropdown menus, sidebars |
| **Level 2** | Advanced options, configuration, edge cases | On explicit request | Settings page, advanced mode toggle, modal dialogs |
| **Level 3** | Raw data, debugging info, system internals | Only when needed | Developer tools, export to CSV, API docs |

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| **Everything at Level 0** | All features visible at once — cognitive overload | Move secondary features to Level 1+ |
| **Everything at Level 2** | Core features buried — discoverability failure | Promote core features to Level 0 |
| **Progressive concealment** | Features hidden with no indication they exist | Always show the trigger/label, hide the content |
| **Inconsistent nesting** | Sometimes one click to expand, sometimes two — unpredictable | Standardize disclosure interaction across the interface |
| **Disclosure amnesia** | Expanded sections collapse on page navigation or refresh | Remember disclosure state in session |

## Working Memory Management Checklist

| Check | Extraneous Load Source | Fix |
|-------|----------------------|-----|
| Does the user need to remember data from a previous screen? | Cross-screen recall | Carry forward in context panel, breadcrumb, or summary |
| Does the user need to translate between formats? (e.g., code to label, ID to name) | Format translation | Show human-readable labels; provide ID only on demand |
| Does the user need to calculate something mentally? (e.g., time difference, percentage) | Mental arithmetic | Pre-compute and display the derived value |
| Does the user need to compare items by scrolling back and forth? | Spatial separation of related items | Side-by-side comparison view |
| Does the user need to hold a mental model of system state? | Hidden state | Show state explicitly (status indicators, active filters, selection count) |
| Does the user need to read documentation to use a feature? | Deferred explanation | Contextual help, tooltips, inline examples |
| Does the user need to map between terminology systems? | Vocabulary mismatch | Use the user's domain vocabulary consistently |
