"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api, type AttestationRequest } from "@/lib/api";
import { type Identity, shortNpub } from "@/lib/identity";
import { errorMessage } from "@/lib/messages";

const MAX_TITLE = 140;

/** Artisan home: describe a finished job and send the attestation link by WhatsApp. */
export function Dashboard({ identity, onLock }: { identity: Identity; onLock: () => void }) {
  const [title, setTitle] = useState("");
  const [created, setCreated] = useState<AttestationRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setCreated(await api.createRequest(identity.pubkey, title.trim()));
      setTitle("");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const link = created ? `${window.location.origin}/a/${created.token}` : "";
  const whatsapp = created
    ? `https://wa.me/?text=${encodeURIComponent(
        `Bonjour, merci de confirmer le chantier « ${created.title} » sur Tekki-Pass : ${link}`,
      )}`
    : "";

  return (
    <section>
      <h1>Mes chantiers</h1>
      <p className="muted">Profil {shortNpub(identity.npub)}</p>

      {created ? (
        <div className="card">
          <h2>Lien prêt</h2>
          <p>Envoie ce lien à ton client. Il confirmera le chantier et paiera la preuve.</p>
          <a className="button whatsapp" href={whatsapp} target="_blank" rel="noreferrer">
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

      <Link className="button secondary" href={`/p/${identity.pubkey}`}>
        Voir ma page publique
      </Link>
      <button className="link" onClick={onLock}>
        Verrouiller
      </button>
    </section>
  );
}
