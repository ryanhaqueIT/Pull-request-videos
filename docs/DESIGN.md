# Design System

> Reference for agents building frontend UI.

<!-- EVOLVE: Fill in brand colors and typography once UI design is established -->

## Brand Colors

Define your brand palette here. Use semantic names in your component library.

| Token | Hex | Usage |
|-------|-----|-------|
| brand-50 | TBD | Hover backgrounds |
| brand-100 | TBD | Avatar backgrounds, subtle accents |
| brand-500 | TBD | Focus rings, logo accent |
| brand-600 | TBD | Primary buttons, links |
| brand-700 | TBD | Button hover, strong emphasis |

## Status Colors

| Status | Badge BG | Badge Text | Dot |
|--------|----------|------------|-----|
| active / success | `bg-green-50` | `text-green-700` | `bg-green-500` |
| warning / pending | `bg-yellow-50` | `text-yellow-700` | `bg-yellow-500` |
| inactive / paused | `bg-gray-50` | `text-gray-600` | `bg-gray-400` |
| error / failed | `bg-red-50` | `text-red-700` | `bg-red-500` |

## Component Patterns

- **Cards**: rounded border with padding. Add hover shadow when clickable.
- **Stat cards**: label/value/sub structure in a bordered container.
- **Badges**: inline-flex with colored dot and ring.
- **Primary button**: brand-colored background, white text, rounded, hover state.
- **Form inputs**: bordered, rounded, focus ring in brand color.
- **Error banners**: red background, red border, red text.

## Spacing

- Page padding: 2rem (p-8)
- Content max-width: varies by page type (list: 64rem, detail: 56rem, form: 48rem)
- Section gap: 2rem (mb-8)
- Card grid: responsive columns with 1rem gap
