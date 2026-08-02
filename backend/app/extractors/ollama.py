import json
import logging
from typing import Optional

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
  "title": <string: recipe title>,
  "ingredients": [{"quantity": <string>, "unit": <string>, "item": <string>}],
  "instructions": [<string: each step as a complete sentence>],
  "prep_time": <integer minutes or null>,
  "cook_time": <integer minutes or null>,
  "servings": <string or null>,
  "is_dairy_free": <boolean or null (null if cannot determine)>,
  "mentions_mammal_ingredients": <boolean: true if any ingredient mentions beef, pork, lamb, venison, bison, buffalo, rabbit, dairy (milk, cheese, butter, cream, yogurt, whey), gelatin, lard, rennet, tallow, or other mammal-derived ingredients>
}

If is_recipe is false, all other fields may be empty/null.
"""


async def extract_recipe(text: str) -> Optional[dict]:
    truncated = text[:6000]
    prompt = f"{SCHEMA_DESCRIPTION}\n\nPage content:\n{truncated}"
    return await _call_ollama(prompt)


async def _call_ollama(prompt: str, retry: bool = True) -> Optional[dict]:
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
            return None
        return data
    except json.JSONDecodeError:
        if retry:
            logger.warning("Ollama returned invalid JSON, retrying with stricter prompt")
            return await _call_ollama(
                "Return ONLY the JSON object, nothing else.\n\n" + prompt,
                retry=False,
            )
        logger.error("Ollama extraction failed after retry")
        return None
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None
