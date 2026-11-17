/** Typed client for the Tekki-Pass API (through the same-origin /api proxy). */
import { nip98Header } from "./nip98";

export type RequestStatus =
  "awaiting_client" | "awaiting_payment" | "paid" | "published" | "expired";

export interface AttestationRequest {
  token: string;
  status: RequestStatus;
  title: string;
  artisan_pubkey: string;
  amount_sat: number;
  network: string;
  bolt11: string | null;
  payment_hash: string | null;
  invoice_expires_at: string | null;
  event_id: string | null;
}

export interface PublishedAttestation {
  event_id: string;
  title: string;
  payment_hash: string;
  published_at: string;
  event_json: string;
}

export interface Issuer {
  pubkey: string | null;
  network: string;
  /** Public relays where attestations are published (read directly by the public page). */
  relays: string[];
}

/** Error carrying the API's stable `code` (mapped to a French message by lib/messages). */
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

interface CallOptions {
  method?: "POST";
  body?: unknown;
  /** Artisan secret key: when given, the request is signed with NIP-98. */
  signWith?: Uint8Array;
}

async function call<T>(path: string, init?: CallOptions): Promise<T> {
  const method = init?.method ?? "GET";
  // Serialize once: the NIP-98 signature covers these exact bytes.
  const body = init?.body === undefined ? undefined : JSON.stringify(init.body);
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (init?.signWith) {
    headers.authorization = nip98Header(
      init.signWith,
      `${window.location.origin}/api${path}`,
      method,
      body,
    );
  }
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("network", "network error", 0);
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    // FastAPI validation errors (422) return a list; our own errors return {code, message}.
    if (detail && typeof detail === "object" && "code" in detail) {
      const { code, message } = detail as { code: string; message: string };
      throw new ApiError(code, message, response.status);
    }
    throw new ApiError(response.status === 422 ? "invalid_input" : "unknown", "", response.status);
  }
  return data as T;
}

export const api = {
  /** Signed with the artisan key (NIP-98): the API refuses unsigned or foreign requests. */
  createRequest: (artisanPubkey: string, title: string, secretKey: Uint8Array) =>
    call<AttestationRequest>("/attestation-requests", {
      method: "POST",
      body: { artisan_pubkey: artisanPubkey, title },
      signWith: secretKey,
    }),
  getRequest: (token: string) =>
    call<AttestationRequest>(`/attestation-requests/${encodeURIComponent(token)}`),
  confirm: (token: string, clientPhone: string) =>
    call<AttestationRequest>(`/attestation-requests/${encodeURIComponent(token)}/confirm`, {
      method: "POST",
      body: { client_phone: clientPhone },
    }),
  refresh: (token: string) =>
    call<AttestationRequest>(`/attestation-requests/${encodeURIComponent(token)}/refresh`, {
      method: "POST",
    }),
  simulatePayment: (token: string) =>
    call<{ status: "paid" }>(
      `/dev/attestation-requests/${encodeURIComponent(token)}/simulate-payment`,
      { method: "POST" },
    ),
  attestations: (pubkey: string) =>
    call<PublishedAttestation[]>(`/artisans/${encodeURIComponent(pubkey)}/attestations`),
  issuer: () => call<Issuer>("/issuer"),
};
