## Context

`boards/applications.js` renders `StatusChip` (a plain span) followed by a
`Menu` with a "+" button whose popover holds the status radio list, the "new
status" form, and the "add tag" form. Browser tests open it by the accessible
name "Change status or add a tag".

## Decisions

### S1. Two controls instead of one

- **Status:** the chip itself is the `Menu` button. Its popover holds the
  status list (grouped by stage, current one checked) and the inline "new
  status" form, unchanged in behavior. Accessible name: "Status: <name>.
  Change status". A chevron and the existing hover/focus styles make it look
  actionable.
- **Tags:** the "+" button keeps a popover with only the "add tag" form.
  Accessible name: "Add a tag". Existing tag chips keep their "×" remove
  buttons.

*Alternative:* keep one menu and only relabel "+" (still hides the most
common action behind an icon that means "add").

### S2. Keyboard and screen readers

Both controls are buttons with `aria-expanded`, open with Enter/Space, close
with Escape and return focus, as the existing `Menu` component already does.

## Risks / Trade-offs

- [Muscle memory for the old "+"] → the change is small and the chip is the
  more natural target; the tag "+" stays where it was.
