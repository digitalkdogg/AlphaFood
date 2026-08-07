"use client";

import { useEffect, useState } from "react";
import { getSources, updateSource, getScrapeRuns, triggerSourceScrape, Source, ScrapeRun, ScraperType } from "@/lib/api";
import { useParams } from "next/navigation";
import Link from "next/link";

const SCRAPER_LABELS: Record<ScraperType, string> = {
  wordpress: "WordPress",
  generic_rss: "Generic RSS",
  html_sitemap: "HTML / Sitemap",
  single_page: "Single Page",
};

function statusBadge(status: ScrapeRun["status"]) {
  const map: Record<string, string> = {
    running: "bg-blue-100 text-blue-800",
    success: "bg-green-100 text-green-800",
    partial: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    cancelled: "bg-gray-100 text-gray-600",
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? "bg-gray-100 text-gray-600"}`}>{status}</span>;
}

export default function SourceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [source, setSource] = useState<Source | null>(null);
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Source>>({});
  const [toast, setToast] = useState("");

  async function load() {
    const [sources, runList] = await Promise.all([getSources(), getScrapeRuns(id)]);
    const s = sources.find((x) => x.id === id);
    if (s) { setSource(s); setForm(s); }
    setRuns(runList);
  }

  useEffect(() => { load(); }, [id]);

  function notify(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  async function handleSave() {
    try {
      await updateSource(id, form);
      notify("Source updated");
      setEditing(false);
      load();
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : "Failed to update");
    }
  }

  async function handleScrape() {
    try {
      await triggerSourceScrape(id);
      notify("Scrape started");
      setTimeout(load, 3000);
    } catch {
      notify("Failed to start scrape");
    }
  }

  if (!source) return <div className="text-center py-12 text-gray-400">Loading…</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin/sources" className="text-sm text-brand-600 hover:underline">← Sources</Link>
        <h2 className="text-xl font-bold">{source.name}</h2>
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">{toast}</div>
      )}

      {/* Source detail card */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        {editing ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
                <input type="url" value={form.url || ""} onChange={(e) => setForm({ ...form, url: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scraper Type</label>
                <select value={form.scraper_type || "wordpress"} onChange={(e) => setForm({ ...form, scraper_type: e.target.value as ScraperType })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                  {(Object.keys(SCRAPER_LABELS) as ScraperType[]).map((t) => (
                    <option key={t} value={t}>{SCRAPER_LABELS[t]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Frequency (hours)</label>
                <input type="number" min="1" value={form.frequency_hours ?? ""} onChange={(e) => setForm({ ...form, frequency_hours: e.target.value ? Number(e.target.value) : null })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  placeholder="Default" />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.active ?? true} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="rounded accent-brand-600" />
              Active
            </label>
            <div className="flex gap-3">
              <button onClick={handleSave} className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">Save</button>
              <button onClick={() => setEditing(false)} className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2">Cancel</button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">URL</p>
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-brand-700 text-sm underline">{source.url}</a>
              </div>
              <div className="flex gap-2">
                <button onClick={handleScrape} className="text-sm bg-brand-50 text-brand-700 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition-colors">Scrape Now</button>
                <button onClick={() => setEditing(true)} className="text-sm bg-gray-50 text-gray-700 hover:bg-gray-100 px-3 py-1.5 rounded-lg transition-colors">Edit</button>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div><p className="text-gray-400 text-xs mb-0.5">Type</p><p>{SCRAPER_LABELS[source.scraper_type]}</p></div>
              <div><p className="text-gray-400 text-xs mb-0.5">Status</p><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${source.active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>{source.active ? "Active" : "Inactive"}</span></div>
              <div><p className="text-gray-400 text-xs mb-0.5">Frequency</p><p>{source.frequency_hours ? `${source.frequency_hours}h` : "Default"}</p></div>
              <div><p className="text-gray-400 text-xs mb-0.5">Last Scraped</p><p>{source.last_scraped_at ? new Date(source.last_scraped_at).toLocaleString() : "Never"}</p></div>
            </div>
          </div>
        )}
      </div>

      {/* Scrape run history */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold">Scrape Run History</h3>
          <button onClick={load} className="text-sm text-brand-600 hover:text-brand-800">Refresh</button>
        </div>
        {runs.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-10">No scrape runs yet for this source.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-2 text-left">Started</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-right">Found</th>
                <th className="px-4 py-2 text-right">Added</th>
                <th className="px-4 py-2 text-right">Skipped</th>
                <th className="px-4 py-2 text-left">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {runs.map((run) => (
                <tr key={run.id}>
                  <td className="px-4 py-2 text-gray-500">{new Date(run.started_at).toLocaleString()}</td>
                  <td className="px-4 py-2">{statusBadge(run.status)}</td>
                  <td className="px-4 py-2 text-right">{run.recipes_found}</td>
                  <td className="px-4 py-2 text-right text-green-700">{run.recipes_added}</td>
                  <td className="px-4 py-2 text-right text-gray-400">{run.recipes_skipped_non_recipe}</td>
                  <td className="px-4 py-2 text-red-600 text-xs max-w-xs truncate">{run.error_message ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
