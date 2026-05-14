# open-slide — Agent Guide

You are authoring **slides** in this repo. Every slide is arbitrary React code that you write.

## Hard rules

- Put your slide under `slides/<kebab-case-id>/`.
- The entry is `slides/<id>/index.tsx`.
- Put images/videos/fonts under `slides/<id>/assets/`.
- Do **not** touch `package.json`, `open-slide.config.ts`, or other slides.
- Do not add dependencies. Use only `react` and standard web APIs.

## House rules (Ronen / ABS Israel)

These are **non-negotiable** authoring rules for every deck in this repo. They apply on top of
whatever the `slide-authoring` skill says, and they survive `pnpm sync:skills` (skills get
overwritten — this file does not).

1. **Every quote is clickable.** Any quoted text — customer quote, analyst quote, press release,
   manager email, internal memo — must be wrapped in an `<a href="…">` whose `href` points to the
   primary source (PR URL, transcript, internal doc link, MSX opportunity URL). If the source is
   internal-only, link to the internal URL anyway. No floating quotes without a way to verify.
2. **Every acronym is expanded the first time it appears,** in parentheses on the same slide. Examples:
   - `$1T` → `$1T (one trillion dollars)`
   - `CSP` → `CSP (Cloud Solution Provider)`
   - `P&C` → `P&C (Property & Casualty)`
   - `FNOL` → `FNOL (First Notice of Loss)`
   - `CCaaS` → `CCaaS (Contact Center as a Service)`
   - `CIJ` → `CIJ (Customer Insights — Journeys)`
   - `CI RT` → `CI RT (Customer Insights — Real Time)`
   - `EA` → `EA (Enterprise Agreement)`
   - `MSX` → `MSX (Microsoft Sales Experience)`
   - `ATU` → `ATU (Account Technology Unit)`
   - `STU` → `STU (Specialist Team Unit)`
   - `TPID` → `TPID (Top-Parent ID)`
   This includes Hebrew shorthand and unit shorthand (B, M, K). Be friendly to people who haven't
   memorised the field's jargon.
3. **Signature footer on every page:** `Made by Ronen Ehrenreich · ABS Israel · FY27` (or the
   current FY). The page-number / context chip lives next to it.
4. **Pipeline-grounded.** When a slide cites pipeline numbers, account names, competitors, or
   sales plays, those numbers must come from the latest MSX export under `docs/`. Do not invent
   accounts or estimate pipeline. Re-run `python docs/_aggregate_accounts.py` after any new export.

## Which skill to use

- **Drafting a new deck** — use the `create-slide` skill. It walks through scoping questions, structure, and hand-off.
- **Applying inspector comments** (`@slide-comment` markers in a page) — use the `apply-comments` skill.
- **Creating or extracting a theme** — use the `create-theme` skill. Themes live as markdown under `themes/<id>.md` and are read by `create-slide` before authoring.
- **Resolving "this page" / "this element"** — when the user references the current slide or selection without naming it, consult the `current-slide` skill. It reads the dev server's `node_modules/.open-slide/current.json` to find which slide, page, and inspector-picked element they mean.
- **Any other slide edit** — read the `slide-authoring` skill before writing. It is the technical reference for everything inside `slides/<id>/`: file contract, the 1920×1080 canvas, type scale, palette, layout, assets, self-review checklist, and anti-patterns. `create-slide` and `apply-comments` both defer to it for the *how*.

Keep this file short: hard rules only. All deeper guidance lives in the skills above.

## Updating skills

The skills above are managed by `@open-slide/core`. Do not edit them in place. To pull the latest versions:

```
pnpm up @open-slide/core
pnpm sync:skills
```

`pnpm dev` will also detect drift on startup and offer to sync. `pnpm sync:skills --dry-run` (via `pnpm exec open-slide sync:skills --dry-run`) previews changes without writing.
