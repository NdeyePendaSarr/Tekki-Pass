"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type AttestationRequest, type RequestStatus } from "@/lib/api";
import type { Identity } from "@/lib/identity";
import { errorMessage } from "@/lib/messages";
import { clientLink, whatsappLink } from "@/lib/share";

/** Plain-French status, and whether the client still has something to do. */
const STATUS: Record<
  RequestStatus,
  { label: string; waitingForClient: boolean; tone: "waiting" | "done" | "late" }
> = {
  awaiting_client: {
    label: "En attente de confirmation du client",
    waitingForClient: true,
    tone: "waiting",
  },
  awaiting_payment: {
    label: "Confirmé, en attente du paiement",
    waitingForClient: true,
    tone: "waiting",
  },
  paid: { label: "Payé, publication de la preuve en cours", waitingForClient: false, tone: "done" },
  published: { label: "✓ Preuve publiée", waitingForClient: false, tone: "done" },
  expired: { label: "Délai dépassé : crée un nouveau lien", waitingForClient: false, tone: "late" },
};

/**
 * The artisan's requests and where each one stands, with a way to resend the link.
 * Refreshes when `version` changes (a new request was just created) or on demand:
 * no automatic polling, to stay light on 3G and under the API rate limit.
 */
export function MyRequests({ identity, version }: { identity: Identity; version: number }) {
  const [requests, setRequests] = useState<AttestationRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRequests(await api.myRequests(identity.pubkey, identity.secretKey));
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [identity]);

  useEffect(() => {
    let active = true;
    api.myRequests(identity.pubkey, identity.secretKey).then(
      (list) => {
        if (!active) return;
        setRequests(list);
        setError(null);
      },
      (e: unknown) => active && setError(errorMessage(e)),
    );
    return () => {
      active = false;
    };
  }, [identity, version]);

  return (
    <section aria-labelledby="my-requests-title">
      <div className="section-title">
        <h2 id="my-requests-title">Mes demandes</h2>
        {requests && requests.length > 0 && (
          <span className="muted">
            {requests.length} chantier{requests.length > 1 ? "s" : ""}
          </span>
        )}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {requests === null && !error && <p>Chargement…</p>}
      {requests?.length === 0 && <p className="muted">Aucune demande pour l&apos;instant.</p>}

      <ul className="attestations">
        {requests?.map((request) => {
          const { label, waitingForClient, tone } = STATUS[request.status];
          const link = clientLink(window.location.origin, request.token);
          return (
            <li key={request.token} className="card">
              <h3>{request.title}</h3>
              <p className={`chip ${tone}`}>{label}</p>
              {waitingForClient && (
                <a
                  className="button whatsapp"
                  href={whatsappLink(request.title, link)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Renvoyer le lien par WhatsApp
                </a>
              )}
            </li>
          );
        })}
      </ul>

      <button className="link" onClick={() => void load()} disabled={loading}>
        {loading ? "Actualisation…" : "Actualiser"}
      </button>
    </section>
  );
}
