# Task Model Analysis

## Purpose

Answer: "Does the interface's task structure match how users actually think about their tasks?"

## GOMS Framework Reference

GOMS (Goals, Operators, Methods, Selection rules) — Card, Moran & Newell, 1983. A computational framework for modeling human task decomposition in interfaces.

| Element | Definition | Example |
|---------|-----------|---------|
| **Goal** | What the user wants to achieve | "Find how a specific player performed in last week's match" |
| **Operator** | Atomic action the user performs | Click button, type text, read label, scan list, scroll page |
| **Method** | Sequence of operators that achieves a goal | Navigate to player page → select match → read stats |
| **Selection rule** | How the user chooses between alternative methods | "If I know the player name, use search. If browsing, use the roster list." |

### Hierarchical Task Decomposition

Users decompose goals into sub-goals, sub-goals into methods, methods into operators. The interface should mirror this natural hierarchy:

```
Goal: Compare two players' passing accuracy
  Sub-goal 1: Find Player A's stats
    Method: Search by name → Select match → Read passing %
  Sub-goal 2: Find Player B's stats
    Method: Same sequence for Player B
  Sub-goal 3: Compare the values
    Method: Remember Player A's value (working memory) → read Player B's value → compare
```

**Audit red flag:** If sub-goal 3 requires the user to *remember* a value from a previous screen, the interface is forcing a working memory burden. The fix is side-by-side comparison or persistent selection.

### Task Decomposition Worksheet

For each core task identified in Phase 1, complete this worksheet:

```
Task: [name]
User goal (in user's words, not system terms): ___
User's expected sequence (how they'd describe it to a colleague): ___
Interface's actual sequence (count every click/input/decision): ___
Divergence points (where interface forces a different path): ___
Working memory demands (information user must hold across steps): ___
Selection rules (where multiple paths exist): ___
Default method (most prominent/discoverable path): ___
Expert shortcut (keyboard, URL, saved filter): ___
```

## User Expertise Spectrum

Every interface serves users across a spectrum. The task model must accommodate all levels without degrading for any.

### Level 1: Kiosk / First-Time User

**Mental model:** None. Learning the system's vocabulary and structure for the first time.

**GOMS characteristics:**
- High operator count (visual search dominates — scanning for labels, buttons, links)
- No compiled methods (every step requires conscious attention)
- No selection rules (doesn't know alternatives exist)
- Heavy reliance on recognition over recall

**Design requirements:**
- Self-explanatory labels — no jargon, no abbreviations, no assumed knowledge
- Guided workflows — clear "what do I do next?" at every step
- Minimal choices per step — reduce decision paralysis
- Prominent "help" and "back" affordances
- Progressive disclosure — don't show everything at once
- Good empty states — "Start here" is better than a blank screen

**Audit check:** Can someone who has never seen this interface complete the core task in their first session without external help?

### Level 2: Regular User

**Mental model:** Functional. Knows the vocabulary, common paths, and what to expect.

**GOMS characteristics:**
- Methods forming — sequences becoming habitual
- Selection rules emerging — starting to choose between paths
- Some compiled sequences (login, navigation, common filters)
- Mix of recognition and recall

**Design requirements:**
- Consistent patterns that reinforce developing methods — same action, same location, same feedback
- Predictable navigation — don't rearrange menus or move buttons
- Feedback that confirms their developing mental model
- Reasonable defaults that match common use cases
- Recent/frequent items for fast access

**Audit check:** After 5 sessions, can the user complete common tasks 50% faster than their first session? (If not, the interface isn't learnable.)

### Level 3: Power User

**Mental model:** Expert. Has compiled methods for all common tasks. Thinks in terms of the system's capabilities.

**GOMS characteristics:**
- Low operator count (compiled motor sequences, keyboard shortcuts)
- Fast selection rules (instant method choice based on context)
- Keyboard-dominant interaction
- Recall-based navigation (knows where everything is)

**Design requirements:**
- Don't slow them down — no unnecessary confirmation dialogs on routine actions
- Keyboard shortcuts for frequent actions
- Batch operations (select multiple, bulk edit)
- Customizable defaults and saved views
- URL-based deep linking (bookmark specific views/filters)
- Command palette or search-based navigation

**Audit check:** Can a power user complete their daily workflow using only the keyboard? Are there unnecessary speed bumps on routine paths?

### Graceful Degradation

The interface must serve all three levels simultaneously:
- Power-user shortcuts must not confuse first-timers (hidden behind keyboard shortcuts, advanced menus)
- First-timer guidance must not impede power users (dismissible, remembers preferences)
- Regular users must not hit a "cliff" where the interface suddenly becomes complex (progressive disclosure, not a binary novice/expert mode)

## Signs of Task Model Mismatch

These indicators suggest the interface's task model diverges from users' mental models:

| Indicator | What it means | Where to look |
|-----------|--------------|---------------|
| Users consistently click the wrong button first | Button labels or positions don't match expected action | User testing, analytics (click heatmaps) |
| Users navigate to the wrong page for a task | Navigation labels don't map to user goals | Navigation analytics, support tickets |
| Users ask "where do I find X?" for core features | Feature is discoverable only by developers who know the code structure | Support tickets, onboarding feedback |
| Users create workarounds (copy-paste to spreadsheet, screenshots) | Interface doesn't support a task the user considers core | User observation, support tickets |
| Users make the same error repeatedly | The error is predicted by the task model — the interface's affordance suggests the wrong action | Error logs, user testing |
| High abandonment on a specific step | Step is either confusing, overwhelming, or doesn't match the user's expected sequence | Analytics (funnel analysis) |
| Users describe the system differently than developers | Vocabulary mismatch — interface uses implementation terms, not user domain terms | User interviews |

## Common Task Model Anti-Patterns

| Anti-Pattern | Description | Fix |
|-------------|-------------|-----|
| **Implementation-Driven Structure** | Pages organized by database tables or code modules, not user goals | Reorganize around user tasks |
| **Feature Soup** | Every feature equally prominent — no hierarchy of importance | Progressive disclosure; core tasks front and center |
| **Wizard Overuse** | Forcing linear steps when the user's mental model is non-linear | Allow out-of-order completion with clear status |
| **Hidden Defaults** | System applies important defaults the user doesn't know about | Make defaults visible and overridable |
| **Expert Blind Spot** | Interface assumes domain knowledge that regular users lack | Add contextual help, tooltips, examples |
| **Frankenflow** | Task requires visiting 3+ unrelated pages to complete one logical operation | Consolidate related operations |
