---
name: drrepo-ux-simplification
description: Review DrRepo UX flow and reduce clutter. Checklist covers: path-to-diagnosis clarity, bad-repo handling, evidence grouping, advisor readability, right-rail simplicity, and no unsupported features (history, AI toggle, GitHub login). Use for UX audit, simplification pass, flow review.
compatibility: opencode
---

# DrRepo UX Simplification

Review DrRepo UX flow and reduce clutter. The product must feel like a diagnostic tool, not a dashboard platform.

## Core flow

### 1. User understands the action in under 5 seconds
- [ ] On first load, the user sees: "Run repository diagnostic" form with a path input.
- [ ] The "How it works" panel explains the three-step pipeline in plain language.
- [ ] No onboarding tour, tooltips, or feature banners.
- [ ] Single clear CTA: "Run Diagnostic".

### 2. Local path → run diagnostic → diagnosis → fix first
- [ ] Flow is linear: enter path → loading → diagnosis result.
- [ ] "New diagnostic" button resets to idle with one click.
- [ ] Sidebar "Audit" button also resets to idle.
- [ ] No intermediate confirmation dialogs. No "Are you sure?" modals.
- [ ] Error state is clear: shows the error message and a "Try again" button that resets.

### 3. Bad repos don't become overwhelming
- [ ] If a repo has many findings, they are grouped into families (security, testing, docs, structure).
- [ ] Each family shows a severity badge, family name, and count.
- [ ] Details are collapsed by default — the user opens one family at a time.
- [ ] Hard flags appear in a compact "Attention areas" banner at the top of results.
- [ ] Do **not** dump all findings in a raw table or JSON view.

### 4. Group evidence instead of repeating findings
- [ ] `getFindingFamilies()` groups findings by tool family (README, structure, pytest, coverage, bandit, ruff, radon).
- [ ] Inside each family, findings with the same code or message are merged into code groups with a count.
- [ ] File locations are shown compactly (first 3, "+N more").
- [ ] Do **not** list every individual finding as a separate card.

### 5. Advisor reads like a remediation plan
- [ ] "Fix now" items are numbered, actionable, and explained with "Why it matters" notes.
- [ ] Duplicate action titles are merged into one group.
- [ ] Duplicate "why it matters" notes within a group are deduplicated.
- [ ] "Fix next" items are less prominent, secondary.
- [ ] Profile name is clearly shown as a badge.
- [ ] Limitations are collapsed by default at the bottom.
- [ ] No AI chat interface. No "Ask the advisor" prompt.

### 6. Right rail is secondary
- [ ] Evidence coverage, repository metadata, and markdown report live in the right column (desktop) or below main content (mobile).
- [ ] The user can understand the full diagnosis without reading the right rail.
- [ ] No interactive widgets in the right rail — read-only summaries.
- [ ] Markdown report is preview-only with a Copy button.

### 7. No unsupported features
- [ ] No history or audit log (no backend endpoint).
- [ ] No GitHub login, OAuth, or URL-based repo input (no backend support).
- [ ] No AI toggle or model selector (not exposed by API).
- [ ] No audit IDs, permalinks, or sharing (no persistence).
- [ ] No ZIP upload or multi-file drop.
- [ ] No PR review or "Push to GitHub" (no Git integration).
- [ ] No auth, user accounts, or team management.
- [ ] No export-to-PDF or print layout.
- [ ] No dark/light mode toggle — dark only.

## Simplification checklist (run before every frontend PR)

- [ ] Can I remove any element without reducing clarity?
- [ ] Is every piece of text necessary? Can I shorten labels?
- [ ] Does any component repeat information already shown elsewhere?
- [ ] Is every state (idle, loading, error, done) handled with minimal UI?
- [ ] Are there any generic AI-dashboard patterns (three-column feature cards, hero gradients, social proof)?
- [ ] Does the flow feel like a tool (fast, focused) or a website (browsing, exploring)?
- [ ] Can a new user complete an audit without reading documentation?

## Anti-patterns to avoid
- Opening modals for simple actions.
- Nesting scrollable areas inside scrollable areas.
- Using tooltips to explain obvious UI.
- Adding a second action button that competes with the primary CTA.
- Showing raw data tables when a grouped summary would suffice.
- Adding a "Settings" or "Preferences" page without a clear need.
- Adding a "Dashboard" or "Home" page that just duplicates the idle screen.
- Wrapping content in unnecessary card containers.
