"use client";

import * as nip19 from "nostr-tools/nip19";
import { useEffect, useState, useSyncExternalStore } from "react";
import { QrCode } from "@/components/QrCode";
import { api } from "@/lib/api";
import { shortNpub } from "@/lib/npub";
import { errorMessage } from "@/lib/messages";
import { fetchAwardsFromRelays, type FoundAttestation, mergeAttestations } from "@/lib/relays";
import { type Verification, verifyAttestation } from "@/lib/verify";
import { Icon } from "../Icon";

const noSubscription = () => () => {};

interface Row {
  found: FoundAttestation;
  verification: Verification;
}

/** How the list was obtained, shown to the verifier. */
type Origin = "relays" | "api-only";

/**
 * Public artisan page, opened by scanning the QR code. Attestations are read
 * directly from the Nostr relays (the API is only a fallback), then each one is
 * re-verified in the browser: signature, issuer key and proof of payment.
 */
export function PublicProfile({ pubkey }: { pubkey: string }) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [origin, setOrigin] = useState<Origin | null>(null);
  const [issuer, setIssuer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The URL shown in the QR code; empty during server rendering.
  const pageUrl = useSyncExternalStore(
    noSubscription,
    () => window.location.href,
    () => "",
  );

  useEffect(() => {
    let active = true;
    (async () => {
      const info = await api.issuer();
      if (!info.pubkey) throw new Error("no issuer key");
      const issuerPubkey = info.pubkey;
      const [fromRelays, fromApi] = await Promise.allSettled([
        fetchAwardsFromRelays(info.relays, issuerPubkey, pubkey),
        api.attestations(pubkey),
      ]);
      if (fromRelays.status === "rejected" && fromApi.status === "rejected") throw fromApi.reason;
      const relayEvents = fromRelays.status === "fulfilled" ? fromRelays.value : [];
      const merged = mergeAttestations(
        relayEvents,
        fromApi.status === "fulfilled" ? fromApi.value : [],
      );
      if (!active) return;
      setIssuer(issuerPubkey);
      setOrigin(relayEvents.length > 0 ? "relays" : "api-only");
      setRows(
        merged.map((found) => ({
          found,
          verification: verifyAttestation(found.eventJson, issuerPubkey),
        })),
      );
    })().catch((e: unknown) => active && setError(errorMessage(e)));
    return () => {
      active = false;
    };
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
      <div className="card">
        <div className="profile-head">
          <span className="avatar">
            <Icon name="user" size={30} />
          </span>
          <div>
            <p className="eyebrow">Historique vérifiable</p>
            <h1>Artisan {shortNpub(npub)}</h1>
          </div>
        </div>
        {rows && (
          <p className="stat big">
            <strong>{verified}</strong> chantier{verified > 1 ? "s" : ""} attesté
            {verified > 1 ? "s" : ""} et payé{verified > 1 ? "s" : ""}
          </p>
        )}
      </div>
      {origin === "relays" && (
        <p className="ok small">
          ✓ Preuves lues directement sur le réseau Nostr, sans passer par nous.
        </p>
      )}
      {origin === "api-only" && rows && rows.length > 0 && (
        <p className="muted small">
          Réseau Nostr injoignable pour l&apos;instant : preuves fournies par Tekki-Pass, vérifiées
          sur ce téléphone.
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
        {rows?.map(({ found, verification }) => (
          <li key={found.eventId} className="card">
            <div className="attestation-head">
              {verification.ok ? (
                <span className="success-mark small-mark">
                  <Icon name="check" />
                </span>
              ) : null}
              <div>
                <h2>{verification.ok ? verification.title : "Chantier"}</h2>
                {verification.ok ? (
                  <p className="ok">
                    ✓ Vérifié : confirmé par le client et payé le{" "}
                    {verification.issuedAt.toLocaleDateString("fr-FR")}
                    {verification.network === "testnet" && " (réseau de test)"}
                  </p>
                ) : (
                  <p className="error">✗ Non vérifié : {verification.reason}</p>
                )}
              </div>
            </div>
            <details>
              <summary>Détails techniques</summary>
              <p className="mono">Événement Nostr : {found.eventId}</p>
              {verification.ok && (
                <p className="mono">Hash du paiement : {verification.paymentHash}</p>
              )}
              <p className="mono">
                Source : {found.source === "api" ? "Tekki-Pass" : "relais Nostr"}
              </p>
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
