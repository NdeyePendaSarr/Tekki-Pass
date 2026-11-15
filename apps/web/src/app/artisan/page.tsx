import type { Metadata } from "next";
import { ArtisanApp } from "@/components/artisan/ArtisanApp";

export const metadata: Metadata = { title: "Mon espace artisan · Tekki-Pass" };

export default function ArtisanPage() {
  return (
    <main>
      <ArtisanApp />
    </main>
  );
}
