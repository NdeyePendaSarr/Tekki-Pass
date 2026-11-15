"use client";

import { nip19 } from "nostr-tools";
import { useEffect, useState, useSyncExternalStore } from "react";
import { QrCode } from "@/components/QrCode";
import { api, type PublishedAttestation } from "@/lib/api";
import { shortNpub } from "@/lib/identity";
import { errorMessage } from "@/lib/messages";
import { type Verification, verifyAttestation } from "@/lib/verify";

const noSubscription = () => () => {};

interface Row {
  attestation: PublishedAttestation;
  verification: Verification;
}

/**
 * Public artisan page, opened by scanning the QR code. Every attestation is
 * re-verified here in the browser against the issuer key (signature + proof of payment).
 */
export function PublicProfile({ pubkey }: { pubkey: string }) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [issuer, setIssuer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The URL shown in the QR code; empty during server rendering.
  const pageUrl = useSyncExternalStore(
    noSubscription,
    () => window.location.href,
    () => "",
  );

  useEffect(() => {
    Promise.all([api.issuer(), api.attestations(pubkey)])
      .then(([issuerInfo, attestations]) => {
        setIssuer(issuerInfo.pubkey);
        setRows(
          attestations.map((attestation) => ({
            attestation,
            verification: issuerInfo.pubkey
              ? verifyAttestation(attestation.event_json, issuerInfo.pubkey)
              : { ok: false, reason: "Émetteur inconnu." },
          })),
        );
      })
      .catch((e: unknown) => setError(errorMessage(e)));
  }, [pubkey]);

  let npub = "";
  try {
    npub = nip19.npubEncode(pubkey);
  } catch {
    return (
      <p role="alert" className="error">
        Ce profil n&apos;existe pas.
      </p>
    );
  }

  const verified = rows?.filter((r) => r.verification.ok).length ?? 0;

  return (
    <section>
      <p className="muted">Historique vérifiable</p>
      <h1>Artisan {shortNpub(npub)}</h1>
      {rows && (
        <p className="big">
          <strong>{verified}</strong> chantier{verified > 1 ? "s" : ""} attesté
          {verified > 1 ? "s" : ""} et payé{verified > 1 ? "s" : ""}
        </p>
      )}

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!rows && !error && <p>Chargement…</p>}
      {rows?.length === 0 && <p>Aucun chantier attesté pour l&apos;instant.</p>}

      <ul className="attestations">
        {rows?.map(({ attestation, verification }) => (
          <li key={attestation.event_id} className="card">
            <h2>{attestation.title}</h2>
            {verification.ok ? (
              <p className="ok">
                ✓ Vérifié : confirmé par le client et payé le{" "}
                {verification.issuedAt.toLocaleDateString("fr-FR")}
                {verification.network === "testnet" && " (réseau de test)"}
              </p>
            ) : (
              <p className="error">✗ Non vérifié : {verification.reason}</p>
            )}
            <details>
              <summary>Détails techniques</summary>
              <p className="mono">Événement Nostr : {attestation.event_id}</p>
              <p className="mono">Hash du paiement : {attestation.payment_hash}</p>
            </details>
          </li>
        ))}
      </ul>

      {pageUrl && (
        <div className="card center">
          <QrCode value={pageUrl} label="QR code de cette page" />
          <p className="muted small">Scanne ce code pour vérifier cet artisan.</p>
        </div>
      )}
      {issuer && <p className="muted small mono">Clé de l&apos;émetteur : {issuer}</p>}
    </section>
  );
}
