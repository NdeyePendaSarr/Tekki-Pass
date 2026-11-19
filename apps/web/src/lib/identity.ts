/**
 * Artisan identity: one 12-word recovery phrase (BIP-39) from which the Nostr key
 * is derived (NIP-06). The same phrase will seed the Lightning wallet (docs/adr/0005),
 * so the artisan has a single thing to back up. Uses nostr-tools: no home-made crypto.
 */
import { npubEncode } from "nostr-tools/nip19";
import { getPublicKey } from "nostr-tools/pure";
import { generateSeedWords, privateKeyFromSeedWords, validateWords } from "nostr-tools/nip06";

export interface Identity {
  /** Nostr public key, hex. */
  pubkey: string;
  /** Same key in the human-readable npub form. */
  npub: string;
  /**
   * Nostr secret key, used only to sign requests (NIP-98). Kept in memory while the
   * profile is unlocked; never stored in clear, never sent anywhere.
   */
  secretKey: Uint8Array;
}

export function newRecoveryPhrase(): string {
  return generateSeedWords();
}

export function isValidRecoveryPhrase(phrase: string): boolean {
  return validateWords(normalizePhrase(phrase));
}

export function normalizePhrase(phrase: string): string {
  return phrase.trim().toLowerCase().split(/\s+/).join(" ");
}

export function identityFromPhrase(phrase: string): Identity {
  const secretKey = privateKeyFromSeedWords(normalizePhrase(phrase));
  const pubkey = getPublicKey(secretKey);
  return { pubkey, npub: npubEncode(pubkey), secretKey };
}

/** Pick `count` distinct word positions (0-based) for the backup check, in ascending order. */
export function pickCheckPositions(wordCount: number, count = 3): number[] {
  const positions = new Set<number>();
  const random = new Uint32Array(1);
  while (positions.size < Math.min(count, wordCount)) {
    crypto.getRandomValues(random);
    positions.add(random[0]! % wordCount);
  }
  return [...positions].sort((a, b) => a - b);
}

export { shortNpub } from "./npub";
