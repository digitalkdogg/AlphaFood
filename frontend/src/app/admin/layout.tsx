"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isLoggedIn, clearToken } from "@/lib/auth";
import Link from "next/link";

const NAV_LINKS = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/sources", label: "Sources" },
  { href: "/admin/review", label: "Review Queue" },
  { href: "/admin/published", label: "Published" },
  { href: "/admin/skipped", label: "Skipped URLs" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoggedIn() && pathname !== "/admin/login") {
      router.replace("/admin/login");
    } else {
      setReady(true);
    }
  }, [pathname, router]);

  // Close mobile menu on route change
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  if (!ready) return null;
  if (pathname === "/admin/login") return <>{children}</>;

  function signOut() {
    clearToken();
    router.push("/admin/login");
  }

  function isActive(href: string) {
    if (href === "/admin") return pathname === "/admin";
    return pathname.startsWith(href);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-800 text-white px-4 md:px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="font-bold text-lg shrink-0">🌿 AlphaFood</Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex gap-4 text-sm">
              {NAV_LINKS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`transition-colors ${
                    isActive(href)
                      ? "text-white font-semibold underline underline-offset-4 decoration-brand-400"
                      : "text-brand-100 hover:text-white"
                  }`}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {/* Desktop sign out */}
            <button
              onClick={signOut}
              className="hidden md:block text-sm text-brand-200 hover:text-white"
            >
              Sign Out
            </button>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="md:hidden p-1 rounded text-brand-100 hover:text-white"
              aria-label="Toggle menu"
            >
              {menuOpen ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile dropdown menu */}
        {menuOpen && (
          <nav className="md:hidden mt-3 pt-3 border-t border-brand-700 flex flex-col gap-1">
            {NAV_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive(href)
                    ? "bg-brand-700 text-white font-semibold"
                    : "text-brand-100 hover:bg-brand-700 hover:text-white"
                }`}
              >
                {label}
              </Link>
            ))}
            <button
              onClick={signOut}
              className="mt-1 px-3 py-2.5 rounded-lg text-sm text-left text-brand-300 hover:bg-brand-700 hover:text-white transition-colors"
            >
              Sign Out
            </button>
          </nav>
        )}
      </header>

      <main className="flex-1 bg-gray-50 p-4 md:p-6">{children}</main>
    </div>
  );
}
