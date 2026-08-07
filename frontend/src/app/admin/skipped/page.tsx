"use client";

import { useEffect, useState } from "react";
import { getSkippedUrls, removeSkippedUrl, markSkippedUrlPermanent, getSources, SkippedUrl, Source } from "@/lib/api";

const PAGE_SIZE = 50;

function parseReason(reason: string | null): { label: string; detail: string | null; color: string } {
  if (!reason) return { label: "Unknown", detail: null, color: "bg-gray-100 text-gray-600" };
  if (reason.startsWith("Contains mammal ingredients"))
    return { label: "Mammal ingredients", detail: null, color: "bg-red-50 text-red-700" };
  if (reason.startsWith("Not a recipe: "))
    return { label: "Not a recipe", detail: reason.slice("Not a recipe: ".length) || null, color: "bg-yellow-50 text-yellow-700" };
  if (reason === "Not a recipe")
    return { label: "Not a recipe", detail: null, color: "bg-yellow-50 text-yellow-700" };
  if (reason.startsWith("Ollama") || reason.includes("invalid JSON") || reason.includes("call failed"))
    return { label: "Extraction error", detail: reason, color: "bg-orange-50 text-orange-700" };
  if (reason === "No extractable text")
    return { label: "No text extracted", detail: null, color: "bg-gray-100 text-gray-500" };
  return { label: reason, detail: null, color: "bg-gray-100 text-gray-600" };
}

function formatUrl(url: string): { host: string; path: string } {
  try {
    const u = new URL(url);
    const path = u.pathname.replace(/\/$/, "");
    const short = path.length > 60 ? path.slice(0, 57) + "…" : path;
    return { host: u.hostname, path: short || "/" };
  } catch {
    return { host: url.slice(0, 40), path: "" };
  }
}

export default function SkippedUrlsPage() {
  const [items, setItems] = useState<SkippedUrl[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<Record<string, "requeue" | "permanent">>({});
  const [toast, setToast] = useState("");

  useEffect(() => {
    getSources().then(setSources).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    getSkippedUrls({ source_id: sourceFilter || undefined, page, limit: PAGE_SIZE })
      .then((data) => { setItems(data.items); setTotal(data.total); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, sourceFilter]);

  function sourceName(id: string) {
    return sources.find((s) => s.id === id)?.name ?? "Unknown source";
  }

  function notify(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  async function handleRequeue(id: string) {
    setBusy((b) => ({ ...b, [id]: "requeue" }));
    try {
      await removeSkippedUrl(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      setTotal((t) => t - 1);
      notify("URL re-queued — will be picked up on next scrape");
    } catch {
      notify("Failed to re-queue URL");
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[id]; return n; });
    }
  }

  async function handlePermanent(id: string) {
    setBusy((b) => ({ ...b, [id]: "permanent" }));
    try {
      const updated = await markSkippedUrlPermanent(id);
      setItems((prev) => prev.map((i) => i.id === id ? updated : i));
      notify("URL marked as permanently skipped");
    } catch {
      notify("Failed to mark as permanent");
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[id]; return n; });
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Skipped URLs</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} URL{total !== 1 ? "s" : ""} excluded from future scrape runs</p>
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All sources</option>
          {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">{toast}</div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No skipped URLs yet.</div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const { label, detail, color } = parseReason(item.reason);
            const { host, path } = formatUrl(item.url);
            const isBusy = !!busy[item.id];

            return (
              <div
                key={item.id}
                className={`bg-white rounded-xl border shadow-sm px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3 ${item.permanent ? "border-gray-300 opacity-75" : "border-gray-100"}`}
              >
                {/* Title + URL */}
                <div className="flex-1 min-w-0">
                  {detail && (
                    <p className="font-medium text-sm text-gray-800 truncate mb-0.5">{detail}</p>
                  )}
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    title={item.url}
                    className="text-xs text-brand-600 hover:underline flex items-baseline gap-1 min-w-0"
                  >
                    <span className="font-medium shrink-0">{host}</span>
                    <span className="text-gray-400 truncate">{path}</span>
                  </a>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{label}</span>
                    <span className="text-xs text-gray-400">{sourceName(item.source_id)}</span>
                    <span className="text-xs text-gray-400">{new Date(item.skipped_at).toLocaleDateString()}</span>
                    {item.permanent && (
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-800 text-white">Permanent</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 shrink-0">
                  {!item.permanent ? (
                    <>
                      <button
                        onClick={() => handleRequeue(item.id)}
                        disabled={isBusy}
                        className="text-xs px-3 py-1.5 rounded-lg bg-brand-50 text-brand-700 hover:bg-brand-100 font-medium disabled:opacity-50 transition-colors"
                      >
                        {busy[item.id] === "requeue" ? "Re-queuing…" : "Re-queue"}
                      </button>
                      <button
                        onClick={() => handlePermanent(item.id)}
                        disabled={isBusy}
                        className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 font-medium disabled:opacity-50 transition-colors"
                      >
                        {busy[item.id] === "permanent" ? "Saving…" : "Skip Forever"}
                      </button>
                    </>
                  ) : (
                    <span className="text-xs text-gray-400 italic px-1">Permanently ignored</span>
                  )}
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
