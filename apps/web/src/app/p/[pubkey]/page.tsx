import type { Metadata } from "next";
import { PublicProfile } from "@/components/public/PublicProfile";

export const metadata: Metadata = { title: "Historique vérifiable · Tekki-Pass" };

export default async function PublicPage({ params }: { params: Promise<{ pubkey: string }> }) {
  const { pubkey } = await params;
  return (
    <main>
      <PublicProfile pubkey={pubkey.toLowerCase()} />
    </main>
  );
}
