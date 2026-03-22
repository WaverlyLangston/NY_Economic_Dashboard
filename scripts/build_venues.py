#!/usr/bin/env python3
"""
build_venues.py
---------------
One-time script that uses the Anthropic API with web search to build
a comprehensive venues.json for NYC Music Map.

Run this locally when you want to expand or refresh the venue list.
It works in batches so it never hits output limits.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/build_venues.py

Output:
    venues.json  (in repo root)

The script searches for venues in batches by borough + neighborhood,
deduplicates, assigns IDs, and writes the final file.
"""

import json
import os
import re
import time
from pathlib import Path

import anthropic

BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "venues.json"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ── Search batches: (borough, neighborhood_or_focus, tier_hint) ───────────
# Each entry becomes one API call. Adjust or add entries to expand coverage.
SEARCH_BATCHES = [
    # ── Manhattan DIY / small ──────────────────────────────────────────────
    ("Manhattan", "Lower East Side small bars and DIY venues", 1),
    ("Manhattan", "East Village small music venues and bars", 1),
    ("Manhattan", "West Village and Greenwich Village jazz and small clubs", 1),
    ("Manhattan", "Harlem jazz clubs and music venues", 1),
    ("Manhattan", "Washington Heights and Inwood music venues", 1),
    ("Manhattan", "Hell's Kitchen and Midtown small music venues", 1),
    ("Manhattan", "Upper West Side music venues", 2),
    ("Manhattan", "SoHo TriBeCa Chelsea music venues and galleries", 1),
    ("Manhattan", "larger Manhattan concert halls and theaters", 3),
    # ── Brooklyn DIY / small ───────────────────────────────────────────────
    ("Brooklyn", "Bushwick DIY spaces and small music venues", 1),
    ("Brooklyn", "Ridgewood and East Williamsburg small venues and bars", 1),
    ("Brooklyn", "Williamsburg and Greenpoint music bars and venues", 1),
    ("Brooklyn", "Bed-Stuy Crown Heights Flatbush music bars", 1),
    ("Brooklyn", "Park Slope Gowanus Red Hook music venues", 1),
    ("Brooklyn", "Downtown Brooklyn DUMBO Fort Greene music", 2),
    ("Brooklyn", "Prospect Heights Carroll Gardens Cobble Hill music bars", 1),
    ("Brooklyn", "Sunset Park and Bay Ridge music venues", 1),
    ("Brooklyn", "Coney Island Brighton Beach music venues", 2),
    ("Brooklyn", "larger Brooklyn concert venues and clubs", 3),
    # ── Queens ────────────────────────────────────────────────────────────
    ("Queens", "Ridgewood Maspeth Glendale small music venues", 1),
    ("Queens", "Astoria Long Island City music bars and venues", 1),
    ("Queens", "Jackson Heights Elmhurst Woodside music venues", 1),
    ("Queens", "Flushing Jamaica music venues and clubs", 2),
    ("Queens", "Forest Hills Rockaway other Queens music venues", 2),
    # ── Bronx ─────────────────────────────────────────────────────────────
    ("Bronx", "Mott Haven Hunts Point South Bronx music venues", 1),
    ("Bronx", "Fordham Tremont Belmont Bronx music bars", 1),
    ("Bronx", "Riverdale Pelham Bay other Bronx music venues", 2),
    ("Bronx", "Bronx cultural centers and performing arts", 2),
    # ── Staten Island ─────────────────────────────────────────────────────
    ("Staten Island", "St George Stapleton New Brighton music venues", 1),
    ("Staten Island", "other Staten Island music venues and bars", 2),
]

BATCH_PROMPT = """
You are building a dataset of music venues in New York City.

Search for currently operating music venues in: {borough} — {focus}

Return a JSON array. Each item must have these fields:
- "name": venue name (string, required)
- "address": full street address including zip code (string, required)
- "borough": "{borough}" (string)
- "neighborhood": neighborhood name (string)
- "description": their tagline or brief description of music genre/vibe (string)
- "website": homepage URL (string)
- "calendar_url": the specific page on their site listing upcoming shows — e.g. venue.com/events or venue.com/calendar. If they use Eventbrite, Dice, Resident Advisor, or Songkick, use their organizer/venue page on that platform (string, required)
- "instagram": full Instagram URL (string)
- "facebook": full Facebook URL (string)
- "capacity": approximate capacity as integer, 0 if unknown (integer)
- "tier": 1 for DIY/small (under 200), 2 for medium (200-700), 3 for large (700+) (integer)

Rules:
- Only include venues CURRENTLY OPERATING in 2025 (not closed)
- address and calendar_url are required — omit any venue where you cannot confirm both
- Include every venue you can find, not just well-known ones
- For calendar_url: look for /events, /calendar, /shows, /schedule pages. Check Eventbrite, Dice.fm, RA, Songkick for their pages if the venue uses those platforms.
- Use web search to verify venues are still open and to find accurate URLs

Search sources: nyc-noise.com, ohmyrockness.com, residentadvisor.net, donyc.com, timeout.com, songkick.com, Google searches for the specific area.

Return ONLY the JSON array, no other text.
"""


def search_batch(borough: str, focus: str, tier: int) -> list[dict]:
    """Call Claude with web search for one batch."""
    prompt = BATCH_PROMPT.format(borough=borough, focus=focus)
    print(f"  Searching: {borough} — {focus}")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                text += block.text

        if not text.strip():
            print(f"    [no text response]")
            return []

        # Parse JSON from response
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)

        # Find JSON array in text
        start = text.find("[")
        end   = text.rfind("]") + 1
        if start == -1 or end == 0:
            print(f"    [no JSON array found in response]")
            return []

        venues = json.loads(text[start:end])
        if not isinstance(venues, list):
            return []

        # Validate and clean each venue
        clean = []
        for v in venues:
            if not isinstance(v, dict):
                continue
            name    = str(v.get("name", "")).strip()
            address = str(v.get("address", "")).strip()
            cal_url = str(v.get("calendar_url", "")).strip()
            if not name or not address or not cal_url:
                continue
            # Set tier from batch hint if not present
            if not v.get("tier"):
                v["tier"] = tier
            v["name"]         = name
            v["address"]      = address
            v["calendar_url"] = cal_url
            v["borough"]      = v.get("borough", borough)
            v["neighborhood"] = str(v.get("neighborhood", "")).strip()
            v["description"]  = str(v.get("description", "")).strip()
            v["website"]      = str(v.get("website", "")).strip()
            v["instagram"]    = str(v.get("instagram", "")).strip()
            v["facebook"]     = str(v.get("facebook", "")).strip()
            v["capacity"]     = int(v.get("capacity", 0) or 0)
            clean.append(v)

        print(f"    → {len(clean)} venues found")
        return clean

    except json.JSONDecodeError as e:
        print(f"    [JSON parse error: {e}]")
        return []
    except Exception as e:
        print(f"    [error: {e}]")
        return []


def deduplicate(venues: list[dict]) -> list[dict]:
    """Remove duplicates by normalizing names and addresses."""
    seen    = set()
    result  = []
    for v in venues:
        # Normalize key: lowercase name + first part of address
        key = re.sub(r'\s+', ' ', v["name"].lower().strip())
        # Also check address prefix to catch same venue different name spellings
        addr_prefix = re.sub(r'\s+', ' ', v["address"].lower().strip())[:30]
        dedup_key   = f"{key}|{addr_prefix}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            result.append(v)
    return result


def assign_ids(venues: list[dict]) -> list[dict]:
    """
    Assign stable numeric IDs sorted by tier then borough then name.
    """
    borough_order = {
        "Manhattan": 0,
        "Brooklyn": 1,
        "Queens": 2,
        "Bronx": 3,
        "Staten Island": 4,
    }
    venues.sort(key=lambda v: (
        v.get("tier", 2),
        borough_order.get(v.get("borough", ""), 9),
        v.get("name", "").lower()
    ))
    for i, v in enumerate(venues, 1):
        v["id"] = i
    return venues


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable first.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        raise SystemExit(1)

    print(f"Building venues.json — {len(SEARCH_BATCHES)} search batches")
    print("=" * 60)

    all_venues: list[dict] = []
    MAX_VENUES = 1000

    for i, (borough, focus, tier) in enumerate(SEARCH_BATCHES, 1):
        print(f"\n[{i}/{len(SEARCH_BATCHES)}]")
        batch = search_batch(borough, focus, tier)
        all_venues.extend(batch)

        total = len(deduplicate(all_venues))
        print(f"  Running total (deduplicated): {total}")

        if total >= MAX_VENUES:
            print(f"\nReached {MAX_VENUES} venue limit — stopping early.")
            break

        # Be polite between API calls
        if i < len(SEARCH_BATCHES):
            time.sleep(2)

    print("\n" + "=" * 60)
    print("Deduplicating...")
    venues = deduplicate(all_venues)
    print(f"Unique venues: {len(venues)}")

    print("Assigning IDs...")
    venues = assign_ids(venues)

    # Borough summary
    from collections import Counter
    boroughs = Counter(v.get("borough", "Unknown") for v in venues)
    tiers    = Counter(v.get("tier", 0) for v in venues)
    print("\nBy borough:")
    for b, n in sorted(boroughs.items()):
        print(f"  {b}: {n}")
    print("By tier:")
    print(f"  DIY/small (1): {tiers.get(1,0)}")
    print(f"  Medium    (2): {tiers.get(2,0)}")
    print(f"  Large     (3): {tiers.get(3,0)}")

    # Write output
    OUTPUT_FILE.write_text(json.dumps(venues, indent=2, ensure_ascii=False))
    print(f"\nWritten to: {OUTPUT_FILE}")
    print("Done. Commit venues.json to your repository.")


if __name__ == "__main__":
    main()
