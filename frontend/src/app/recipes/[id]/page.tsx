import type { Recipe } from "@/lib/api";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";

async function fetchRecipe(id: string): Promise<Recipe> {
  // Use internal URL for server-side fetches (works in Docker); fallback to public URL
  const base =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
  const res = await fetch(`${base}/api/recipes/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("not found");
  return res.json();
}

export default async function RecipeDetailPage({
  params,
}: {
  params: { id: string };
}) {
  let recipe: Recipe;
  try {
    recipe = await fetchRecipe(params.id);
  } catch {
    notFound();
  }

  const totalTime = (recipe.prep_time ?? 0) + (recipe.cook_time ?? 0);

  return (
    <div className="min-h-screen">
      <header className="bg-brand-700 text-white">
        <div className="max-w-4xl mx-auto px-4 py-6 flex items-center gap-4">
          <Link href="/" className="text-brand-200 hover:text-white text-sm">← All Recipes</Link>
          <h1 className="text-xl font-bold">🌿 AlphaFood</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Disclaimer */}
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          <strong>Verify before cooking:</strong> This recipe was extracted automatically. Always check all ingredients — especially hidden mammal derivatives (gelatin, lard, rennet, dairy) — against the <a href={recipe.source_url} target="_blank" rel="noopener noreferrer" className="underline">original source</a> and your own tolerance.
        </div>

        {/* Hero image */}
        {recipe.image_url && (
          <div className="relative h-72 rounded-xl overflow-hidden mb-6">
            <Image src={recipe.image_url} alt={recipe.title} fill className="object-cover" unoptimized />
          </div>
        )}

        <h1 className="text-3xl font-bold mb-4">{recipe.title}</h1>

        {/* Meta row */}
        <div className="flex flex-wrap gap-3 mb-6 text-sm">
          {recipe.is_dairy_free && (
            <span className="bg-brand-100 text-brand-800 px-3 py-1 rounded-full font-medium">✓ Dairy-Free</span>
          )}
          {recipe.prep_time && (
            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full">Prep: {recipe.prep_time} min</span>
          )}
          {recipe.cook_time && (
            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full">Cook: {recipe.cook_time} min</span>
          )}
          {totalTime > 0 && (
            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full font-medium">Total: {totalTime} min</span>
          )}
          {recipe.servings && (
            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full">Serves: {recipe.servings}</span>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Ingredients */}
          <div className="lg:col-span-1">
            <h2 className="text-xl font-semibold mb-3 text-brand-800">Ingredients</h2>
            {recipe.ingredients && recipe.ingredients.length > 0 ? (
              <ul className="space-y-2">
                {recipe.ingredients.map((ing, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-2 shrink-0" />
                    <span>
                      {[ing.quantity, ing.unit, ing.item].filter(Boolean).join(" ")}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 text-sm">Ingredients not available.</p>
            )}
          </div>

          {/* Instructions */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-semibold mb-3 text-brand-800">Instructions</h2>
            {recipe.instructions && recipe.instructions.length > 0 ? (
              <ol className="space-y-4">
                {recipe.instructions.map((step, i) => (
                  <li key={i} className="flex gap-4">
                    <span className="flex-shrink-0 w-7 h-7 rounded-full bg-brand-600 text-white text-sm font-bold flex items-center justify-center mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-sm leading-relaxed pt-1">{step}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-gray-400 text-sm">Instructions not available.</p>
            )}
          </div>
        </div>

        {/* Source attribution */}
        <div className="mt-10 pt-6 border-t border-gray-100 text-sm text-gray-500">
          <p>
            Recipe sourced from{" "}
            <a href={recipe.source_url} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline hover:text-brand-900">
              {recipe.source_url}
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
