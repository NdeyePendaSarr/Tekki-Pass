"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useState } from "react";
import { api, type AttestationRequest } from "@/lib/api";
import { type Identity, shortNpub } from "@/lib/identity";
import { errorMessage } from "@/lib/messages";
import { clientLink, whatsappLink } from "@/lib/share";
import { savedLightningAddress } from "@/lib/wallet";
import { MyRequests } from "./MyRequests";
import { Wallet } from "./Wallet";

const MAX_TITLE = 140;

/** Artisan home: describe a finished job, send the link by WhatsApp, follow every request. */
export function Dashboard({
  identity,
  phrase,
  onLock,
}: {
  identity: Identity;
  phrase: string;
  onLock: () => void;
}) {
  const [title, setTitle] = useState("");
  const [created, setCreated] = useState<AttestationRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Bumped after each creation so the list below reloads.
  const [version, setVersion] = useState(0);
  // Where the clients' payments go. Remembered on the phone: no need to load the wallet.
  const [lightningAddress, setLightningAddress] = useState(() =>
    savedLightningAddress(identity.pubkey),
  );
  const onAddress = useCallback((address: string) => setLightningAddress(address), []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setCreated(
        await api.createRequest(
          identity.pubkey,
          title.trim(),
          identity.secretKey,
          lightningAddress,
        ),
      );
      setTitle("");
      setVersion((v) => v + 1);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const link = created ? clientLink(window.location.origin, created.token) : "";

  return (
    <section>
      <h1>Mes chantiers</h1>
      <p className="muted">Profil {shortNpub(identity.npub)}</p>

      {created ? (
        <div className="card">
          <h2>Lien prêt</h2>
          <p>Envoie ce lien à ton client. Il confirmera le chantier et paiera la preuve.</p>
          <a
            className="button whatsapp"
            href={whatsappLink(created.title, link)}
            target="_blank"
            rel="noreferrer"
          >
            Envoyer par WhatsApp
          </a>
          <p className="link-box">{link}</p>
          <button className="link" onClick={() => setCreated(null)}>
            Nouveau chantier
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="card">
          <h2>Nouveau chantier terminé</h2>
          <label className="field">
            Qu&apos;as-tu fait ?
            <input
              placeholder="Ex. Carrelage cuisine, 9 m²"
              maxLength={MAX_TITLE}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="button" type="submit" disabled={busy || !title.trim()}>
            {busy ? "Création…" : "Créer le lien pour le client"}
          </button>
        </form>
      )}

      <MyRequests identity={identity} version={version} />

      <Wallet identity={identity} phrase={phrase} onAddress={onAddress} />

      <Link className="button secondary" href={`/p/${identity.pubkey}`}>
        Voir ma page publique
      </Link>
      <button className="link" onClick={onLock}>
        Verrouiller
      </button>
    </section>
  );
}
