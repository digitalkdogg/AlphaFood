"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isLoggedIn, clearToken } from "@/lib/auth";
import Link from "next/link";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn() && pathname !== "/admin/login") {
      router.replace("/admin/login");
    } else {
      setReady(true);
    }
  }, [pathname, router]);

  if (!ready) return null;

  if (pathname === "/admin/login") return <>{children}</>;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-800 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-lg">🌿 AlphaFood</Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/admin" className="text-brand-100 hover:text-white transition-colors">Dashboard</Link>
            <Link href="/admin/sources" className="text-brand-100 hover:text-white transition-colors">Sources</Link>
            <Link href="/admin/review" className="text-brand-100 hover:text-white transition-colors">Review Queue</Link>
            <Link href="/admin/skipped" className="text-brand-100 hover:text-white transition-colors">Skipped URLs</Link>
          </nav>
        </div>
        <button
          onClick={() => { clearToken(); router.push("/admin/login"); }}
          className="text-sm text-brand-200 hover:text-white"
        >
          Sign Out
        </button>
      </header>
      <main className="flex-1 bg-gray-50 p-6">{children}</main>
    </div>
  );
}
