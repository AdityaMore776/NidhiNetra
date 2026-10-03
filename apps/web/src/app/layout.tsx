import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif, Noto_Sans_Devanagari } from "next/font/google";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import { SmoothScroll } from "@/components/motion/SmoothScroll";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Geist carries the interface and every number (tabular figures); Instrument Serif is kept for
// editorial headlines only; Noto Sans Devanagari renders the Hindi reasons; Geist Mono the ids.
const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });
const instrument = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument",
});
const devanagari = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-noto-deva" });

export const metadata: Metadata = {
  title: { default: "NidhiNetra: the eye on every MPLADS rupee", template: "%s · NidhiNetra" },
  description:
    "NidhiNetra checks every MPLADS work on eSAKSHI and ranks the ones an officer should verify first, with the reasons. SIH 2026 · SIH26102 · Team NeuralNexus.",
  applicationName: "NidhiNetra",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={cn("h-full antialiased", geist.variable, geistMono.variable, instrument.variable, devanagari.variable)}
    >
      <body className="min-h-full bg-background font-sans text-foreground">
        <TooltipProvider delayDuration={150}>
          <SmoothScroll>{children}</SmoothScroll>
          <Toaster position="bottom-right" />
        </TooltipProvider>
      </body>
    </html>
  );
}
