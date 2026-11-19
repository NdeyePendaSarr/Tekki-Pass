"use client";

import { useState, useSyncExternalStore } from "react";
import { type Identity, identityFromPhrase, normalizePhrase } from "@/lib/identity";
import { savedPubkey } from "@/lib/vault";
import { Dashboard } from "./Dashboard";
import { Onboarding } from "./Onboarding";
import { Unlock } from "./Unlock";

// localStorage has no change event within the same tab: re-read on every render is enough.
const noSubscription = () => () => {};

/**
 * Artisan space. The recovery phrase stays in memory only while unlocked; it is
 * never sent to the API (only the public key is).
 */
export function ArtisanApp() {
  // null during server rendering, where localStorage does not exist.
  const hasProfile = useSyncExternalStore(
    noSubscription,
    () => savedPubkey() !== null,
    () => null,
  );
  // The phrase also seeds the Lightning wallet: kept in memory only while unlocked.
  const [session, setSession] = useState<{ identity: Identity; phrase: string } | null>(null);
  const open = (phrase: string) =>
    setSession({ identity: identityFromPhrase(phrase), phrase: normalizePhrase(phrase) });

  if (session) {
    return (
      <Dashboard
        identity={session.identity}
        phrase={session.phrase}
        onLock={() => setSession(null)}
      />
    );
  }
  if (hasProfile === null) return <p>Chargement…</p>;
  return hasProfile ? <Unlock onUnlocked={open} /> : <Onboarding onDone={open} />;
}
