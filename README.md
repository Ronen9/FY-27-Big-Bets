# FY-27 Big Bets — Deck Builder

A small local web app. You drop your **MSX pipeline export** into the
browser, pick three accounts, pick a product, hit **Build my deck →**, and
an LLM writes a 1920×1080 React slide deck onto your disk in about a
minute. Then a hot-reloading dev server shows it in your browser, ready to
edit.

> Your MSX file never leaves your machine. The browser parses it locally;
> only the three account names you pick (plus the brief and product) go to
> the LLM.

---

## 1. Install the prerequisites

Install these once on your machine:

| Tool | Where | Used for |
| --- | --- | --- |
| **Node.js 20+** | <https://nodejs.org/> | Slide dev server |
| **pnpm** | `npm install -g pnpm` | Faster `npm` |
| **Python 3.10+** | <https://www.python.org/downloads/> | Deck-builder server |
| **Git** | <https://git-scm.com/> | Cloning the repo |
| **Azure CLI** | <https://aka.ms/azcli> | Sign in to Azure OpenAI |

You also need:

- An **Azure OpenAI** resource with a `gpt-4.1` deployment.
- The **Cognitive Services OpenAI User** role on that resource (Ronen
  grants this — give him your Microsoft email).

---

## 2. Get the code

```powershell
git clone https://github.com/Ronen9/FY-27-Big-Bets.git
cd FY-27-Big-Bets
```

---

## 3. Add your credentials

```powershell
copy .env.example .env
notepad .env
```

Fill in these four values (Ronen will give them to you):

```
AZURE_OPENAI_ENDPOINT=https://<your-aoai-resource>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_TENANT_ID=<your-tenant-guid>
```

Save and close.

---

## 4. Sign in to Azure (one time)

```powershell
az login --tenant <your-tenant-id>
```

A browser opens; pick your work account.

---

## 5. Install dependencies

```powershell
# Slide dev server
pnpm install

# Deck-builder server (creates .venv, installs Flask etc.)
cd tools\deck-builder
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
deactivate
cd ..\..
```

---

## 6. Run it

You need **two terminals** open at the same time.

**Terminal 1 — slide dev server:**

```powershell
pnpm dev
```

Leave it running. It serves the slides at <http://localhost:5173>.

**Terminal 2 — deck builder UI:**

```powershell
cd tools\deck-builder
.\start.ps1
```

That opens <http://localhost:8765> in your browser.

---

## 7. Build a deck

In the deck-builder browser tab:

1. **Drag your MSX pipeline export (`.xlsx`) onto the upload card.**
   Required columns: `Account Name (English)` (or `CRM Account Name`),
   `Qualified Pipeline`, `Opportunity ID`, `Sales Stage`,
   `Forecast Recommendation`, `Primary Sales Play`.
2. **Pick a mode:**
   - **Mode A — Manual:** three dropdowns, pick three accounts.
   - **Mode B — ✨ Magic Picker:** pick a product, the tool recommends
     the top three accounts.
3. **Type a one-line brief** (optional but helps).
4. **Click "Build my deck →".**

After ~60 seconds the page shows a link like
`http://localhost:5173/<auto-id>`. Click it. Your deck is live.

The deck source is at `slides/<auto-id>/index.tsx` — edit it and the
browser hot-reloads.

---

## Slide controls

- `←` `→` / PageUp / PageDown — between pages
- `F` — fullscreen present mode
- `Esc` — exit fullscreen

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `start.ps1` errors on activate | Run `Set-ExecutionPolicy -Scope Process Bypass` first, then re-run `start.ps1`. |
| `pnpm` not recognized | Install pnpm globally: `npm install -g pnpm`. |
| `401 Unauthorized` from Azure OpenAI | Re-run `az login --tenant <id>` and confirm Ronen granted you **Cognitive Services OpenAI User**. |
| Dropdowns are empty after upload | The MSX file is missing one of the required columns (see step 7). |
| Generated deck text overflows the slide | Open `slides/<id>/index.tsx`, find the page that overflows, and reduce font sizes or remove a bullet. |
| Tool says "no LLM backend configured" | `.env` is missing or `AZURE_OPENAI_ENDPOINT` is blank. Re-do step 3. |

---

## What's where

```
FY-27-Big-Bets/
├── README.md                        ← you are here
├── .env.example                     ← copy to .env and fill in
├── slides/
│   └── getting-started/             ← example slide
├── tools/deck-builder/
│   ├── README.md                    ← deeper tool docs
│   ├── server.py                    ← Flask server (LLM call + file write)
│   ├── index.html                   ← UI (parses MSX in-browser)
│   ├── start.ps1                    ← one-shot launcher
│   ├── requirements.txt             ← Python deps
│   ├── reference/example-deck.tsx   ← fictional reference deck for the LLM
│   └── vendor/xlsx.full.min.js      ← in-browser MSX parser
└── AGENTS.md / CLAUDE.md            ← for Copilot / Claude Code skills
```

For the magic-picker scoring formula, alternative LLM backends (Cohere),
and required MSX columns in detail, see
[`tools/deck-builder/README.md`](tools/deck-builder/README.md).

---

Made by Ronen Ehrenreich · ABS Israel · FY27.
