const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("alphafood_token");
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("alphafood_token");
      window.location.href = "/admin/login";
      return undefined as T;
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type ScraperType = "wordpress" | "generic_rss" | "html_sitemap" | "single_page";
export type ScrapeStatus = "running" | "success" | "partial" | "error";

export interface Source {
  id: string;
  name: string;
  url: string;
  scraper_type: ScraperType;
  active: boolean;
  frequency_hours: number | null;
  created_at: string;
  last_scraped_at: string | null;
}

export interface RecipeListItem {
  id: string;
  title: string;
  source_url: string;
  image_url: string | null;
  prep_time: number | null;
  cook_time: number | null;
  is_dairy_free: boolean | null;
  needs_review: boolean;
  published: boolean;
  created_at: string;
  source_id: string;
}

export interface IngredientItem {
  quantity: string;
  unit: string;
  item: string;
}

export interface Recipe {
  id: string;
  source_id: string;
  source_url: string;
  title: string;
  ingredients: IngredientItem[] | null;
  instructions: string[] | null;
  prep_time: number | null;
  cook_time: number | null;
  servings: string | null;
  image_url: string | null;
  is_dairy_free: boolean | null;
  mentions_mammal_ingredients: boolean;
  disclaimer: string | null;
  needs_review: boolean;
  published: boolean;
  extracted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecipesPage {
  items: RecipeListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface ScrapeRun {
  id: string;
  source_id: string | null;
  started_at: string;
  finished_at: string | null;
  status: ScrapeStatus | "cancelled";
  recipes_found: number;
  recipes_added: number;
  recipes_updated: number;
  recipes_skipped_non_recipe: number;
  error_message: string | null;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<string> {
  const data = await apiFetch<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return data.access_token;
}

// ── Sources ───────────────────────────────────────────────────────────────────

export async function getSources(): Promise<Source[]> {
  return apiFetch("/api/admin/sources/");
}

export async function createSource(body: Omit<Source, "id" | "created_at" | "last_scraped_at">): Promise<Source> {
  return apiFetch("/api/admin/sources/", { method: "POST", body: JSON.stringify(body) });
}

export async function updateSource(id: string, body: Partial<Source>): Promise<Source> {
  return apiFetch(`/api/admin/sources/${id}`, { method: "PUT", body: JSON.stringify(body) });
}

export async function deleteSource(id: string): Promise<void> {
  return apiFetch(`/api/admin/sources/${id}`, { method: "DELETE" });
}

export async function triggerSourceScrape(id: string): Promise<{ run_id: string; status: string }> {
  return apiFetch(`/api/admin/sources/${id}/scrape`, { method: "POST" });
}

export async function triggerScrapeAll(): Promise<{ run_id: string; status: string }> {
  return apiFetch("/api/admin/scrape/all", { method: "POST" });
}

export async function cancelScrapeRun(runId: string): Promise<ScrapeRun> {
  return apiFetch(`/api/admin/scrape/runs/${runId}/cancel`, { method: "POST" });
}

export async function getScrapeRuns(sourceId?: string): Promise<ScrapeRun[]> {
  const q = sourceId ? `?source_id=${sourceId}` : "";
  return apiFetch(`/api/admin/scrape/runs${q}`);
}

// ── Admin recipes ─────────────────────────────────────────────────────────────

export async function getAdminRecipes(params: {
  needs_review?: boolean;
  published?: boolean;
  page?: number;
  limit?: number;
}): Promise<RecipesPage> {
  const q = new URLSearchParams();
  if (params.needs_review !== undefined) q.set("needs_review", String(params.needs_review));
  if (params.published !== undefined) q.set("published", String(params.published));
  if (params.page) q.set("page", String(params.page));
  if (params.limit) q.set("limit", String(params.limit));
  return apiFetch(`/api/admin/recipes/?${q}`);
}

export async function getAdminRecipe(id: string): Promise<Recipe> {
  return apiFetch(`/api/admin/recipes/${id}`);
}

export async function publishRecipe(id: string): Promise<Recipe> {
  return apiFetch(`/api/admin/recipes/${id}/publish`, { method: "PUT" });
}

export async function rejectRecipe(id: string): Promise<Recipe> {
  return apiFetch(`/api/admin/recipes/${id}/reject`, { method: "PUT" });
}

export async function deleteRecipe(id: string): Promise<void> {
  return apiFetch(`/api/admin/recipes/${id}`, { method: "DELETE" });
}

export async function reprocessRecipe(id: string): Promise<Recipe> {
  return apiFetch(`/api/admin/recipes/${id}/reprocess`, { method: "POST" });
}

// ── Public recipes ────────────────────────────────────────────────────────────

export async function getPublicRecipes(params: {
  q?: string;
  source_id?: string;
  is_dairy_free?: boolean;
  max_time?: number;
  page?: number;
  limit?: number;
}): Promise<RecipesPage> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.source_id) qs.set("source_id", params.source_id);
  if (params.is_dairy_free !== undefined) qs.set("is_dairy_free", String(params.is_dairy_free));
  if (params.max_time) qs.set("max_time", String(params.max_time));
  if (params.page) qs.set("page", String(params.page));
  if (params.limit) qs.set("limit", String(params.limit));
  return apiFetch(`/api/recipes/?${qs}`);
}

export async function getPublicRecipe(id: string): Promise<Recipe> {
  return apiFetch(`/api/recipes/${id}`);
}

// ── Skipped URLs ──────────────────────────────────────────────────────────────

export interface SkippedUrl {
  id: string;
  source_id: string;
  url: string;
  reason: string | null;
  permanent: boolean;
  skipped_at: string;
}

export interface SkippedUrlsPage {
  items: SkippedUrl[];
  total: number;
  page: number;
  limit: number;
}

export async function getSkippedUrls(params: {
  source_id?: string;
  permanent?: boolean;
  page?: number;
  limit?: number;
}): Promise<SkippedUrlsPage> {
  const q = new URLSearchParams();
  if (params.source_id) q.set("source_id", params.source_id);
  if (params.permanent !== undefined) q.set("permanent", String(params.permanent));
  if (params.page) q.set("page", String(params.page));
  if (params.limit) q.set("limit", String(params.limit));
  return apiFetch(`/api/admin/skipped/?${q}`);
}

export async function removeSkippedUrl(id: string): Promise<void> {
  return apiFetch(`/api/admin/skipped/${id}`, { method: "DELETE" });
}

export async function markSkippedUrlPermanent(id: string): Promise<SkippedUrl> {
  return apiFetch(`/api/admin/skipped/${id}/permanent`, { method: "PUT" });
}

export async function unmarkSkippedUrlPermanent(id: string): Promise<SkippedUrl> {
  return apiFetch(`/api/admin/skipped/${id}/permanent`, { method: "DELETE" });
}

// ── Public sources (no auth required) ────────────────────────────────────────

export async function getPublicSources(): Promise<Source[]> {
  return apiFetch("/api/public/sources");
}
