import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AlphaFood — Alpha-Gal Friendly Recipes",
  description:
    "Find mammal-free recipes aggregated from top alpha-gal syndrome food blogs. Search, filter, and cook safely.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
