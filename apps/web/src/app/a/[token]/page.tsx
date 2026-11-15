import type { Metadata } from "next";
import { ClientAttestation } from "@/components/client/ClientAttestation";

export const metadata: Metadata = {
  title: "Confirmer un chantier · Tekki-Pass",
  // Personal link sent by WhatsApp: keep it out of search engines.
  robots: { index: false, follow: false },
};

export default async function ClientPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return (
    <main>
      <ClientAttestation token={token} />
    </main>
  );
}
