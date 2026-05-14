# Deck Builder

A small UI + local server that picks three accounts from your MSX pipeline export and asks
**Azure OpenAI (default `gpt-4.1`)** to write a slide deck TSX directly into
`slides/<id>/index.tsx`. No copy-paste required.

## What it does

1. You drop your MSX pipeline export (`.xlsx`) on the upload card. Parsing happens in the
   browser only — the spreadsheet never leaves your machine.
2. Two ways to drive a deck:
   - **Mode A · Manual.** Three dropdowns populated from the accounts in the file you uploaded.
     Pick three.
   - **Mode B · ✨ Magic Picker.** Pick a product (CI–RT, D365 Sales, D365 Service / CCaaS,
     Copilot Studio, Power Platform, M365 Copilot, W365, Security, Fabric). The picker scores
     every account in your file and recommends the top three, with a one-line "why" per account.
3. A single **Build my deck →** click:
   1. Sends the brief + the open-slide skill files + the fictional reference deck
      (`tools/deck-builder/reference/example-deck.tsx`) to the LLM
   2. Receives a brand-new TSX file
   3. Writes it to `slides/<auto-id>/index.tsx`
   4. Surfaces the dev-server URL so you can open the deck immediately

When you touch one of the two mode cards, the other one **dims out** so it's clear which mode
you're submitting.

## Run it (local server)

```powershell
cd tools\deck-builder
.\start.ps1
```

That script will:

1. Create a Python venv at `.venv/` (one-time, ~10 s)
2. Install `flask`, `requests`, `azure-identity`, `python-dotenv`
3. Check that you're logged in to `az`
4. Start the server at <http://localhost:8765> and open the browser

Stop with `Ctrl+C`.

## How does Copilot Chat compare?

Two paths exist:

- **Local server (this README, recommended).** Submit → gpt-4o writes the slide → file is on disk
  before the page finishes its loading animation.
- **Static `file://` mode.** If you double-click `index.html` instead, the tool runs in
  *prompt-only* mode (the header banner says `static mode · prompt only`). Submit shows a
  Markdown brief you copy/paste into Copilot Chat **inside this open-slide repo**. Copilot then
  reads `AGENTS.md` + `.agents/skills/*/SKILL.md` from the workspace and authors the deck.

> Copilot Chat only knows about the open-slide skill *because the repo is open in VS Code*. If you
> open Copilot Chat in a different workspace, those files aren't visible to it. The local-server
> mode bypasses that entirely — it sends the skill files to Azure OpenAI directly.

## Auth — and how a colleague gets this working

The server picks an LLM backend automatically:

- Default → **Azure OpenAI** (deployment `gpt-4.1`, api version `2024-10-21`) using your
  Entra identity via `az login`.
- Optional → **Cohere `command-a-03-2025`** if `COHERE_API_KEY` is set in `.env`.

You can force a backend with `LLM_BACKEND=cohere` or `LLM_BACKEND=aoai`.

### Option A · Azure OpenAI with Entra identity (recommended)

Each colleague:

1. Has `az` CLI installed (<https://aka.ms/azcli>)
2. Runs `az login --tenant <your-tenant-id>` (one time)
3. Has the `Cognitive Services OpenAI User` role on the AOAI resource
4. Copies `.env.example` to `.env` and fills in `AZURE_OPENAI_ENDPOINT`,
   `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_TENANT_ID`

Granting the role (one time, in the Azure Portal):

1. Open your OpenAI resource
2. Access control (IAM) → Add role assignment → role **Cognitive Services OpenAI User** →
   assign to the colleague (or a security group they're in)
3. Make sure the resource has `disableLocalAuth=false` if you also want to allow API keys

### Option B · Cohere

Drop `COHERE_API_KEY=...` in `.env` and the server picks it up automatically. Cohere's
`command-a-03-2025` has a 256k-token context window. Output is capped at 8k tokens.

## Where credentials are read from

The server looks at these in order:

1. Environment variables in your shell
2. `open-slide/.env` (gitignored — copy from `.env.example`)
3. Built-in defaults (deployment `gpt-4.1`, api version `2024-10-21`, Cohere model
   `command-a-03-2025` via <https://api.cohere.com/v2/chat>). The endpoint has no default — set
   `AZURE_OPENAI_ENDPOINT` in `.env`.

## How the magic picker scores

Deterministic, no random:

| Component | Range | Source |
| --- | --- | --- |
| Industry fit | 0–40 | Per-product weights for each industry (in `index.html` → `PRODUCTS`) |
| Pipeline size | 0–30 | `log10(total_pipeline + 10) × 5` |
| Active opportunities | 0–15 | `min(15, opps × 3)` |
| Compete signal | 5–15 | Higher when a known competitor is already in the account |
| Sales-play match | +0 or +6 | Bonus if any active sales play matches the product's keywords |

## Refresh the pipeline data

There is no offline refresh step. The dropdowns are populated from the MSX export you upload
through the UI. The browser parses the file with `vendor/xlsx.full.min.js` and aggregates
accounts client-side. Only the three accounts you actually pick (plus the brief / product) are
sent to the server when you click **Build my deck**.

Expected MSX columns (the parser auto-detects on upload):

- `Account Name (English)` or `CRM Account Name`
- `Qualified Pipeline`
- `Opportunity ID`
- `Sales Stage`
- `Forecast Recommendation`
- `Primary Sales Play`

Optional Whitespace export columns:

- `MSSales Account Name`
- `M365 E3 Seats`, `M365 E5 Seats`
- `ME5 full potential revenue ($)`
- `FY27 Whitespace Seats`

## Files

- `index.html` — the UI. Self-contained; works on `file://` (prompt-only mode) or via the server.
- `vendor/xlsx.full.min.js` — bundled SheetJS for in-browser MSX parsing.
- `reference/example-deck.tsx` — fictional 10-page reference deck embedded in the LLM prompt.
- `server.py` — Flask server: serves `/`, exposes `/api/health` + `/api/generate`, calls Azure
  OpenAI, writes the slide.
- `requirements.txt` — Python deps (4 packages).
- `start.ps1` — one-shot launcher (venv + deps + start).
