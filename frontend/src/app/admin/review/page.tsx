"use client";

import { useEffect, useState } from "react";
import {
  getAdminRecipes,
  getAdminRecipe,
  publishRecipe,
  rejectRecipe,
  deleteRecipe,
  RecipeListItem,
  Recipe,
} from "@/lib/api";
import Image from "next/image";

function RecipePreview({ id }: { id: string }) {
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAdminRecipe(id).then(setRecipe).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-xs text-gray-400 py-2">Loading preview…</div>;
  if (!recipe) return <div className="text-xs text-red-400 py-2">Failed to load details.</div>;

  const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];
  const instructions = Array.isArray(recipe.instructions) ? recipe.instructions : [];

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
      {recipe.mentions_mammal_ingredients && (
        <div className="col-span-2 bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2 rounded-lg font-medium">
          ⚠ Mammal ingredients detected — review carefully before publishing
        </div>
      )}

      <div>
        <h4 className="font-semibold text-xs text-gray-500 uppercase tracking-wide mb-2">
          Ingredients ({ingredients.length})
        </h4>
        {ingredients.length === 0 ? (
          <p className="text-xs text-gray-400 italic">None extracted</p>
        ) : (
          <ul className="space-y-1">
            {ingredients.map((ing, i) => {
              const parts = [ing.quantity, ing.unit, ing.item].filter(Boolean).join(" ");
              return (
                <li key={i} className="text-xs text-gray-700 flex gap-1">
                  <span className="text-gray-300 select-none">•</span>
                  <span>{parts || JSON.stringify(ing)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div>
        <h4 className="font-semibold text-xs text-gray-500 uppercase tracking-wide mb-2">
          Instructions ({instructions.length} steps)
        </h4>
        {instructions.length === 0 ? (
          <p className="text-xs text-gray-400 italic">None extracted</p>
        ) : (
          <ol className="space-y-1.5 list-none">
            {instructions.map((step, i) => (
              <li key={i} className="text-xs text-gray-700 flex gap-2">
                <span className="font-semibold text-gray-400 shrink-0 w-4">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        )}
      </div>

      {(recipe.servings || recipe.prep_time != null || recipe.cook_time != null) && (
        <div className="col-span-2 flex gap-4 text-xs text-gray-500">
          {recipe.servings && <span>Serves: {recipe.servings}</span>}
          {recipe.prep_time != null && <span>Prep: {recipe.prep_time} min</span>}
          {recipe.cook_time != null && <span>Cook: {recipe.cook_time} min</span>}
        </div>
      )}
    </div>
  );
}

export default function ReviewQueuePage() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const limit = 20;

  async function load() {
    setLoading(true);
    try {
      const data = await getAdminRecipes({ needs_review: true, page, limit });
      setRecipes(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [page]);

  function notify(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handlePublish(id: string) {
    try {
      await publishRecipe(id);
      notify("Recipe published ✓");
      setExpanded((prev) => { const next = new Set(prev); next.delete(id); return next; });
      load();
    } catch {
      notify("Failed to publish");
    }
  }

  async function handleReject(id: string) {
    try {
      await rejectRecipe(id);
      notify("Recipe kept in review queue");
      load();
    } catch {
      notify("Failed to reject");
    }
  }

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Delete "${title}" permanently?`)) return;
    try {
      await deleteRecipe(id);
      notify("Recipe deleted");
      setExpanded((prev) => { const next = new Set(prev); next.delete(id); return next; });
      load();
    } catch {
      notify("Failed to delete");
    }
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Review Queue <span className="text-gray-400 font-normal text-base">({total} pending)</span></h2>
        <button onClick={load} className="text-sm text-brand-600 hover:text-brand-800">Refresh</button>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        Review each recipe carefully — especially the ingredients list. Publish only recipes that are genuinely mammal-free and correctly extracted. Pay special attention to any that flagged mammal ingredients.
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">{toast}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : recipes.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <div className="text-4xl mb-3">✅</div>
          <p>Review queue is empty!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {recipes.map((recipe) => {
            const isExpanded = expanded.has(recipe.id);
            return (
              <div key={recipe.id} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="flex gap-0">
                  {recipe.image_url && (
                    <div className="relative w-24 sm:w-32 shrink-0">
                      <Image src={recipe.image_url} alt={recipe.title} fill className="object-cover" unoptimized />
                    </div>
                  )}
                  <div className="flex-1 p-3 sm:p-4 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4">
                      <div className="min-w-0">
                        <h3 className="font-semibold text-sm sm:text-base leading-snug">{recipe.title}</h3>
                        <a href={recipe.source_url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-brand-600 hover:underline truncate block max-w-xs mt-0.5">
                          {recipe.source_url}
                        </a>
                        <div className="flex flex-wrap gap-2 mt-1.5">
                          {recipe.is_dairy_free === true && (
                            <span className="bg-brand-100 text-brand-800 text-xs px-2 py-0.5 rounded-full">Dairy-Free</span>
                          )}
                          {recipe.is_dairy_free === false && (
                            <span className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded-full">Contains Dairy</span>
                          )}
                          {recipe.prep_time != null && (
                            <span className="text-xs text-gray-400">{recipe.prep_time + (recipe.cook_time ?? 0)} min</span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 shrink-0">
                        <button
                          onClick={() => toggleExpand(recipe.id)}
                          className="bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                        >
                          {isExpanded ? "Hide" : "Preview"}
                        </button>
                        <button onClick={() => handlePublish(recipe.id)}
                          className="bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                          Publish
                        </button>
                        <button onClick={() => handleDelete(recipe.id, recipe.title)}
                          className="bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                          Delete
                        </button>
                      </div>
                    </div>

                    {isExpanded && <RecipePreview id={recipe.id} />}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50">Previous</button>
          <span className="px-4 py-2 text-sm text-gray-600">{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50">Next</button>
        </div>
      )}
    </div>
  );
}
