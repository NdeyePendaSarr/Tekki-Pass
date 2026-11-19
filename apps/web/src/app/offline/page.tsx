import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Hors connexion · Tekki-Pass" };

/** Shown by the service worker when there is no network and no cached copy of the page. */
export default function OfflinePage() {
  return (
    <main>
      <section className="card">
        <h1>Pas de connexion</h1>
        <p>Cette page a besoin d&apos;internet. Vérifie ton réseau ou ta data, puis réessaie.</p>
        <p className="muted">
          Ton profil et tes 12 mots restent sur ton téléphone : rien n&apos;est perdu.
        </p>
        <Link className="button" href="/artisan">
          Ouvrir mon espace
        </Link>
      </section>
    </main>
  );
}
