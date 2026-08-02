"use client";

import { useEffect, useState, useCallback } from "react";
import { getPublicRecipes, RecipeListItem, getPublicSources, Source } from "@/lib/api";
import Link from "next/link";
import Image from "next/image";

function RecipeCard({ recipe }: { recipe: RecipeListItem }) {
  const totalTime =
    (recipe.prep_time ?? 0) + (recipe.cook_time ?? 0);

  return (
    <Link href={`/recipes/${recipe.id}`} className="group block bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="relative h-48 bg-brand-50">
        {recipe.image_url ? (
          <Image
            src={recipe.image_url}
            alt={recipe.title}
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="flex items-center justify-center h-full text-5xl">🍽️</div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 group-hover:text-brand-700 line-clamp-2 mb-2">
          {recipe.title}
        </h3>
        <div className="flex flex-wrap gap-2 text-xs">
          {recipe.is_dairy_free && (
            <span className="bg-brand-100 text-brand-800 px-2 py-0.5 rounded-full">Dairy-Free</span>
          )}
          {totalTime > 0 && (
            <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              {totalTime} min
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function HomePage() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [dairyFree, setDairyFree] = useState<boolean | undefined>();
  const [maxTime, setMaxTime] = useState<number | undefined>();
  const [sourceId, setSourceId] = useState<string>("");

  const limit = 24;

  const fetchRecipes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPublicRecipes({
        q: query || undefined,
        source_id: sourceId || undefined,
        is_dairy_free: dairyFree,
        max_time: maxTime,
        page,
        limit,
      });
      setRecipes(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [query, sourceId, dairyFree, maxTime, page]);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  useEffect(() => {
    getPublicSources().catch(() => []).then(setSources);
  }, []);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-brand-700 text-white">
        <div className="max-w-6xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">🌿 AlphaFood</h1>
            <p className="text-brand-100 text-sm mt-0.5">Alpha-Gal Friendly Recipes</p>
          </div>
          <Link href="/admin" className="text-sm text-brand-200 hover:text-white transition-colors">
            Admin →
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Disclaimer */}
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          <strong>Important:</strong> Recipes are extracted automatically. Always verify ingredients — especially hidden mammal derivatives like gelatin, lard, rennet, and dairy — against the original source and your own tolerance.
        </div>

        {/* Filters */}
        <div className="mb-6 bg-white rounded-xl border border-gray-100 shadow-sm p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            type="search"
            placeholder="Search recipes…"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1); }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 col-span-full lg:col-span-1"
          />
          <select
            value={sourceId}
            onChange={(e) => { setSourceId(e.target.value); setPage(1); }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All Sources</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <select
            value={dairyFree === undefined ? "" : String(dairyFree)}
            onChange={(e) => {
              setDairyFree(e.target.value === "" ? undefined : e.target.value === "true");
              setPage(1);
            }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Any Dairy Status</option>
            <option value="true">Dairy-Free</option>
            <option value="false">Contains Dairy</option>
          </select>
          <select
            value={maxTime ?? ""}
            onChange={(e) => {
              setMaxTime(e.target.value ? Number(e.target.value) : undefined);
              setPage(1);
            }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Any Time</option>
            <option value="30">Under 30 min</option>
            <option value="60">Under 60 min</option>
            <option value="120">Under 2 hours</option>
          </select>
        </div>

        {/* Results count */}
        {!loading && (
          <p className="text-sm text-gray-500 mb-4">
            {total} recipe{total !== 1 ? "s" : ""} found
          </p>
        )}

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 overflow-hidden animate-pulse">
                <div className="h-48 bg-gray-100" />
                <div className="p-4 space-y-2">
                  <div className="h-4 bg-gray-100 rounded w-3/4" />
                  <div className="h-3 bg-gray-100 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : recipes.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <div className="text-5xl mb-4">🍃</div>
            <p>No recipes found. Try adjusting your filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {recipes.map((r) => <RecipeCard key={r.id} recipe={r} />)}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-8 flex justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-sm text-gray-600">
              {page} / {totalPages}
            </span>
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
    </div>
  );
}
