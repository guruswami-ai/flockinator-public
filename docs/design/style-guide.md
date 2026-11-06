# Flockinator site style guide

## How the benchmark was built (primary-source audit, 2026-11-06)
patternflow.work is Next.js (App Router) + Turbopack served via OpenNext
on Cloudflare (`x-opennext: 1`, RSC payloads, immutable hashed chunks,
`s-maxage` HTML), Tailwind v4 + token CSS, self-hosted WOFF2 with
font-display:swap, Next Image (q=75, wide srcsets), PostHog, sitemap +
RSS. Audits: /tmp research notes summarised here; no branding copied.

## Stack decision for Flockinator: stay static
Our site needs no server rendering: benchmark data is precomputed,
two small Pages Functions serve JSON. The visual quality of the
benchmark comes from its design system, not its framework. Static
Pages keeps the site free, fast, and reproducible. Revisit vinext /
OpenNext only if per-user server state ever becomes a requirement.

## Grammar adopted (mechanisms, not identity)
- One accent with a job; everything else is ground, ink, hairlines.
- Sections separated by padding + 1px rules, never background blocks.
- Square corners, no shadows, no gradients, calm motion (<=200ms).
- Mono uppercase kickers; display type does hierarchy, not size spam.
- Documentary media first: real photos/frames, captioned as evidence;
  illustrations labelled as illustrations; numbered sequences (01..).
- Honesty as a feature: costs, limits, and failure modes stated inline.

## Flockinator vocabulary (ours, do not swap for the benchmark's)
- Ground `#0b0b0c`, panel `#101214`, ink `#f2f0e9`, muted `#a49e90`.
- Accent: panel teal `#2dd4bf`. Signals are data-only: survivor
  `#2fdd8b`, hazard `#ff6b5e`, forged `#5eb2ff`, amber `#f5b544`.
- Type: system sans; mono for kickers/buttons/labels; display clamp
  2.4-4rem, -0.03em. Content cap 1120px; prose ~62ch.
- Media: wall frames rotated to read correctly, screened before
  publication (legible, no people, no identities); video silent-only;
  derivatives 854px video / 1280px stills; GIF panels from the
  audited build (cloudflare/check_panels.py must pass).

## Do / Don't
Do: real captures over renders; exact numbers; a source-repo link on
every tutorial page; reduced-motion stills for animations.
Don't: second accent; glass/rounded cards; stock imagery as proof;
publish any frame that has not been visually screened.
