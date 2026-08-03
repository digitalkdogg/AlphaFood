"use client";

import { useEffect, useState } from "react";
import { getSkippedUrls, removeSkippedUrl, getSources, SkippedUrl, Source } from "@/lib/api";

const PAGE_SIZE = 50;

export default function SkippedUrlsPage() {
  const [items, setItems] = useState<SkippedUrl[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<string | null>(null);

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
    return sources.find((s) => s.id === id)?.name ?? id;
  }

  async function handleRemove(id: string) {
    setRemoving(id);
    try {
      await removeSkippedUrl(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      setTotal((t) => t - 1);
    } catch (e) {
      alert("Failed to remove: " + e);
    } finally {
      setRemoving(null);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Skipped URLs</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} URL{total !== 1 ? "s" : ""} marked as non-recipe — removed from future scrape runs.
          </p>
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No skipped URLs yet.</div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">URL</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-64">Reason</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-36">Source</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-28">Skipped</th>
                <th className="px-4 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-600 hover:underline truncate block max-w-xs"
                      title={item.url}
                    >
                      {item.url}
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      item.reason?.startsWith("Not a recipe")
                        ? "bg-yellow-50 text-yellow-700"
                        : item.reason?.startsWith("Ollama")
                        ? "bg-red-50 text-red-700"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      {item.reason ?? "Unknown"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-sm">{sourceName(item.source_id)}</td>
                  <td className="px-4 py-3 text-gray-500 text-sm">
                    {new Date(item.skipped_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRemove(item.id)}
                      disabled={removing === item.id}
                      className="text-xs px-3 py-1 rounded bg-brand-50 text-brand-700 hover:bg-brand-100 disabled:opacity-50"
                    >
                      {removing === item.id ? "Removing…" : "Re-queue"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded border text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
