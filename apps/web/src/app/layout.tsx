import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DRISHTI — Evidence-based monitoring for MPLADS",
  description:
    "AI agents that check MPLADS works against photos, maps and prices, and rank what officers should verify first. SIH 2026 · SIH26102 · Team NeuralNexus.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
