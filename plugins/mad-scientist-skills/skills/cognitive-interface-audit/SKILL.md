---
name: cognitive-interface-audit
description: Comprehensive cognitive interface audit with two modes and a single tier. Planning mode designs task models, user expertise mapping, and error tolerance strategy. Audit mode evaluates mental model alignment, consistency, error tolerance (Wood 7-layer defense), cognitive load (NASA-TLX), visual grounding (Gergle), and accessibility. Single tier — cognitive evaluation tools are methodology-based, not software-licensed. Grounded in GOMS (Card, Moran & Newell), error-tolerant design (Wood & Byrne), and visual grounding theory (Gergle, Kraut & Fussell). Use when asked to "UI audit", "UX review", "cognitive audit", "mental model check", "usability review", or "interface audit".
---

# Cognitive Interface Audit

A comprehensive cognitive interface audit with two modes and a single tier:

**Modes:**
- **Planning** (before UI exists) — task model design, user expertise mapping, error tolerance strategy, information architecture
- **Audit** (on existing UI) — mental model alignment, consistency, error tolerance, cognitive load, visual grounding, accessibility

**Single tier:** Unlike security auditing, cognitive interface evaluation is methodology-based (GOMS analysis, heuristic evaluation, NASA-TLX scoring), not tool-licensed. No paid software is required. The value is in the analytical framework, not the scanner.

**Core question:** "Does the interface think the way the user thinks?"

## Academic foundations

This skill synthesizes three research threads into a single audit methodology:

1. **Task Model & Error Tolerance** (Card, Moran & Newell 1983; Wood & Byrne 2002; Rasmussen 1983) — GOMS models predict how users decompose tasks. Wood's 7-layer defense framework predicts where errors occur and what defenses are needed at each stage. Rasmussen's SRK framework classifies errors by cognitive level (skill-based slips, rule-based misapplication, knowledge-based wrong mental model), each requiring different design countermeasures.

2. **Visual Grounding & Common Ground** (Gergle, Kraut & Fussell 2004/2013; Gergle et al. 2021) — Shared visual information affects task performance through two distinct mechanisms: situation awareness (does the user understand system state?) and conversational grounding (does the interface provide enough shared context?). Not just availability but the *form* of visual information differentially affects performance. The Joint Action Storyboard framework maps each interaction to its grounding cost.

3. **Cognitive Load** (Sweller 1988; Hart & Staveland 1988; Madsen 2021) — Every interface decision either consumes or conserves working memory. NASA-TLX provides structured evaluation across 6 dimensions. Sweller's distinction between intrinsic load (inherent task complexity), extraneous load (poor design), and germane load (productive learning) guides where to invest and where to cut.

**Convergence:** Brinck, Gergle & Wood, *Usability for the Web: Designing Web Sites that Work* (Morgan Kaufmann, 2001) — the two primary research threads (Wood's error tolerance, Gergle's grounding) converge in a single prior collaboration: a "pervasive usability" framework with stage-by-stage checklists.

**Key references:**
- Card, Moran & Newell, *The Psychology of Human-Computer Interaction* (1983) — GOMS
- Wood & Byrne, "A Cognitive Approach to Designing Human Error Tolerant Interfaces" (2002) — 7-layer defense
- Wood, "Modeling Human Error for Experimentation, Training, and Error-Tolerant Design" (IITSEC 2002)
- Gergle, Kraut & Fussell, "Using Visual Information for Grounding and Awareness" (*HCI*, 2013)
- Gergle et al., "Joint Action Storyboards" (CSCW 2021) — grounding cost visualization
- Brinck, Gergle & Wood, *Usability for the Web* (Morgan Kaufmann, 2001)
- Rasmussen, "Skills, Rules, and Knowledge" (*IEEE SMC*, 1983) — SRK framework
- Hart & Staveland, "Development of NASA-TLX" (1988) — cognitive load measurement
- Sweller, "Cognitive Load During Problem Solving" (*Cognitive Science*, 1988)
- Nielsen, "10 Usability Heuristics for User Interface Design" (1994)

## When to use this skill

- When the user says "UI audit", "UX review", "cognitive audit", "mental model check", "usability review", "interface audit", or "check the UI"
- Before designing a new interface (planning mode) — to define task models and error tolerance strategy
- On an existing UI (audit mode) — to find mental model misalignment, cognitive overload, and error traps
- Before shipping a new page, workflow, or user-facing feature
- After user complaints about confusion, errors, or abandonment
- When onboarding users with different expertise levels (kiosk vs power user)

## Mode detection

Determine which mode to operate in based on the project state:

| Signal | Mode | Rationale |
|--------|------|-----------|
| User says "design the UI", "plan the interface", "task model" | **Planning** | Architecture-level UI design |
| User says "audit", "review the UI", "check usability", "why are users confused" | **Audit** | Existing interface evaluation |
| No UI code exists yet (wireframes, specs, or nothing) | **Planning** | Nothing to scan — design the task model |
| UI code exists (Streamlit, React, HTML, Gradio, etc.) | **Audit** | Concrete interface to evaluate |
| Both code and a request to "redesign the workflow" | **Both** | Audit current state, plan improvements |

When in doubt, ask the user. If both modes apply, run all phases.

## Severity classification

Every finding must be assigned a severity based on cognitive impact:

| Severity | Criteria | Action | SLA |
|----------|----------|--------|-----|
| **Critical** | Users cannot complete core tasks. Systematic mental model mismatch — the interface's workflow contradicts how users think about the task. No error recovery path exists for common mistakes | Fix immediately before shipping | Block release |
| **High** | Users frequently make errors or abandon tasks. Significant cognitive overhead on primary workflows. Error recovery exists but is non-obvious or lossy | Fix before next release | 1 sprint |
| **Medium** | Users succeed but with unnecessary friction. Inconsistent patterns cause momentary confusion. Error recovery works but requires extra steps | Schedule fix | 2 sprints |
| **Low** | Minor polish, best practice deviation, or optimization for power users. Does not impede task completion | Track in backlog | Best effort |

## Audit process

Execute all applicable phases in order. Skip phases marked for a mode you are not running. Do NOT skip applicable phases. Do NOT claim completion without evidence.

**Phase order:** 0 &rarr; 1 &rarr; 2 &rarr; 3 &rarr; 4 &rarr; 5 &rarr; 6 &rarr; 7 &rarr; 8 &rarr; 9

---

### Phase 0: UI Anti-Pattern Scan (Audit mode)

Fast grep-based scan for common cognitive interface anti-patterns. Runs first to catch obvious issues before deeper analysis. Each match requires manual review — some patterns are intentional in specific contexts.

#### Streamlit patterns

| Pattern | Issue | Severity |
|---------|-------|----------|
| `st.button(` with label containing "Delete" / "Remove" / "Clear" / "Reset" without preceding confirmation logic | Destructive action without confirmation (Wood Layer 1: Prevention) | High |
| `st.error(` with hardcoded string and no `st.button` or link in the same block | Error message without recovery guidance (Wood Layer 5: Correction) | High |
| `st.write("Error` or `st.write("Failed` | Informal error display — no structured error handling | Medium |
| `st.empty()` with no subsequent `.write` / `.markdown` / `.dataframe` call | Potential dead-end placeholder (no content rendered) | Low |
| `st.columns(` with 5+ columns | Cognitive overload — too many parallel elements per viewport | Medium |
| `st.selectbox(` or `st.multiselect(` with inline list of 20+ items | Option overload without search/filter affordance | Medium |
| `st.form_submit_button(` without corresponding `st.success` / `st.error` / `st.toast` in the form handler | Missing submit feedback — user doesn't know if action succeeded | High |
| Long-running operation (SQL query, API call, computation) without `st.spinner` or `st.status` wrapper | Missing progress indicator — user perceives system as frozen | High |
| Different `st.success` / `st.toast` / `st.balloons` patterns across pages for equivalent actions | Inconsistent success feedback (Consistency violation) | Medium |
| `st.page_link` or `st.switch_page` targets that don't match any registered page | Orphaned navigation — link to nowhere | Critical |
| `st.sidebar` with 10+ interactive widgets | Sidebar cognitive overload — too many controls | Medium |
| `st.metric(` with `delta` but no `delta_color` specification | Ambiguous delta direction — user must guess if up is good or bad | Medium |
| `st.tabs(` with 6+ tabs | Tab overload — exceeds working memory chunk limit | Medium |

#### React / JSX patterns

| Pattern | Issue | Severity |
|---------|-------|----------|
| `window.confirm(` | Native confirm dialog — no custom styling, poor UX, breaks flow | Medium |
| `window.alert(` or `alert(` | Native alert — blocks thread, no structured error handling | Medium |
| `onClick` on `<div>` or `<span>` without `role="button"` and `tabIndex` | Non-semantic interactive element — keyboard/screen reader inaccessible | High |
| `<img` without `alt` attribute | Missing image alt text — screen reader blind spot | High |
| Form `onSubmit` without corresponding loading/success/error state management | Missing form feedback | High |
| `useEffect(` with `fetch` / API call and no loading state | Data fetch without loading indicator | Medium |
| `dangerouslySetInnerHTML` | XSS risk AND potential layout surprise (cross-concern: security + cognitive) | Critical |
| `<button` with only an icon (no `aria-label` and no visible text) | Unlabeled action — user must guess the icon's meaning | High |
| `disabled={true}` without tooltip or explanation of why | Disabled control without explanation — user cannot learn requirement | Medium |

#### General UI patterns (any framework)

| Pattern | Issue | Severity |
|---------|-------|----------|
| Same action concept with different labels across files (e.g., "Save" / "Submit" / "Apply" / "Update" for the same operation type) | Inconsistent action vocabulary — violates GOMS selection rule consistency | High |
| Color-only status indicators (`color:` / `background:` with red/green/yellow but no text/icon status) | Color-only differentiation — fails for color-blind users (8% of males) | High |
| Hardcoded pixel-based layouts without responsive breakpoints | Fixed layout — breaks on different screen sizes | Medium |
| `placeholder=` used as the only label for form inputs | Placeholder-as-label — disappears on focus, fails accessibility | High |
| Modal/dialog without visible close button or escape key handler | Trapped modal — no obvious exit (Wood Layer 6: Resumption failure) | Critical |
| `cursor: pointer` on non-interactive elements | False affordance — element looks clickable but isn't | Medium |
| Navigation menu items without visual indication of current page/section | Missing "you are here" indicator — user loses orientation | High |
| Tooltip-only labels on primary actions (not supplementary information) | Essential information hidden behind hover — mobile-hostile, discoverable only by accident | Medium |

For each finding: record file path, line number, pattern matched, severity, the Wood defense layer violated (if applicable), and whether it is a true positive or intentional usage.

**Output:** Anti-pattern findings table organized by framework with file paths, severity, and cognitive impact classification.

---

### Phase 1: Discovery (Both modes)

Explore the project to understand its cognitive interface surface:

- Read `CLAUDE.md`, `README.md`, and any design docs or wireframes
- Identify the UI tech stack (Streamlit, React, Vue, Angular, Gradio, HTML/CSS, etc.)
- Map the **cognitive surface**:
  - **Pages / screens**: List every distinct view the user encounters
  - **User types**: Who uses this interface? What is their expertise level? (kiosk/first-time, regular, power user)
  - **Core tasks**: What are the 3-5 things users primarily come to do?
  - **Task frequency**: Which tasks are performed daily vs weekly vs rarely?
  - **Decision points**: Where must users make choices? How many options at each point?
  - **Data density**: Which screens present the most information? How much data per viewport?
  - **Error-prone paths**: Which workflows are most likely to produce user errors? (complex, multi-step, irreversible)
  - **Navigation structure**: How do users move between screens? Linear, hub-and-spoke, free-form?
  - **Feedback mechanisms**: How does the system communicate success, failure, progress, and state changes?
  - **External dependencies**: Does the UI depend on external data, APIs, or other systems that introduce latency or failure modes?
  - **Collaborative features**: Do multiple users interact with the same data? (affects grounding requirements)
  - **Domain vocabulary**: What specialized terms does the interface use? Do they match the users' domain language?

**Output:** Cognitive surface summary listing all pages, user types, core tasks, and identified risk areas for deeper analysis.

---

### Phase 2: Task Model Mapping (Both modes)

Apply GOMS-based analysis to decompose user tasks and identify where the interface's task structure diverges from users' mental models.

Load `templates/task-model-analysis.md` for the full GOMS methodology reference, user expertise spectrum guide, and task decomposition worksheet.

**Planning mode:** Design the task model before building:
- What are the user's top-level goals? (not features — goals)
- How does the user mentally decompose each goal into sub-tasks?
- What is the natural sequence of operations for each sub-task?
- Where do users have selection rules (multiple methods to achieve the same goal)?
- Which method should the interface make default? (frequency-based: most common method = easiest path)

**Audit mode:** Evaluate the existing task model:

| Check | What to look for | Severity if misaligned |
|-------|-----------------|----------------------|
| Goal-task alignment | Do page titles and section headers match user goals (not implementation concepts)? | High |
| Task decomposition match | Does the interface's step sequence match how users naturally think about the task? | Critical |
| Operation granularity | Are individual operations (clicks, selections, inputs) at the right level — not too atomic, not too bundled? | Medium |
| Selection rule clarity | When multiple paths exist, is the most common one most prominent? | High |
| Vocabulary alignment | Do labels, buttons, and headers use the user's domain language, not developer jargon? | High |
| Progressive complexity | Can novices complete core tasks without encountering power-user features? | High |
| Chunk boundaries | Are related operations grouped together? Do logical chunks fit within working memory (4 +/- 1 items per group)? | Medium |
| Interruption recovery | If the user is interrupted mid-task, can they resume without starting over? | High |

#### User expertise spectrum

Every interface serves users across a spectrum. The audit must evaluate task model fit at each level:

| Level | Mental Model | GOMS Characteristics | Design Requirement |
|-------|-------------|---------------------|-------------------|
| **Kiosk / First-time** | No pre-existing model. Learning the system's vocabulary and structure | High operator count, no compiled methods, heavy reliance on visual search | Self-explanatory labels, guided workflows, minimal choices per step |
| **Regular** | Functional model. Knows the vocabulary and common paths | Methods forming, selection rules emerging, some compiled sequences | Consistent patterns that reinforce developing methods, predictable navigation |
| **Power user** | Expert model. Has compiled methods for all common tasks | Low operator count, fast selection rules, keyboard shortcuts, batch operations | Don't slow them down. Provide shortcuts, keyboard navigation, bulk actions, customizable defaults |

The interface must **degrade gracefully** across all three levels. A power-user shortcut must not confuse a first-timer. A first-timer's guided flow must not impede a power user.

**Output:** Task model analysis for each core task, with expertise spectrum evaluation and identified misalignment points.

---

### Phase 3: Consistency & Convention (Audit mode)

Evaluate whether the interface uses the same patterns for the same operations, and leverages existing user knowledge (platform conventions, domain standards).

| Check | What to look for | Severity if violated |
|-------|-----------------|---------------------|
| Action vocabulary | Same operation uses the same label everywhere (not "Save" on one page and "Submit" on another) | High |
| Icon consistency | Same icon means the same thing everywhere. No icon used for two different actions | High |
| Layout patterns | Similar pages have similar layouts. Data tables, forms, and detail views follow the same template | Medium |
| Color semantics | Colors convey the same meaning everywhere (red = error/danger, green = success, etc.) | High |
| Interaction patterns | Same gesture/click pattern produces same type of result (e.g., clicking a row always opens detail) | High |
| Platform conventions | Interface follows platform norms (web: links are blue/underlined, buttons look clickable; mobile: swipe, pull-to-refresh) | Medium |
| Domain conventions | Interface follows domain-specific conventions (e.g., in soccer analytics: pitch orientation, color coding by team, standard stat abbreviations) | High |
| Error message format | All errors use the same structure (icon + message + recovery action) | Medium |
| Loading patterns | Progress indication uses the same mechanism throughout (spinner, skeleton, progress bar) | Medium |
| Empty states | "No data" scenarios handled consistently across all views | Medium |
| Navigation patterns | Back/forward/breadcrumb behavior is predictable and consistent | High |
| Keyboard shortcuts | If shortcuts exist, they follow platform conventions (Ctrl+S = save, Escape = cancel/close) | Medium |

#### Grep patterns for consistency violations

| Pattern | What it catches |
|---------|-----------------|
| Multiple distinct `st.success(` / `st.error(` / `st.warning(` / `st.toast(` message formats across pages | Inconsistent feedback patterns |
| Varying `st.button(` labels for semantically equivalent actions across pages | Action vocabulary drift |
| Inconsistent `st.header` / `st.subheader` / `st.title` hierarchy across pages | Heading level inconsistency |
| Mix of `st.dataframe` and `st.table` for similar data displays | Display component inconsistency |
| Different date/number formatting across pages | Data formatting inconsistency |

**Output:** Consistency findings table with pattern, locations, severity, and recommended standard.

---

### Phase 4: Error Tolerance (Both modes)

Evaluate every critical task path against Wood & Byrne's 7-layer defense framework. Classify error risks by Rasmussen's SRK level.

Load `templates/error-tolerance-checklist.md` for the full 7-layer framework reference, Rasmussen SRK classification guide, and Reason's error mechanism taxonomy.

**Planning mode:** Design error tolerance strategy:
- For each critical task, identify the most likely error classes (SRK level)
- Design defenses at each of the 7 layers
- Determine which errors are preventable by design constraints vs which need detection and recovery
- Plan the cost/benefit of each defense (some prevention measures add friction)

**Audit mode:** For each critical task path identified in Phase 2:

| Layer | Audit Question | What to check | Severity if missing |
|-------|---------------|---------------|---------------------|
| **1. Prevention** | Can this error class be eliminated by design constraints? | Input masks, disabled invalid options, type constraints, required fields, sane defaults | High |
| **2. Reduction** | Does the task model minimize opportunities for this error? | Step count minimization, progressive disclosure, smart defaults, auto-fill, disambiguation | Medium |
| **3. Detection** | Will the user notice something went wrong? | Inline validation, visual state changes, confirmation dialogs, diff views before commit | Critical |
| **4. Identification** | Can the user understand *what* went wrong? | Specific error messages (not "Something went wrong"), field-level validation, contextual help | High |
| **5. Correction** | Is fixing the error straightforward and discoverable? | Edit-in-place, undo button, "fix this" links, pre-populated correction forms | High |
| **6. Resumption** | Can the user return to their task without losing context? | State preservation after error, no page reload on validation failure, draft saving, back button works | High |
| **7. Mitigation** | When all else fails, is damage minimized? | Soft delete (trash), version history, audit trail, confirmation on irreversible actions | Critical for destructive paths |

#### Rasmussen SRK error classification

Different cognitive levels produce different error types requiring different defenses:

| SRK Level | Error Type | Example | Best Defense Layers |
|-----------|-----------|---------|---------------------|
| **Skill-based** (slips) | Correct intention, wrong execution. Habitual action fires incorrectly | Clicking "Delete" instead of adjacent "Edit" button | Prevention (spacing/grouping), Detection (confirm dialog) |
| **Rule-based** (mistakes) | Wrong rule selected for the situation. User applies a familiar procedure in the wrong context | Applying a filter meant for one data view to a different view because the UI looks similar | Reduction (visual differentiation), Identification (clear context labels) |
| **Knowledge-based** (errors) | Wrong mental model. User fundamentally misunderstands what the system does or how it works | User expects "Save" to publish immediately because that's how their previous tool worked | Prevention (explicit state labels), Detection (preview before publish) |

#### Reason's error mechanisms

Two mechanisms from Reason's taxonomy that Wood identified as particularly relevant to interface design:

- **Similarity matching** — A wrong-but-similar rule fires because the interface makes two different contexts look too similar. *Audit:* identify pages or workflows that look alike but behave differently.
- **Frequency gambling** — The most-used routine executes even when context demands otherwise. *Audit:* identify workflows where the most common action is also the most dangerous in certain contexts (e.g., "Confirm" button always means "proceed" except on one screen where it means "delete permanently").

**Output:** Error tolerance assessment per critical task path, with SRK classification, defense layer gaps, and recommended fixes.

---

### Phase 5: Cognitive Load Assessment (Both modes)

Evaluate information density, decision complexity, and working memory demands across all screens.

Load `templates/cognitive-load-assessment.md` for the full NASA-TLX scoring guide, Sweller's cognitive load taxonomy, and information density heuristics.

**Planning mode:** Design for minimal extraneous load:
- What is the intrinsic complexity of each task? (irreducible — determined by the domain)
- Where will extraneous load creep in? (reducible — determined by the design)
- How can germane load be maximized? (productive — schema building, pattern recognition)
- What progressive disclosure strategy will be used? (show complexity only when needed)

**Audit mode:** Score each screen against cognitive load indicators:

| Check | What to look for | Threshold | Severity if exceeded |
|-------|-----------------|-----------|---------------------|
| Interactive elements per viewport | Buttons, inputs, selectors, toggles visible without scrolling | >15 interactive elements | High |
| Decision points per task | Choices the user must make to complete a single task | >5 sequential decisions | High |
| Information density | Distinct data points visible simultaneously | >30 distinct values per viewport | Medium |
| Visual hierarchy levels | Number of distinct heading/text sizes used on one screen | >4 levels | Medium |
| Required recall | Information user must remember from a previous screen to complete current task | Any cross-screen recall without reference | High |
| Simultaneous comparisons | Number of items user must compare at once | >7 items (Miller's Law) | Medium |
| Mode indicators | Number of active modes/states the user must track | >3 simultaneous modes | High |
| Text density | Paragraph-length instructions or descriptions | >3 sentences of instruction per action | Medium |
| Data table columns | Visible columns in a data table | >10 columns without horizontal scroll | Medium |
| Filter/parameter count | Number of filters or parameters visible simultaneously | >8 without grouping/progressive disclosure | Medium |

#### NASA-TLX dimensions (for manual assessment)

When deeper evaluation is warranted, score each critical workflow on 6 dimensions (1-20 scale):

| Dimension | Question | High Score Indicates |
|-----------|---------|---------------------|
| **Mental Demand** | How much thinking, deciding, calculating, remembering, searching was required? | Interface demands too much cognitive processing |
| **Physical Demand** | How much clicking, scrolling, typing, mouse movement was required? | Interface demands too much physical interaction |
| **Temporal Demand** | How much time pressure did you feel? Was the pace imposed by the system? | System creates artificial urgency or slowness |
| **Effort** | How hard did you have to work to accomplish your level of performance? | Task completion requires disproportionate effort |
| **Performance** | How successful were you in accomplishing what you were asked to do? | Users feel they failed or got a partial result |
| **Frustration** | How insecure, discouraged, irritated, stressed was the experience? | Interface creates negative emotional response |

#### Sweller's load taxonomy — design implications

| Load Type | Source | Design Goal |
|-----------|--------|-------------|
| **Intrinsic** | Inherent task complexity (domain-determined) | Cannot reduce — but can scaffold with progressive disclosure |
| **Extraneous** | Poor design (interface-determined) | **Eliminate.** This is the audit's primary target |
| **Germane** | Productive learning (schema-building) | **Maximize.** Consistent patterns help users build accurate mental models |

**Output:** Cognitive load assessment per screen with dimension scores, threshold violations, and extraneous load reduction recommendations.

---

### Phase 6: Visual Grounding & Feedback (Audit mode)

Evaluate whether the interface provides sufficient visual grounding for situation awareness and efficient task completion.

Load `templates/visual-grounding-checklist.md` for the full Gergle grounding theory reference, feedback latency thresholds, and Joint Action Storyboard methodology.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| System state visibility | Can the user tell what state the system is in at a glance? (loading, ready, error, empty, filtered) | Critical |
| Action feedback | Every user action produces visible feedback within 100ms (click acknowledgment) and meaningful feedback within 1000ms (result or progress) | High |
| Progress indication | Operations >1 second show progress; operations >10 seconds show estimated time or percentage | High |
| State change visibility | When data changes, is the change visually highlighted? (not just silently updated) | Medium |
| Context preservation | After an action, does the user maintain their visual context? (no unexpected scroll jumps, page reloads, or focus changes) | High |
| Spatial stability | Do UI elements stay in the same position? Moving targets cause motor errors and disorientation | High |
| Error visibility | Error states are visually distinct from normal states — not just a small text change | High |
| Filter/selection visibility | Active filters and selections are always visible — user knows what subset of data they're seeing | Critical |
| Undo visibility | If undo is available, the affordance is visible immediately after the action (not buried in a menu) | Medium |
| Empty state messaging | When no data matches, the screen explains why and suggests next steps (not just a blank area) | High |
| Data freshness | If data can be stale, the last-updated timestamp is visible | Medium |
| Collaborative awareness | In multi-user contexts: who else is viewing/editing? Are changes by others visible in real-time? | High (if collaborative) |

#### Feedback latency thresholds (Gergle + Nielsen)

| Threshold | User Perception | Design Requirement |
|-----------|----------------|-------------------|
| **<100ms** | Instantaneous | Direct manipulation feedback (button press, hover, toggle) |
| **100ms-1s** | System is working | Show acknowledgment (button state change, spinner start) |
| **1s-10s** | Noticeable delay | Show progress indicator (spinner, progress bar) |
| **>10s** | System might be broken | Show progress percentage, estimated time, or allow background processing with notification |

#### Joint Action Storyboard analysis

For complex multi-step workflows, apply Gergle's Joint Action Storyboard framework:

1. Map each step of the workflow as a panel in the storyboard
2. For each panel, identify the **grounding cost** — what cognitive work must the user do to understand the current state and determine their next action?
3. Flag panels where grounding cost is high: the user must remember information from previous panels, infer hidden state, or interpret ambiguous feedback
4. Reduce grounding cost by adding visual anchors: persistent state indicators, breadcrumbs, progress visualization, contextual summaries

**Output:** Visual grounding findings with feedback latency analysis, grounding cost hotspots, and recommended visual anchors.

---

### Phase 7: Accessibility & Inclusion (Audit mode)

Evaluate whether the interface is usable by people with different abilities, demographics, and devices.

Load `templates/accessibility-inclusion.md` for the full WCAG 2.1 AA checklist, demographic bias patterns, and assistive technology compatibility checks.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Keyboard navigation | All interactive elements reachable and operable via keyboard (Tab, Enter, Escape, Arrow keys) | Critical |
| Focus indicators | Visible focus ring on all interactive elements when navigating by keyboard | High |
| Screen reader compatibility | All content has semantic HTML structure; images have alt text; form inputs have labels; ARIA roles where needed | High |
| Color contrast | Text meets WCAG AA contrast ratios (4.5:1 normal text, 3:1 large text) | High |
| Color-only indicators | No information conveyed by color alone — always paired with text, icon, or pattern | High |
| Responsive layout | Interface functions on screen widths from 320px to 4K | Medium |
| Touch targets | Interactive elements are at least 44x44px on touch devices | Medium |
| Text scaling | Interface remains usable at 200% browser zoom | Medium |
| Reduced motion | Respects `prefers-reduced-motion` — no essential information conveyed only through animation | Medium |
| Language clarity | Instructions use plain language; jargon is defined or has tooltips; reading level appropriate for audience | Medium |
| Error messages | Errors are announced to screen readers (via `aria-live` or equivalent) | High |
| Time limits | If the interface has timeouts, users can extend or disable them | High |
| Demographic bias | Data visualizations don't embed bias (e.g., gendered defaults, culturally specific color meanings, age-biased interaction patterns) | Medium |

#### Automated checks (grep-detectable)

| Pattern | Framework | Issue |
|---------|-----------|-------|
| `<img` without `alt=` | HTML/JSX | Missing alt text |
| `<input` without `<label` or `aria-label` | HTML/JSX | Unlabeled form field |
| `<div` or `<span` with `onClick` but no `role` / `tabIndex` | React/JSX | Non-semantic interactive element |
| `color:` with red/green/yellow as sole differentiator (no accompanying text or icon) | CSS | Color-only status indicator |
| `outline: none` or `outline: 0` on focusable elements | CSS | Removed focus indicator |
| `user-select: none` on text content | CSS | Prevents text selection (assistive technology) |
| `tabindex="-1"` on interactive elements | HTML | Removed from keyboard tab order |
| `aria-hidden="true"` on content with visible text | HTML | Screen reader content hidden |

**Output:** Accessibility findings with WCAG criteria references, automated check results, and remediation steps.

---

### Phase 8: Information Architecture (Audit mode)

Evaluate the navigation structure, error recovery paths, and overall information organization.

| Check | What to look for | Severity if missing |
|-------|-----------------|---------------------|
| Navigation coherence | Every page is reachable from the main navigation. No orphan pages | High |
| Breadcrumb / location | User always knows where they are in the hierarchy | High |
| Back button behavior | Browser back button works as expected (no broken history states) | Critical |
| Deep linking | Key views can be bookmarked and shared via URL | Medium |
| Search / find | For interfaces with >10 pages or >100 items, search functionality exists | Medium |
| Progressive disclosure | Complex features are hidden behind expandable sections, not visible by default | Medium |
| Error recovery navigation | After an error, the user can navigate away and return without data loss | High |
| Cross-reference links | Related information is linked (e.g., from a player stats page to that player's match history) | Medium |
| Consistent hierarchy | Same number of clicks to reach equivalent-importance pages | Medium |
| URL structure | URLs are human-readable and reflect the navigation hierarchy | Low |
| Help discoverability | Help, documentation, or tooltips are findable when the user is confused | Medium |
| Onboarding | First-time users have a clear starting point (not a blank screen with too many options) | High |

#### Navigation anti-patterns

| Pattern | Issue | Severity |
|---------|-------|----------|
| Hidden hamburger menu as only navigation on desktop | Desktop users expect visible navigation — hamburger is a mobile convention | Medium |
| More than 3 levels of nested navigation | Users lose orientation beyond 3 levels | High |
| Navigation labels that are ambiguous without context (e.g., "Overview", "Details", "More") | Labels must be self-describing — user shouldn't need to click to understand | Medium |
| Pagination without alternative (no "show all" or "jump to page" option) | Users scanning for specific items are forced to page through sequentially | Low |
| Tab-based navigation with dependent state (selecting Tab A changes what Tab B shows) | Hidden state coupling — user doesn't expect tab selection to affect other tabs | High |

**Output:** Information architecture findings with navigation map, identified dead ends, and restructuring recommendations.

---

### Phase 9: Findings Report (Both modes)

Generate the final report. The format depends on the mode.

#### Planning mode report

Present the task model design and cognitive interface strategy:

```markdown
## Cognitive Interface Strategy — [System Name]

### Cognitive Surface Summary
- Pages/screens: [count and list]
- User types: [kiosk/regular/power user breakdown]
- Core tasks: [3-5 primary user goals]
- Task frequency: [daily/weekly/rare distribution]
- Identified risk areas: [high complexity, error-prone, high data density]

### Task Model Design
| Goal | Sub-tasks | Operations | Default Method | Expert Shortcut |
|------|-----------|------------|----------------|-----------------|
| [User goal] | [Decomposition] | [Clicks/inputs] | [Primary path] | [Power user path] |

### Error Tolerance Strategy
| Critical Task | Most Likely Error (SRK) | Prevention | Detection | Recovery |
|--------------|------------------------|------------|-----------|----------|
| [Task name] | [Skill/Rule/Knowledge] | [Design constraint] | [Feedback mechanism] | [Undo/fix path] |

### Cognitive Load Budget
| Screen | Intrinsic Load | Extraneous Load Sources | Progressive Disclosure Plan |
|--------|---------------|------------------------|----------------------------|
| [Page] | [Inherent complexity] | [Design-added friction] | [What to hide by default] |

### Design Recommendations
| # | Area | Recommendation | Priority | Framework |
|---|------|----------------|----------|-----------|
| 1 | Task Model | [Specific recommendation] | Critical | GOMS |
| 2 | Error Tolerance | [Specific recommendation] | High | Wood 7-layer |

### Interface Design Checklist
- [ ] Task models designed for all core user goals
- [ ] User expertise spectrum considered (kiosk to power user)
- [ ] Error tolerance strategy for each critical task path
- [ ] Cognitive load budget per screen
- [ ] Consistency standards defined (vocabulary, layout, feedback)
- [ ] Visual grounding requirements specified (feedback latency, state visibility)
- [ ] Accessibility requirements defined (WCAG AA minimum)
- [ ] Information architecture designed with navigation map
```

#### Audit mode report

Present concrete findings with cognitive impact assessment:

```markdown
## Cognitive Interface Audit Report — [System Name]

### Executive Summary
- Total findings: X
- Critical: X | High: X | Medium: X | Low: X
- Fixed during audit: X
- Remaining: X
- Primary cognitive risk: [summary of biggest user-facing issue]

### Findings
| # | Severity | Phase | File:Line | Description | Framework | Status |
|---|----------|-------|-----------|-------------|-----------|--------|
| 1 | Critical | Phase 4 | pages/edit.py:42 | Destructive action without confirmation — no Prevention or Detection layer | Wood L1/L3 | Fixed |
| 2 | High | Phase 2 | pages/search.py:18 | Search workflow requires 6 sequential decisions — exceeds cognitive load threshold | NASA-TLX | Recommended |

### Task Model Assessment
| Core Task | Model Alignment | Expertise Coverage | Issues |
|-----------|----------------|-------------------|--------|
| [Task] | Aligned / Misaligned | Kiosk: Y/N, Regular: Y/N, Power: Y/N | [Summary] |

### Error Tolerance Coverage
| Critical Task | L1 | L2 | L3 | L4 | L5 | L6 | L7 | SRK Level |
|--------------|----|----|----|----|----|----|----|-----------|
| [Task] | [tick/gap] per layer | | | | | | | [S/R/K] |

### Cognitive Load Heatmap
| Screen | Elements | Decisions | Data Points | Load Rating |
|--------|----------|-----------|-------------|-------------|
| [Page] | [count] | [count] | [count] | Low/Medium/High/Critical |

### Phase Coverage Matrix
| Phase | Checks Run | Findings | Key Result |
|-------|-----------|----------|------------|
| Phase 0: Anti-Patterns | [X patterns scanned] | [Y findings] | [summary] |
| Phase 1: Discovery | [X surfaces mapped] | [Y risk areas] | [summary] |
| Phase 2: Task Model | [X tasks analyzed] | [Y misalignments] | [summary] |
| Phase 3: Consistency | [X checks] | [Y violations] | [summary] |
| Phase 4: Error Tolerance | [X task paths x 7 layers] | [Y gaps] | [summary] |
| Phase 5: Cognitive Load | [X screens scored] | [Y overloaded] | [summary] |
| Phase 6: Visual Grounding | [X checks] | [Y findings] | [summary] |
| Phase 7: Accessibility | [X checks] | [Y findings] | [summary] |
| Phase 8: Info Architecture | [X checks] | [Y findings] | [summary] |

### Cognitive Interface Maturity Rating
- **Checks passed**: X/Y (Z% coverage)
- **Overall**: [Excellent / Good / Needs Work / Critical Gaps]
- **Strongest area**: [phase/area]
- **Weakest area**: [phase/area]

### Ready for users: Yes / No (with blockers)
```

---

## Important rules

- **Fix as you go.** When audit mode finds a Critical or High issue that you can fix in code (anti-pattern, missing feedback, inconsistency), fix it immediately. Don't just report — remediate.
- **Evidence-based claims.** Every finding must include file path, line number, or specific evidence. Never say "users probably find this confusing" without identifying the specific cognitive mechanism (SRK level, defense layer, load type).
- **User-centered, not developer-centered.** Evaluate the interface from the user's perspective, not the developer's. "It works" is not the same as "users can complete their task efficiently and without errors."
- **Expertise spectrum awareness.** Every task model finding must consider the full spectrum (kiosk to power user). A feature that delights power users may paralyze first-timers.
- **Framework attribution.** Each finding should reference the specific framework that identifies it (GOMS, Wood 7-layer, NASA-TLX, Gergle grounding). This is what distinguishes a cognitive audit from generic UX feedback.
- **Quantify cognitive cost.** Where possible, count: elements per viewport, decisions per task, steps to recover from an error, milliseconds of feedback delay. Numbers are more actionable than "this feels heavy."
- **No assumptions.** Read the actual UI code. Render pages if possible. Don't assume the interface works well because the framework has good defaults.
- **Respect the design intent.** If a design choice is intentional (e.g., data density is high because users are analysts who need it), note it and evaluate whether the density is *managed* (progressive disclosure, filters, good hierarchy) rather than flagging density itself as a problem.
- **Scope awareness.** Don't flag framework-managed UX as a finding (e.g., Streamlit's built-in error handling, React's form state management) unless the developer has overridden it poorly.
- **Prioritize.** Fix Critical and High findings. Track Medium and Low in the backlog. A perfect Phase 7 (accessibility) doesn't matter if Phase 2 (task model) has Critical misalignments.
- **The interface should be invisible.** The best outcome of this audit is that users complete tasks without thinking about the interface at all. Every finding should point toward that goal.
