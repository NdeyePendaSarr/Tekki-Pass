/**
 * NIP-98 HTTP Auth: the artisan signs each sensitive request with their Nostr key, so
 * nobody can create attestation requests in their name. Mirrors the API's verifier
 * (apps/api/app/auth/nip98.py). Spec: https://github.com/nostr-protocol/nips/blob/master/98.md
 *
 * Signing uses nostr-tools (no home-made crypto). The secret key stays in memory, in
 * the browser: only the signed event leaves the device.
 */
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { finalizeEvent } from "nostr-tools/pure";

export const HTTP_AUTH_KIND = 27235;

/**
 * Build the `Authorization` header value for one request.
 *
 * @param url Absolute URL the browser calls (e.g. https://site/api/attestation-requests).
 * @param body Exact request body: the API hashes the bytes it receives, so the same
 *   string must be both signed and sent.
 */
export function nip98Header(
  secretKey: Uint8Array,
  url: string,
  method: string,
  body?: string,
  now: Date = new Date(),
): string {
  const tags = [
    ["u", url],
    ["method", method.toUpperCase()],
    // Random nonce (allowed by NIP-98): two identical requests in the same second would
    // otherwise produce the same event, and the API would reject the second as a replay.
    ["nonce", bytesToHex(crypto.getRandomValues(new Uint8Array(8)))],
  ];
  if (body) tags.push(["payload", bytesToHex(sha256(new TextEncoder().encode(body)))]);
  const event = finalizeEvent(
    { kind: HTTP_AUTH_KIND, created_at: Math.floor(now.getTime() / 1000), tags, content: "" },
    secretKey,
  );
  // btoa() expects Latin-1: encode the UTF-8 bytes first (the title can contain accents).
  const bytes = new TextEncoder().encode(JSON.stringify(event));
  return `Nostr ${btoa(String.fromCharCode(...bytes))}`;
}
