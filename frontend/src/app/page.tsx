"use client";

import { useEffect, useState, useCallback } from "react";
import { getPublicRecipes, getPublicRecipe, Recipe, RecipeListItem, getPublicSources, Source } from "@/lib/api";
import { useFavorites, getFavoriteIds } from "@/lib/favorites";
import Link from "next/link";
import Image from "next/image";

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
  { value: "snack", label: "Snack" },
  { value: "appetizer", label: "Appetizer" },
  { value: "side dish", label: "Side Dish" },
  { value: "soup", label: "Soup" },
  { value: "salad", label: "Salad" },
  { value: "dessert", label: "Dessert" },
  { value: "drink", label: "Drink" },
];

function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor" strokeWidth={2}
      className="w-4 h-4"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
    </svg>
  );
}

function RecipeCard({ recipe, onToggleFavorite, isFavorite }: {
  recipe: RecipeListItem;
  onToggleFavorite: (id: string) => void;
  isFavorite: boolean;
}) {
  const totalTime = (recipe.prep_time ?? 0) + (recipe.cook_time ?? 0);

  return (
    <div className="group relative bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <Link href={`/recipes/${recipe.id}`} className="block">
        <div className="relative h-48 bg-brand-50">
          {recipe.image_url ? (
            <Image src={recipe.image_url} alt={recipe.title} fill className="object-cover" unoptimized />
          ) : (
            <div className="flex items-center justify-center h-full text-5xl">🍽️</div>
          )}
          {recipe.meal_category && (
            <span className="absolute top-2 left-2 bg-white/90 text-gray-700 text-xs font-medium px-2 py-0.5 rounded-full capitalize shadow-sm">
              {recipe.meal_category}
            </span>
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
              <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{totalTime} min</span>
            )}
          </div>
        </div>
      </Link>
      {/* Favorite button — sits on top of the Link */}
      <button
        onClick={(e) => { e.preventDefault(); onToggleFavorite(recipe.id); }}
        title={isFavorite ? "Remove from favorites" : "Save to favorites"}
        className={`absolute top-2 right-2 p-1.5 rounded-full shadow transition-colors ${
          isFavorite
            ? "bg-red-500 text-white hover:bg-red-600"
            : "bg-white/90 text-gray-400 hover:text-red-500"
        }`}
      >
        <HeartIcon filled={isFavorite} />
      </button>
    </div>
  );
}

export default function HomePage() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [favoritesMode, setFavoritesMode] = useState(false);
  const [dairyFree, setDairyFree] = useState<boolean | undefined>();
  const [maxTime, setMaxTime] = useState<number | undefined>();
  const [sourceId, setSourceId] = useState<string>("");

  const { isFavorite, toggle } = useFavorites();

  const limit = 24;

  const fetchRecipes = useCallback(async () => {
    setLoading(true);
    try {
      if (favoritesMode) {
        const ids = getFavoriteIds();
        if (ids.length === 0) {
          setRecipes([]);
          setTotal(0);
        } else {
          const results = await Promise.all(ids.map((id) => getPublicRecipe(id).catch((): Recipe | null => null)));
          const valid = results.filter((r): r is Recipe => r !== null) as RecipeListItem[];
          setRecipes(valid);
          setTotal(valid.length);
        }
      } else {
        const data = await getPublicRecipes({
          q: query || undefined,
          source_id: sourceId || undefined,
          is_dairy_free: dairyFree,
          max_time: maxTime,
          meal_category: category || undefined,
          page,
          limit,
        });
        setRecipes(data.items);
        setTotal(data.total);
      }
    } finally {
      setLoading(false);
    }
  }, [query, sourceId, dairyFree, maxTime, category, page, favoritesMode]);

  useEffect(() => { fetchRecipes(); }, [fetchRecipes]);
  useEffect(() => { getPublicSources().catch(() => []).then(setSources); }, []);

  const totalPages = Math.ceil(total / limit);

  function setFilter<T>(setter: (v: T) => void, value: T) {
    setter(value);
    setPage(1);
  }

  function selectCategory(value: string) {
    setFavoritesMode(false);
    setFilter(setCategory, value);
  }

  function selectFavorites() {
    setCategory("");
    setPage(1);
    setFavoritesMode(true);
  }

  return (
    <div className="min-h-screen">
      <header className="bg-brand-700 text-white">
        <div className="max-w-6xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">🌿 AlphaFood</h1>
            <p className="text-brand-100 text-sm mt-0.5">Alpha-Gal Friendly Recipes</p>
          </div>
          <Link href="/admin" className="text-sm text-brand-200 hover:text-white transition-colors">Admin →</Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          <strong>Important:</strong> Recipes are extracted automatically. Always verify ingredients — especially hidden mammal derivatives like gelatin, lard, rennet, and dairy — against the original source and your own tolerance.
        </div>

        {/* Category pills + Favorites */}
        <div className="mb-4 flex flex-wrap gap-2">
          {CATEGORIES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => selectCategory(value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                !favoritesMode && category === value
                  ? "bg-brand-600 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:border-brand-400 hover:text-brand-700"
              }`}
            >
              {label}
            </button>
          ))}
          <button
            onClick={selectFavorites}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors flex items-center gap-1.5 ${
              favoritesMode
                ? "bg-red-500 text-white"
                : "bg-white border border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-600"
            }`}
          >
            <HeartIcon filled={favoritesMode} />
            Favorites
          </button>
        </div>

        {/* Secondary filters — hidden in favorites mode */}
        {!favoritesMode && (
          <div className="mb-6 bg-white rounded-xl border border-gray-100 shadow-sm p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <input
              type="search"
              placeholder="Search recipes…"
              value={query}
              onChange={(e) => setFilter(setQuery, e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 col-span-full lg:col-span-1"
            />
            <select
              value={sourceId}
              onChange={(e) => setFilter(setSourceId, e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">All Sources</option>
              {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select
              value={dairyFree === undefined ? "" : String(dairyFree)}
              onChange={(e) => setFilter(setDairyFree, e.target.value === "" ? undefined : e.target.value === "true")}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Any Dairy Status</option>
              <option value="true">Dairy-Free</option>
              <option value="false">Contains Dairy</option>
            </select>
            <select
              value={maxTime ?? ""}
              onChange={(e) => setFilter(setMaxTime, e.target.value ? Number(e.target.value) : undefined)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Any Time</option>
              <option value="30">Under 30 min</option>
              <option value="60">Under 60 min</option>
              <option value="120">Under 2 hours</option>
            </select>
          </div>
        )}

        {!loading && (
          <p className="text-sm text-gray-500 mb-4">
            {favoritesMode ? `${total} saved recipe${total !== 1 ? "s" : ""}` : `${total} recipe${total !== 1 ? "s" : ""} found`}
          </p>
        )}

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
            <div className="text-5xl mb-4">{favoritesMode ? "💔" : "🍃"}</div>
            <p>{favoritesMode ? "No saved recipes yet. Hit the heart on any recipe to save it." : "No recipes found. Try adjusting your filters."}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {recipes.map((r) => (
              <RecipeCard
                key={r.id}
                recipe={r}
                isFavorite={isFavorite(r.id)}
                onToggleFavorite={toggle}
              />
            ))}
          </div>
        )}

        {!favoritesMode && totalPages > 1 && (
          <div className="mt-8 flex justify-center gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50">Previous</button>
            <span className="px-4 py-2 text-sm text-gray-600">{page} / {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-4 py-2 rounded-lg border border-gray-200 text-sm disabled:opacity-40 hover:bg-gray-50">Next</button>
          </div>
        )}
      </div>
    </div>
  );
}
