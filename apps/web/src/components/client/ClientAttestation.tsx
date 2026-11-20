"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { QrCode } from "@/components/QrCode";
import { api, type AttestationRequest } from "@/lib/api";
import { errorMessage } from "@/lib/messages";
import { Icon } from "../Icon";
import { Stepper } from "../Stepper";

const POLL_MS = 3000;
const STEPS = ["Confirmer", "Payer", "Preuve publiée"] as const;
const STEP_OF = { awaiting_client: 0, awaiting_payment: 1, paid: 1, published: 3, expired: 1 };

/**
 * QR content for an invoice: upper case is the standard form for BOLT 11 in QR codes. It
 * uses the compact alphanumeric mode, so the code is much less dense and scans easily from
 * a phone screen (version 11 instead of 17 for our invoices).
 */
export function invoiceQrValue(bolt11: string): string {
  return `LIGHTNING:${bolt11.toUpperCase()}`;
}

/**
 * Client page reached from the artisan's WhatsApp link: confirm the job, pay the
 * small fee, and watch the proof being published. No account, no crypto jargon.
 */
export function ClientAttestation({ token }: { token: string }) {
  const [request, setRequest] = useState<AttestationRequest | null>(null);
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyInvoice(bolt11: string) {
    try {
      await navigator.clipboard.writeText(bolt11);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  useEffect(() => {
    api.getRequest(token).then(setRequest, (e: unknown) => setError(errorMessage(e)));
  }, [token]);

  const refresh = useCallback(async () => {
    try {
      setRequest(await api.refresh(token));
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [token]);

  // While waiting for the payment (or for a retry after a relay outage), check regularly.
  const waiting = request?.status === "awaiting_payment" || request?.status === "paid";
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, refresh]);

  async function confirm(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setRequest(await api.confirm(token, phone));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function simulate() {
    setBusy(true);
    try {
      await api.simulatePayment(token);
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (!request) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p>Chargement…</p>
    );
  }

  return (
    <section>
      <Stepper steps={STEPS} current={STEP_OF[request.status]} />
      <p className="eyebrow">Demande de confirmation de chantier</p>
      <h1>{request.title}</h1>

      {request.status === "awaiting_client" && (
        <form onSubmit={confirm} className="card">
          <p>
            L&apos;artisan te demande de confirmer que ce chantier a bien été fait. La preuve coûte{" "}
            <strong className="amount">{request.amount_sat} sats</strong>, payés directement à
            l&apos;artisan.
          </p>
          <label className="field">
            Ton numéro de téléphone
            <input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="77 123 45 67"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </label>
          <p className="muted small">
            <Icon name="lock" size={18} /> Ton numéro n&apos;est jamais publié : seule une empreinte
            protégée est gardée.
          </p>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="button" type="submit" disabled={busy}>
            {busy ? "Envoi…" : "Je confirme le chantier"}
          </button>
        </form>
      )}

      {request.status === "awaiting_payment" && request.bolt11 && (
        <div className="card">
          <h2>Paiement de la preuve</h2>
          <p>
            Montant : <strong className="amount">{request.amount_sat} sats</strong>
          </p>
          <a className="button" href={`lightning:${request.bolt11}`}>
            <Icon name="bolt" /> Ouvrir mon application de paiement
          </a>
          <p className="muted small center">
            Ou scanne ce code depuis ton application Bitcoin Lightning (l&apos;appareil photo seul
            ne suffit pas).
          </p>
          <QrCode value={invoiceQrValue(request.bolt11)} label="Code de paiement" />
          <button
            type="button"
            className="button secondary"
            onClick={() => void copyInvoice(request.bolt11 ?? "")}
          >
            <Icon name="copy" /> {copied ? "Facture copiée ✓" : "Copier la facture"}
          </button>
          <p className="waiting-line" role="status">
            <span className="spinner" aria-hidden="true" /> En attente du paiement…
          </p>
          {request.bolt11.startsWith("lnfake") && (
            <button className="button secondary" onClick={simulate} disabled={busy}>
              Simuler le paiement (démo)
            </button>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </div>
      )}

      {request.status === "paid" && (
        <div className="card">
          <h2>Paiement reçu</h2>
          <p className="waiting-line" role="status">
            <span className="spinner" aria-hidden="true" /> Publication de la preuve en cours…
          </p>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </div>
      )}

      {request.status === "published" && (
        <div className="card success center">
          <span className="success-mark">
            <Icon name="check" size={30} />
          </span>
          <h2>Merci, la preuve est publiée ✓</h2>
          <p>
            Ce chantier fait maintenant partie de l&apos;historique vérifiable de l&apos;artisan.
          </p>
          <Link className="button secondary" href={`/p/${request.artisan_pubkey}`}>
            Voir la page de l&apos;artisan
          </Link>
        </div>
      )}

      {request.status === "expired" && (
        <div className="card">
          <h2>Délai dépassé</h2>
          <p>
            Le paiement n&apos;a pas été reçu à temps. Demande un nouveau lien à l&apos;artisan.
          </p>
        </div>
      )}
    </section>
  );
}
