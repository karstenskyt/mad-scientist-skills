# Visual Grounding Checklist

## Purpose

Answer: "Does the interface provide sufficient visual information for the user to maintain situation awareness and complete tasks efficiently?"

## Gergle's Grounding Theory

Darren Gergle's research (CollabLab, Northwestern; CHI Academy 2026) demonstrates that shared visual information affects task performance through two distinct mechanisms:

### Mechanism 1: Situation Awareness

**Definition:** The user's perception and comprehension of the current state of the system.

**Three levels** (Endsley 1995, applied to interface design):

| Level | Question | Example | When it fails |
|-------|---------|---------|---------------|
| **Perception** | Can the user see what state the system is in? | Is the filter active? Is the data loading? Is there an error? | Hidden state changes, silent failures, no loading indicators |
| **Comprehension** | Does the user understand what the state means? | What does "3 items selected" imply for the next action? | Ambiguous indicators, missing context, jargon-heavy labels |
| **Projection** | Can the user anticipate what will happen next? | If I click "Apply", what will change? | No preview, no undo warning, surprising side effects |

### Mechanism 2: Conversational Grounding

**Definition:** The shared context between user and system that enables efficient communication.

Gergle's key finding: **not just the availability but the form of visual information differentially affects performance.** Two interfaces can show the same data but ground the user differently based on layout, timing, and visual structure.

**Grounding costs** (Clark & Brennan 1991, adapted for UI):

| Cost | Description | UI Manifestation |
|------|-------------|-----------------|
| **Formulation** | Effort to express an intention | Complex filter construction, multi-step form entry |
| **Production** | Effort to execute the action | Number of clicks, precision required, scroll distance |
| **Reception** | Effort to perceive the system's response | Small visual changes, buried feedback, slow rendering |
| **Understanding** | Effort to comprehend the response | Ambiguous results, unclear error messages, missing context |
| **Repair** | Effort to fix a misunderstanding | Going back, clearing state, re-entering data |

### Gergle's Key Findings for Interface Design

| Finding | Citation | Audit Implication |
|---------|----------|-------------------|
| Delayed visual feedback degrades collaborative performance | Gergle, Kraut & Fussell 2006 | Feedback latency thresholds must be respected (see below) |
| Display characteristics differentially affect spatial tasks | Gergle 2006 | Layout decisions should be evaluated per task type, not one-size-fits-all |
| Visual information form matters more than availability | Gergle et al. 2013 | Showing data is not enough — HOW it's shown determines effectiveness |
| Age-related bias can be embedded in computational systems | Gergle et al. (CHI 2018, Best Paper) | Data visualizations must be evaluated for demographic bias |
| Model positionality affects design outcomes | Gergle et al. (CHI 2022, Best Paper HM) | Audit should consider whose perspective the interface privileges |

## Feedback Latency Thresholds

Based on Nielsen (1993) response time limits, validated by Gergle's visual feedback research:

| Threshold | User Perception | Required Design Response |
|-----------|----------------|------------------------|
| **<100ms** | "Instantaneous" — direct manipulation | Visual acknowledgment of user action (button press state, hover effect, toggle change). No loading indicator needed |
| **100ms-1s** | "System is responding" — noticeable but tolerable | Show immediate acknowledgment (button disables, spinner appears). User maintains feeling of control |
| **1s-10s** | "System is working" — user's attention may wander | Show progress indicator (spinner, progress bar, skeleton screen). User needs assurance the system hasn't frozen |
| **>10s** | "Am I still connected?" — user questions system health | Show progress percentage, estimated time remaining, or allow background processing with notification. Consider allowing the user to continue other tasks |

### Audit Procedure for Latency

1. Identify every user-initiated action in the interface
2. Measure (or estimate) response time for each
3. Check that the feedback mechanism matches the latency threshold
4. Flag any action >100ms without visual acknowledgment (High severity)
5. Flag any action >1s without progress indicator (High severity)
6. Flag any action >10s without progress/estimation (Critical severity)

## Joint Action Storyboard Framework

Gergle et al. (CSCW 2021) — a structured method for visualizing communication grounding costs in interactive workflows.

### How to Use

1. **Select a critical workflow** (from Phase 2 task model mapping)
2. **Draw each step as a panel** — what the user sees, what they do, what changes
3. **For each panel, score the grounding cost:**

| Grounding Dimension | Score 1 (Low) | Score 3 (Medium) | Score 5 (High) |
|--------------------|----|----|----|
| **State visibility** | System state is immediately obvious | State requires scanning to determine | State is hidden or ambiguous |
| **Action clarity** | Next action is obvious from visual cues | Next action requires reading instructions | Next action requires external knowledge |
| **Feedback immediacy** | Response appears within 100ms | Response appears within 1-10s | Response is delayed >10s or absent |
| **Context continuity** | User maintains visual context across steps | Minor context shift (scroll, tab switch) | Major context loss (page reload, navigation) |
| **Recovery cost** | One-click undo or back | Multi-step recovery | Must restart from beginning |

4. **Sum scores per panel** — panels scoring >15 are grounding hotspots
5. **Total across workflow** — workflows scoring >50 need redesign

### Storyboard Template

```
Panel 1: [Step name]
  User sees: [description of visible state]
  User does: [action taken]
  System responds: [what changes visually]
  Grounding cost: State[_] + Action[_] + Feedback[_] + Context[_] + Recovery[_] = [total]
  Notes: [any issues identified]

Panel 2: [Step name]
  ...
```

## State Visibility Checklist

Every system state must be visually communicated to the user:

| State | Must be visible | How to communicate |
|-------|----------------|-------------------|
| **Loading** | Always | Spinner, skeleton, progress bar |
| **Empty** | Always | "No data" message with explanation and next step |
| **Error** | Always | Red/orange indicator + specific message + recovery action |
| **Success** | After user action | Green indicator or toast + what succeeded |
| **Filtered** | When filters are active | Active filter badges, "Showing X of Y", clear all button |
| **Selected** | When items are selected | Highlight, count badge, action bar |
| **Modified (unsaved)** | When user has unsaved changes | Dirty indicator (dot, asterisk), save prompt on navigation |
| **Stale** | When data may be outdated | "Last updated: [timestamp]", refresh button |
| **Offline** | When connectivity is lost | Banner or indicator, queue actions for when online |
| **Permission-limited** | When user can't perform an action | Disabled state with tooltip explaining why |
| **Paginated** | When viewing a subset | "Page X of Y", total count, navigation controls |
| **Sorted** | When data is ordered | Sort indicator on column header, sort direction arrow |

## Visual Anchoring Patterns

Techniques to reduce grounding cost across multi-step workflows:

| Pattern | Purpose | When to use |
|---------|---------|------------|
| **Breadcrumbs** | Show position in hierarchy | Any navigation deeper than 2 levels |
| **Step indicator** | Show progress in multi-step workflow | Any workflow with 3+ sequential steps |
| **Persistent context panel** | Keep key information visible while details change | Master-detail layouts, drill-down analysis |
| **Sticky headers** | Keep column labels visible while scrolling data | Any data table taller than one viewport |
| **Active state highlighting** | Show which item/filter/tab is currently selected | Any selection-based navigation |
| **Mini-map / overview** | Show position within large content | Long documents, large data sets, complex visualizations |
| **Transition animations** | Show spatial relationship between views | Navigation between related content (slide in/out, expand/collapse) |
| **Persistent search/filter bar** | Keep the user's query visible while browsing results | Search results, filtered lists |
