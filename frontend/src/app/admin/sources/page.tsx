"use client";

import { useEffect, useState } from "react";
import { getSources, createSource, deleteSource, triggerSourceScrape, Source, ScraperType } from "@/lib/api";
import Link from "next/link";

const SCRAPER_LABELS: Record<ScraperType, string> = {
  wordpress: "WordPress",
  generic_rss: "Generic RSS",
  html_sitemap: "HTML / Sitemap",
  single_page: "Single Page",
};

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [form, setForm] = useState({
    name: "",
    url: "",
    scraper_type: "wordpress" as ScraperType,
    active: true,
    frequency_hours: "",
  });

  async function load() {
    setLoading(true);
    try {
      setSources(await getSources());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function notify(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createSource({
        name: form.name,
        url: form.url,
        scraper_type: form.scraper_type,
        active: form.active,
        frequency_hours: form.frequency_hours ? Number(form.frequency_hours) : null,
      });
      notify("Source created");
      setShowForm(false);
      setForm({ name: "", url: "", scraper_type: "wordpress", active: true, frequency_hours: "" });
      load();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : "Failed to create source");
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete "${name}"? This will remove all associated recipes and scrape runs.`)) return;
    try {
      await deleteSource(id);
      notify("Source deleted");
      load();
    } catch {
      notify("Failed to delete source");
    }
  }

  async function handleScrape(id: string) {
    try {
      await triggerSourceScrape(id);
      notify("Scrape started");
    } catch {
      notify("Failed to start scrape");
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Sources</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {showForm ? "Cancel" : "+ Add Source"}
        </button>
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">{toast}</div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-4">
          <h3 className="font-semibold">New Source</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Source Name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. Sage Alpha Gal"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
              <input
                required
                type="url"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="https://example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scraper Type</label>
              <select
                value={form.scraper_type}
                onChange={(e) => setForm({ ...form, scraper_type: e.target.value as ScraperType })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {(Object.keys(SCRAPER_LABELS) as ScraperType[]).map((t) => (
                  <option key={t} value={t}>{SCRAPER_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequency Override (hours)</label>
              <input
                type="number"
                min="1"
                value={form.frequency_hours}
                onChange={(e) => setForm({ ...form, frequency_hours: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="Leave blank for default"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
              className="rounded accent-brand-600"
            />
            Active (include in scheduled scrapes)
          </label>
          <button
            type="submit"
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition-colors"
          >
            Create Source
          </button>
        </form>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading…</div>
      ) : sources.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No sources yet. Add one above.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Last Scraped</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {sources.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3">
                    <Link href={`/admin/sources/${s.id}`} className="font-medium text-brand-700 hover:underline">
                      {s.name}
                    </Link>
                    <p className="text-xs text-gray-400 truncate max-w-xs">{s.url}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{SCRAPER_LABELS[s.scraper_type]}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>
                      {s.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {s.last_scraped_at ? new Date(s.last_scraped_at).toLocaleString() : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right flex gap-2 justify-end">
                    <button
                      onClick={() => handleScrape(s.id)}
                      className="text-xs bg-brand-50 text-brand-700 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Scrape Now
                    </button>
                    <button
                      onClick={() => handleDelete(s.id, s.name)}
                      className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
