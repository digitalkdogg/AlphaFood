import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a recipe data extractor. "
    "Return ONLY valid JSON matching the exact schema provided. "
    "Do not include any explanation, markdown, or text outside the JSON object."
)

SCHEMA_DESCRIPTION = """
Return a JSON object with exactly these fields:
{
  "is_recipe": <boolean: true if the page contains an actual recipe with ingredients and numbered instructions>,
  "title": <string: recipe title or page title if not a recipe>,
  "ingredients": [{"quantity": <string>, "unit": <string>, "item": <string>}],
  "instructions": [<string: each step as a complete sentence>],
  "prep_time": <integer minutes or null>,
  "cook_time": <integer minutes or null>,
  "servings": <string or null>,
  "is_dairy_free": <boolean or null (null if cannot determine)>,
  "mammal_status": <string: exactly one of "safe", "questionable", or "contains_mammal".
    - "contains_mammal": one or more ingredients are CLEARLY and DEFINITIVELY a mammal product with no plant-based ambiguity — beef, pork, veal, bacon, ham, lamb, venison, bison, buffalo, goat meat, rabbit, lard, tallow, suet, bone broth (unless specified vegetable), gelatin (unless specified plant-based), rennet.
    - "questionable": one or more ingredients COULD be mammal-derived OR plant-based depending on the brand used — butter (could be vegan butter), milk (could be oat/almond/soy milk), cream (could be coconut cream), cheese (could be vegan cheese), yogurt (could be coconut yogurt), broth or stock (could be vegetable), ghee (could be vegan ghee).
    - "safe": no mammal-derived ingredients detected, or all ambiguous ingredients are explicitly specified as plant-based (e.g. "oat milk", "vegan butter", "vegetable broth").>
}

If is_recipe is false, still populate "title" with whatever the page is actually about.
"""


async def warmup() -> None:
    """Load the model into RAM before scraping starts so the first real request doesn't cold-load."""
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            await client.post(
                f"{settings.ollama_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": "hi", "stream": False, "keep_alive": "10m"},
            )
        logger.info("Ollama model warmed up")
    except Exception as e:
        logger.warning(f"Ollama warmup failed (will proceed anyway): {e}")


async def extract_recipe(text: str) -> tuple[dict | None, str]:
    """Return (recipe_data, skip_reason). recipe_data is None when skipped."""
    truncated = text[:6000]
    prompt = f"{SCHEMA_DESCRIPTION}\n\nPage content:\n{truncated}"
    return await _call_ollama(prompt)


async def _call_ollama(prompt: str, retry: bool = True) -> tuple[dict | None, str]:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
            r.raise_for_status()
            raw = r.json().get("response", "")
        data = json.loads(raw)
        if not data.get("is_recipe", False):
            title = (data.get("title") or "").strip()
            reason = f"Not a recipe: {title}" if title else "Not a recipe"
            return None, reason
        return data, ""
    except json.JSONDecodeError:
        if retry:
            logger.warning("Ollama returned invalid JSON, retrying with stricter prompt")
            return await _call_ollama(
                "Return ONLY the JSON object, nothing else.\n\n" + prompt,
                retry=False,
            )
        logger.error("Ollama extraction failed after retry")
        return None, "Ollama returned invalid JSON"
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None, "Ollama call failed"
