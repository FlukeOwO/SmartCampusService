---
name: ux-ui
description: "Design cohesive, warm education interfaces. Use when building or refining UI for learning centers, campus services, or education platforms."
type: knowledge
lifecycle: active
---

# UX/UI — Warm Education Interfaces

Create interfaces that feel cohesive, inviting, and purposeful. Based on warm cream + atomic orange palettes and clear visual hierarchy.

## Color System

Use a limited palette. Orange is an accent, not a dominant surface.

| Role | Hex | Usage |
|------|-----|-------|
| Background | `#F7F4EF` | Page background (warm cream) |
| Surface | `#FFFFFF` | Cards, modals |
| Surface soft | `#F0EBE3` | Subtle panels, hover |
| Accent | `#E9631A` | Primary buttons, active states, links |
| Accent dark | `#C44E10` | Hover, pressed |
| Accent soft | `#FFF1E6` | Badges, icon backgrounds |
| Text primary | `#1C1917` | Headings |
| Text body | `#44403C` | Body text |
| Text muted | `#78716C` | Secondary info |
| Border | `#E7E5E4` | Card borders, dividers |
| Success | `#16A34A` | Available, approved |
| Warning | `#D97706` | Pending |
| Danger | `#DC2626` | Rejected, error |

**Rules**
- Background stays warm cream, never pure white page.
- Orange appears on buttons, active tabs, icons, and thin accents only.
- One accent color. Do not introduce extra brand colors.
- Status colors (green/amber/red) are reserved for state, not decoration.

## Typography

- Font: `Plus Jakarta Sans` or `Prompt` (Thai support).
- Heading weight: 700. Body: 400–500.
- Base size: 15px. Line height: 1.55.
- Headings use tight tracking (`-0.02em`).
- Max 2 type sizes per card (title + meta).

## Spacing & Layout

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Icon gaps |
| sm | 8px | Tight groups |
| md | 16px | Card padding, form gaps |
| lg | 24px | Section gaps |
| xl | 32px | Page sections |

- Cards: `border-radius: 12px`, padding `1.25rem`, border `1px solid #E7E5E4`.
- Hover: lift `1px`, soft shadow. No dramatic transforms.
- Max content width: `1120px`.

## Components

### Navbar
- Dark warm (`#292524`) or solid accent. Not a multi-stop gradient.
- White text. Active link has subtle pill background.
- Height ~56px. Logo left, links right.

### Cards
- White surface on cream background.
- Title bold, meta muted, one action at bottom.
- Optional thin top accent (2–3px orange) on hover only.

### Buttons
- Primary: solid `#E9631A`, white text, slight shadow.
- Secondary: white surface, border, dark text.
- Hover: darken 8%, no scale jumps.

### Status badges
- Pill shape, soft background + matching text.
- Pending = amber, Approved = green, Rejected = red.

## Visual Hierarchy

1. Page title (large, dark)
2. Primary action (orange button)
3. Content cards (white, clear titles)
4. Meta / secondary (muted)
5. Tertiary links

## Education-Specific Patterns

- Resource cards show: name, location/type, status, one action.
- Booking flows: date first, then time. Equipment prefers day range.
- Empty states: icon + short message + next step.
- Forms: label above input, error below, success as toast.

## Checklist Before Done

- [ ] Page background is warm cream, not pure white
- [ ] Orange is accent only (buttons, active, icons)
- [ ] Cards have consistent padding and radius
- [ ] Text contrast ≥ 4.5:1
- [ ] One clear action per card
- [ ] Spacing uses the token scale
- [ ] Hover states are subtle
- [ ] Thai text remains readable
