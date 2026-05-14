# FY-27 Big Bets — Deck Builder

A small local web app that turns an MSX pipeline export into a fresh React
slide deck in about a minute. You upload your `.xlsx`, pick three accounts
(or let the picker pick them), pick a product, and an LLM writes a
1920×1080 TSX deck straight into `slides/<id>/index.tsx` — ready to open
in the dev server.

The slide framework underneath is [open-slide](https://github.com/open-slide/open-slide):
each deck is plain React (TSX) inside `slides/<id>/`, and the dev server hot-reloads as
you edit.

> **Your MSX export never leaves your browser.** The spreadsheet is parsed
> client-side. Only the three account names you actually pick (plus your
> brief and the chosen product) are sent to the LLM.

---

## Prerequisites

- **Node.js 20+** and **pnpm** (or npm) — for the slide dev server
- **Python 3.10+** — for the deck-builder server
- **Azure CLI** (`az`) — for Entra-based auth to Azure OpenAI
  ([install](https://aka.ms/azcli))
- An **Azure OpenAI** resource with a chat-completion deployment. The
  default and tested model is `gpt-4.1`. You need the `Cognitive Services
  OpenAI User` role on the resource.

Optional:

- A **[Cohere](https://dashboard.cohere.com/) API key** if you want to use
  Cohere `command-a-03-2025` instead of Azure OpenAI.
- A **[Tavily](https://tavily.com/) API key** to enable the Magic Picker's
  one-line "why" lookup per account.

---

## Install

```powershell
git clone https://github.com/microsoft/FY-27-Big-Bets.git
cd FY-27-Big-Bets

# 1. Slide framework
pnpm install            # or: npm install

# 2. Credentials
copy .env.example .env  # then open .env and fill in your values
#                         (AZURE_OPENAI_ENDPOINT, _DEPLOYMENT,
#                          _API_VERSION, _TENANT_ID at minimum)

# 3. Deck-builder Python deps (one-time, takes ~10s)
cd tools\deck-builder
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..

# 4. Sign in to Azure (one-time, opens a browser)
az login --tenant <your-tenant-id>
```

---

## Run it

You need two terminals.

**Terminal 1 — slide dev server:**

```powershell
pnpm dev
```

Serves the React slides at <http://localhost:5173>.

**Terminal 2 — deck-builder UI:**

```powershell
cd tools\deck-builder
.\start.ps1
```

That opens <http://localhost:8765> in your browser.

---

## Build a deck

1. Drag your MSX pipeline export onto the **Upload MSX** card. The required
   columns are listed in [`tools/deck-builder/README.md`](tools/deck-builder/README.md#refresh-the-pipeline-data).
2. Pick **Mode A** (manual — three dropdowns) or **Mode B** (Magic Picker
   recommends three accounts based on a chosen product).
3. Type a one-line brief (optional but recommended).
4. Click **Build my deck →**. The LLM writes a new deck to
   `slides/<auto-id>/index.tsx` and the UI shows the dev-server URL.
5. Open the URL. Edit the TSX live; the dev server hot-reloads.

---

## Authoring a slide by hand

Every slide is plain React. Drop a new file at `slides/<your-slide>/index.tsx`:

```tsx
import type { Page, SlideMeta } from '@open-slide/core';

const Cover: Page = () => (
  <div style={{ width: '100%', height: '100%' }}>Hello</div>
);

export const meta: SlideMeta = { title: 'My slide' };
export default [Cover] satisfies Page[];
```

Pages render into a fixed **1920 × 1080** canvas — design with absolute pixel
values. Put images, fonts, and videos under `slides/<id>/assets/` and import
them directly. See [`slides/getting-started/index.tsx`](slides/getting-started/index.tsx)
for a working example, and [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md)
for the full authoring guide if you're using Copilot or Claude Code.

---

## Deeper docs

- [`tools/deck-builder/README.md`](tools/deck-builder/README.md) — server
  internals, magic-picker scoring, backend selection (AOAI vs Cohere),
  required MSX columns.
- [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md) — slide-authoring
  rules consumed by Copilot / Claude Code skills in this repo.
- `tools/deck-builder/reference/example-deck.tsx` — the fictional reference
  deck embedded in the LLM prompt as a structural / density example.

---

## Scripts

| Command | Description |
| --- | --- |
| `pnpm dev` | Start the slide dev server with hot reload (port 5173). |
| `pnpm build` | Build a static bundle you can deploy. |
| `pnpm preview` | Preview the built bundle locally. |
| `tools\deck-builder\start.ps1` | Start the deck-builder UI (port 8765). |

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `start.ps1` fails activating venv | Run `Set-ExecutionPolicy -Scope Process Bypass` first. |
| `401 Unauthorized` from AOAI | `az login --tenant <id>` and confirm you have **Cognitive Services OpenAI User** on the resource. |
| Dropdowns are empty | You haven't uploaded an MSX file yet, or the file is missing a required column (see `tools/deck-builder/README.md`). |
| Generated deck overflows the 1080px canvas | The prompt has guard-rails but the model occasionally regresses. Open the page, find the absolutely-positioned `Footer`, and add bottom padding ≥ 120px to the page container. |

