---
name: ux-ui
description: "Design cohesive education interfaces. Use when building or refining UI for learning centers, campus services, or education platforms."
type: knowledge
lifecycle: active
---

# UX/UI — Education Interfaces

Create interfaces that are cohesive, readable, and purposeful. Based on Smart Campus iterations.

## Color System

| Role | Hex | Usage |
|------|-----|-------|
| Background | `#F7F4EF` | Page background (warm cream) |
| Surface | `#FFFFFF` | Cards, modals, drawers |
| Accent | `#E9631A` | Primary buttons, active tabs, icons |
| Accent hover | `#C44E10` | Button hover |
| Accent soft | `#FFF1E6` | Badges, icon backgrounds |
| Text primary | `#1C1917` | Headings |
| Text body | `#44403C` | Body text |
| Text muted | `#78716C` | Secondary info |
| Border | `#E7E5E4` | Card borders |
| Success | `#16A34A` | Available, confirmed |
| Warning | `#D97706` | Pending |
| Danger | `#DC2626` | Rejected, error |

**Rules**
- Navbar: solid `#E9631A`, white text. No dark gradients.
- Orange is accent only (buttons, active states). Not page background.
- Primary button: orange bg + **white text**. Secondary: white bg + dark text.
- Never put dark text on orange background.

## Typography

- Font: `Plus Jakarta Sans` or `Prompt` (Thai).
- Base: 15px, line-height 1.55.
- Headings: weight 700, tracking `-0.02em`.
- Thai text: prefer Thai labels consistently across the app.

## Spacing

| Token | Value |
|-------|-------|
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |

- Cards: radius 12px, padding 1.25rem, border 1px solid `#E7E5E4`.
- Hover: lift 1px, soft shadow. No dramatic transforms.

## Components

### Navbar
- Solid orange `#E9631A`, white text.
- Height ~56px. Logo left, links right.
- Active link: subtle white pill.

### Buttons
- Primary: `#E9631A` bg, white text, slight shadow.
- Secondary: white bg, dark text, light border.
- Hover primary: darken to `#C44E10`.
- Never dark text on orange.

### Cards
- White surface on cream background.
- Title bold, meta muted, one action at bottom.
- Optional thin top accent on hover only.

### Status badges
- Pill shape, soft background + matching text.
- Pending = amber, Confirmed = green, Rejected = red.
- Use Thai labels: รออนุมัติ, ยืนยันแล้ว, ปฏิเสธ, ยกเลิก.

### Drawer
- Slide from right, max-width 520px.
- Header with title + close button.
- Body scrolls independently.

### Tables
- Thai column headers.
- Priority as colored badge (high/medium/low).
- Filter tabs show counts: `ทั้งหมด (12)`, `รออนุมัติ (3)`.

## Language

- Prefer Thai throughout for Thai users.
- Consistent status labels across all pages.
- Empty states: icon + short title + helpful text.

## Checklist

- [ ] Navbar is solid orange, not dark gradient
- [ ] Primary buttons have white text
- [ ] Secondary buttons have dark text on white
- [ ] Page background is warm cream
- [ ] Status labels are consistent and in Thai
- [ ] Filter tabs show counts
- [ ] Empty states have icon and helpful text
- [ ] Contrast ≥ 4.5:1 for all text
