# Design System: NutriLens Botanical Editorial

## 1. Visual Theme & Atmosphere

NutriLens is a botanical editorial inspection workstation: warm, precise,
quietly premium, and grounded in real food rather than generic wellness
imagery. The interface should feel like a beautifully typeset field guide
combined with a trustworthy nutrition instrument.

The atmosphere is gallery-airy on the scan surface and information-dense on
the result surface. Use an offset asymmetric composition at desktop sizes:
the camera/viewfinder is the visual anchor, while nutrition data and scan
provenance occupy a calm inspection rail. Motion is restrained but alive:
spring-weighted transitions, staged result reveals, and subtle status pulses.

Density: 5/10. Variance: 7/10. Motion: 5/10.

## 2. Color Palette & Roles

- **Botanical Forest** (`#1E4B33`) — the single accent; primary actions,
  active navigation, focus rings, and the key brand mark.
- **Organic Paper** (`#FCF9F4`) — the global canvas and page background.
- **Clean Surface** (`#FFFFFF`) — upload surface, result panels, and readable
  inspection regions.
- **Deep Ink** (`#20261F`) — headlines, nutrient values, and primary text;
  never use pure black.
- **Sage Tint** (`#E9F0E8`) — selected states, quiet status backgrounds, and
  positive insight panels.
- **Muted Sage** (`#667568`) — helper text, metadata, secondary labels, and
  scan-stage descriptions.
- **Structural Line** (`#D9E1D8`) — one-pixel dividers and input borders.
- **Caution Terracotta** (`#A6533D`) — honest nutrition cautions only; never
  use alarm-red styling for ordinary food guidance.
- **Benefit Gold** (`#B88328`) — small benefit marker and emphasis only; do not
  introduce a second competing CTA color.

Never use neon gradients, purple/blue AI clichés, pure black, or saturated
rainbow accents.

## 3. Typography Rules

- **Display:** Fraunces, weight 500–600 — distinctive editorial headlines,
  tight tracking, controlled scale; use `clamp()` rather than oversized type.
- **Body:** Archivo, weight 400–600 — highly readable explanatory copy with
  relaxed line height and a maximum measure of 65 characters.
- **Numerical data:** Archivo or a restrained monospace companion — tabular
  numerals, aligned nutrient values, clear units, and no decorative glyphs.
- **Labels:** Archivo semibold, uppercase only for short metadata labels with
  generous tracking.

Avoid Inter and generic system-font-only styling. Avoid Times New Roman,
Georgia, Garamond, and other generic serif defaults.

## 4. Component Stylings

* **Primary action:** Botanical Forest fill, white text, minimum 44px touch
  height, tactile `translateY(1px)` active feedback, and no glow.
* **Secondary action:** transparent or white surface with a Structural Line
  border; use underline or tonal change on hover rather than another filled
  accent button.
* **Viewfinder upload:** a single large surface with a clean image frame,
  corner brackets, clear camera/upload affordance, and a concise helper line.
  Do not use a generic dashed dropzone.
* **Cards:** use only where elevation communicates a real hierarchy. Prefer
  open paper surfaces, top rules, and negative space for nutrition data.
* **Inputs:** label above the field, visible units, strong focus ring, helper
  text below, and inline error text. Never use floating labels.
* **Result nutrients:** calories get the strongest typographic emphasis;
  protein, carbohydrates, fat, sugar, fiber, and sodium follow a structured
  two-column desktop grid and a single-column mobile list.
* **Insight panel:** exactly two items. Benefits use Sage Tint with a small
  Benefit Gold marker; cautions use a pale terracotta tint and direct,
  non-judgmental language.
* **Provenance badge:** always state `USDA-sourced` or `Label-sourced` near
  the result; never hide the data origin.
* **Loading:** use skeleton blocks matching the eventual layout and short
  scan-stage labels. Do not use a generic circular spinner.
* **Errors:** explain what happened, why NutriLens stopped, and the one best
  recovery action. Never blame the user or hide provider failures.

## 5. Layout Principles

Use a centered max-width of approximately 1400px with a grid-first desktop
layout. At 1440px, use a persistent left navigation rail, a large central
viewfinder/inspection area, and a right-side scan-status or nutrition rail.
The central visual anchor should be offset rather than centered in a generic
hero.

Desktop scan layout:

1. Left rail: NutriLens identity, Scan, recent state only if available, and
   quiet product context.
2. Main workspace: the viewfinder or captured image, primary action, and
   current scan stage.
3. Right rail: image-quality checks, identification status, nutrition source,
   and the next required action.

Desktop result layout:

1. Left: food identity, portion, provenance, and the hero calorie value.
2. Center: structured nutrient breakdown with aligned values and units.
3. Right: exactly two health insights and a compact source explanation.

Below 768px, collapse every multi-column region into one readable column,
keep touch targets at least 44px, and remove horizontal overflow. Preserve
the same hierarchy; do not create a separate mobile visual language.

Do not use three equal feature cards, absolute-positioned overlapping content,
percentage-based `calc()` layout hacks, or full-height `h-screen` sections.
Use `min-height: 100dvh` where a page needs viewport height.

## 6. Motion & Interaction

Use spring-like transitions with an approximate stiffness of 100 and damping
of 20. Animate only `transform` and `opacity`.

- Stagger scan-stage labels as the request advances.
- Reveal result nutrient rows with a short cascade after identification.
- Give the active viewfinder a low-amplitude botanical pulse while waiting.
- Use tactile button feedback on press and a clear focus state for keyboard
  users.
- Respect `prefers-reduced-motion` by collapsing transitions to near-zero.

Motion should communicate state, not decorate empty space. Never use bouncing
arrows, perpetual distracting loops, or blocking animation before content.

## 7. Anti-Patterns (Banned)

- No emojis in the interface.
- No purple, blue-neon, or AI-glow visual language.
- No pure black (`#000000`).
- No generic serif fonts or Inter.
- No gradients used as decoration or text fill.
- No neon outer glows or excessive shadows.
- No three-equal-card feature rows.
- No centered generic hero at desktop variance 7.
- No overlapping text, image, or controls.
- No fake live telemetry or invented confidence values.
- No fake health claims, medical claims, or “everything is healthy” copy.
- No AI clichés such as “seamless,” “next-gen,” “elevate,” or “unlock.”
- No filler copy such as “scroll to explore.”
- No placeholder names, fake metrics, or fake nutrition numbers.
- No hidden nutrition provenance.
