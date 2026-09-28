import type { Metadata } from "next";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "DRISHTI — Risk Intelligence System",
    template: "%s · DRISHTI",
  },
  description:
    "Risk-intelligence platform for MPLADS works. AI agents check works against prices, records, maps and photos and rank what an officer should verify first. SIH 2026 · SIH26102 · Team NeuralNexus.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
