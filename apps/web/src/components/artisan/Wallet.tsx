"use client";

import type { BreezSdk } from "@breeztech/breez-sdk-spark/ssr";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Identity } from "@/lib/identity";
import {
  connectWallet,
  fetchWalletConfig,
  savedLightningAddress,
  type WalletConfig,
  type WalletSummary,
  walletSummary,
} from "@/lib/wallet";

type State =
  | { step: "loading" }
  | { step: "disabled" }
  | { step: "closed"; config: WalletConfig }
  | { step: "opening"; config: WalletConfig }
  | { step: "open"; summary: WalletSummary }
  | { step: "error"; config: WalletConfig };

const formatSats = (sats: number) => `${sats.toLocaleString("fr-FR")} sats`;
const formatDate = (seconds: number) =>
  new Date(seconds * 1000).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });

/**
 * The artisan's Lightning wallet: where the clients' payments arrive. Opened on demand,
 * because the first opening downloads the wallet module (about 4 MB).
 */
export function Wallet({
  identity,
  phrase,
  onAddress,
}: {
  identity: Identity;
  phrase: string;
  /** Called with the Lightning address once known, so new requests are paid to it. */
  onAddress: (address: string) => void;
}) {
  const [state, setState] = useState<State>({ step: "loading" });
  const sdk = useRef<BreezSdk | null>(null);
  const address = savedLightningAddress(identity.pubkey);

  useEffect(() => {
    let cancelled = false;
    fetchWalletConfig()
      .then((config) => {
        if (!cancelled)
          setState(config.enabled ? { step: "closed", config } : { step: "disabled" });
      })
      .catch(() => !cancelled && setState({ step: "disabled" }));
    return () => {
      cancelled = true;
      void sdk.current?.disconnect();
    };
  }, []);

  const refresh = useCallback(async () => {
    if (!sdk.current) return;
    const summary = await walletSummary(sdk.current, identity.pubkey);
    onAddress(summary.lightningAddress);
    setState({ step: "open", summary });
  }, [identity.pubkey, onAddress]);

  async function open(config: WalletConfig) {
    setState({ step: "opening", config });
    try {
      sdk.current ??= await connectWallet(phrase, config);
      await sdk.current.addEventListener({
        onEvent: (event) => {
          if (event.type === "paymentSucceeded" || event.type === "synced") void refresh();
        },
      });
      await refresh();
    } catch {
      setState({ step: "error", config });
    }
  }

  if (state.step === "loading") return null;

  if (state.step === "disabled") {
    return (
      <div className="card">
        <h2>Mon portefeuille</h2>
        <p className="muted">
          Le portefeuille Lightning arrive bientôt. Pour l&apos;instant, les paiements de
          démonstration sont simulés.
        </p>
      </div>
    );
  }

  if (state.step === "open") {
    const { summary } = state;
    return (
      <div className="card">
        <h2>Mon portefeuille</h2>
        <p className="balance">{formatSats(summary.balanceSats)}</p>
        <p className="muted">
          Les paiements de tes clients arrivent ici, même si ton téléphone est éteint.
        </p>
        <p>
          Mon adresse : <span className="link-box">{summary.lightningAddress}</span>
        </p>
        {summary.payments.length > 0 && (
          <>
            <h3>Derniers paiements reçus</h3>
            <ul className="payments">
              {summary.payments.map((p) => (
                <li key={p.id}>
                  <span>{formatDate(p.timestamp)}</span> <span>{p.description ?? "Paiement"}</span>{" "}
                  <strong>+{formatSats(p.amountSats)}</strong>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    );
  }

  const busy = state.step === "opening";
  return (
    <div className="card">
      <h2>Mon portefeuille</h2>
      {address ? (
        <p>
          Mon adresse : <span className="link-box">{address}</span>
        </p>
      ) : (
        <p>Ouvre ton portefeuille une première fois pour recevoir les paiements de tes clients.</p>
      )}
      <p className="muted">
        Il est protégé par tes 12 mots : personne d&apos;autre n&apos;y a accès. La première
        ouverture télécharge environ 4 Mo.
      </p>
      {state.step === "error" && (
        <p role="alert" className="error">
          Le portefeuille n&apos;a pas pu s&apos;ouvrir. Vérifie ta connexion puis réessaie.
        </p>
      )}
      <button className="button" onClick={() => open(state.config)} disabled={busy}>
        {busy ? "Ouverture…" : "Ouvrir mon portefeuille"}
      </button>
    </div>
  );
}
