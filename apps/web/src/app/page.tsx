import Link from "next/link";

/** Home: one clear entry point for the artisan. Clients and verifiers arrive by link or QR. */
export default function HomePage() {
  return (
    <main>
      <h1>Tekki-Pass</h1>
      <p>Chaque chantier payé devient une preuve de travail vérifiable par tous.</p>
      <ol className="steps">
        <li>Tu décris ton chantier terminé.</li>
        <li>Ton client le confirme depuis un lien WhatsApp.</li>
        <li>La preuve est publiée et consultable par QR code.</li>
      </ol>
      <Link className="button" href="/artisan">
        Je suis artisan
      </Link>
    </main>
  );
}
