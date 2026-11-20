import type { Metadata, Viewport } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/Icon";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tekki-Pass",
  description: "Chaque chantier attesté devient une preuve de travail vérifiable.",
  applicationName: "Tekki-Pass",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f5132",
};

/** Root layout: French first (Wolof planned), mobile-first PWA shell. */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body>
        <header className="topbar">
          <div className="topbar-inner">
            <Link className="brand" href="/" aria-label="Tekki-Pass, accueil">
              <BrandMark />
              <span>Tekki-Pass</span>
            </Link>
            <span className="topbar-tag">Preuves de travail</span>
          </div>
        </header>
        {children}
        <footer className="footer">
          Paiements Bitcoin Lightning · Preuves publiées sur Nostr · Ton argent reste à toi
        </footer>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
