import Link from "next/link";
import { Icon } from "@/components/Icon";

/** Home: one clear entry point for the artisan. Clients and verifiers arrive by link or QR. */
export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Pour les artisans du bâtiment au Sénégal</p>
        <h1>Tekki-Pass</h1>
        <p className="lead">
          Chaque chantier payé devient une <strong>preuve de travail vérifiable</strong> par tous :
          tes clients, tes futurs clients, ta banque.
        </p>
        <Link className="button" href="/artisan">
          Je suis artisan
        </Link>
      </section>

      <section className="card">
        <h2>Comment ça marche</h2>
        <ol className="steps-list">
          <li>
            <span>
              <strong>Tu décris ton chantier terminé</strong>
              <br />
              <span className="muted">Depuis ton téléphone, en une phrase.</span>
            </span>
          </li>
          <li>
            <span>
              <strong>Ton client le confirme depuis un lien WhatsApp</strong>
              <br />
              <span className="muted">Il paie une petite preuve en Bitcoin (210 sats).</span>
            </span>
          </li>
          <li>
            <span>
              <strong>La preuve est publiée et consultable par QR code</strong>
              <br />
              <span className="muted">N&apos;importe qui peut la vérifier, même sans nous.</span>
            </span>
          </li>
        </ol>
      </section>

      <ul className="trust">
        <li>
          <Icon name="wallet" />
          <span>
            <strong>Ton argent reste à toi.</strong> Le paiement arrive dans ton portefeuille,
            Tekki-Pass ne le garde jamais.
          </span>
        </li>
        <li>
          <Icon name="shield" />
          <span>
            <strong>Des preuves impossibles à inventer.</strong> Chaque chantier est confirmé par le
            client et payé.
          </span>
        </li>
        <li>
          <Icon name="signal" />
          <span>
            <strong>Pensé pour la 3G.</strong> Léger, et ton espace s&apos;ouvre même sans réseau.
          </span>
        </li>
      </ul>
    </main>
  );
}
