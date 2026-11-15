/**
 * Independent verification of an attestation in the browser, mirroring the API's
 * verify_attestation (apps/api/app/attestations/nostr.py). The verifier does not have
 * to trust our server: the signature, the issuer key and the proof of payment are
 * all checked here with nostr-tools and @noble/hashes.
 */
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { type Event, verifyEvent } from "nostr-tools";

export const BADGE_IDENTIFIER = "tekki-pass-job";

export type Verification =
  | { ok: true; title: string; network: string; paymentHash: string; issuedAt: Date }
  | { ok: false; reason: string };

const HEX64 = /^[0-9a-f]{64}$/;

function sha256Hex(data: Uint8Array): string {
  return bytesToHex(sha256(data));
}

function singleTags(event: Event): Map<string, string> {
  const tags = new Map<string, string>();
  for (const [name, value] of event.tags) {
    if (name === undefined || value === undefined || name === "t") continue;
    if (tags.has(name)) throw new Error(`duplicate ${name} tag`);
    tags.set(name, value);
  }
  return tags;
}

export function verifyAttestation(eventJson: string, issuerPubkey: string): Verification {
  let event: Event;
  try {
    event = JSON.parse(eventJson) as Event;
  } catch {
    return { ok: false, reason: "Preuve illisible." };
  }
  if (!verifyEvent(event)) return { ok: false, reason: "Signature invalide." };
  if (event.kind !== 8) return { ok: false, reason: "Ce n'est pas une attestation." };
  if (event.pubkey !== issuerPubkey) return { ok: false, reason: "Émetteur inconnu." };

  let tags: Map<string, string>;
  try {
    tags = singleTags(event);
  } catch {
    return { ok: false, reason: "Preuve mal formée." };
  }
  if (tags.get("a") !== `30009:${issuerPubkey}:${BADGE_IDENTIFIER}`) {
    return { ok: false, reason: "Ce n'est pas un badge Tekki-Pass." };
  }

  const artisan = tags.get("p") ?? "";
  const paymentHash = tags.get("payment_hash") ?? "";
  const preimage = tags.get("preimage") ?? "";
  if (![artisan, paymentHash, preimage].every((v) => HEX64.test(v))) {
    return { ok: false, reason: "Preuve mal formée." };
  }
  if (sha256Hex(hexToBytes(preimage)) !== paymentHash) {
    return { ok: false, reason: "Preuve de paiement invalide." };
  }
  const expectedId = sha256Hex(new TextEncoder().encode(`${paymentHash}:${artisan}`));
  if (tags.get("attestation") !== expectedId) {
    return { ok: false, reason: "Preuve réutilisée pour un autre artisan." };
  }
  return {
    ok: true,
    title: event.content,
    network: tags.get("network") ?? "",
    paymentHash,
    issuedAt: new Date(event.created_at * 1000),
  };
}
