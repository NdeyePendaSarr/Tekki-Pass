"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, type AttestationRequest } from "@/lib/api";
import { type Identity, shortNpub } from "@/lib/identity";
import { errorMessage } from "@/lib/messages";
import { clientLink, whatsappLink } from "@/lib/share";
import { fetchWalletConfig, savedLightningAddress } from "@/lib/wallet";
import { Icon } from "../Icon";
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
  // Real payments on (Breez key set): the wallet must be opened once before the first request.
  const [walletEnabled, setWalletEnabled] = useState(false);
  useEffect(() => {
    let active = true;
    fetchWalletConfig()
      .then((config) => active && setWalletEnabled(config.enabled))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

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
  // Real payments go to the artisan's Lightning address: until the wallet has been opened
  // once, opening it is the first thing to do, so it comes first.
  const wallet = <Wallet identity={identity} phrase={phrase} onAddress={onAddress} />;
  const walletFirst = walletEnabled && !lightningAddress;

  return (
    <section>
      <p className="eyebrow">Mon espace artisan</p>
      <h1>Mes chantiers</h1>
      <p className="chip">
        <Icon name="user" size={18} />
        Profil {shortNpub(identity.npub)}
      </p>

      {walletFirst && wallet}

      {created ? (
        <div className="card success">
          <h2>
            <Icon name="check" /> Lien prêt
          </h2>
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
          <p className="muted">Ton client recevra un lien pour confirmer et payer la preuve.</p>
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

      {!walletFirst && wallet}

      <Link className="button secondary" href={`/p/${identity.pubkey}`}>
        <Icon name="qr" /> Voir ma page publique
      </Link>
      <button className="link" onClick={onLock}>
        Verrouiller
      </button>
    </section>
  );
}
