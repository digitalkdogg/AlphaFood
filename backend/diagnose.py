#!/usr/bin/env python3
"""
Diagnostic script for troubleshooting Ollama extraction failures.

Usage (local):
    python3 diagnose.py https://example.com/some-recipe

Usage (inside Docker on NAS):
    docker exec -it alphafood-backend-1 python3 /app/diagnose.py https://example.com/some-recipe
"""

import asyncio
import json
import os
import sys
import time

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

SYSTEM_PROMPT = (
    "You are a recipe data extractor. "
    "Return ONLY valid JSON matching the exact schema provided. "
    "Do not include any explanation, markdown, or text outside the JSON object."
)

SCHEMA_DESCRIPTION = """
Return a JSON object with exactly these fields:
{
  "is_recipe": <boolean>,
  "title": <string: recipe title or page title if not a recipe>,
  "ingredients": [{"quantity": <string>, "unit": <string>, "item": <string>}],
  "instructions": [<string>],
  "prep_time": <integer minutes or null>,
  "cook_time": <integer minutes or null>,
  "servings": <string or null>,
  "is_dairy_free": <boolean or null>,
  "mentions_mammal_ingredients": <boolean>
}
If is_recipe is false, still populate "title" with what the page is about.
"""

SEP = "─" * 70


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


async def run(url: str):
    print(f"\n{'═' * 70}")
    print(f"  AlphaFood Diagnostic")
    print(f"  URL:   {url}")
    print(f"  Model: {OLLAMA_MODEL}  |  Ollama: {OLLAMA_URL}")
    print(f"{'═' * 70}")

    # ── Step 1: Fetch HTML ────────────────────────────────────────────────────
    section("STEP 1 — Fetch HTML")
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        fetch_ms = int((time.time() - t0) * 1000)
        html = resp.text
        print(f"  Status : {resp.status_code}")
        print(f"  Size   : {len(html):,} bytes")
        print(f"  Time   : {fetch_ms}ms")
        if resp.status_code >= 400:
            print(f"\n  ✗ HTTP error — cannot proceed")
            return
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return

    # ── Step 2: Clean text ────────────────────────────────────────────────────
    section("STEP 2 — Extract clean text (trafilatura)")
    try:
        import trafilatura
        t0 = time.time()
        cleaned = trafilatura.extract(html)
        clean_ms = int((time.time() - t0) * 1000)
        if cleaned:
            print(f"  Length : {len(cleaned):,} chars")
            print(f"  Time   : {clean_ms}ms")
            print(f"\n  Preview (first 500 chars):")
            print(f"  {cleaned[:500].replace(chr(10), ' ')!r}")
        else:
            print(f"  ✗ trafilatura returned empty — page has no extractable text")
            print(f"     This URL would be saved as: 'No extractable text'")
            return
    except ImportError:
        print("  ✗ trafilatura not installed — skipping clean step, using raw HTML")
        cleaned = html[:6000]

    # ── Step 3: Check Ollama reachability ────────────────────────────────────
    section("STEP 3 — Ollama connectivity check")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{OLLAMA_URL}/api/version")
        print(f"  ✓ Ollama reachable — version: {r.json().get('version', '?')}")
    except Exception as e:
        print(f"  ✗ Cannot reach Ollama at {OLLAMA_URL}: {e}")
        print(f"     All extractions will fail with 'Ollama call failed'")
        return

    # ── Step 4: Check model is available ─────────────────────────────────────
    section("STEP 4 — Model availability")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        if any(OLLAMA_MODEL in m for m in models):
            print(f"  ✓ Model '{OLLAMA_MODEL}' found")
        else:
            print(f"  ✗ Model '{OLLAMA_MODEL}' NOT found")
            print(f"     Available models: {models or 'none'}")
            print(f"     Run: ollama pull {OLLAMA_MODEL}")
            return
    except Exception as e:
        print(f"  ✗ Could not list models: {e}")

    # ── Step 5: Send to Ollama ────────────────────────────────────────────────
    section("STEP 5 — Ollama extraction")
    truncated = cleaned[:6000]
    prompt = f"{SCHEMA_DESCRIPTION}\n\nPage content:\n{truncated}"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
    }
    print(f"  Prompt length : {len(prompt):,} chars")
    print(f"  Sending request (timeout=300s)...")

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        ollama_ms = int((time.time() - t0) * 1000)
        print(f"  HTTP status   : {r.status_code}")
        print(f"  Time          : {ollama_ms}ms ({ollama_ms/1000:.1f}s)")

        if r.status_code != 200:
            print(f"\n  ✗ Ollama returned non-200")
            print(f"  Response body: {r.text[:500]}")
            return

        body = r.json()
        raw_response = body.get("response", "")
        print(f"  Response chars: {len(raw_response):,}")

        eval_count = body.get("eval_count")
        eval_duration = body.get("eval_duration")
        load_duration = body.get("load_duration")
        if load_duration:
            print(f"  Model load    : {load_duration / 1e9:.2f}s")
        if eval_count and eval_duration:
            tps = eval_count / (eval_duration / 1e9)
            print(f"  Tokens        : {eval_count} @ {tps:.1f} tok/s")

    except httpx.TimeoutException as e:
        ollama_ms = int((time.time() - t0) * 1000)
        print(f"\n  ✗ TIMEOUT after {ollama_ms}ms ({ollama_ms/1000:.1f}s)")
        print(f"     The model took too long to respond.")
        print(f"     Model load alone may exceed the timeout on this hardware.")
        return
    except Exception as e:
        ollama_ms = int((time.time() - t0) * 1000)
        print(f"\n  ✗ FAILED after {ollama_ms}ms: {type(e).__name__}: {e}")
        return

    # ── Step 6: Parse JSON ────────────────────────────────────────────────────
    section("STEP 6 — Parse Ollama response")
    print(f"\n  Raw response:\n  {raw_response[:1000]}")
    try:
        data = json.loads(raw_response)
        print(f"\n  ✓ Valid JSON")
        print(f"\n  Parsed result:")
        print(f"    is_recipe              : {data.get('is_recipe')}")
        print(f"    title                  : {data.get('title')!r}")
        print(f"    ingredients count      : {len(data.get('ingredients') or [])}")
        print(f"    instructions count     : {len(data.get('instructions') or [])}")
        print(f"    prep_time              : {data.get('prep_time')}")
        print(f"    cook_time              : {data.get('cook_time')}")
        print(f"    is_dairy_free          : {data.get('is_dairy_free')}")
        print(f"    mentions_mammal        : {data.get('mentions_mammal_ingredients')}")

        if data.get("is_recipe"):
            print(f"\n  ✓ RESULT: Would be SAVED as a recipe")
        else:
            title = (data.get("title") or "").strip()
            reason = f"Not a recipe: {title}" if title else "Not a recipe"
            print(f"\n  ✗ RESULT: Would be SKIPPED — reason: '{reason}'")
    except json.JSONDecodeError as e:
        print(f"\n  ✗ JSON parse failed: {e}")
        print(f"     Would be saved as: 'Ollama returned invalid JSON'")

    print(f"\n{'═' * 70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 diagnose.py <url>")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))
