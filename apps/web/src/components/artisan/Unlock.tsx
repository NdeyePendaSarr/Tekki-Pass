"use client";

import { type FormEvent, useState } from "react";
import { unlockVault, WrongPinError } from "@/lib/vault";

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
    <form onSubmit={submit}>
      <h1>Mon profil</h1>
      <label className="field">
        Ton code à 6 chiffres
        <input
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
