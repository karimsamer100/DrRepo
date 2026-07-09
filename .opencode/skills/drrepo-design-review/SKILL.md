---
name: drrepo-design-review
description: Review DrRepo frontend screens against the product direction (premium developer diagnostic command center, evidence-first, dark but not flat, strong hierarchy, no generic AI SaaS patterns). Use for design audit, visual review, layout check, component density, status colors, empty state, result page, advisor panel, right rail, repeated card patterns, AI-generated UI smell.
compatibility: opencode
---

# DrRepo Design Review

Review DrRepo frontend screens against these product-direction constraints.

**Product identity:**
- Premium developer diagnostic command center — not a chatbot, not a generic AI SaaS dashboard.
- Evidence-first: data leads, not decoration.
- Dark but not flat: use depth through subtle borders, layered surfaces, not gradients or glassmorphism.
- Strong hierarchy: two-tier label system (major headers `text-xs font-medium text-muted`, micro-labels `text-[11px] uppercase tracking-wider text-faint`).
- No random gradients, glassmorphism, 3D effects, or cinematic intros.
- No fake features: no history, no GitHub URL, no AI toggle, no audit IDs, no ZIP upload, no auth, no PR review, no Push to GitHub unless the backend supports it.

## Checklist

### Layout hierarchy
- [ ] Two-column layout on desktop (main content 2/3, right rail 1/3) used for diagnosis results.
- [ ] Single-column stack on mobile — same order, no reordering tricks.
- [ ] Sidebar is collapsible, icon-only when collapsed, wordmark when expanded.
- [ ] Header is visually quiet — title, API badge (brand-cyan, not health-green), action button that doesn't overpower content.
- [ ] No competing primary actions; the dominant CTA is "Run Diagnostic" on idle screen.
- [ ] Scrollable main area without nested scroll traps.

### Typography
- [ ] Inter for UI text, JetBrains Mono for code/data.
- [ ] Major section headers: `text-xs font-medium text-muted` (e.g. "Findings", "Evidence coverage", "Repository metadata", "Markdown report", "Category scores", "Advisor").
- [ ] Micro-labels: `text-[11px] uppercase tracking-wider text-faint` for field labels, card titles, status chips.
- [ ] Page titles (`h1`, `h2`) remain `text-sm` to `text-lg` with `font-semibold text-primary`.
- [ ] Score hero uses large weight (`text-5xl font-bold`) with label badge.
- [ ] No all-caps body text. No centered prose blocks.

### Spacing
- [ ] Consistent `gap-4`/`gap-6` for section spacing.
- [ ] Cards use `p-3` (compact) to `p-5` (hero).
- [ ] No excessive whitespace that pushes content below the fold on standard 1440px viewports.
- [ ] Right rail components align vertically without large gaps between cards.

### Component density
- [ ] Don't inflate simple cards into full-width banners.
- [ ] Don't repeat the same information at different zoom levels.
- [ ] Tool results in the analyzer status grid are compact chips, not full rows.
- [ ] Metadata card limits itself to key counts and boolean flags.

### Status colors (Tailwind tokens)
- [ ] Health/success: `health` (`#22c55e`)
- [ ] Attention: `attention` (`#eab308`)
- [ ] Warning: `warning` (`#f59e0b`)
- [ ] Error/critical: `error` (`#ef4444`)
- [ ] Brand: `brand` (`#22d3ee`) — used for API badge, focus rings, logo, active nav.
- [ ] Muted: `muted` (`#94a3b8`), Faint: `faint` (`#7c8aa0`)
- [ ] Status badges follow `scoreBgColor`/`scoreColor` from `lib/score.ts`.
- [ ] No custom hex colors in components — use Tailwind config tokens only.

### Empty state (idle screen)
- [ ] Form card is centered, not full-screen hero.
- [ ] On `lg+`, form card and "How it works" panel sit side by side (two-column).
- [ ] "How it works" uses responsive grid (3 steps, 1 column on mobile, 3 on desktop).
- [ ] Autofocus on the path input. Enter submits. No submit-on-blur.

### Result page
- [ ] Overall score is a wide hero card (not a ring/arc), left-aligned score + label badge.
- [ ] Category scores use width-transitioned progress bars.
- [ ] Findings grouped into families with severity badges and expandable details.
- [ ] No raw JSON dumps. No duplicate finding messages.
- [ ] Analyzer status grid is a compact chip cloud, not a table.
- [ ] Markdown report is preview-only with a Copy button that shows feedback.

### Advisor/Remediation panel
- [ ] Deduplicated: same-title actions merged; identical why-it-matters lines deduplicated.
- [ ] "Fix now" items are numbered, with severity-colored left border.
- [ ] "Fix next" items are bulleted with attention-colored dot.
- [ ] Profile name shown as a brand-colored pill.
- [ ] Limitations collapsible at the bottom.

### Right rail
- [ ] Contains: Evidence coverage, Repository metadata, Markdown report preview.
- [ ] Secondary information only — the user should understand the diagnosis without reading the right rail.
- [ ] Components are ordered by importance: evidence → metadata → markdown.

### Repeated card patterns
- [ ] Every card uses the same border (`border-border`), background (`bg-surface` or `bg-surface-2`), and rounded corners (`rounded-lg`).
- [ ] No card has a unique background color unless it conveys status (health/warning/error).
- [ ] No card has a gradient background.
- [ ] Focus rings are consistent: cyan outline with offset.

### AI-generated UI smell
- [ ] No generic "✨ AI-powered" badges.
- [ ] No three-column feature cards with icons and taglines.
- [ ] No gradient hero sections.
- [ ] No "Trusted by X teams" social proof.
- [ ] No "Pricing" or "Enterprise" tier tables.
- [ ] No CTA-stacking (multiple primary buttons competing).
- [ ] No carousels, testimonials, or newsletter signup forms.
