"""
Deck Builder server — serves the static UI at / and the deck-generation API at /api/*.

Workflow:
  1. Browser POSTs the picked accounts + product + language + tone to /api/generate
  2. Server assembles a system prompt from the open-slide skill files + the fy27-big-bet example
  3. Server calls Azure OpenAI (gpt-4o) with the brief
  4. Server extracts the TSX, writes it to slides/<id>/index.tsx
  5. Server returns {slideId, slidePath, devUrl, pitch, tsxPreview}

Run:
  cd tools/deck-builder
  pip install -r requirements.txt
  az login                        # one-time, uses your Entra identity
  python server.py                # opens http://localhost:8765 in your browser

Auth: identity (Entra) by default. Reads MCP_CX_ENG/.env if present. See README.md.

Made by Ronen Ehrenreich for ABS Israel.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request, send_from_directory

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*_a, **_k) -> bool:
        return False


# ─── Paths ───────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent  # …/open-slide
SLIDES_DIR = REPO_ROOT / "slides"
# Few-shot reference deck shown to the LLM. Lives inside the tool folder so
# the tool ships self-contained and we never embed real customer data into
# the system prompt. The fictional companies in this file (Contoso /
# Northwind / Adventure) signal both structure (10 pages, per-account
# divider+intro+play, custom atoms) and content density.
EXAMPLE_RICH = HERE / "reference" / "example-deck.tsx"
EXAMPLE_SLIDE = EXAMPLE_RICH  # alias for the (currently unused) second few-shot slot
SKILL_AUTHORING = REPO_ROOT / ".agents" / "skills" / "slide-authoring" / "SKILL.md"
SKILL_CREATE = REPO_ROOT / ".agents" / "skills" / "create-slide" / "SKILL.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"

# ─── Env ─────────────────────────────────────────────────────────────────────
# All credentials live in open-slide/.env. This tool is intentionally
# self-contained so colleagues can clone, drop a .env in place, and run.
load_dotenv(REPO_ROOT / ".env")

DEFAULT_ENDPOINT = "https://openai-voice-bot-abs.openai.azure.com"
DEFAULT_DEPLOYMENT = "gpt-4.1"
DEFAULT_API_VERSION = "2024-10-21"
DEFAULT_COHERE_MODEL = "command-a-03-2025"
COHERE_CHAT_URL = "https://api.cohere.com/v2/chat"

PORT = int(os.getenv("DECK_BUILDER_PORT", "8765"))
DEV_SERVER_URL = os.getenv("OPEN_SLIDE_DEV_URL", "http://localhost:5173")
AZ_CLI_CANDIDATES = [
    r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    "az",
]


def _az_cli() -> str:
    for c in AZ_CLI_CANDIDATES:
        if c == "az":
            return c
        if Path(c).exists():
            return c
    return "az"


# ─── Azure OpenAI auth (Entra identity only) ─────────────────────────────────

def _normalize_endpoint(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        cleaned = f"{parsed.scheme}://{parsed.netloc}"
    else:
        cleaned = raw.rstrip("/")
    if cleaned.endswith(".cognitiveservices.azure.com"):
        cleaned = cleaned.replace(".cognitiveservices.azure.com", ".openai.azure.com")
    return cleaned.rstrip("/")


def _runtime_config() -> tuple[str, str, str]:
    endpoint = _normalize_endpoint(os.getenv("AZURE_OPENAI_ENDPOINT", DEFAULT_ENDPOINT))
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", DEFAULT_DEPLOYMENT).strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION).strip()
    return endpoint, deployment, api_version


def _entra_token_headers() -> dict[str, str]:
    """Get an Entra access token for Azure Cognitive Services. If
    AZURE_OPENAI_TENANT_ID is set, scope to that tenant; otherwise use the
    user's default `az` session."""
    tenant_id = os.getenv("AZURE_OPENAI_TENANT_ID", "").strip()
    cmd = [_az_cli(), "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com"]
    if tenant_id:
        cmd.extend(["--tenant", tenant_id])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            token = json.loads(result.stdout).get("accessToken")
            if token:
                return {"Authorization": f"Bearer {token}"}
        err = (result.stderr or result.stdout or "").strip()
        hint = (
            f"`az login --tenant {tenant_id}`" if tenant_id else "`az login`"
        )
        raise RuntimeError(
            f"Failed to acquire Entra token. Run {hint} and retry. Details: {err[:300]}"
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "Azure CLI (`az`) not found. Install it from https://aka.ms/azcli, then run `az login`."
        ) from e


# ─── Prompt assembly ─────────────────────────────────────────────────────────

def _read_text(p: Path, max_chars: int | None = None) -> str:
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return f"(could not read {p}: {e})"
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + "\n\n…(truncated for context budget)…"
    return text


def _read_example_slide() -> str:
    """Return the COMPLETE fy27-big-bet/index.tsx as a few-shot template.
    gpt-4o's 128K input window easily fits the full ~50KB file, and previous
    truncation (head 510 + tail 40) was producing shallow 6-page outputs
    because the model only saw cover/brief/thesis and never saw the rich
    Situation / Bet / RollUp / Closing pages it should mirror."""
    try:
        return EXAMPLE_SLIDE.read_text(encoding="utf-8")
    except Exception as e:
        return f"(could not read {EXAMPLE_SLIDE}: {e})"


def _read_example_rich() -> str:
    """Return the COMPLETE d365-sales-play/index.tsx — a denser hand-authored
    deck with custom Stat/Chip/PlayCard/AccountRow/PipeCard atoms, per-page
    bespoke JSX, and real Israeli-customer narrative (Clalit/Nuvei/Teva).
    This is the deck Ronen calls 'rich' — the model should match this density."""
    try:
        return EXAMPLE_RICH.read_text(encoding="utf-8")
    except Exception as e:
        return f"(could not read {EXAMPLE_RICH}: {e})"


_SYSTEM_PROMPT_HEAD = textwrap.dedent("""\
    You are an expert React/TypeScript slide author for the open-slide framework.
    You write a SINGLE FILE — `slides/<kebab-case-id>/index.tsx` — that exports
    a slide deck. The file must be self-contained and follow the framework
    contract below precisely.

    ABSOLUTE RULES (will fail review if violated):
    - Output ONLY raw TypeScript/TSX file content. No markdown fences (no
      ```tsx, no ```typescript, no ``` of any kind), no prose, no explanation,
      no leading or trailing commentary. The very first character of your
      response must be the letter `i` (start of `import`).
    - Use ONLY `react` and standard web APIs. No new dependencies.
    - **Fixed 1920×1080 canvas — content MUST visibly fit.** This is a hard
      physical ceiling, not a guideline. The slide will be rendered exactly
      1920px × 1080px and never scrolls. Anything taller than 1080 (or wider
      than 1920) is broken — it bleeds past the slide edge into nowhere or
      collides with the footer.
      Concretely:
        * The page root must use `width: '100%', height: '100%', overflow: 'hidden'`
          (the local `fill` const must include `overflow: 'hidden'`). This is
          a safety clip — but you must STILL design content to fit naturally.
        * Top + bottom padding combined ≤ 200px (e.g. `padding: '88px 140px'`).
          Anything over `padding: '108px 160px'` is risky on dense pages.
        * **Reserve ~120px at the bottom for the absolutely-positioned `Footer`.**
          The Footer atom uses `position: absolute; bottom: 46` — it does NOT
          take part in the page's flex layout and therefore reserves ZERO
          space. If your content fills the page top-to-bottom, the Footer
          will visually OVERLAP the bottom-most content. Two ways to prevent
          this — pick at least one on every page:
            (a) Set the page root's bottom padding to ≥ 120px
                (e.g. `padding: '60px 140px 120px'`), OR
            (b) Make sure the body content's natural height ends ~120px
                above the page bottom — i.e. don't `flex: 1` the bottom
                element all the way to the edge.
          On dense pages with stacked rows of cards, prefer (a) — it gives
          a hard guarantee that the Footer has its own band.
        * Start content HIGHER on dense pages. If a page has a Tag + h2 +
          paragraph + 2 rows of stat cards + Footer, set top padding to
          ~60px (not 105px) so the bottom row clears the Footer band.
        * Plan a page-height budget BEFORE writing it. Add up: top padding +
          tag/eyebrow + h2 (fontSize × lineHeight × line-count) + subtitle
          pill + main body (cards/columns/etc) + bottom paragraph + footer
          gap + bottom padding. If it exceeds ~1000px, you have to cut.
        * Long body bullets WRAP. A bullet like "Embed Copilot in NICE's CX
          platforms for real-time agent assist and next-best-action" is
          ~60 chars and will wrap to 2–3 lines inside a 450px-wide card,
          eating ~120px of vertical space per bullet. Either keep bullets
          ≤ 8 words each, or use fewer bullets per card.
        * For Play / Bet pages with 3 cards × 3 bullets + a heading + a
          subtitle pill + a Next-step paragraph + footer: use h2 ≤ 64px,
          card title ≤ 32px, bullet text ≤ 24px, card padding ≤ '32px 28px',
          and keep the bottom Next-step paragraph to ONE short sentence.
          If you cannot make all three columns fit, drop to 2 cards or
          split the page in two.
        * If a Situation page has 3 stat cards + 2 paragraphs + a quote +
          footer, reduce stat fontSize from 82 → 64 and paragraph fontSize
          from 38 → 30, OR move the quote to its own page.
        * **When in doubt, split into TWO pages instead of cramming one.**
          The deck target is 9–14 pages — there is plenty of room.
    - Each page is rendered as an explicit `<Component />` in the `pages` array.
      Do NOT generate slide-level content with `array.map()`.
    - **NEVER define a parameterized page-level component and reuse it for
      every account.** Patterns like
      `const Situation = ({accountName, pipeline, opportunities, ...}) => (...)`
      called once per account are FORBIDDEN. They produce shallow 1-liner
      pages and are the #1 cause of a deck feeling thin. Instead, define each
      page as its OWN bespoke top-level constant:
         const ClalitIntro: Page = () => (...)
         const ClalitPlay:  Page = () => (...)
         const TevaIntro:   Page = () => (...)
         const TevaPlay:    Page = () => (...)
      — each one with hand-written JSX specific to that customer's industry,
      scale, and story. Look at the reference example: every per-account page
      is a uniquely-named const. Mirror that exactly.
    - You MAY define small reusable ATOMS like `Stat`, `Chip`, `Bullet`,
      `PlayCard`, `Footer` — those are encouraged. The rule above only forbids
      using parameterization to skip writing each page's actual content.
    - **NEVER stop halfway with a placeholder comment.** Do NOT write things
      like `// Additional pages for X would follow the same format`,
      `// (Additional account-specific pages would go here)`, `// TODO: add
      Roll-up`, `// ...rest of pages omitted...`, or any other elided-content
      marker. You MUST emit every single page component in full TSX. The
      deck is not done until every page named in the user prompt's PAGE
      CHECKLIST exists as a bespoke const AND appears in the default export
      array. If you feel yourself running long, KEEP GOING — a complete deck
      with 10 pages is mandatory; stopping at 3 with a TODO comment is an
      automatic failure.
    - The default export array MUST list every page const you defined, in
      reading order. Do NOT leave trailing-comment placeholders inside the
      array (e.g. `// Additional pages for Clalit, IAI, Roll-up, and Closing
      would come here`).
    - Every quote in the deck MUST be wrapped in `<a href="...">` linking to its
      source URL. If you don't have a real URL, use the MSX link supplied in the
      brief. No floating quotes.
    - Every acronym/abbreviation MUST be expanded in parentheses on first use.
      Examples: "$1T (one trillion dollars)", "CSP (Cloud Solution Provider)",
      "P&C (Property & Casualty)", "CCaaS (Contact Center as a Service)".
    - Every page MUST include the footer signature
      `Made by Ronen Ehrenreich · ABS Israel · FY27` (use the `Footer` atom).
    - Numbers, account names, competitors, and pipeline figures must come from
      the brief. Do not invent accounts or estimate pipeline.
    - Match the chosen language and tone in the brief.

    AT THE VERY END of the file, after the default export, add a single
    JavaScript-style comment line of the form:
        // PITCH: <one-sentence elevator pitch for the room>
    The server will parse that line and surface it back to the user.

    DEPTH AND RICHNESS (this is what separates a winning deck from filler):
    - Aim for 10–14 pages. Mirror the reference deck's arc:
        Cover → Brief/Thesis → for EACH account: Section divider + Situation page +
        Bet/Plan page → Roll-up with combined number → Closing with the ask.
    - Each per-account block must have at least 2 pages (one situation, one bet).
      A 6-page deck for 3 accounts is shallow and unacceptable.
    - The Situation page must paint a vivid picture of the customer: who they are,
      scale (members / clinics / employees / countries / revenue / market position),
      what they're doing right now (recent transformations, hiring signals,
      acquisitions, competitor moves), and why this moment is the right moment.
      Use 3+ stat cards (big number + caption) plus a narrative paragraph.
    - The Bet page must name the specific Microsoft motion, the size of the prize,
      the 2–3 plays we run, and the next step / ask of the room.
    - ENRICH from your training knowledge: when an account is a well-known
      Israeli or global company (Clalit, Teva, Bank Hapoalim, Phoenix, El Al,
      Strauss, Elbit, Rafael, NICE, Amdocs, Check Point, Wix, Mobileye, etc.),
      use the public facts you know about them — headcount, revenue scale,
      market position, recent strategic moves, AI initiatives, transformation
      programs. The brief gives you the deal numbers; YOU bring the story.
      Never fabricate numbers or quotes, but real well-known facts about a public
      company are exactly what makes the deck land.
    - When the brief includes Tavily news links, work them into the relevant
      Situation page as clickable evidence (`<a href="...">`) — these are real,
      verifiable, and dated.

    DENSITY — the reference deck below (`d365-sales-play`) is the GOLD
    STANDARD. It has bespoke per-page JSX, custom atoms (Stat, Chip, PlayCard,
    AccountRow, PipeCard, Step), heavy use of color-coded big numbers, and
    paragraphs of customer-specific narrative. Each per-account page is a
    uniquely-named const (ClalitIntro, ClalitPlay, NuveiIntro, NuveiPlay,
    TevaIntro, TevaPlay) with hand-written content — NOT a generic factory.
    Match THAT density and that construction style. A deck under ~15KB / 400
    lines of TSX is a failure.

    TARGET LENGTH: 9–14 pages, ~400–600 lines of TSX, ~15–25KB.
""")


def _camel(name: str) -> str:
    """Turn 'Bank Hapoalim B M' or 'kupat-holim' into 'BankHapoalim' for use
    as a TSX component-name prefix. Strips non-letters, title-cases words."""
    parts = re.split(r"[^A-Za-z0-9]+", (name or "").strip())
    out = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    # Drop trailing single letters that are usually corporate suffix junk
    # ('B M', 'L T D'). Keep the result alphanumeric only.
    out = re.sub(r"[^A-Za-z0-9]", "", out)
    return out or "Account"


def _build_page_checklist(brief: dict) -> str:
    """Return an explicit, account-specific page list the model MUST emit in
    full. This stops gpt-4o from writing 3 pages then dropping a TODO comment
    (`// Additional pages for X would follow the same format`). Every name
    here MUST appear as a real `const Name: Page = () => (...)` AND in the
    default export array."""
    accounts = []
    for a in brief.get("accounts", []) or []:
        nm = (a.get("acc") or {}).get("name") or ""
        if nm:
            accounts.append(nm)
    if not accounts:
        return ""

    per_account_lines: list[str] = []
    for nm in accounts:
        c = _camel(nm)
        per_account_lines.append(
            f"  - `{c}Divider` \u2014 full-bleed divider naming the account"
        )
        per_account_lines.append(
            f"  - `{c}Situation` \u2014 who they are, scale, recent moves, 3+ Stat cards"
        )
        per_account_lines.append(
            f"  - `{c}Play` \u2014 our motion, 2\u20133 PlayCards, the ask"
        )

    expected = ["Cover", "TheBrief", "Thesis"]
    for nm in accounts:
        c = _camel(nm)
        expected += [f"{c}Divider", f"{c}Situation", f"{c}Play"]
    expected += ["RollUp", "NextSteps"]

    head = (
        "=== PAGE CHECKLIST (MANDATORY \u2014 emit EVERY page in full) ===\n"
        f"You must produce exactly these {len(expected)} page components, in this order, "
        "each as a bespoke `const Name: Page = () => (...)` with hand-written JSX. "
        "Then list every name in the default export array. Do NOT use placeholder "
        "comments \u2014 emit the complete TSX for every page.\n\n"
        "  - `Cover` \u2014 hero title + account chips\n"
        "  - `TheBrief` \u2014 combined pipeline number + per-account stat cards\n"
        "  - `Thesis` \u2014 why this product, why now, in one strong page\n"
    )
    tail = (
        "  - `RollUp` \u2014 combined number across all accounts, side-by-side\n"
        "  - `NextSteps` \u2014 the ask of the room, numbered Steps\n\n"
        f"Required default export: `export default [{', '.join(expected)}] satisfies Page[];`\n\n"
    )
    return head + "\n".join(per_account_lines) + "\n" + tail


def _build_messages(brief: dict, prompt_md: str) -> list[dict]:
    skill_authoring = _read_text(SKILL_AUTHORING)
    skill_create = _read_text(SKILL_CREATE)
    example_rich = _read_example_rich()

    system_full = (
        _SYSTEM_PROMPT_HEAD
        + "\n\n=== open-slide skill: create-slide/SKILL.md ===\n"
        + skill_create
        + "\n\n=== open-slide skill: slide-authoring/SKILL.md ===\n"
        + skill_authoring
        + "\n\n=== Reference example (CONTENT-DENSITY gold standard — match this richness AND this construction style): slides/d365-sales-play/index.tsx ===\n"
        + example_rich
    )

    user_msg = (
        "Build me a brand-new slide deck for the brief below. Output ONLY the "
        "TSX file content, ready to write to disk at `slides/<id>/index.tsx`. "
        "Pick a sensible kebab-case id and tell me about it via the trailing "
        "// PITCH comment.\n\n"
        + _build_page_checklist(brief)
        + f"=== BRIEF (markdown form, also includes house rules) ===\n{prompt_md}\n\n"
        + f"=== BRIEF (structured form) ===\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n"
    )

    return [
        {"role": "system", "content": system_full},
        {"role": "user", "content": user_msg},
    ]


def _select_backend() -> str:
    """Default = AOAI gpt-4o (Ronen's local-only setup; Entra auth, fast, no
    reasoning-token tax). Switch to Cohere with LLM_BACKEND=cohere — useful as
    a fallback if the AOAI resource is down or for quick A/B tests."""
    explicit = os.getenv("LLM_BACKEND", "").strip().lower()
    if explicit == "cohere":
        return "cohere"
    if explicit in ("aoai", "azure"):
        return "aoai"
    return "aoai"


def _call_cohere(messages: list[dict]) -> str:
    key = os.getenv("COHERE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("COHERE_API_KEY is not set.")
    model = os.getenv("COHERE_MODEL", DEFAULT_COHERE_MODEL).strip()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 6000,
    }
    r = requests.post(
        COHERE_CHAT_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=600,
    )
    if not r.ok:
        body = r.text.strip() or "(empty)"
        raise RuntimeError(f"Cohere returned {r.status_code}. Body: {body[:600]}")
    data = r.json()
    parts = (data.get("message", {}) or {}).get("content", []) or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text:
        raise RuntimeError(f"Cohere response had no text content: {json.dumps(data)[:600]}")
    return text


def _messages_to_responses_input(messages: list[dict]) -> list[dict]:
    """Convert Chat Completions–style messages into the Responses API
    `input` array. Each entry becomes a typed item with role + content
    parts. The Responses API uses `input_text` for user/system input."""
    out: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        out.append(
            {
                "role": role,
                "content": [{"type": "input_text", "text": content}],
            }
        )
    return out


def _extract_responses_text(data: dict) -> str:
    """Pull the assistant's visible text out of a Responses-API response.
    Looks for the first `message`-typed output item with `output_text`
    content. Falls back to the convenience `output_text` field if present."""
    if isinstance(data.get("output_text"), str) and data["output_text"]:
        return data["output_text"]
    for item in data.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text" and part.get("text"):
                return part["text"]
    return ""


def _call_aoai_responses(messages: list[dict]) -> str:
    """Call the Azure OpenAI Responses API (the only API that supports the
    gpt-5.x reasoning models). Auth is Entra-only."""
    endpoint, deployment, api_version = _runtime_config()
    url = f"{endpoint}/openai/responses"
    payload = {
        "model": deployment,
        "input": _messages_to_responses_input(messages),
        # gpt-5.x burns hidden reasoning tokens before producing visible text.
        # Give the model plenty of headroom for a 9–14 page deck (~12k visible
        # output tokens) plus reasoning overhead.
        "max_output_tokens": 32000,
        "reasoning": {"effort": "medium"},
        "store": False,
    }
    headers = {"Content-Type": "application/json", **_entra_token_headers()}
    r = requests.post(
        url, headers=headers, params={"api-version": api_version}, json=payload, timeout=600
    )
    if not r.ok:
        req_id = r.headers.get("apim-request-id", "n/a")
        body = r.text.strip() or "(empty)"
        raise RuntimeError(
            f"Azure OpenAI Responses API returned {r.status_code} (request {req_id}). "
            f"Endpoint={endpoint} deployment={deployment}. Body: {body[:600]}"
        )
    data = r.json()
    text = _extract_responses_text(data)
    if not text:
        status = data.get("status", "?")
        incomplete = data.get("incomplete_details", {})
        raise RuntimeError(
            f"AOAI Responses returned no visible text (status={status}, incomplete={incomplete}). "
            f"Raw response: {json.dumps(data)[:800]}"
        )
    return text


def _call_aoai_chat(messages: list[dict]) -> str:
    """Call the Azure OpenAI Chat Completions API. Used for non-reasoning
    models (gpt-4o, gpt-4.1, gpt-3.5-turbo). Faster and cheaper than the
    Responses API for these models — no hidden reasoning tokens."""
    endpoint, deployment, api_version = _runtime_config()
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions"
    payload = {
        "messages": messages,
        "temperature": 0.7,
        # gpt-4.1 caps completion at 32768 tokens (2× gpt-4o). Use most of it
        # so a full deck (9–14 rich pages, ~600 lines TSX) can fit in one shot.
        "max_tokens": 32000,
    }
    headers = {"Content-Type": "application/json", **_entra_token_headers()}
    r = requests.post(
        url, headers=headers, params={"api-version": api_version}, json=payload, timeout=600
    )
    if not r.ok:
        req_id = r.headers.get("apim-request-id", "n/a")
        body = r.text.strip() or "(empty)"
        raise RuntimeError(
            f"Azure OpenAI Chat Completions returned {r.status_code} (request {req_id}). "
            f"Endpoint={endpoint} deployment={deployment}. Body: {body[:600]}"
        )
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"AOAI Chat returned no choices. Raw: {json.dumps(data)[:600]}")
    text = (choices[0].get("message", {}) or {}).get("content", "") or ""
    if not text:
        raise RuntimeError(f"AOAI Chat returned empty content. Raw: {json.dumps(data)[:600]}")
    return text


def _is_reasoning_model(deployment: str) -> bool:
    """Reasoning models (gpt-5.x, o1, o3, o4) only expose the Responses API
    on this resource. Everything else is fine on Chat Completions."""
    d = deployment.lower()
    return d.startswith("gpt-5") or d.startswith("o1") or d.startswith("o3") or d.startswith("o4")


def _call_aoai(messages: list[dict]) -> tuple[str, str]:
    _, deployment, _ = _runtime_config()
    if _is_reasoning_model(deployment):
        return _call_aoai_responses(messages), "aoai-responses"
    return _call_aoai_chat(messages), "aoai-chat"


def _call_llm(messages: list[dict]) -> tuple[str, str]:
    backend = _select_backend()
    if backend == "cohere":
        return _call_cohere(messages), "cohere"
    return _call_aoai(messages)


# ─── Tavily web research (optional, used by Mode C smart picker) ─────────────
TAVILY_URL = "https://api.tavily.com/search"


def _tavily_search(query: str, *, max_results: int = 3, days: int = 365) -> list[dict]:
    """Return up to `max_results` recent web hits for `query`. Empty list on
    any failure (including no API key) — the caller decides what to do."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        r = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "days": days,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=15,
        )
        if r.status_code != 200:
            return []
        results = (r.json() or {}).get("results") or []
        out = []
        for hit in results[:max_results]:
            out.append({
                "title": (hit.get("title") or "").strip()[:200],
                "url": hit.get("url") or "",
                "snippet": (hit.get("content") or "").strip()[:400],
                "published": hit.get("published_date") or "",
            })
        return out
    except Exception:
        return []


def _research_account(name: str, sub_segment: str = "") -> list[dict]:
    """One Tavily query per account, biased toward Israeli business news.
    Caller runs this in a thread pool."""
    seg = f" ({sub_segment})" if sub_segment else ""
    query = (
        f'"{name}" Israel news 2025..2026 strategy OR layoffs OR acquisition '
        f'OR "AI" OR cloud OR Microsoft{seg}'
    )
    return _tavily_search(query, max_results=3, days=365)


# ─── Mode C smart picker — LLM + (optional) Tavily ───────────────────────────
def _whitespace_pick_messages(
    candidates: list[dict],
    product: dict,
    research: dict[str, list[dict]],
) -> list[dict]:
    """Build the chat messages for the smart whitespace picker. Output contract
    is a strict JSON object so the frontend can parse without surprises."""
    plabel = product.get("label") or "the chosen Microsoft product"
    pkw = ", ".join(product.get("playKeywords") or []) or "n/a"

    cand_blocks = []
    for c in candidates:
        name = c.get("originalName") or c.get("name") or ""
        bits = [
            f"  - Sub-segment: {c.get('subSegment') or 'n/a'}",
            f"  - M365 install base: E3 {int(c.get('e3Seats') or 0):,} seats / "
            f"E5 {int(c.get('e5Seats') or 0):,} seats / "
            f"E5-Sec {int(c.get('e5SecuritySeats') or 0):,} / "
            f"E5-Comp {int(c.get('e5ComplianceSeats') or 0):,}",
            f"  - IW PCIB: {int(c.get('iwPcib') or 0):,}",
            f"  - FY27 whitespace headroom: {int(c.get('fy27WhitespaceSeats') or 0):,} seats",
            f"  - ME5 full potential revenue: ${int(c.get('me5PotentialRevenue') or 0):,}",
        ]
        if c.get("fy26FlipOrGfa"):
            bits.append(f"  - FY26 Flip/GFA status: {c['fy26FlipOrGfa']}")
        if c.get("comments"):
            bits.append(f"  - Field notes: {c['comments']}")

        hits = research.get(name) or []
        if hits:
            bits.append("  - Recent news (Tavily, last 12 months):")
            for h in hits:
                line = f"      • {h['title']}"
                if h.get("published"):
                    line += f" ({h['published']})"
                line += f" — {h['url']}"
                if h.get("snippet"):
                    line += f"\n          {h['snippet']}"
                bits.append(line)
        else:
            bits.append("  - Recent news: (no fresh signal — rely on the data above)")

        cand_blocks.append(f"Candidate: {name}\n" + "\n".join(bits))

    system = (
        "You are a senior Microsoft seller for ABS Israel (FY27). Your job is to "
        "pick the THREE accounts most likely to buy a specific Microsoft product, "
        "based on (a) M365 / ME5 install footprint and whitespace headroom, "
        "(b) sub-segment / industry fit for the product, and (c) any recent news "
        "signal that suggests momentum or urgency (M&A, leadership change, layoffs, "
        "AI initiative, regulatory pressure, security incident, cloud migration, etc.).\n\n"
        "Be honest about evidence. If recent news is missing for an account, you may "
        "still pick it — but lean on the install-base / whitespace fit and say so. "
        "Do NOT invent news, opportunities, owners, contacts, or pipeline numbers.\n\n"
        "Output STRICT JSON only — no prose, no markdown fences. Schema:\n"
        '{ "picks": [ { "name": "<exact candidate name>", '
        '"reason": "<1–2 sentences, plain English, mention the product fit + the strongest signal>", '
        '"evidence": [ { "title": "<news title>", "url": "<url>" } ] } ] }\n'
        "Exactly 3 picks. `evidence` may be empty if no news was provided. "
        "`name` MUST be copied verbatim from the candidate list — no paraphrasing."
    )

    user = (
        f"Product to sell: {plabel}\n"
        f"Play keywords (motion hints): {pkw}\n\n"
        f"=== Candidates ({len(candidates)}) ===\n\n"
        + "\n\n".join(cand_blocks)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_picks_json(raw: str) -> list[dict]:
    """Tolerant JSON extractor — handles fenced code blocks and stray prose."""
    s = _strip_fences(raw).strip()
    # Find the first {...} block if the model wrapped it.
    if not s.startswith("{"):
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            s = m.group(0)
    try:
        data = json.loads(s)
    except Exception:
        return []
    picks = data.get("picks") if isinstance(data, dict) else None
    if not isinstance(picks, list):
        return []
    out = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").strip()
        if not name:
            continue
        reason = (p.get("reason") or "").strip()
        evidence = p.get("evidence") or []
        if not isinstance(evidence, list):
            evidence = []
        ev_clean = []
        for e in evidence[:5]:
            if isinstance(e, dict) and e.get("url"):
                ev_clean.append({
                    "title": (e.get("title") or e["url"])[:200],
                    "url": e["url"],
                })
        out.append({"name": name, "reason": reason, "evidence": ev_clean})
    return out[:3]


# ─── TSX post-processing & file write ────────────────────────────────────────

_FENCE_OPEN_RE = re.compile(r"^\s*```(?:tsx?|typescript|jsx?|javascript)?\s*\n?", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n?\s*```\s*$")


def _strip_fences(s: str) -> str:
    """Strip a leading ```lang fence and trailing ``` fence if present.
    Tolerant of: missing language tag, missing newline after the opener,
    missing trailing fence, leading whitespace/prose. We also fall back to
    slicing from the first `import` line if everything else fails — gpt-4o
    occasionally prefixes a one-liner like ```tsx before the imports."""
    s = s.strip()
    s = _FENCE_OPEN_RE.sub("", s, count=1)
    s = _FENCE_CLOSE_RE.sub("", s)
    s = s.strip()
    # Last-resort safety net: if there's still leading junk before the first
    # `import`, drop it. This catches any other prose the model added.
    if not s.startswith("import"):
        idx = s.find("\nimport ")
        if idx == -1:
            idx = s.find("import ")
        if idx > 0:
            s = s[idx:].lstrip()
    return s


_PITCH_RE = re.compile(r"//\s*PITCH:\s*(.+?)\s*$", re.MULTILINE)


def _extract_pitch(tsx: str) -> str:
    matches = _PITCH_RE.findall(tsx)
    return matches[-1].strip() if matches else ""


# ─── Laziness detection ─────────────────────────────────────────────────────
# gpt-4o has a strong tendency to write 3 pages then drop a placeholder
# comment ("// CONTINUE WITH THE REST...", "// Additional pages would go
# here", "[Cover /* , TheBrief, ... */ ]"). The system prompt forbids it
# but the model still does it. We detect those cases server-side and ask
# for a second pass that fills in the missing pages.

_LAZY_PATTERNS = [
    re.compile(r"//\s*CONTINUE\b", re.IGNORECASE),
    re.compile(r"//\s*\(?Additional\s+(account|page|slide)", re.IGNORECASE),
    re.compile(r"//\s*TODO[: ]", re.IGNORECASE),
    re.compile(r"//\s*\.{3}", re.IGNORECASE),  # "// ..."
    re.compile(r"//\s*(rest|remaining|other)\s+(pages|slides|accounts)", re.IGNORECASE),
    re.compile(r"//\s*omitted\b", re.IGNORECASE),
    re.compile(r"//\s*would\s+(follow|come|go)\b", re.IGNORECASE),
]

# A commented-out chunk inside the export array, e.g.
# `export default [Cover /* , TheBrief, Thesis */ ]`
_EXPORT_COMMENT_RE = re.compile(
    r"export\s+default\s*\[[^\]]*/\*[^*]*(?:\*(?!/)[^*]*)*\*/[^\]]*\]",
    re.DOTALL,
)


def _list_export_names(tsx: str) -> list[str]:
    """Extract the names listed in `export default [Foo, Bar, Baz]`. Returns
    [] if no such export found. Strips out commented-out names so we count
    only the ones that will actually render."""
    m = re.search(r"export\s+default\s*\[(.*?)\]\s*(?:satisfies|as)?",
                  tsx, re.DOTALL)
    if not m:
        return []
    inside = m.group(1)
    # Remove block comments so commented-out names don't count.
    inside = re.sub(r"/\*.*?\*/", "", inside, flags=re.DOTALL)
    inside = re.sub(r"//[^\n]*", "", inside)
    parts = [p.strip() for p in inside.split(",")]
    return [p for p in parts if p and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p)]


def _list_defined_pages(tsx: str) -> list[str]:
    """Find every `const Name: Page = ...` defined in the file."""
    return re.findall(r"^\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*Page\b", tsx, re.MULTILINE)


def _expected_page_names(brief: dict) -> list[str]:
    accounts = [(a.get("acc") or {}).get("name", "") for a in brief.get("accounts", []) or []]
    accounts = [a for a in accounts if a]
    expected = ["Cover", "TheBrief", "Thesis"]
    for nm in accounts:
        c = _camel(nm)
        expected += [f"{c}Divider", f"{c}Situation", f"{c}Play"]
    expected += ["RollUp", "NextSteps"]
    return expected


def _detect_laziness(tsx: str, brief: dict) -> tuple[bool, list[str], list[str]]:
    """Return (is_lazy, missing_pages, reasons)."""
    reasons: list[str] = []

    for pat in _LAZY_PATTERNS:
        m = pat.search(tsx)
        if m:
            reasons.append(f"placeholder comment found: {m.group(0)!r}")
            break

    if _EXPORT_COMMENT_RE.search(tsx):
        reasons.append("export array contains a commented-out section (/* ... */)")

    expected = _expected_page_names(brief)
    exported = set(_list_export_names(tsx))
    defined = set(_list_defined_pages(tsx))
    rendered = exported & defined  # only pages both defined AND exported show up
    missing = [n for n in expected if n not in rendered]

    # Less strict than "every checklist name" — if at least 80% are present
    # we consider it good enough. The checklist is a target, not a contract.
    threshold = max(6, int(len(expected) * 0.7))
    if len(rendered) < threshold:
        reasons.append(
            f"only {len(rendered)} pages will render (defined+exported), "
            f"expected at least {threshold} of {len(expected)}"
        )

    is_lazy = bool(reasons)
    return is_lazy, missing, reasons


def _build_continuation_messages(
    brief: dict, prompt_md: str, prior_tsx: str, missing: list[str], reasons: list[str]
) -> list[dict]:
    """Build a follow-up call that asks the model to re-emit the WHOLE file
    with the missing pages added. We pass the original system prompt + the
    prior (incomplete) output and tell it precisely what to fix."""
    base = _build_messages(brief, prompt_md)
    fix = (
        "Your previous attempt was INCOMPLETE. Issues found:\n"
        + "\n".join(f"  - {r}" for r in reasons)
        + "\n\n"
        "Missing page components that MUST be added: "
        + ", ".join(missing) + "\n\n"
        "Output the COMPLETE TSX file again, from `import` to `// PITCH:`, "
        "with EVERY page from the checklist defined as its own bespoke "
        "`const Name: Page = () => (...)` and listed in the default export "
        "array. NO placeholder comments. NO `// CONTINUE...`. NO `/* , X, Y */`. "
        "NO `// Additional pages would go here`. Just the full file. "
        "Reuse the atoms (Tag, Chip, Stat, Bullet, PlayCard, Footer) you "
        "already defined \u2014 do not redefine them.\n\n"
        "Here is your previous incomplete output for reference (do NOT just "
        "repeat it \u2014 expand it):\n\n"
        + prior_tsx
    )
    return base + [
        {"role": "assistant", "content": prior_tsx},
        {"role": "user", "content": fix},
    ]


_KEBAB_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    s = _KEBAB_RE.sub("-", name.lower()).strip("-")
    return s[:40] or "deck"


def _build_slide_id(brief: dict) -> str:
    accounts = [a.get("acc", {}).get("name", "") for a in brief.get("accounts", [])]
    seed_words: list[str] = []
    for n in accounts[:3]:
        first_word = (n or "").split()[0].lower() if n else ""
        if first_word:
            seed_words.append(first_word)
    product = (brief.get("product") or {}).get("id") or "deck"
    stamp = time.strftime("%y%m%d-%H%M")
    base = "-".join([*seed_words, product]) or "deck"
    return f"{_slugify(base)}-{stamp}"


def _write_slide(slide_id: str, tsx: str) -> Path:
    slide_dir = SLIDES_DIR / slide_id
    slide_dir.mkdir(parents=True, exist_ok=True)
    slide_path = slide_dir / "index.tsx"
    slide_path.write_text(_stamp_meta_title(tsx), encoding="utf-8")
    return slide_path


# Append the creation timestamp to the deck's exported meta.title so the
# open-slide draft UI (localhost:5173) shows when each deck was made and
# the user can tell which one is the latest at a glance. We rewrite the
# `export const meta: SlideMeta = { title: '...' }` line if present, or
# inject one at the end of the file as a fallback.
_META_TITLE_RE = re.compile(
    r"""(export\s+const\s+meta\s*:\s*SlideMeta\s*=\s*\{\s*title\s*:\s*)(['"])(.*?)\2""",
    re.DOTALL,
)


def _stamp_meta_title(tsx: str) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M")
    suffix = f"  ·  {stamp}"

    def _sub(m: re.Match[str]) -> str:
        head, q, current = m.group(1), m.group(2), m.group(3)
        # If we somehow re-process a stamped file, don't double-stamp.
        if re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", current):
            return m.group(0)
        return f"{head}{q}{current}{suffix}{q}"

    new_tsx, n = _META_TITLE_RE.subn(_sub, tsx, count=1)
    if n:
        return new_tsx

    # No meta export found — append a minimal one before the trailing PITCH
    # comment (or at end of file) so the card still gets a label.
    fallback = (
        f"\n\nexport const meta: SlideMeta = {{ title: 'Deck{suffix}' }};\n"
    )
    pitch_idx = tsx.rfind("// PITCH")
    if pitch_idx == -1:
        return tsx.rstrip() + fallback
    return tsx[:pitch_idx].rstrip() + fallback + "\n" + tsx[pitch_idx:]


# ─── Flask app ───────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(HERE), static_url_path="")


@app.get("/")
def index():
    return send_from_directory(str(HERE), "index.html")


@app.get("/api/health")
def health():
    backend = _select_backend()
    if backend == "cohere":
        model = os.getenv("COHERE_MODEL", DEFAULT_COHERE_MODEL)
        return jsonify(
            {
                "ok": True,
                "backend": "cohere",
                "model": model,
                "endpoint": COHERE_CHAT_URL,
                "slidesDir": str(SLIDES_DIR.relative_to(REPO_ROOT)),
                "devServerUrl": DEV_SERVER_URL,
            }
        )
    endpoint, deployment, api_version = _runtime_config()
    api = "responses" if _is_reasoning_model(deployment) else "chat"
    return jsonify(
        {
            "ok": True,
            "backend": f"aoai-{api}",
            "model": deployment,
            "endpoint": endpoint,
            "apiVersion": api_version,
            "auth": "entra",
            "slidesDir": str(SLIDES_DIR.relative_to(REPO_ROOT)),
            "devServerUrl": DEV_SERVER_URL,
            "tavilyEnabled": bool(os.getenv("TAVILY_API_KEY", "").strip()),
        }
    )


@app.post("/api/whitespace-pick")
def whitespace_pick():
    """Mode C smart picker. Given the full whitespace dataset + a chosen
    Microsoft product, returns the 3 best-fit accounts with reasons and
    optional news evidence (when TAVILY_API_KEY is set)."""
    from concurrent.futures import ThreadPoolExecutor

    body = request.get_json(silent=True) or {}
    accounts_in = body.get("accounts") or []
    product = body.get("product") or {}
    candidates_limit = max(3, min(int(body.get("candidatesLimit") or 12), 30))

    if not isinstance(accounts_in, list) or not accounts_in:
        return jsonify({"error": "Missing accounts[] in request body."}), 400
    if not (product.get("label") or product.get("id")):
        return jsonify({"error": "Missing product.label / product.id."}), 400

    # Score-and-trim to the strongest candidates so the prompt stays focused.
    def _score(a: dict) -> float:
        return (
            float(a.get("me5PotentialRevenue") or 0) * 1.0
            + float(a.get("fy27WhitespaceSeats") or 0) * 50.0
            + float(a.get("e3Seats") or 0) * 5.0
        )

    candidates = sorted(accounts_in, key=_score, reverse=True)[:candidates_limit]

    # Parallel Tavily research (no-ops when TAVILY_API_KEY is missing).
    research: dict[str, list[dict]] = {}
    used_tavily = bool(os.getenv("TAVILY_API_KEY", "").strip())
    if used_tavily:
        names = [(c.get("originalName") or c.get("name") or "").strip() for c in candidates]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(_research_account, n, c.get("subSegment") or ""): n
                for n, c in zip(names, candidates)
                if n
            }
            for fut in futures:
                name = futures[fut]
                try:
                    research[name] = fut.result(timeout=20) or []
                except Exception:
                    research[name] = []

    # LLM reasoning over candidates + research → strict JSON.
    try:
        messages = _whitespace_pick_messages(candidates, product, research)
        raw, backend_used = _call_llm(messages)
    except Exception as e:
        return jsonify({"error": f"LLM call failed: {e}"}), 502

    picks = _parse_picks_json(raw)
    if not picks:
        return jsonify({
            "error": "Model did not return parseable picks JSON.",
            "rawPreview": raw[:600],
        }), 502

    # Re-attach the full whitespace record per pick (verbatim name match,
    # case-insensitive fallback) so the frontend can build the brief without
    # another lookup.
    by_name = {(c.get("originalName") or c.get("name") or "").strip(): c for c in accounts_in}
    by_name_lower = {k.lower(): v for k, v in by_name.items()}
    enriched: list[dict] = []
    for p in picks:
        rec = by_name.get(p["name"]) or by_name_lower.get(p["name"].lower())
        if not rec:
            # Model fabricated a name — drop it, frontend will show how many we have.
            continue
        enriched.append({
            "name": rec.get("originalName") or rec.get("name") or p["name"],
            "reason": p["reason"],
            "evidence": p["evidence"],
            "ws": rec,
        })

    if not enriched:
        return jsonify({
            "error": "Model returned picks but none matched a known account name.",
            "rawPreview": raw[:600],
        }), 502

    return jsonify({
        "picks": enriched,
        "candidatesConsidered": len(candidates),
        "totalAccounts": len(accounts_in),
        "usedTavily": used_tavily,
        "backend": backend_used,
        "product": {"id": product.get("id"), "label": product.get("label")},
    })


@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    brief = body.get("brief") or {}
    prompt_md = body.get("prompt") or ""
    if not brief.get("accounts"):
        return jsonify({"error": "Missing brief.accounts"}), 400

    try:
        messages = _build_messages(brief, prompt_md)
        raw, backend_used = _call_llm(messages)
    except Exception as e:
        return jsonify({"error": f"LLM call failed: {e}"}), 502

    tsx = _strip_fences(raw)
    if not tsx.lstrip().startswith("import"):
        return jsonify(
            {
                "error": "Model output does not look like a TSX file (must start with `import`). "
                "First 400 chars: " + tsx[:400]
            }
        ), 502

    # ── Anti-laziness: detect placeholder comments / stubbed exports and
    # do up to 2 follow-up calls to fill in the missing pages. gpt-4o
    # consistently writes 3 rich pages then bails with a "// CONTINUE..."
    # comment; this loop catches it and asks for the rest.
    retries = 0
    retry_log: list[dict] = []
    while retries < 2:
        is_lazy, missing, reasons = _detect_laziness(tsx, brief)
        if not is_lazy:
            break
        retry_log.append({
            "attempt": retries + 1,
            "reasons": reasons,
            "missing": missing,
            "prevBytes": len(tsx.encode("utf-8")),
        })
        try:
            cont_messages = _build_continuation_messages(
                brief, prompt_md, tsx, missing, reasons
            )
            cont_raw, _ = _call_llm(cont_messages)
            cont_tsx = _strip_fences(cont_raw)
            if cont_tsx.lstrip().startswith("import"):
                tsx = cont_tsx
        except Exception as e:
            retry_log[-1]["error"] = str(e)
            break
        retries += 1

    slide_id = _build_slide_id(brief)
    try:
        slide_path = _write_slide(slide_id, tsx)
    except Exception as e:
        return jsonify({"error": f"Could not write slide: {e}"}), 500

    pitch = _extract_pitch(tsx) or "Open the deck in your dev server to see it live."
    rel_path = slide_path.relative_to(REPO_ROOT).as_posix()

    return jsonify(
        {
            "slideId": slide_id,
            "slidePath": rel_path,
            "devUrl": DEV_SERVER_URL.rstrip("/") + "/",
            "pitch": pitch,
            "tsxPreview": tsx[:6000],
            "tsxBytes": len(tsx.encode("utf-8")),
            "backend": backend_used,
            "retryLog": retry_log,
        }
    )


def main() -> None:
    backend = _select_backend()
    print(f"\n  Deck Builder → http://localhost:{PORT}")
    print(f"  Slides dir   → {SLIDES_DIR}")
    if backend == "cohere":
        print(f"  LLM backend  → cohere ({os.getenv('COHERE_MODEL', DEFAULT_COHERE_MODEL)})")
    else:
        endpoint, deployment, _ = _runtime_config()
        print(f"  LLM backend  → aoai ({endpoint}, deployment {deployment})")
    print(f"  Dev server   → {DEV_SERVER_URL}\n")
    if "--no-open" not in sys.argv:
        # Open browser shortly after server boots
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except Exception:
            pass
    # threaded=True so a slow Azure OpenAI call doesn't block /api/health probes
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
