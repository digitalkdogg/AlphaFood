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
  "meal_category": <string or null: best single category for this recipe — one of "breakfast", "lunch", "dinner", "snack", "dessert", "appetizer", "side dish", "soup", "salad", "drink" — or null if it genuinely does not fit any category>,
  "mammal_status": <string: exactly one of "safe", "questionable", or "contains_mammal".
    IMPORTANT: base this ONLY on ingredients that are explicitly written in the recipe text. Do NOT infer or assume ingredients based on the dish name, cuisine, or traditional preparation methods. For example, if a refried bean recipe does not list lard, do not assume lard is present.
    - "contains_mammal": one or more ingredients are explicitly listed and are a mammal-derived product. This includes: beef, pork, veal, bacon, ham, lamb, venison, bison, buffalo, goat meat, rabbit, lard, tallow, suet, rennet, gelatin, worcestershire sauce, AND these specific dairy products — milk, butter, cream, yogurt, ghee, whey, sour cream, half-and-half, buttermilk, kefir, cream cheese, mascarpone, ricotta, creme fraiche. Only mark "contains_mammal" if the ingredient is actually present in the listed ingredients. IMPORTANT: style or flavor adjectives such as "greek", "plain", "vanilla", "low-fat", "non-fat", "full-fat", "whole", "skim", "2%", "unsalted", "salted", "whipped", "organic", "raw" do NOT make a dairy ingredient plant-based. "Greek yogurt" is still yogurt. "Unsalted butter" is still butter. Only qualifiers that explicitly indicate a plant-based source (coconut, oat, almond, soy, rice, cashew, vegan, dairy-free, plant-based) change the classification.
    - "questionable": an ingredient that is explicitly listed but could reasonably be mammal-derived or plant-based depending on brand. This includes: plain "cheese" or "shredded cheese" (easy to substitute with vegan cheese), plain "broth" or "stock" without a qualifier, "shortening", "natural flavors", "lactic acid".
    - "safe": all explicitly listed ingredients are plant-based, poultry, seafood, or any ambiguous ingredients are qualified as plant-based (e.g. "oat milk", "coconut yogurt", "vegan butter", "vegetable broth", "dairy-free cheese").>,
  "questionable_ingredients": [<list the exact ingredient names (as written in the recipe) that caused a "questionable" rating. Empty array if mammal_status is not "questionable".>]
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


async def classify_category(title: str, ingredients: list) -> str | None:
    """Ask Ollama for just the meal category of an existing recipe."""
    ingredient_names = ", ".join(
        str(i.get("item", "")).strip()
        for i in (ingredients or [])
        if isinstance(i, dict) and str(i.get("item", "")).strip()
    ) or "unknown"
    prompt = (
        f'Given this recipe, return a JSON object with a single field "meal_category".\n'
        f'Choose exactly one of: "breakfast", "lunch", "dinner", "snack", "appetizer", '
        f'"side dish", "soup", "salad", "dessert", "drink" — or null if none fit.\n\n'
        f'Title: {title}\n'
        f'Main ingredients: {ingredient_names}\n\n'
        f'Return only: {{"meal_category": "..."}}'
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "system": SYSTEM_PROMPT,
                      "stream": False, "format": "json", "keep_alive": "10m"},
            )
            r.raise_for_status()
            data = json.loads(r.json().get("response", "{}"))
            cat = str(data.get("meal_category") or "").strip().lower()
            valid = {"breakfast","lunch","dinner","snack","appetizer","side dish","soup","salad","dessert","drink"}
            return cat if cat in valid else None
    except Exception as e:
        logger.warning(f"Category classification failed: {e}")
        return None


TIPS_SYSTEM_PROMPT = (
    "You are a helpful assistant for people with Alpha-Gal Syndrome (AGS), "
    "a condition caused by a tick bite that results in an allergy to mammal-derived products. "
    "Return ONLY valid JSON. No explanation, markdown, or text outside the JSON object."
)

TIPS_SCHEMA = """
Given a recipe's ingredients, identify any ingredients that an Alpha-Gal Syndrome patient should be cautious about and suggest a safe, specific alternative for each one.

Alpha-Gal Syndrome patients must avoid: all red meat (beef, pork, lamb, venison, bison, etc.), mammal dairy (milk, butter, cream, yogurt, cheese, ghee, etc.), gelatin, lard, tallow, rennet, worcestershire sauce.
They CAN safely eat: chicken, turkey, fish, seafood, plant-based ingredients, oat/almond/coconut/soy alternatives.

Return a JSON object:
{
  "tips": [
    "Consider replacing <original ingredient> with <specific safe alternative> — <brief reason if helpful>"
  ]
}

Rules:
- Only flag ingredients that are genuinely problematic for AGS. Do not flag safe ingredients.
- Be specific in your suggestions (e.g. "Violife mozzarella" or "oat milk" rather than just "a dairy-free option").
- Keep each tip to one sentence.
- Return an empty array if there are no problematic ingredients.
"""


async def generate_substitution_tips(title: str, ingredients: list) -> list[str]:
    """Return a list of substitution tip strings for AGS-unsafe ingredients, or [] if none."""
    if not ingredients:
        return []
    ingredient_lines = "\n".join(
        "- " + " ".join(filter(None, [
            str(i.get("quantity", "")).strip(),
            str(i.get("unit", "")).strip(),
            str(i.get("item", "")).strip(),
        ]))
        for i in ingredients
        if isinstance(i, dict) and str(i.get("item", "")).strip()
    )
    if not ingredient_lines:
        return []
    prompt = f"{TIPS_SCHEMA}\n\nRecipe: {title}\nIngredients:\n{ingredient_lines}"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "system": TIPS_SYSTEM_PROMPT,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m",
                },
            )
            r.raise_for_status()
            data = json.loads(r.json().get("response", "{}"))
            tips = data.get("tips", [])
            return [str(t).strip() for t in tips if str(t).strip()]
    except Exception as e:
        logger.warning(f"Substitution tip generation failed for '{title}': {e}")
        return []


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
