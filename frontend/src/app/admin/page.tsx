"use client";

import { useEffect, useState } from "react";
import { getAdminRecipes, getScrapeRuns, getSources, triggerScrapeAll, ScrapeRun } from "@/lib/api";
import Link from "next/link";

function StatCard({ label, value, href }: { label: string; value: number | string; href?: string }) {
  const content = (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <p className="text-3xl font-bold text-brand-700">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

function statusBadge(status: ScrapeRun["status"]) {
  const map = {
    running: "bg-blue-100 text-blue-800",
    success: "bg-green-100 text-green-800",
    partial: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status]}`}>
      {status}
    </span>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState({ sources: 0, review: 0, published: 0 });
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [scraping, setScraping] = useState(false);
  const [toast, setToast] = useState("");

  async function loadData() {
    const [sourcesData, reviewData, publishedData, runsData] = await Promise.allSettled([
      getSources(),
      getAdminRecipes({ needs_review: true, limit: 1 }),
      getAdminRecipes({ published: true, limit: 1 }),
      getScrapeRuns(),
    ]);
    setStats({
      sources: sourcesData.status === "fulfilled" ? sourcesData.value.length : 0,
      review: reviewData.status === "fulfilled" ? reviewData.value.total : 0,
      published: publishedData.status === "fulfilled" ? publishedData.value.total : 0,
    });
    if (runsData.status === "fulfilled") setRuns(runsData.value.slice(0, 10));
  }

  useEffect(() => { loadData(); }, []);

  async function handleScrapeAll() {
    setScraping(true);
    try {
      await triggerScrapeAll();
      setToast("Scrape started for all active sources");
      setTimeout(() => setToast(""), 4000);
      setTimeout(loadData, 2000);
    } catch {
      setToast("Failed to start scrape");
    } finally {
      setScraping(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl font-bold">Dashboard</h2>
        <button
          onClick={handleScrapeAll}
          disabled={scraping}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50 transition-colors self-start sm:self-auto"
        >
          {scraping ? "Starting…" : "Scrape All Sources"}
        </button>
      </div>

      {toast && (
        <div className="bg-brand-50 border border-brand-200 text-brand-800 text-sm px-4 py-3 rounded-lg">
          {toast}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Active Sources" value={stats.sources} href="/admin/sources" />
        <StatCard label="Needs Review" value={stats.review} href="/admin/review" />
        <StatCard label="Published Recipes" value={stats.published} />
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold">Recent Scrape Runs</h3>
          <button onClick={loadData} className="text-sm text-brand-600 hover:text-brand-800">Refresh</button>
        </div>
        {runs.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-10">No scrape runs yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[480px]">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Started</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-right">Found</th>
                  <th className="px-4 py-2 text-right">Added</th>
                  <th className="px-4 py-2 text-right">Updated</th>
                  <th className="px-4 py-2 text-right">Skipped</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td className="px-4 py-2 text-gray-500 whitespace-nowrap">{new Date(run.started_at).toLocaleString()}</td>
                    <td className="px-4 py-2">{statusBadge(run.status)}</td>
                    <td className="px-4 py-2 text-right">{run.recipes_found}</td>
                    <td className="px-4 py-2 text-right text-green-700">{run.recipes_added}</td>
                    <td className="px-4 py-2 text-right text-blue-700">{run.recipes_updated}</td>
                    <td className="px-4 py-2 text-right text-gray-400">{run.recipes_skipped_non_recipe}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
