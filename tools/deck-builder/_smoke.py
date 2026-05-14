"""Quick end-to-end smoke test for the deck-builder server. Posts a sample brief
to /api/generate, prints the result, and confirms the slide TSX was written."""
import json
import sys
from pathlib import Path

import requests

BASE = "http://localhost:8765"

brief = {
    "mode": "magic",
    "language": "english",
    "languageLabel": "English",
    "tone": "executive",
    "toneLabel": "Executive",
    "product": {
        "id": "ci-rt",
        "label": "CI-RT (Customer Insights - Real Time)",
        "playKeywords": ["personalization", "journey", "real-time"],
    },
    "accounts": [
        {
            "acc": {"name": "MACCABI HEALTH SERVICES", "industry": "Healthcare", "total": 16834958, "opps": 6},
            "breakdown": "industry fit + healthcare + active opps",
            "reasons": ["Largest healthcare pipeline", "6 active opps"],
            "score": 88,
        },
        {
            "acc": {"name": "PHOENIX INSURANCE", "industry": "Insurance", "total": 1900000, "opps": 3},
            "breakdown": "P&C insurer with proactive engagement need",
            "reasons": ["Active CCaaS play", "FNOL automation in roadmap"],
            "score": 79,
        },
        {
            "acc": {"name": "BANK HAPOALIM", "industry": "Financial Services", "total": 2100000, "opps": 4},
            "breakdown": "FSI with personalization use cases",
            "reasons": ["Open banking journeys", "Compete vs Salesforce"],
            "score": 76,
        },
    ],
    "generatedAt": "2026-05-13",
}

prompt = (
    "Build me a 9-page FY27 Big Bet deck for the brief above. Anchor on "
    "CI-RT (Customer Insights - Real Time). Honor the house rules in AGENTS.md."
)

print("[smoke] GET /api/health")
h = requests.get(f"{BASE}/api/health", timeout=10).json()
print(json.dumps(h, indent=2))

print("\n[smoke] POST /api/generate (this can take 30-90s) ...")
r = requests.post(f"{BASE}/api/generate", json={"brief": brief, "prompt": prompt}, timeout=600)
if not r.ok:
    print(f"FAIL {r.status_code}: {r.text[:1000]}")
    sys.exit(1)
res = r.json()

print()
print(f"  slideId   : {res['slideId']}")
print(f"  slidePath : {res['slidePath']}")
print(f"  backend   : {res['backend']}")
print(f"  tsxBytes  : {res['tsxBytes']}")
print(f"  pitch     : {res['pitch']}")
print(f"  devUrl    : {res['devUrl']}")

# Verify the file exists on disk
repo_root = Path(__file__).resolve().parent.parent.parent
slide_path = repo_root / res["slidePath"]
print(f"\n[smoke] file on disk: {slide_path.exists()}  ({slide_path})")
if slide_path.exists():
    head = slide_path.read_text(encoding="utf-8").splitlines()[:6]
    print("[smoke] first 6 lines:")
    for line in head:
        print(f"    {line}")
