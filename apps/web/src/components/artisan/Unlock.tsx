"use client";

import { type FormEvent, useState } from "react";
import { unlockVault, WrongPinError } from "@/lib/vault";
import { Icon } from "../Icon";

/** Unlock the saved profile with the 6-digit PIN. */
export function Unlock({ onUnlocked }: { onUnlocked: (phrase: string) => void }) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      onUnlocked(await unlockVault(pin));
    } catch (e) {
      setError(e instanceof WrongPinError ? "Code incorrect. Réessaie." : "Profil illisible.");
      setPin("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card">
      <div className="center">
        <span className="avatar avatar-center">
          <Icon name="lock" size={28} />
        </span>
      </div>
      <h1 className="center">Mon profil</h1>
      <p className="muted center">Ton profil est protégé sur ce téléphone.</p>
      <label className="field">
        Ton code à 6 chiffres
        <input
          className="pin"
          inputMode="numeric"
          type="password"
          maxLength={6}
          autoFocus
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
        />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button className="button" type="submit" disabled={busy}>
        {busy ? "Ouverture…" : "Ouvrir"}
      </button>
    </form>
  );
}
