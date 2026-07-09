---
name: drrepo-motion-review
description: Review and propose tasteful motion for DrRepo that clarifies state transitions — not decoration. Covers audit start, loading progress, score reveal, findings disclosure, copy feedback, and sidebar collapse. Rules: prefer CSS transform/opacity, no animation dependencies, no over-animation.
compatibility: opencode
---

# DrRepo Motion Review

Tasteful motion that clarifies state transitions — not decoration.

## Principles
- Motion must **explain state**, not decorate.
- Every animation must have a clear purpose: reveal new content, confirm an action, or indicate a transition.
- Prefer CSS `transform` and `opacity` — GPU-friendly, no layout thrash.
- No animation libraries unless explicitly approved for a specific need.
- No decorative over-animation: no bounce-in on every card, no parallax scrolling, no typewriter effects, no particle effects.

## Transition inventory

### Audit start transition
- When the user submits the form, the idle screen should transition smoothly to the loading state.
- Current behavior: `fade-up` animation on loading skeletons. Acceptable.
- Proposal: fade out the form card, fade in the loading state. No sliding or scaling.

### Loading scanner / progress
- Current behavior: shimmer progress bar at top, skeleton cards, stage pills.
- Acceptable. Do **not** add step-by-step live progress indicators or animated checkmarks unless the backend emits real-time events.
- If real-time progress becomes available, use a horizontal progress bar with `transition-width`.

### Score reveal
- When the diagnosis loads, the overall score hero card appears with `animate-fade-up` and staggered delays.
- Category bars animate width from 0% to target on mount using `transition-width`.
- Acceptable. Do **not** add count-up number animations (costly, distracting).

### Findings / details disclosure
- `<details>` elements use native browser disclosure with hover color transitions on the summary.
- Acceptable. Do **not** animate height of details panels — native works.
- For future: if findings list is long, consider a subtle `max-height` transition with `overflow-hidden`, but only if needed for UX.

### Copy feedback
- Markdown copy button transitions from "Copy" to "Copied" with:
  - A subtle checkmark (`✓`) appearing
  - A short CSS `scale` or `opacity` pulse on the button
  - Reset to "Copy" after 1500ms
- Current implementation is acceptable. Do **not** add toast notifications or floating popovers.

### Sidebar collapse
- Sidebar transitions from expanded width to collapsed width and back.
- Proposal: use `transition-[width]` with `duration-300 ease-out` on the aside element.
- Collapsed icons should remain stable; label text fades out with `opacity` transition.
- Do **not** animate individual nav items sliding in/out.

## General rules
- [ ] Every animation uses `transform` and/or `opacity` unless `width` transition is explicitly needed for progress bars.
- [ ] No JS-driven animation loops (requestAnimationFrame, setInterval).
- [ ] No animation libraries in `package.json`.
- [ ] Tailwind `animate-*` utilities only — no custom `@keyframes` unless approved.
- [ ] Animations respect `prefers-reduced-motion`. If a user has reduced motion enabled, all animations should be disabled or replaced with instant transitions.
- [ ] Staggered reveals use `animation-delay` CSS utilities (existing pattern with `.animate-delay-*` classes), not JS timeouts.
- [ ] No animation on critical path (form submission, API call) that adds latency.
