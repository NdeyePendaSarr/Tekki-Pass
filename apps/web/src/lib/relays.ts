/**
 * Read attestations straight from the Nostr relays, so a verifier does not have to
 * trust the Tekki-Pass API: "les preuves survivent à Tekki-Pass". The API list is
 * only a fallback (relays unreachable, slow 3G).
 */
import type { Event } from "nostr-tools/pure";
import { SimplePool } from "nostr-tools/pool";
import type { PublishedAttestation } from "./api";
import { BADGE_IDENTIFIER } from "./verify";

/** Badge awards (NIP-58). */
const AWARD_KIND = 8;
/** Long enough for a 3G phone to get answers, short enough to fall back quickly. */
export const RELAY_TIMEOUT_MS = 5000;

/** Fetch the issuer's badge awards for one artisan from the given relays. */
export async function fetchAwardsFromRelays(
  relays: string[],
  issuerPubkey: string,
  artisanPubkey: string,
  timeoutMs = RELAY_TIMEOUT_MS,
): Promise<Event[]> {
  if (relays.length === 0) return [];
  const pool = new SimplePool();
  try {
    return await pool.querySync(
      relays,
      {
        kinds: [AWARD_KIND],
        authors: [issuerPubkey],
        "#p": [artisanPubkey],
        "#a": [`30009:${issuerPubkey}:${BADGE_IDENTIFIER}`],
      },
      { maxWait: timeoutMs },
    );
  } finally {
    pool.close(relays);
  }
}

/** Where an attestation was found. */
export type Source = "relays" | "api" | "both";

export interface FoundAttestation {
  eventId: string;
  eventJson: string;
  source: Source;
}

/**
 * Merge relay events and the API list, without duplicates. Relay events come first:
 * they are what anyone can fetch without us. Validity is checked afterwards by
 * verifyAttestation, whatever the source.
 */
export function mergeAttestations(
  relayEvents: Event[],
  apiList: PublishedAttestation[],
): FoundAttestation[] {
  const found = new Map<string, FoundAttestation>();
  for (const event of relayEvents) {
    found.set(event.id, { eventId: event.id, eventJson: JSON.stringify(event), source: "relays" });
  }
  for (const item of apiList) {
    const existing = found.get(item.event_id);
    if (existing) existing.source = "both";
    else
      found.set(item.event_id, {
        eventId: item.event_id,
        eventJson: item.event_json,
        source: "api",
      });
  }
  return [...found.values()];
}
