"use client";

import { useEffect, useState } from "react";
import { getAdminRecipes, deleteRecipe, reprocessRecipe, RecipeListItem } from "@/lib/api";
import Image from "next/image";

export default function PublishedRecipesPage() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");
  const [reprocessing, setReprocessing] = useState<Set<string>>(new Set());
  const limit = 24;

  async function load() {
    setLoading(true);
    try {
      const data = await getAdminRecipes({ published: true, page, limit });
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

  async function handleDelete(id: string, title: string) {
    if (!confirm(`Delete "${title}" permanently?`)) return;
    try {
      await deleteRecipe(id);
      notify("Recipe deleted");
      load();
    } catch {
      notify("Failed to delete");
    }
  }

  async function handleReprocess(id: string, title: string) {
    if (!confirm(`Reprocess "${title}"? It will be unpublished and sent back to the review queue while Ollama re-extracts it.`)) return;
    setReprocessing((prev) => new Set(prev).add(id));
    try {
      await reprocessRecipe(id);
      notify("Reprocess started — recipe moved to review queue");
      load();
    } catch {
      notify("Failed to start reprocess");
    } finally {
      setReprocessing((prev) => { const next = new Set(prev); next.delete(id); return next; });
    }
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">
          Published Recipes <span className="text-gray-400 font-normal text-base">({total})</span>
        </h2>
        <button onClick={load} className="text-sm text-brand-600 hover:text-brand-800">Refresh</button>
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">{toast}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : recipes.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No published recipes yet.</div>
      ) : (
        <div className="space-y-3">
          {recipes.map((recipe) => (
            <div key={recipe.id} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden flex gap-0">
              {recipe.image_url && (
                <div className="relative w-28 shrink-0">
                  <Image src={recipe.image_url} alt={recipe.title} fill className="object-cover" unoptimized />
                </div>
              )}
              <div className="flex-1 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="font-semibold truncate">{recipe.title}</h3>
                    <a
                      href={recipe.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand-600 hover:underline truncate block max-w-sm mt-0.5"
                    >
                      {recipe.source_url}
                    </a>
                    <div className="flex gap-2 mt-2">
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
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => handleReprocess(recipe.id, recipe.title)}
                      disabled={reprocessing.has(recipe.id)}
                      className="bg-amber-50 hover:bg-amber-100 text-amber-700 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {reprocessing.has(recipe.id) ? "Starting…" : "Reprocess"}
                    </button>
                    <button
                      onClick={() => handleDelete(recipe.id, recipe.title)}
                      className="bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">{page} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
