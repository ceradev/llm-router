# Web App (Astro + React)

This app uses Astro for page/layout rendering and a React island for the interactive
LLM Router flow (`hero -> analyzing -> results`).

## Current Architecture

- `src/pages/index.astro` mounts `LLMRouterApp` with `client:load`.
- `src/app/LLMRouterApp.tsx` owns interactive UI state, transitions, and abortable
  recommendation fetches.
- React providers (`ThemeProvider`, `I18nProvider`) are scoped inside the app island.

## Decision: keep a single React island on `/`

For the home route, we keep the current pattern: **Astro as the page/layout shell** and
**one React island** (`LLMRouterApp`) owning the interactive flow and shared state.

Multiple islands are only worth introducing if there is a specific, measurable goal
(see next section) that the current approach cannot meet.

## Optimization Goal Before Any Architecture Change

Do not change the Astro/React split without a single explicit optimization goal and
measurable success criteria.

Choose one primary goal:

- Less JS shipped to the browser
- Better Time to Interactive (TTI)
- Better maintainability

Success criteria (must be defined before refactor):

- **Less JS**: reduce initial JS by at least 25% on `/` (measured from production build
  assets/chunks and request waterfall).
- **TTI**: improve median TTI by at least 20% on a throttled profile (4x CPU slowdown,
  Slow 4G) across 5 runs.
- **Maintainability**: reduce cross-view state coupling by introducing a documented
  module boundary (e.g., extracted store or bounded islands) and keep complexity stable
  (no increase in lint/type errors, no additional duplicated flow logic).

If none of the above can be proven with measurements, keep the current single-island
architecture.

## Commands

Run from `apps/web`:

| Command           | Action                                      |
| :---------------- | :------------------------------------------ |
| `npm install`     | Install dependencies                        |
| `npm run dev`     | Start local dev server                      |
| `npm run build`   | Build production assets                     |
| `npm run preview` | Preview production build locally            |
| `npm run check`   | Run Astro/TypeScript checks (if configured) |
