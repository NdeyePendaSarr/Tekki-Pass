/**
 * Artisan identity: one 12-word recovery phrase (BIP-39) from which the Nostr key
 * is derived (NIP-06). The same phrase will seed the Lightning wallet (docs/adr/0005),
 * so the artisan has a single thing to back up. Uses nostr-tools: no home-made crypto.
 */
import { getPublicKey, nip19 } from "nostr-tools";
import { generateSeedWords, privateKeyFromSeedWords, validateWords } from "nostr-tools/nip06";

export interface Identity {
  /** Nostr public key, hex. */
  pubkey: string;
  /** Same key in the human-readable npub form. */
  npub: string;
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
  const pubkey = getPublicKey(privateKeyFromSeedWords(normalizePhrase(phrase)));
  return { pubkey, npub: nip19.npubEncode(pubkey) };
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

/** Short display form, e.g. "npub1abcd…wxyz". */
export function shortNpub(npub: string): string {
  return `${npub.slice(0, 10)}…${npub.slice(-4)}`;
}
